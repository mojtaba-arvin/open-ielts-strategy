import unittest
from open_ielts_strategy.skill_lift import compare_skill_lift


class SkillLiftAuditTests(unittest.TestCase):
    def setUp(self):
        self.base = [
            {"case_id": "a", "passed": False, "score": 0.2, "category": "writing"},
            {"case_id": "b", "passed": True, "score": 0.8, "category": "writing"},
            {"case_id": "c", "passed": False, "score": 0.3, "category": "speaking"},
        ]
        self.skill = [
            {"case_id": "a", "passed": True, "score": 0.7, "category": "writing"},
            {"case_id": "b", "passed": True, "score": 0.9, "category": "writing"},
            {"case_id": "c", "passed": False, "score": 0.4, "category": "speaking"},
        ]

    def test_fixture_report_is_paired_and_never_claimable(self):
        report = compare_skill_lift(self.base, self.skill)
        self.assertEqual(report["status"], "simulated-fixture")
        self.assertFalse(report["claim_eligible"])
        self.assertEqual(report["overall"]["resolution_rate_delta"], 1 / 3)
        self.assertEqual(report["by_category"]["writing"]["n"], 2)

    def test_live_mode_is_still_descriptive_not_claimable(self):
        report = compare_skill_lift(self.base, self.skill, mode="live")
        self.assertEqual(report["status"], "descriptive-live-evaluation")
        self.assertFalse(report["claim_eligible"])

    def test_rejects_empty_nonobject_and_duplicate_rows(self):
        for rows in ([], ["x"], [{"case_id": "a", "passed": True}, {"case_id": "a", "passed": False}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                compare_skill_lift(rows, self.skill)

    def test_rejects_non_boolean_and_invalid_scores(self):
        for row in (
            {"case_id": "a", "passed": 1},
            {"case_id": "a", "passed": True, "score": True},
            {"case_id": "a", "passed": True, "score": float("nan")},
            {"case_id": "a", "passed": True, "score": 1.1},
        ):
            with self.subTest(row=row), self.assertRaises(ValueError):
                compare_skill_lift([row], [row])

    def test_rejects_mismatched_case_sets_and_categories(self):
        with self.assertRaisesRegex(ValueError, "same case IDs"):
            compare_skill_lift(self.base, self.skill[:-1])
        changed = [dict(row) for row in self.skill]
        changed[0]["category"] = "other"
        with self.assertRaisesRegex(ValueError, "categories must match"):
            compare_skill_lift(self.base, changed)

    def test_rejects_unknown_mode(self):
        with self.assertRaisesRegex(ValueError, "mode"):
            compare_skill_lift(self.base, self.skill, mode="pretend")


if __name__ == "__main__":
    unittest.main()
