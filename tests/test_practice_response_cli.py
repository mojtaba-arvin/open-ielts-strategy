import contextlib
import io
import json
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from open_ielts_strategy.practice_response_cli import main
from open_ielts_strategy.practice_sessions import PracticeSessionStore


def evaluation():
    return {
        "status": "evaluated",
        "next_steps": ["Add a specific example."],
        "strategy_ids_used": ["writing.plan"],
    }


class PracticeResponseCliSessionTests(unittest.TestCase):
    def _run(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), redirect_stderr(output):
            code = main(args)
        return code, output.getvalue()

    def _patch_dependencies(self):
        return (
            patch("open_ielts_strategy.practice_response_cli.load_knowledge_pack",
                  return_value=SimpleNamespace(pack_version="1.0.0")),
            patch("open_ielts_strategy.practice_response_cli.build_consumption_provider",
                  return_value=object()),
            patch("open_ielts_strategy.practice_response_cli.evaluate_published_response",
                  side_effect=lambda *a, **k: evaluation()),
        )

    def test_reuses_existing_session_and_appends_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "practice.sqlite3")
            args = ["--skill", "writing", "--question", "Discuss both views.",
                    "--answer", "First response.", "--model", "local", "--session-db", db]
            with ExitStack() as stack:
                for dependency in self._patch_dependencies():
                    stack.enter_context(dependency)
                code, output = self._run(args)
                self.assertEqual(code, 0)
                first = json.loads(output)
                session_id = first["persistence"]["session_id"]
                self.assertEqual(first["persistence"]["attempt_count"], 1)

                second_args = args.copy()
                second_args[second_args.index("--answer") + 1] = "Second response."
                second_args += ["--session-id", session_id]
                code, output = self._run(second_args)
                self.assertEqual(code, 0)
                second = json.loads(output)
                self.assertEqual(second["persistence"]["session_id"], session_id)
                self.assertEqual(second["persistence"]["attempt_count"], 2)

            with PracticeSessionStore(db) as store:
                session = store.get_session(session_id)
                self.assertEqual([item["answer"] for item in session["attempts"]],
                                 ["First response.", "Second response."])

    def test_rejects_session_with_different_task_or_pack_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "practice.sqlite3")
            args = ["--skill", "writing", "--question", "Discuss both views.",
                    "--answer", "First response.", "--model", "local", "--session-db", db]
            with ExitStack() as stack:
                for dependency in self._patch_dependencies():
                    stack.enter_context(dependency)
                code, output = self._run(args)
                self.assertEqual(code, 0)
                session_id = json.loads(output)["persistence"]["session_id"]
                mismatch = args.copy()
                mismatch[mismatch.index("--question") + 1] = "Describe a process."
                mismatch += ["--session-id", session_id]
                code, error = self._run(mismatch)
                self.assertEqual(code, 2)
                self.assertIn("does not match", error)

            with PracticeSessionStore(db) as store:
                self.assertEqual(store.get_session(session_id)["attempt_count"], 1)

    def test_scope_mismatch_is_rejected_before_evaluator_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "practice.sqlite3")
            with PracticeSessionStore(db) as store:
                session = store.create_session(
                    "Original question", skill="writing", pack_version="1.0.0"
                )
            with patch("open_ielts_strategy.practice_response_cli.load_knowledge_pack",
                       return_value=SimpleNamespace(pack_version="1.0.0")), \
                 patch("open_ielts_strategy.practice_response_cli.build_consumption_provider",
                       return_value=object()), \
                 patch("open_ielts_strategy.practice_response_cli.evaluate_published_response") as evaluate:
                code, error = self._run([
                    "--skill", "writing", "--question", "Different question",
                    "--answer", "Answer", "--model", "local", "--session-db", db,
                    "--session-id", session["id"],
                ])
                self.assertEqual(code, 2)
                self.assertIn("does not match", error)
                evaluate.assert_not_called()

    def test_session_id_requires_session_database(self):
        with ExitStack() as stack:
            for dependency in self._patch_dependencies():
                stack.enter_context(dependency)
            code, error = self._run([
                "--skill", "writing", "--question", "Question", "--answer", "Answer",
                "--model", "local", "--session-id", "existing",
            ])
        self.assertEqual(code, 2)
        self.assertIn("--session-id requires --session-db", error)


if __name__ == "__main__":
    unittest.main()
