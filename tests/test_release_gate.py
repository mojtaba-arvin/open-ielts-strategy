import unittest
from pathlib import Path
from scripts.validate_release import validate_claim_registry, validate_release_preflight

def valid_claim():
    return {"id": "claim-a", "description": "A measured claim.", "status": "validated", "public_claim_allowed": True, "evidence_refs": ["private://study/report"], "reviewer": "independent-reviewer", "method": "pre-registered paired study", "scope": "Writing Task 2 synthetic cohort", "sample_count": 120, "reviewed_at": "2026-11-22T10:00:00Z"}

class ReleaseGateTests(unittest.TestCase):
    def test_default_deny_claim_register_is_valid(self):
        data = {"schema_version": 1, "claims": [{"id": "official-band", "description": "No official band claim.", "status": "not_established", "public_claim_allowed": False, "evidence_refs": []}]}
        self.assertEqual(validate_claim_registry(data), [])

    def test_public_claim_requires_evidence_and_review_metadata(self):
        claim = valid_claim()
        self.assertEqual(validate_claim_registry({"schema_version": 1, "claims": [claim]}), [])

    def test_public_claim_fails_closed_without_evidence(self):
        claim = valid_claim()
        claim["evidence_refs"] = []
        claim["reviewer"] = ""
        claim["sample_count"] = 0
        claim["reviewed_at"] = "2026-11-22T10:00:00"
        errors = validate_claim_registry({"schema_version": 1, "claims": [claim]})
        self.assertTrue(any("evidence_refs" in error for error in errors))
        self.assertTrue(any("reviewer" in error for error in errors))
        self.assertTrue(any("sample_count" in error for error in errors))
        self.assertTrue(any("timezone-aware" in error for error in errors))

    def test_public_claim_requires_validated_status(self):
        claim = valid_claim()
        claim["status"] = "not_established"
        self.assertTrue(any("validated status" in error for error in validate_claim_registry({"schema_version": 1, "claims": [claim]})))

    def test_duplicate_claim_ids_are_rejected(self):
        claim = valid_claim()
        duplicate = dict(claim)
        errors = validate_claim_registry({"schema_version": 1, "claims": [claim, duplicate]})
        self.assertTrue(any("duplicate claim id" in error for error in errors))

    def test_rejects_boolean_schema_and_unhashable_status(self):
        claim = valid_claim()
        errors = validate_claim_registry({"schema_version": True, "claims": [claim]})
        self.assertTrue(errors)
        claim["status"] = []
        errors = validate_claim_registry({"schema_version": 1, "claims": [claim]})
        self.assertTrue(any("status is invalid" in error for error in errors))

    def test_release_workflow_has_manual_candidate_tag_gate(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/release.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("RELEASE_TAG", workflow)
        self.assertIn("python scripts/validate_release.py", workflow)
        self.assertNotIn("types: [published]", workflow)

    def test_malformed_registry_is_rejected(self):
        self.assertTrue(validate_claim_registry([]))
        self.assertTrue(validate_claim_registry({"schema_version": 1, "claims": []}))

if __name__ == "__main__":
    unittest.main()


    def test_release_preflight_checks_version_cli_and_license_contracts(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(validate_release_preflight(root), [])
        self.assertEqual(validate_release_preflight(root, "v0.1.0"), [])

    def test_release_preflight_rejects_tag_version_mismatch(self):
        root = Path(__file__).resolve().parents[1]
        errors = validate_release_preflight(root, "v9.9.9")
        self.assertTrue(any("does not match project.version" in error for error in errors))

    def test_release_preflight_rejects_non_semver_tag(self):
        root = Path(__file__).resolve().parents[1]
        errors = validate_release_preflight(root, "latest")
        self.assertTrue(any("canonical vMAJOR.MINOR.PATCH" in error for error in errors))
