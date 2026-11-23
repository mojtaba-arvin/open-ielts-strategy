import tempfile
import unittest
from pathlib import Path
from open_ielts_strategy.learner_state import LearnerStateStore


class LearnerStateTests(unittest.TestCase):
    def test_study_state_is_persistent_and_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            with LearnerStateStore(path) as store:
                self.assertTrue(store.mark_path_completed("a", "1.0", "speaking.basics"))
                self.assertFalse(store.mark_path_completed("a", "1.0", "speaking.basics"))
                self.assertEqual(store.completed_paths("a", "1.0"), {"speaking.basics"})
                self.assertEqual(store.completed_paths("b", "1.0"), set())
                self.assertEqual(store.completed_paths("a", "2.0"), set())
            with LearnerStateStore(path) as reopened:
                self.assertEqual(reopened.completed_paths("a", "1.0"), {"speaking.basics"})

    def test_mentor_history_is_scoped_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp, LearnerStateStore(Path(tmp) / "state.sqlite3") as store:
            for i in range(8):
                store.append_mentor_turn("a", "1.0", "writing.plan", f"Q{i}", f"A{i}")
            self.assertEqual([x["content"] for x in store.mentor_history("a", "1.0", "writing.plan", 4)],
                             ["Q6", "A6", "Q7", "A7"])
            self.assertEqual(store.mentor_history("b", "1.0", "writing.plan"), [])
            self.assertEqual(store.mentor_history("a", "2.0", "writing.plan"), [])
            self.assertEqual(store.mentor_history("a", "1.0", "speaking.plan"), [])

    def test_invalid_learner_scope_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, LearnerStateStore(Path(tmp) / "s.db") as store:
            with self.assertRaises(ValueError):
                store.completed_paths("", "1.0")


if __name__ == "__main__":
    unittest.main()
