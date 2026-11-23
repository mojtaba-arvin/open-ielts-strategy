import unittest

from open_ielts_strategy.provenance import validate_source_record


def sample_source(**changes):
    value = {
        "id": "sample",
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
    value.update(changes)
    return value


class ProvenanceTests(unittest.TestCase):
    def test_default_deny_metadata_is_valid(self):
        self.assertEqual(validate_source_record(sample_source()), [])

    def test_public_use_fails_without_evidence_and_approval(self):
        errors = validate_source_record(sample_source(public_content_allowed=True))
        self.assertIn("public content requires cleared or licensed status", errors)
        self.assertIn("public content requires permission_record.private_evidence_ref", errors)
        self.assertIn("public content requires permission_record.reviewer", errors)
        self.assertIn("public content requires a timezone-aware permission review timestamp", errors)
        self.assertIn("public content requires explicit allowed_uses", errors)

    def test_public_use_accepts_complete_scoped_permission_metadata(self):
        permission = {
            "private_evidence_ref": "private://evidence/record",
            "reviewer": "reviewer",
            "reviewed_at": "2026-11-22T10:00:00Z",
            "notes": "Scope limited to private excerpt use.",
        }
        record = sample_source(
            legal_status="licensed",
            public_content_allowed=True,
            allowed_uses=["specific approved use"],
            permission_record=permission,
        )
        self.assertEqual(validate_source_record(record), [])

    def test_public_permission_review_requires_timezone(self):
        permission = {
            "private_evidence_ref": "private://evidence/record",
            "reviewer": "reviewer",
            "reviewed_at": "2026-11-22T10:00:00",
            "notes": "Metadata only.",
        }
        record = sample_source(
            legal_status="licensed",
            public_content_allowed=True,
            allowed_uses=["specific approved use"],
            permission_record=permission,
        )
        self.assertIn(
            "public content requires a timezone-aware permission review timestamp",
            validate_source_record(record),
        )

    def test_unsafe_url_and_duplicate_scope_are_rejected(self):
        errors = validate_source_record(sample_source(
            source_url="https://user:secret@example.org",
            allowed_uses=["private", "private"],
        ))
        self.assertIn("source_url must be HTTPS without embedded credentials", errors)
        self.assertIn("allowed_uses must not contain duplicates", errors)

    def test_malformed_status_and_url_fail_without_crashing(self):
        for status, url in [([], "https://example.org"), ("under_review", "https://[invalid")]:
            with self.subTest(status=status, url=url):
                errors = validate_source_record(sample_source(legal_status=status, source_url=url))
                self.assertTrue(errors)

    def test_invalid_expiry_is_rejected(self):
        self.assertIn(
            "expiry must be null or timezone-aware ISO-8601",
            validate_source_record(sample_source(expiry="later")),
        )

    def test_expiry_requires_timezone(self):
        self.assertIn(
            "expiry must be null or timezone-aware ISO-8601",
            validate_source_record(sample_source(expiry="2027-01-01T00:00:00")),
        )

    def test_expiry_accepts_explicit_timezone(self):
        self.assertEqual(
            validate_source_record(sample_source(expiry="2027-01-01T00:00:00+04:00")),
            [],
        )

    def test_expired_permission_cannot_remain_licensed(self):
        errors = validate_source_record(sample_source(
            legal_status="licensed",
            expiry="2020-01-01T00:00:00Z",
        ))
        self.assertIn("expired permission must use legal_status=expired", errors)

    def test_expired_permission_cannot_allow_public_content(self):
        permission = {
            "private_evidence_ref": "private://evidence/record",
            "reviewer": "reviewer",
            "reviewed_at": "2026-11-22T10:00:00Z",
            "notes": "Previously approved scope; now expired.",
        }
        errors = validate_source_record(sample_source(
            legal_status="licensed",
            public_content_allowed=True,
            allowed_uses=["specific approved use"],
            permission_record=permission,
            expiry="2020-01-01T00:00:00Z",
        ))
        self.assertIn("expired permission must use legal_status=expired", errors)
        self.assertIn("expired permission cannot allow public content", errors)

    def test_non_object_is_rejected(self):
        self.assertEqual(validate_source_record(None), ["source record must be an object"])


if __name__ == "__main__":
    unittest.main()
