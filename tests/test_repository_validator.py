import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_repo import validate_repository_data


def source_record():
    return {
        "id": "sample-source",
        "name": "Sample metadata",
        "source_type": "documentation",
        "source_url": "https://example.org/policy",
        "legal_status": "under_review",
        "public_content_allowed": False,
        "allowed_uses": [],
        "permission_record": {
            "private_evidence_ref": "",
            "reviewer": "",
            "reviewed_at": "",
            "notes": "Metadata only.",
        },
        "expiry": None,
    }


class RepositoryValidatorShapeTests(unittest.TestCase):
    def test_malformed_root_documents_are_reported_without_crashing(self):
        errors, skill_count, source_count = validate_repository_data([], [])
        self.assertIn("skills.lock must be a JSON object", errors)
        self.assertIn("source registry must be a JSON object", errors)
        self.assertEqual((skill_count, source_count), (0, 0))

    def test_malformed_collection_shapes_are_reported(self):
        lock = {"lockfile_version": 1, "skills": "not-a-list"}
        registry = {"sources": {"not": "a-list"}}
        errors, _, _ = validate_repository_data(lock, registry)
        self.assertIn("skills.lock skills must be a non-empty list", errors)
        self.assertIn("source registry sources must be a list", errors)

    def test_malformed_skill_rows_and_versions_are_reported(self):
        lock = {
            "lockfile_version": 1,
            "skills": [None, {"name": "../escape", "version": []}],
        }
        errors, _, _ = validate_repository_data(lock, {"sources": []})
        self.assertIn("skills.lock skills[0] must be an object", errors)
        self.assertIn("skills.lock skills[1] has an invalid skill name", errors)

    def test_valid_minimal_repository_metadata_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill_dir = root / "skills" / "sample-skill"
            (skill_dir / "evals").mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: Sample\nlicense: LICENSE-CONTENT\nversion: 1.0.0\n---\n",
                encoding="utf-8",
            )
            (skill_dir / "evals" / "cases.json").write_text(
                json.dumps([{
                    "id": "route",
                    "category": "routing_positive",
                    "input": "synthetic input",
                    "expected": "synthetic expected behavior",
                }]),
                encoding="utf-8",
            )
            lock = {
                "lockfile_version": 1,
                "skills": [{
                    "name": "sample-skill",
                    "version": "1.0.0",
                    "dependencies": [],
                }],
            }
            errors, skill_count, source_count = validate_repository_data(
                lock, {"sources": [source_record()]}, root
            )
            self.assertEqual(errors, [])
            self.assertEqual((skill_count, source_count), (1, 1))


if __name__ == "__main__":
    unittest.main()
