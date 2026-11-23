"""Local, explicit persistence for IELTS Practice sessions and reviewable attempts."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path


class PracticeSessionStore:
    """SQLite store; data remains local and is never uploaded by this module."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.path))
        if os.name != "nt":
            os.chmod(self.path, 0o600)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS practice_sessions (
                id TEXT PRIMARY KEY,
                skill TEXT NOT NULL,
                question TEXT NOT NULL,
                pack_version TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS practice_attempts (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE,
                answer TEXT NOT NULL,
                feedback TEXT,
                strategy_ids_json TEXT NOT NULL,
                assessment_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS practice_attempts_session_idx
                ON practice_attempts(session_id, created_at, id);
        """)
        self._connection.commit()

    def close(self):
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def create_session(self, question: str, *, skill: str, pack_version: str) -> dict:
        if not isinstance(question, str) or not question.strip() or len(question) > 4000:
            raise ValueError("question must contain 1..4000 characters")
        if skill not in {"speaking", "writing", "reading", "listening", "general"}:
            raise ValueError("unsupported IELTS skill")
        if not isinstance(pack_version, str) or not pack_version.strip():
            raise ValueError("pack_version must be non-empty text")
        identifier = str(uuid.uuid4())
        with self._connection:
            self._connection.execute(
                "INSERT INTO practice_sessions(id, skill, question, pack_version) VALUES (?, ?, ?, ?)",
                (identifier, skill, question, pack_version),
            )
        return self.get_session(identifier)

    def record_attempt(self, session_id: str, answer: str, *, feedback: str | None = None,
                       strategy_ids=(), assessment: dict | None = None) -> dict:
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 20000:
            raise ValueError("answer must contain 1..20000 characters")
        if feedback is not None and (not isinstance(feedback, str) or len(feedback) > 12000):
            raise ValueError("feedback must be text no longer than 12000 characters")
        if not isinstance(strategy_ids, (list, tuple)) or any(
            not isinstance(value, str) or not value for value in strategy_ids
        ):
            raise ValueError("strategy_ids must contain non-empty strings")
        if len(strategy_ids) != len(set(strategy_ids)):
            raise ValueError("strategy_ids must be unique")
        if assessment is not None and not isinstance(assessment, dict):
            raise ValueError("assessment must be a JSON object")
        assessment_json = json.dumps(assessment, ensure_ascii=False, sort_keys=True) if assessment is not None else None
        identifier = str(uuid.uuid4())
        with self._connection:
            exists = self._connection.execute(
                "SELECT 1 FROM practice_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if exists is None:
                raise KeyError(f"unknown practice session: {session_id}")
            self._connection.execute(
                """INSERT INTO practice_attempts
                   (id, session_id, answer, feedback, strategy_ids_json, assessment_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (identifier, session_id, answer, feedback,
                 json.dumps(list(strategy_ids), ensure_ascii=False), assessment_json),
            )
        return self.get_attempt(identifier)

    def get_attempt(self, attempt_id: str) -> dict:
        row = self._connection.execute(
            "SELECT * FROM practice_attempts WHERE id = ?", (attempt_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown practice attempt: {attempt_id}")
        result = dict(row)
        result["strategy_ids"] = json.loads(result.pop("strategy_ids_json"))
        raw_assessment = result.pop("assessment_json")
        result["assessment"] = json.loads(raw_assessment) if raw_assessment is not None else None
        return result

    def get_session(self, session_id: str) -> dict:
        row = self._connection.execute(
            "SELECT * FROM practice_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown practice session: {session_id}")
        result = dict(row)
        result["attempts"] = [
            self.get_attempt(item["id"])
            for item in self._connection.execute(
                "SELECT id FROM practice_attempts WHERE session_id = ? ORDER BY created_at, id",
                (session_id,),
            ).fetchall()
        ]
        result["attempt_count"] = len(result["attempts"])
        return result
