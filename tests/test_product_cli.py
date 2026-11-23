import unittest
from unittest.mock import patch
from open_ielts_strategy.product_cli import main

class ProductCliTests(unittest.TestCase):
    def test_study_delegates_to_learning_cli(self):
        with patch("open_ielts_strategy.published_learning_cli.main", return_value=0) as run:
            self.assertEqual(main(["study", "--skill", "speaking"]), 0)
            run.assert_called_once_with(["study", "--skill", "speaking"])
    def test_practice_delegates_without_rewriting_arguments(self):
        with patch("open_ielts_strategy.published_practice_cli.main", return_value=0) as run:
            self.assertEqual(main(["practice", "question", "--model", "local"]), 0)
            run.assert_called_once_with(["question", "--model", "local"])
    def test_unknown_command_is_rejected(self):
        with self.assertRaises(SystemExit):
            main(["not-a-command"])

if __name__ == "__main__":
    unittest.main()
