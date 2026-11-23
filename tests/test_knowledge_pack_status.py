import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pack_status import inspect_knowledge_pack


class KnowledgePackStatusTests(unittest.TestCase):
    def test_missing_pack_is_explicit_and_never_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "knowledge"
            result = inspect_knowledge_pack(path)
            self.assertEqual(result["status"], "missing")
            self.assertFalse(result["usable"])
            self.assertFalse(path.exists())

    def test_incomplete_pack_is_not_reported_as_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "knowledge"
            path.mkdir()
            result = inspect_knowledge_pack(path)
            self.assertEqual(result["status"], "incomplete")
            self.assertFalse(result["usable"])

    def test_invalid_pack_is_not_reported_as_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "knowledge"
            path.mkdir()
            (path / "manifest.json").write_text("{}", encoding="utf-8")
            result = inspect_knowledge_pack(path)
            self.assertEqual(result["status"], "invalid")
            self.assertFalse(result["usable"])


if __name__ == "__main__":
    unittest.main()
