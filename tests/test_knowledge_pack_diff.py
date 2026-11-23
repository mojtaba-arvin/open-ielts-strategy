import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pack_diff import diff_pack_directories


def make_pack(root, version, summary):
    record = {
        "id": "speaking.answer-development", "schema_version": "1.0",
        "title": "Answer Development", "skill": "speaking",
        "summary": summary, "purpose": [], "reasoning": [], "steps": [],
        "applicability": {"question_types": [], "parts": [], "conditions": []},
        "limitations": [], "common_mistakes": [], "examples": [],
        "relationships": {"requires": [], "complements": [], "conflicts_with": [], "alternatives": []},
        "provenance": {"basis": "original", "public_references": []},
        "review": {"content_status": "approved", "publication_status": "approved"},
        "version": "1.0.0",
    }
    folder = root / "strategies" / "speaking"
    folder.mkdir(parents=True)
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    (folder / "strategy.json").write_bytes(payload)
    (root / "manifest.json").write_text(json.dumps({
        "format": "open-ielts-knowledge-pack", "schema_version": "1.0",
        "pack_version": version,
        "files": [{"path": "strategies/speaking/strategy.json",
                   "sha256": hashlib.sha256(payload).hexdigest()}],
    }), encoding="utf-8")


class PublicationDiffTests(unittest.TestCase):
    def test_diff_reports_modified_records_and_exact_pack_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root / "current", "1.0.0", "Develop a direct answer.")
            make_pack(root / "candidate", "1.1.0", "Develop a direct answer with detail.")
            result = diff_pack_directories(str(root / "current"), str(root / "candidate"))
            self.assertEqual(result["change_count"], 1)
            self.assertEqual(result["changes"][0]["status"], "modified")
            self.assertIn("with detail", result["changes"][0]["diff"])
            self.assertEqual(result["current_pack_version"], "1.0.0")
            self.assertFalse(result["git_commit_created"])
            self.assertTrue(result["requires_human_review"])

    def test_diff_blocks_secret_like_candidate_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root / "current", "1.0.0", "Safe content.")
            make_pack(root / "candidate", "1.1.0", "Credential ghp_abcdefghijklmnopqrstuvwxyz123456 leaked.")
            with self.assertRaisesRegex(ValueError, "secret-like"):
                diff_pack_directories(str(root / "current"), str(root / "candidate"))


if __name__ == "__main__":
    unittest.main()
