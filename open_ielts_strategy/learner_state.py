"""Private learner-scoped SQLite persistence for Study and Mentor."""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path


class LearnerStateStore:
    """Persist explicit learner actions locally; never infer mastery or share state."""
    def __init__(self, path):
        raw = str(path)
        if not raw:
            raise ValueError("database path must be non-empty")
        self.path = raw if raw == ":memory:" else str(Path(raw).expanduser())
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS study_completions (
                learner_id TEXT NOT NULL, pack_version TEXT NOT NULL,
                path_id TEXT NOT NULL, completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (learner_id, pack_version, path_id)
            );
            CREATE TABLE IF NOT EXISTS mentor_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT, learner_id TEXT NOT NULL,
                pack_version TEXT NOT NULL, strategy_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('learner','mentor')),
                content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS mentor_turn_scope_idx
                ON mentor_turns(learner_id, pack_version, strategy_id, id);
        """)
        self.connection.commit()
        if self.path != ":memory:" and os.name != "nt":
            os.chmod(self.path, 0o600)

    @staticmethod
    def _check(value, name, maximum=160):
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise ValueError(f"{name} must contain 1..{maximum} characters")
        return value.strip()

    def completed_paths(self, learner_id, pack_version):
        learner_id = self._check(learner_id, "learner_id")
        pack_version = self._check(pack_version, "pack_version")
        rows = self.connection.execute(
            "SELECT path_id FROM study_completions WHERE learner_id=? AND pack_version=?",
            (learner_id, pack_version)).fetchall()
        return {row["path_id"] for row in rows}

    def mark_path_completed(self, learner_id, pack_version, path_id):
        values = (self._check(learner_id, "learner_id"),
                  self._check(pack_version, "pack_version"),
                  self._check(path_id, "path_id"))
        with self.connection:
            cursor = self.connection.execute(
                "INSERT OR IGNORE INTO study_completions(learner_id,pack_version,path_id) VALUES(?,?,?)",
                values)
        return cursor.rowcount == 1

    def mentor_history(self, learner_id, pack_version, strategy_id, limit=12):
        learner_id = self._check(learner_id, "learner_id")
        pack_version = self._check(pack_version, "pack_version")
        strategy_id = self._check(strategy_id, "strategy_id")
        if type(limit) is not int or not 2 <= limit <= 24:
            raise ValueError("limit must be between 2 and 24")
        rows = self.connection.execute(
            """SELECT role,content FROM mentor_turns
               WHERE learner_id=? AND pack_version=? AND strategy_id=?
               ORDER BY id DESC LIMIT ?""",
            (learner_id, pack_version, strategy_id, limit)).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def append_mentor_turn(self, learner_id, pack_version, strategy_id, learner_message, mentor_answer):
        values = (self._check(learner_id, "learner_id"),
                  self._check(pack_version, "pack_version"),
                  self._check(strategy_id, "strategy_id"),
                  self._check(learner_message, "learner_message", 2000),
                  self._check(mentor_answer, "mentor_answer", 12000))
        with self.connection:
            self.connection.executemany(
                """INSERT INTO mentor_turns(learner_id,pack_version,strategy_id,role,content)
                   VALUES(?,?,?,?,?)""",
                [(values[0], values[1], values[2], "learner", values[3]),
                 (values[0], values[1], values[2], "mentor", values[4])])

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
