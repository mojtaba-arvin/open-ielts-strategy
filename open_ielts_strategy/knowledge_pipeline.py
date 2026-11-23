"""Persist optional local semantic extraction while preserving source provenance."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from .semantic_extraction import validate_extraction


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_schema(store):
    store._connection.executescript("""
    CREATE TABLE IF NOT EXISTS semantic_extractions (
        extraction_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
        segment_id TEXT NOT NULL REFERENCES segments(segment_id) ON DELETE CASCADE,
        summary TEXT NOT NULL,
        provider_name TEXT NOT NULL,
        model_name TEXT NOT NULL,
        prompt_version TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS semantic_items (
        item_id TEXT PRIMARY KEY,
        extraction_id TEXT NOT NULL REFERENCES semantic_extractions(extraction_id) ON DELETE CASCADE,
        source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
        segment_id TEXT NOT NULL REFERENCES segments(segment_id) ON DELETE CASCADE,
        kind TEXT NOT NULL,
        text TEXT NOT NULL,
        start_char INTEGER NOT NULL,
        end_char INTEGER NOT NULL,
        topic_tags_json TEXT NOT NULL,
        rationale TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'needs_review',
        review_note TEXT NOT NULL DEFAULT ''
    );
    CREATE INDEX IF NOT EXISTS idx_semantic_items_source ON semantic_items(source_id, start_char);
    CREATE TABLE IF NOT EXISTS source_retention (
        source_id TEXT PRIMARY KEY REFERENCES sources(source_id) ON DELETE CASCADE,
        state TEXT NOT NULL CHECK(state IN ('retained', 'body_purged')),
        purged_at TEXT
    );
    """)
    columns = {row["name"] for row in store._connection.execute("PRAGMA table_info(semantic_items)")}
    if "review_note" not in columns:
        store._connection.execute("ALTER TABLE semantic_items ADD COLUMN review_note TEXT NOT NULL DEFAULT ''")
    store._connection.commit()


def persist_segment_extraction(store, source_id: str, segment_id: str, result: dict,
                               *, provider_name: str, model_name: str,
                               prompt_version: str) -> dict:
    """Validate model output against a segment and persist global source offsets."""
    _ensure_schema(store)
    source = store.get_source(source_id, include_body=True)
    segment = next((item for item in source["segments"] if item["segment_id"] == segment_id), None)
    if segment is None:
        raise KeyError(f"segment {segment_id} does not belong to source {source_id}")
    validated = validate_extraction(result, segment["text"])
    for value, name in ((provider_name, "provider_name"), (model_name, "model_name"), (prompt_version, "prompt_version")):
        if not isinstance(value, str) or not value.strip() or len(value) > 200:
            raise ValueError(f"{name} must be 1..200 characters")
    extraction_id = "ext_" + uuid.uuid4().hex
    created_at = _now()
    connection = store._connection
    with connection:
        connection.execute(
            """INSERT INTO semantic_extractions
               (extraction_id, source_id, segment_id, summary, provider_name, model_name, prompt_version, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (extraction_id, source_id, segment_id, validated["summary"], provider_name,
             model_name, prompt_version, created_at),
        )
        item_ids = []
        for item in validated["items"]:
            start = segment["start_char"] + item["start_char"]
            end = segment["start_char"] + item["end_char"]
            if source["body"][start:end] != item["text"]:
                raise ValueError("persisted source offset failed exact-span verification")
            item_id = "sitem_" + uuid.uuid4().hex
            connection.execute(
                """INSERT INTO semantic_items
                   (item_id, extraction_id, source_id, segment_id, kind, text, start_char,
                    end_char, topic_tags_json, rationale, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'needs_review')""",
                (item_id, extraction_id, source_id, segment_id, item["kind"], item["text"],
                 start, end, json.dumps(item["topic_tags"]), item["rationale"]),
            )
            item_ids.append(item_id)
    return {
        "extraction_id": extraction_id, "source_id": source_id, "segment_id": segment_id,
        "item_ids": item_ids, "item_count": len(item_ids), "status": "needs_review",
        "claim_eligible": False, "provider_name": provider_name,
        "model_name": model_name, "prompt_version": prompt_version,
    }


def extract_source(store, source_id: str, provider, *, provider_name: str,
                   model_name: str, prompt_version: str) -> list[dict]:
    """Run an explicitly supplied provider over each segment; never called by ingestion."""
    source = store.get_source(source_id)
    outputs = []
    for segment in source["segments"]:
        result = provider.extract(segment["text"])
        outputs.append(persist_segment_extraction(
            store, source_id, segment["segment_id"], result,
            provider_name=provider_name, model_name=model_name,
            prompt_version=prompt_version,
        ))
    return outputs


def list_semantic_items(store, source_id: str) -> list[dict]:
    source = store._connection.execute("SELECT 1 FROM sources WHERE source_id=?", (source_id,)).fetchone()
    if source is None:
        raise KeyError(f"unknown source_id: {source_id}")
    _ensure_schema(store)
    rows = store._connection.execute(
        """SELECT i.*, e.provider_name, e.model_name, e.prompt_version, e.created_at,
                  COALESCE(r.state, 'retained') AS source_text_state
           FROM semantic_items i JOIN semantic_extractions e ON e.extraction_id=i.extraction_id
           LEFT JOIN source_retention r ON r.source_id=i.source_id
           WHERE i.source_id=? ORDER BY i.start_char, i.item_id""", (source_id,)
    ).fetchall()
    return [
        {**dict(row), "topic_tags": json.loads(row["topic_tags_json"])}
        for row in rows
    ]


def review_semantic_item(store, item_id: str, status: str, note: str = "") -> dict:
    """Human-review one extracted semantic item without changing its source text."""
    allowed = {"needs_review", "supported", "conflicting", "user_approved", "superseded", "rejected"}
    if not isinstance(item_id, str) or not item_id.startswith("sitem_"):
        raise ValueError("item_id must identify a semantic item")
    if status not in allowed:
        raise ValueError("invalid semantic review status")
    if not isinstance(note, str) or len(note) > 4000:
        raise ValueError("review note must be text no longer than 4000 characters")
    _ensure_schema(store)
    with store._connection:
        cursor = store._connection.execute(
            "UPDATE semantic_items SET status=?, review_note=? WHERE item_id=?",
            (status, note, item_id),
        )
        if cursor.rowcount != 1:
            raise KeyError(f"unknown semantic item: {item_id}")
    return {"item_id": item_id, "status": status, "review_note_updated": bool(note)}


def purge_source_text(store, source_id: str, *, confirm: bool = False) -> dict:
    """Permanently clear raw source/segment text while retaining reviewed semantic items and hash."""
    if confirm is not True:
        raise ValueError("raw source purge requires explicit confirmation")
    _ensure_schema(store)
    source = store._connection.execute(
        "SELECT content_sha256, body FROM sources WHERE source_id=?", (source_id,)
    ).fetchone()
    if source is None:
        raise KeyError(f"unknown source_id: {source_id}")
    state = store._connection.execute(
        "SELECT state FROM source_retention WHERE source_id=?", (source_id,)
    ).fetchone()
    if state and state["state"] == "body_purged":
        return {"source_id": source_id, "state": "body_purged", "already_purged": True}
    items = store._connection.execute(
        "SELECT item_id, status FROM semantic_items WHERE source_id=?", (source_id,)
    ).fetchall()
    if not items:
        raise ValueError("cannot purge raw text until semantic extraction items exist")
    pending = [row["item_id"] for row in items if row["status"] == "needs_review"]
    if pending:
        raise ValueError(f"review all semantic items before purging raw text; pending_count={len(pending)}")
    with store._connection:
        # Lexical cards contain entire segments; remove them before clearing segment text.
        store._connection.execute("DELETE FROM knowledge_cards WHERE source_id=?", (source_id,))
        store._connection.execute("UPDATE segments SET text='' WHERE source_id=?", (source_id,))
        store._connection.execute("UPDATE sources SET body='' WHERE source_id=?", (source_id,))
        # Segment-level summaries can also contain source-derived prose; retain only reviewed items.
        store._connection.execute("UPDATE semantic_extractions SET summary='' WHERE source_id=?", (source_id,))
        store._connection.execute(
            """INSERT INTO source_retention(source_id, state, purged_at)
               VALUES (?, 'body_purged', ?) ON CONFLICT(source_id)
               DO UPDATE SET state='body_purged', purged_at=excluded.purged_at""",
            (source_id, _now()),
        )
    # Rebuild SQLite pages after clearing text. This reduces recoverable remnants in the DB file,
    # but cannot erase filesystem snapshots, SSD wear-leveling copies, or external backups.
    store._connection.execute("VACUUM")
    return {
        "source_id": source_id,
        "state": "body_purged",
        "semantic_items_retained": len(items),
        "content_sha256_retained": source["content_sha256"],
        "raw_body_retained": False,
        "note": "Exact source text cannot be re-verified after purge; item offsets and original hash remain as provenance metadata.",
    }


PUBLICATION_REVIEW_STATUSES = {"pending", "approved", "rejected"}
PUBLICATION_RIGHTS_BASES = {
    "self_authored", "permission_confirmed", "public_domain", "independently_authored",
}


def _ensure_publication_schema(store):
    """Create private publication-review metadata without changing content-review state."""
    _ensure_schema(store)
    store._connection.executescript("""
    CREATE TABLE IF NOT EXISTS publication_reviews (
        item_id TEXT PRIMARY KEY REFERENCES semantic_items(item_id) ON DELETE CASCADE,
        publication_status TEXT NOT NULL CHECK(publication_status IN ('pending', 'approved', 'rejected')),
        rights_basis TEXT,
        reviewer TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        reviewed_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_publication_reviews_status
        ON publication_reviews(publication_status);
    """)
    store._connection.commit()


def review_publication_item(store, item_id: str, status: str, *,
                            reviewer: str, rights_basis: str | None = None,
                            note: str = "") -> dict:
    """Record publication permission separately from educational/content approval.

    Rights evidence and reviewer notes remain private SQLite metadata and are never
    copied into the public Knowledge Pack.
    """
    if not isinstance(item_id, str) or not item_id.startswith("sitem_"):
        raise ValueError("item_id must identify a semantic extraction item")
    if status not in PUBLICATION_REVIEW_STATUSES:
        raise ValueError("invalid publication review status")
    if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 200:
        raise ValueError("reviewer must be non-empty text no longer than 200 characters")
    if not isinstance(note, str) or len(note) > 4000:
        raise ValueError("publication review note must be text no longer than 4000 characters")
    if status == "approved" and rights_basis not in PUBLICATION_RIGHTS_BASES:
        raise ValueError("publication approval requires an explicit publishable rights basis")
    if rights_basis is not None and rights_basis not in PUBLICATION_RIGHTS_BASES:
        raise ValueError("unsupported publication rights basis")
    _ensure_publication_schema(store)
    item = store._connection.execute(
        "SELECT status FROM semantic_items WHERE item_id=?", (item_id,)
    ).fetchone()
    if item is None:
        raise KeyError(f"unknown semantic item: {item_id}")
    if status == "approved" and item["status"] not in {"user_approved", "supported"}:
        raise ValueError("content approval must be completed before publication approval")
    reviewed_at = _now()
    with store._connection:
        store._connection.execute(
            """INSERT INTO publication_reviews
               (item_id, publication_status, rights_basis, reviewer, note, reviewed_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(item_id) DO UPDATE SET
                 publication_status=excluded.publication_status,
                 rights_basis=excluded.rights_basis,
                 reviewer=excluded.reviewer,
                 note=excluded.note,
                 reviewed_at=excluded.reviewed_at""",
            (item_id, status, rights_basis, reviewer.strip(), note, reviewed_at),
        )
    return {
        "item_id": item_id,
        "content_status": item["status"],
        "publication_status": status,
        "rights_basis": rights_basis,
        "reviewer": reviewer.strip(),
        "reviewed_at": reviewed_at,
        "private_note_stored": bool(note),
    }


def get_publication_review(store, item_id: str) -> dict:
    _ensure_publication_schema(store)
    row = store._connection.execute(
        """SELECT item_id, publication_status, rights_basis, reviewer, note, reviewed_at
           FROM publication_reviews WHERE item_id=?""",
        (item_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"no publication review exists for semantic item: {item_id}")
    return dict(row)


def assert_items_publishable(store, item_ids: list[str]) -> list[dict]:
    """Fail closed unless every source-derived item has both approvals and rights basis."""
    if not isinstance(item_ids, list) or not item_ids or any(not isinstance(x, str) for x in item_ids):
        raise ValueError("item_ids must be a non-empty list of semantic item IDs")
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("item_ids must be unique")
    _ensure_publication_schema(store)
    approved = []
    for item_id in item_ids:
        row = store._connection.execute(
            """SELECT i.item_id, i.status AS content_status,
                      p.publication_status, p.rights_basis, p.reviewer, p.reviewed_at
               FROM semantic_items i
               LEFT JOIN publication_reviews p ON p.item_id=i.item_id
               WHERE i.item_id=?""",
            (item_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown semantic item: {item_id}")
        if row["content_status"] not in {"user_approved", "supported"}:
            raise ValueError(f"content approval is missing for semantic item: {item_id}")
        if row["publication_status"] != "approved":
            raise ValueError(f"publication approval is missing for semantic item: {item_id}")
        if row["rights_basis"] not in PUBLICATION_RIGHTS_BASES:
            raise ValueError(f"publishable rights basis is missing for semantic item: {item_id}")
        approved.append(dict(row))
    return approved
