import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from open_ielts_strategy.product_cli import main


class ProductCliTests(unittest.TestCase):
    def test_root_help_explains_private_and_published_data_scopes(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["--help"]), 0)
        self.assertIn("Private authoring DB", output.getvalue())
        self.assertIn("Published Knowledge Pack", output.getvalue())
        self.assertIn("knowledge-release", output.getvalue())

    def test_subcommand_help_is_delegated_to_the_selected_handler(self):
        with patch("open_ielts_strategy.knowledge_library_cli.main", return_value=0) as run:
            self.assertEqual(main(["library", "--help"]), 0)
            run.assert_called_once_with(["--help"])

    def test_returned_command_error_includes_data_scope(self):
        error = io.StringIO()
        with patch("open_ielts_strategy.published_practice_cli.main", return_value=2):
            with redirect_stderr(error):
                self.assertEqual(main(["practice", "question"]), 2)
        self.assertIn("published Knowledge Pack", error.getvalue())

    def test_argument_parser_error_includes_data_scope(self):
        error = io.StringIO()
        with patch("open_ielts_strategy.knowledge_library_cli.main", side_effect=SystemExit(2)):
            with redirect_stderr(error):
                with self.assertRaises(SystemExit):
                    main(["library", "--unknown-option"])
        self.assertIn("private local authoring database", error.getvalue())

    def test_preflight_delegates_without_rewriting_arguments(self):
        with patch("open_ielts_strategy.preflight_cli.main", return_value=0) as run:
            self.assertEqual(main(["preflight", "--mode", "author"]), 0)
            run.assert_called_once_with(["--mode", "author"])

    def test_study_delegates_to_learning_cli(self):
        with patch("open_ielts_strategy.published_learning_cli.main", return_value=0) as run:
            self.assertEqual(main(["study", "--skill", "speaking"]), 0)
            run.assert_called_once_with(["study", "--skill", "speaking"])

    def test_practice_delegates_without_rewriting_arguments(self):
        with patch("open_ielts_strategy.published_practice_cli.main", return_value=0) as run:
            self.assertEqual(main(["practice", "question", "--model", "local"]), 0)
            run.assert_called_once_with(["question", "--model", "local"])

    def test_private_library_delegates_without_rewriting_arguments(self):
        with patch("open_ielts_strategy.knowledge_library_cli.main", return_value=0) as run:
            self.assertEqual(main(["library", "ingest", "-", "--title", "My notes"]), 0)
            run.assert_called_once_with(["ingest", "-", "--title", "My notes"])

    def test_semantic_extraction_delegates_without_rewriting_arguments(self):
        with patch("open_ielts_strategy.knowledge_extract_cli.main", return_value=0) as run:
            self.assertEqual(main(["extract", "--source-id", "src_1", "--model", "qwen3:8b"]), 0)
            run.assert_called_once_with(["--source-id", "src_1", "--model", "qwen3:8b"])

    def test_local_knowledge_answer_delegates_without_rewriting_arguments(self):
        with patch("open_ielts_strategy.knowledge_answer_cli.main", return_value=0) as run:
            self.assertEqual(main(["knowledge-answer", "a speaking question", "--model", "qwen3:8b"]), 0)
            run.assert_called_once_with(["a speaking question", "--model", "qwen3:8b"])

    def test_knowledge_publish_delegates(self):
        with patch("open_ielts_strategy.knowledge_publish_cli.main", return_value=0) as run:
            self.assertEqual(main(["knowledge-publish", "--strategy", "draft.json"]), 0)
            run.assert_called_once_with(["--strategy", "draft.json"])

    def test_knowledge_diff_delegates(self):
        with patch("open_ielts_strategy.knowledge_diff_cli.main", return_value=0) as run:
            self.assertEqual(main(["knowledge-diff", "--current", "a", "--candidate", "b"]), 0)
            run.assert_called_once_with(["--current", "a", "--candidate", "b"])

    def test_knowledge_release_delegates(self):
        with patch("open_ielts_strategy.knowledge_release.main", return_value=0) as run:
            self.assertEqual(main(["knowledge-release", "approve"]), 0)
            run.assert_called_once_with(["approve"])

    def test_knowledge_init_delegates(self):
        with patch("open_ielts_strategy.knowledge_init_cli.main", return_value=0) as run:
            self.assertEqual(main(["knowledge-init", "--workspace", ".local/authoring"]), 0)
            run.assert_called_once_with(["--workspace", ".local/authoring"])

    def test_adapter_status_delegates(self):
        with patch("open_ielts_strategy.integration_adapters_cli.main", return_value=0) as run:
            self.assertEqual(main(["adapter-status"]), 0)
            run.assert_called_once_with([])

    def test_unknown_command_is_rejected(self):
        with self.assertRaises(SystemExit):
            main(["not-a-command"])


if __name__ == "__main__":
    unittest.main()
