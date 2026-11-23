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


def add_example(root):
    example = {
        "id": "speaking.example.direct-answer-01", "schema_version": "1.0",
        "strategy_id": "speaking.answer-development", "skill": "speaking",
        "task": "Describe a recent learning experience.",
        "content": "I recently learned to cook a new dish.",
        "strategy_application": "The first sentence answers directly.",
        "learning_note": "Add one relevant supporting detail.",
        "provenance": {"basis": "original", "public_references": []},
        "review": {"content_status": "approved", "publication_status": "approved"},
        "version": "1.0.0",
    }
    payload = json.dumps(example, sort_keys=True, separators=(",", ":")).encode()
    relative = "examples/speaking/speaking.example.direct-answer-01.json"
    destination = root / relative
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = "1.1"
    manifest["files"].append({"path": relative, "sha256": hashlib.sha256(payload).hexdigest()})
    manifest["files"].sort(key=lambda item: item["path"])
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


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


    def test_diff_reports_added_standalone_example_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root / "current", "1.0.0", "Develop a direct answer.")
            make_pack(root / "candidate", "1.1.0", "Develop a direct answer.")
            add_example(root / "candidate")
            result = diff_pack_directories(str(root / "current"), str(root / "candidate"))
            self.assertEqual(result["change_count"], 1)
            self.assertEqual(result["changes"][0]["record_type"], "examples")
            self.assertEqual(result["changes"][0]["status"], "added")

    def test_diff_requires_version_bump_when_records_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root / "current", "1.0.0", "Develop a direct answer.")
            make_pack(root / "candidate", "1.0.0", "Develop a direct answer with detail.")
            with self.assertRaisesRegex(ValueError, "version must change"):
                diff_pack_directories(str(root / "current"), str(root / "candidate"))

    def test_diff_blocks_secret_like_candidate_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root / "current", "1.0.0", "Safe content.")
            make_pack(root / "candidate", "1.1.0", "Credential ghp_abcdefghijklmnopqrstuvwxyz123456 leaked.")
            with self.assertRaisesRegex(ValueError, "secret-like"):
                diff_pack_directories(str(root / "current"), str(root / "candidate"))


if __name__ == "__main__":
    unittest.main()
