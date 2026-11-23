"""Private, offline SQLite store for IELTS learning sources and derived notes."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .knowledge_extraction import classify_segment

DEFAULT_DB_PATH = ".local/knowledge.sqlite3"
MAX_SOURCE_CHARS = 5_000_000
MAX_SEGMENT_CHARS = 2_400
SOURCE_TYPES = {
    "podcast_transcript", "video_transcript", "personal_notes", "book_excerpt",
    "article", "lecture_notes", "web_article", "other",
}
RIGHTS_STATUSES = {
    "self_authored", "permission_confirmed", "public_domain",
    "personal_copy_unverified", "unknown",
}
CARD_STATUSES = {
    "needs_review", "supported", "conflicting", "user_approved",
    "superseded", "rejected",
}
RELATION_TYPES = {"related_to", "supports", "contradicts", "duplicates", "supersedes"}
TIMESTAMP_RE = re.compile(r"^\s*[\[(]?((?:\d{1,2}:)?\d{1,2}:\d{2})[\])]?(?:\s+|$)")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _validate_published_at(value):
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("published_at must be an ISO date or timezone-aware timestamp")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("published_at must be an ISO date or timezone-aware timestamp") from exc
        return value
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("published_at must be an ISO date or timezone-aware timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("published_at timestamp must include a timezone")
    return value


def _validate_source_url(value):
    if value is None or value == "":
        return None
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("source_url must be HTTPS text no longer than 2048 characters")
    try:
        parsed = urlparse(value)
        valid = parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("source_url must be HTTPS without embedded credentials")
    return value


def _split_long_span(text: str, start: int, end: int, max_chars: int):
    """Yield trimmed source offsets while preferring sentence and whitespace boundaries."""
    cursor = start
    while end - cursor > max_chars:
        window_end = cursor + max_chars
        window = text[cursor:window_end + 1]
        boundaries = list(re.finditer(r"(?<=[.!?؟。！？])\s+", window))
        if boundaries:
            cut = cursor + boundaries[-1].end()
        else:
            whitespace = text.rfind(" ", cursor, window_end)
            newline = text.rfind("\n", cursor, window_end)
            cut = max(whitespace, newline)
            if cut <= cursor:
                cut = window_end
        chunk_start = cursor
        chunk_end = cut
        while chunk_start < chunk_end and text[chunk_start].isspace():
            chunk_start += 1
        while chunk_end > chunk_start and text[chunk_end - 1].isspace():
            chunk_end -= 1
        if chunk_end > chunk_start:
            yield chunk_start, chunk_end
        cursor = cut
        while cursor < end and text[cursor].isspace():
            cursor += 1
    chunk_start = cursor
    chunk_end = end
    while chunk_start < chunk_end and text[chunk_start].isspace():
        chunk_start += 1
    while chunk_end > chunk_start and text[chunk_end - 1].isspace():
        chunk_end -= 1
    if chunk_end > chunk_start:
        yield chunk_start, chunk_end


def segment_text(text: str, max_chars: int = MAX_SEGMENT_CHARS) -> list[dict]:
    """Split text on paragraph boundaries, retaining exact character offsets."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("source text must be non-empty text")
    if type(max_chars) is not int or max_chars < 200:
        raise ValueError("max_chars must be an integer of at least 200")

    spans = []
    paragraph_matches = re.finditer(r"\S.*?(?=\n[ \t]*\n|\Z)", text, re.DOTALL)
    for paragraph_number, match in enumerate(paragraph_matches, start=1):
        spans.extend(_split_long_span(text, match.start(), match.end(), max_chars))

    segments = []
    for ordinal, (start, end) in enumerate(spans, start=1):
        passage = text[start:end]
        timestamp_match = TIMESTAMP_RE.match(passage)
        locator = {"paragraph": ordinal}
        if timestamp_match:
            locator["timestamp"] = timestamp_match.group(1)
        segments.append({
            "ordinal": ordinal,
            "start_char": start,
            "end_char": end,
            "locator": locator,
            "text": passage,
        })
    return segments


class KnowledgeStore:
    """Local SQLite knowledge base; source text is never uploaded by this package."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            path = Path(self.db_path).expanduser()
            parent_existed = path.parent.exists()
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if not parent_existed:
                try:
                    path.parent.chmod(0o700)
                except OSError:
                    pass
            self.db_path = str(path)
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._initialize()
        self._secure_database_file()

    def _secure_database_file(self):
        if self.db_path == ":memory:":
            return
        try:
            Path(self.db_path).chmod(0o600)
        except OSError:
            pass

    def _initialize(self):
        version = self._connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            raise RuntimeError(f"unsupported knowledge database version: {version}")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                author TEXT,
                source_url TEXT,
                published_at TEXT,
                language TEXT,
                user_notes TEXT,
                rights_status TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                body TEXT NOT NULL,
                captured_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sources_hash ON sources(content_sha256);
            CREATE TABLE IF NOT EXISTS segments (
                segment_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
                ordinal INTEGER NOT NULL,
                start_char INTEGER NOT NULL,
                end_char INTEGER NOT NULL,
                locator_json TEXT NOT NULL,
                text TEXT NOT NULL,
                UNIQUE(source_id, ordinal)
            );
            CREATE TABLE IF NOT EXISTS knowledge_cards (
                card_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
                segment_id TEXT NOT NULL UNIQUE REFERENCES segments(segment_id) ON DELETE CASCADE,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                topic_tags_json TEXT NOT NULL,
                status TEXT NOT NULL,
                review_reason TEXT NOT NULL,
                review_note TEXT NOT NULL DEFAULT '',
                extraction_method TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_cards_status ON knowledge_cards(status);
            CREATE TABLE IF NOT EXISTS card_relations (
                relation_id TEXT PRIMARY KEY,
                from_card_id TEXT NOT NULL REFERENCES knowledge_cards(card_id) ON DELETE CASCADE,
                to_card_id TEXT NOT NULL REFERENCES knowledge_cards(card_id) ON DELETE CASCADE,
                relation_type TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(from_card_id, to_card_id, relation_type)
            );
            """
        )
        self._connection.execute("PRAGMA user_version = 1")
        self._connection.commit()

    def close(self):
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def ingest_text(
        self,
        text: str,
        *,
        title: str | None = None,
        source_type: str = "other",
        author: str | None = None,
        source_url: str | None = None,
        published_at: str | None = None,
        language: str | None = None,
        notes: str | None = None,
        rights_status: str = "unknown",
        max_segment_chars: int = MAX_SEGMENT_CHARS,
    ) -> dict:
        """Persist exact source text, source-linked segments, and reviewable candidate cards."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("source text must be non-empty text")
        if len(text) > MAX_SOURCE_CHARS:
            raise ValueError(f"source text exceeds {MAX_SOURCE_CHARS} characters")
        if "\x00" in text:
            raise ValueError("source text must not contain NUL characters")
        if not isinstance(source_type, str) or source_type not in SOURCE_TYPES:
            raise ValueError(f"source_type must be one of: {', '.join(sorted(SOURCE_TYPES))}")
        if not isinstance(rights_status, str) or rights_status not in RIGHTS_STATUSES:
            raise ValueError(f"rights_status must be one of: {', '.join(sorted(RIGHTS_STATUSES))}")
        if title is not None and (not isinstance(title, str) or not title.strip() or len(title) > 300):
            raise ValueError("title must be non-empty text no longer than 300 characters")
        if author is not None and (not isinstance(author, str) or len(author) > 300):
            raise ValueError("author must be text no longer than 300 characters")
        if language is not None and (not isinstance(language, str) or len(language) > 64):
            raise ValueError("language must be text no longer than 64 characters")
        if notes is not None and (not isinstance(notes, str) or len(notes) > 4000):
            raise ValueError("notes must be text no longer than 4000 characters")

        source_url = _validate_source_url(source_url)
        published_at = _validate_published_at(published_at)
        resolved_title = title.strip() if title else " ".join(text.strip().split())[:100]
        resolved_language = language.strip() if language else None
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

        duplicate = self._connection.execute(
            "SELECT source_id FROM sources WHERE content_sha256 = ? AND source_url IS ? LIMIT 1",
            (digest, source_url),
        ).fetchone()
        if duplicate:
            return {
                "source_id": duplicate["source_id"],
                "duplicate": True,
                "content_sha256": digest,
                "segment_count": self._connection.execute(
                    "SELECT COUNT(*) FROM segments WHERE source_id = ?", (duplicate["source_id"],)
                ).fetchone()[0],
            }

        segments = segment_text(text, max_segment_chars)
        source_id = "src_" + uuid.uuid4().hex
        captured_at = _utc_now()
        try:
            with self._connection:
                self._connection.execute(
                    """INSERT INTO sources (
                        source_id, title, source_type, author, source_url, published_at,
                        language, user_notes, rights_status, content_sha256, body, captured_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source_id, resolved_title, source_type, author, source_url, published_at,
                     resolved_language, notes, rights_status, digest, text, captured_at),
                )
                for segment in segments:
                    segment_id = "seg_" + uuid.uuid4().hex
                    card_id = "card_" + uuid.uuid4().hex
                    analysis = classify_segment(segment["text"])
                    self._connection.execute(
                        """INSERT INTO segments (
                            segment_id, source_id, ordinal, start_char, end_char, locator_json, text
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (segment_id, source_id, segment["ordinal"], segment["start_char"],
                         segment["end_char"], json.dumps(segment["locator"], ensure_ascii=False),
                         segment["text"]),
                    )
                    self._connection.execute(
                        """INSERT INTO knowledge_cards (
                            card_id, source_id, segment_id, kind, title, topic_tags_json,
                            status, review_reason, extraction_method, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (card_id, source_id, segment_id, analysis["kind"], analysis["title"],
                         json.dumps(analysis["topic_tags"]), analysis["status"],
                         analysis["review_reason"], analysis["extraction_method"],
                         captured_at, captured_at),
                    )
        except sqlite3.Error:
            self._connection.rollback()
            raise
        self._secure_database_file()
        return {
            "source_id": source_id,
            "duplicate": False,
            "content_sha256": digest,
            "segment_count": len(segments),
            "candidate_count": len(segments),
            "rights_status": rights_status,
            "storage": "local-private",
        }

    def list_sources(self, limit: int = 50) -> list[dict]:
        if type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        rows = self._connection.execute(
            """SELECT s.source_id, s.title, s.source_type, s.author, s.source_url,
                      s.published_at, s.language, s.rights_status, s.content_sha256,
                      s.captured_at, COUNT(g.segment_id) AS segment_count
               FROM sources s LEFT JOIN segments g ON g.source_id = s.source_id
               GROUP BY s.source_id ORDER BY s.captured_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_source(self, source_id: str, include_body: bool = False) -> dict:
        row = self._connection.execute(
            "SELECT * FROM sources WHERE source_id = ?", (source_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown source_id: {source_id}")
        source = dict(row)
        if not include_body:
            source.pop("body", None)
        segments = self._connection.execute(
            """SELECT g.segment_id, g.ordinal, g.start_char, g.end_char, g.locator_json,
                      g.text, c.card_id, c.kind, c.title, c.topic_tags_json,
                      c.status, c.review_reason, c.review_note, c.extraction_method
               FROM segments g JOIN knowledge_cards c ON c.segment_id = g.segment_id
               WHERE g.source_id = ? ORDER BY g.ordinal""",
            (source_id,),
        ).fetchall()
        source["segments"] = [
            {
                **dict(item),
                "locator": json.loads(item["locator_json"]),
                "topic_tags": json.loads(item["topic_tags_json"]),
            }
            for item in segments
        ]
        return source

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        status: str | None = None,
        topic: str | None = None,
    ) -> list[dict]:
        """Rank local source passages lexically; all results retain precise source anchors."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be non-empty text")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if status is not None and status not in CARD_STATUSES:
            raise ValueError("invalid card status")
        if topic is not None and (not isinstance(topic, str) or not topic.strip()):
            raise ValueError("topic must be non-empty text")

        terms = list(dict.fromkeys(re.findall(r"[^\W_]+", query.casefold(), flags=re.UNICODE)))
        if not terms:
            raise ValueError("query must contain searchable terms")
        sql = """SELECT c.card_id, c.kind, c.title, c.topic_tags_json, c.status,
                        c.review_reason, c.review_note, g.text, g.ordinal, g.start_char,
                        g.end_char, g.locator_json, s.source_id, s.title AS source_title,
                        s.source_type, s.author, s.source_url, s.rights_status
                 FROM knowledge_cards c
                 JOIN segments g ON g.segment_id = c.segment_id
                 JOIN sources s ON s.source_id = c.source_id"""
        clauses, params = [], []
        if status:
            clauses.append("c.status = ?")
            params.append(status)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        rows = self._connection.execute(sql, params).fetchall()

        results = []
        phrase = " ".join(query.casefold().split())
        for row in rows:
            tags = json.loads(row["topic_tags_json"])
            if topic and topic not in tags:
                continue
            haystack = " ".join((row["title"], row["text"], *tags)).casefold()
            matched = [term for term in terms if term in haystack]
            if not matched:
                continue
            score = sum(haystack.count(term) for term in terms)
            if phrase in haystack:
                score += 3
            results.append({
                "score": score,
                "card_id": row["card_id"],
                "kind": row["kind"],
                "title": row["title"],
                "topic_tags": tags,
                "status": row["status"],
                "review_reason": row["review_reason"],
                "review_note": row["review_note"],
                "excerpt": row["text"][:600],
                "source_id": row["source_id"],
                "source_title": row["source_title"],
                "source_type": row["source_type"],
                "author": row["author"],
                "source_url": row["source_url"],
                "rights_status": row["rights_status"],
                "ordinal": row["ordinal"],
                "start_char": row["start_char"],
                "end_char": row["end_char"],
                "locator": json.loads(row["locator_json"]),
            })
        results.sort(key=lambda item: (-item["score"], item["source_id"], item["ordinal"]))
        return results[:limit]

    def review_card(self, card_id: str, status: str, note: str = "") -> dict:
        if status not in CARD_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(CARD_STATUSES))}")
        if not isinstance(note, str) or len(note) > 4000:
            raise ValueError("review note must be text no longer than 4000 characters")
        now = _utc_now()
        cursor = self._connection.execute(
            "UPDATE knowledge_cards SET status = ?, review_note = ?, updated_at = ? WHERE card_id = ?",
            (status, note, now, card_id),
        )
        self._connection.commit()
        if cursor.rowcount != 1:
            raise KeyError(f"unknown card_id: {card_id}")
        return {"card_id": card_id, "status": status, "review_note": note, "updated_at": now}

    def link_cards(self, from_card_id: str, to_card_id: str, relation_type: str, note: str = "") -> dict:
        if relation_type not in RELATION_TYPES:
            raise ValueError(f"relation_type must be one of: {', '.join(sorted(RELATION_TYPES))}")
        if from_card_id == to_card_id:
            raise ValueError("a card cannot be related to itself")
        if not isinstance(note, str) or len(note) > 4000:
            raise ValueError("relation note must be text no longer than 4000 characters")
        relation_id = "rel_" + uuid.uuid4().hex
        try:
            with self._connection:
                self._connection.execute(
                    """INSERT INTO card_relations (
                        relation_id, from_card_id, to_card_id, relation_type, note, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)""",
                    (relation_id, from_card_id, to_card_id, relation_type, note, _utc_now()),
                )
        except sqlite3.IntegrityError as exc:
            if "FOREIGN KEY" in str(exc):
                raise KeyError("both card IDs must exist") from exc
            raise ValueError("this card relation already exists") from exc
        return {
            "relation_id": relation_id, "from_card_id": from_card_id,
            "to_card_id": to_card_id, "relation_type": relation_type, "note": note,
        }
