import contextlib
import io
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from open_ielts_strategy.knowledge_release import create_approval, verify_approval, main, publish_pack


class KnowledgeReleaseApprovalTests(unittest.TestCase):
    def setUp(self):
        self.identity = {
            "current_manifest_sha256": "a" * 64,
            "candidate_manifest_sha256": "b" * 64,
            "candidate_pack_version": "1.1.0",
            "diff_sha256": "c" * 64,
        }
        self.diff = {"change_count": 2, "changes": [{"record_id": "strategy.a"}, {"record_id": "strategy.b"}]}
        self.now = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
        self.key = b"local-test-approval-key-that-is-long-enough"

    def test_signed_approval_is_bound_to_exact_pack_and_diff(self):
        with patch("open_ielts_strategy.knowledge_release._diff_identity",
                   return_value=(self.diff, self.identity)):
            approval = create_approval(
                "current", "candidate", reviewer="maintainer-a", key=self.key,
                confirm_diff=True, confirm_rights=True, now=self.now,
            )
            payload = verify_approval(
                approval, "current", "candidate", key=self.key, now=self.now,
            )
        self.assertEqual(payload["candidate_manifest_sha256"], "b" * 64)
        self.assertTrue(payload["human_confirmed_diff_review"])
        self.assertTrue(payload["human_confirmed_rights_review"])

    def test_tampered_approval_is_rejected(self):
        with patch("open_ielts_strategy.knowledge_release._diff_identity",
                   return_value=(self.diff, self.identity)):
            approval = create_approval(
                "current", "candidate", reviewer="maintainer-a", key=self.key,
                confirm_diff=True, confirm_rights=True, now=self.now,
            )
            approval["payload"]["candidate_manifest_sha256"] = "d" * 64
            with self.assertRaisesRegex(ValueError, "signature"):
                verify_approval(approval, "current", "candidate", key=self.key, now=self.now)

    def test_approval_expires_after_24_hours(self):
        with patch("open_ielts_strategy.knowledge_release._diff_identity",
                   return_value=(self.diff, self.identity)):
            approval = create_approval(
                "current", "candidate", reviewer="maintainer-a", key=self.key,
                confirm_diff=True, confirm_rights=True, now=self.now,
            )
            with self.assertRaisesRegex(ValueError, "expired"):
                verify_approval(
                    approval, "current", "candidate", key=self.key,
                    now=self.now + timedelta(hours=25),
                )

    def test_rollback_cli_does_not_require_publication_hmac_key(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "open_ielts_strategy.knowledge_release.rollback_pack",
            return_value={"rolled_back": True},
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main([
                    "rollback", "--repo", ".", "--commit", "a" * 40,
                    "--branch", "release/knowledge-v1", "--expected-head", "b" * 40,
                    "--confirm-rollback",
                ])
        self.assertEqual(result, 0)
        self.assertIn('"rolled_back": true', output.getvalue())

    def test_direct_default_branch_publication_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-default release branch"):
            publish_pack(
                ".", "candidate", "knowledge", approval_path="approval.json",
                branch="main", expected_head="a" * 40, key=self.key,
                confirm_publish=True,
            )

    def test_approval_requires_both_human_gates(self):
        with self.assertRaisesRegex(ValueError, "confirmations"):
            create_approval(
                "current", "candidate", reviewer="maintainer-a", key=self.key,
                confirm_diff=True, confirm_rights=False, now=self.now,
            )


if __name__ == "__main__":
    unittest.main()
