import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from open_ielts_strategy.preflight_cli import main, run_preflight


class PreflightCliTests(unittest.TestCase):
    def test_author_mode_does_not_require_a_published_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_preflight(
                mode="author",
                db=str(Path(tmp) / ".local" / "knowledge.sqlite3"),
                pack=str(Path(tmp) / "missing-pack"),
            )
        self.assertTrue(result["usable"])
        checks = {item["name"]: item for item in result["checks"]}
        self.assertEqual(checks["private_database_path"]["status"], "ok")
        self.assertEqual(checks["published_knowledge_pack"]["status"], "info")

    def test_consumer_mode_does_not_require_private_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_preflight(
                mode="consume",
                db=str(Path(tmp) / "missing" / "private.sqlite3"),
                pack=str(Path(tmp) / "missing-pack"),
            )
        checks = {item["name"]: item for item in result["checks"]}
        self.assertEqual(checks["private_database_path"]["status"], "info")
        self.assertEqual(checks["published_knowledge_pack"]["status"], "blocked")

    def test_ollama_model_must_be_installed(self):
        with patch("open_ielts_strategy.preflight_cli._ollama_models", return_value=({"qwen3:8b"}, None)):
            result = run_preflight(provider="ollama", model="missing:latest")
        checks = {item["name"]: item for item in result["checks"]}
        self.assertEqual(checks["ollama_model"]["status"], "blocked")
        self.assertIn("qwen3:8b", checks["ollama_model"]["installed"])

    def test_ollama_unreachable_is_a_clear_blocker(self):
        with patch("open_ielts_strategy.preflight_cli._ollama_models", return_value=(None, "URLError")):
            result = run_preflight(provider="ollama", model="qwen3:8b")
        checks = {item["name"]: item for item in result["checks"]}
        self.assertEqual(checks["ollama"]["status"], "blocked")
        self.assertEqual(checks["ollama"]["error"], "URLError")

    def test_api_preflight_checks_only_environment_variable_presence(self):
        with patch.dict("os.environ", {"IELTS_TEST_API_KEY": "secret"}, clear=True):
            result = run_preflight(provider="openai-compatible", api_key_env="IELTS_TEST_API_KEY")
        checks = {item["name"]: item for item in result["checks"]}
        self.assertEqual(checks["api_credentials"]["status"], "ok")
        self.assertNotIn("secret", json.dumps(result))

    def test_cli_emits_json_and_returns_nonzero_for_missing_consumer_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["--mode", "consume", "--pack", str(Path(tmp) / "missing")])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
