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
        store._connection.execute(
            """INSERT INTO source_retention(source_id, state, purged_at)
               VALUES (?, 'body_purged', ?) ON CONFLICT(source_id)
               DO UPDATE SET state='body_purged', purged_at=excluded.purged_at""",
            (source_id, _now()),
        )
    return {
        "source_id": source_id,
        "state": "body_purged",
        "semantic_items_retained": len(items),
        "content_sha256_retained": source["content_sha256"],
        "raw_body_retained": False,
        "note": "Exact source text cannot be re-verified after purge; item offsets and original hash remain as provenance metadata.",
    }
