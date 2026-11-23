import os
import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.practice_sessions import PracticeSessionStore


class PracticeSessionStoreTests(unittest.TestCase):
    def test_session_attempts_persist_and_are_retrievable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "local" / "practice.sqlite3"
            with PracticeSessionStore(path) as store:
                session = store.create_session("Describe a place you like.", skill="speaking", pack_version="1.0.0")
                attempt = store.record_attempt(
                    session["id"], "I like the park because...", feedback="Add a specific detail.",
                    strategy_ids=["speaking.answer-development"], assessment={"review_status": "pending"},
                )
                self.assertEqual(attempt["assessment"]["review_status"], "pending")
                self.assertEqual(store.get_session(session["id"])["attempt_count"], 1)
                if os.name != "nt":
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with PracticeSessionStore(path) as reopened:
                self.assertEqual(reopened.get_session(session["id"])["attempts"][0]["answer"],
                                 "I like the park because...")

    def test_rejects_unknown_session_and_duplicate_attribution(self):
        with tempfile.TemporaryDirectory() as tmp, PracticeSessionStore(Path(tmp) / "p.sqlite3") as store:
            with self.assertRaises(KeyError):
                store.record_attempt("missing", "answer")
            session = store.create_session("Question", skill="writing", pack_version="1.0.0")
            with self.assertRaises(ValueError):
                store.record_attempt(session["id"], "answer", strategy_ids=["x", "x"])

    def test_no_assessment_is_not_misrepresented_as_a_score(self):
        with tempfile.TemporaryDirectory() as tmp, PracticeSessionStore(Path(tmp) / "p.sqlite3") as store:
            session = store.create_session("Question", skill="reading", pack_version="1.0.0")
            attempt = store.record_attempt(session["id"], "answer")
            self.assertIsNone(attempt["assessment"])


if __name__ == "__main__":
    unittest.main()
