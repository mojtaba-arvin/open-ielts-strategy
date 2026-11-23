import unittest
from open_ielts_strategy.calibration_audit import DIMENSIONS, audit_calibration


def card(version, values, rubric="a" * 64):
    return {
        "judge_version": version, "rubric_sha256": rubric,
        "results": [
            {"item_id": item, "scores": {dimension: score for dimension, score in zip(DIMENSIONS, scores)}}
            for item, scores in values
        ],
    }


class CalibrationAuditTests(unittest.TestCase):
    def setUp(self):
        self.cards = [
            card("judge-v1", [("x", [5, 5, 5, 5]), ("y", [6, 6, 6, 6])]),
            card("judge-v2", [("x", [7, 5, 5, 5]), ("y", [6, 8, 6, 6])], "b" * 64),
        ]

    def test_reports_dimension_diffs_and_review_flags(self):
        report = audit_calibration(self.cards, review_threshold=2)
        self.assertEqual(report["status"], "simulated-audit")
        self.assertEqual(len(report["flagged_for_review"]), 2)
        self.assertEqual(report["comparisons"][0]["dimensions"]["task_response"]["mean_absolute_difference"], 1.0)

    def test_accepts_optional_reference_with_explicit_provenance(self):
        reference = {
            "provenance": {"reviewer": "reviewer-id", "reviewed_at": "2026-01-01T00:00:00Z", "method": "manual rubric review"},
            "results": [{"item_id": "x", "scores": {dimension: 6 for dimension in DIMENSIONS}}],
        }
        report = audit_calibration(self.cards, human_reference=reference)
        self.assertEqual(report["status"], "audit-with-reference")
        self.assertEqual(report["human_reference"]["comparisons"][0]["common_item_ids"], ["x"])
        self.assertIn("do not independently authenticate", report["human_reference"]["interpretation"])

    def test_rejects_malformed_versions_rubrics_scores_and_duplicates(self):
        invalid = [
            [{}, self.cards[1]],
            [dict(self.cards[0], rubric_sha256="bad"), self.cards[1]],
            [self.cards[0], dict(self.cards[0])],
        ]
        for cards in invalid:
            with self.subTest(cards=cards), self.assertRaises(ValueError):
                audit_calibration(cards)
        bad = card("judge-v3", [("x", [5, 5, 5, 5])])
        bad["results"][0]["scores"]["grammar_accuracy"] = True
        with self.assertRaisesRegex(ValueError, "integers"):
            audit_calibration([self.cards[0], bad])

    def test_rejects_invalid_reference_provenance_and_scores(self):
        with self.assertRaisesRegex(ValueError, "provenance"):
            audit_calibration(self.cards, human_reference={"results": []})
        reference = {
            "provenance": {"reviewer": "x", "reviewed_at": "y", "method": "z"},
            "results": [{"item_id": "x", "scores": {dimension: 0 for dimension in DIMENSIONS}}],
        }
        with self.assertRaisesRegex(ValueError, "integers"):
            audit_calibration(self.cards, human_reference=reference)

    def test_requires_two_cards_and_valid_threshold(self):
        with self.assertRaisesRegex(ValueError, "at least two"):
            audit_calibration([self.cards[0]])
        with self.assertRaisesRegex(ValueError, "review_threshold"):
            audit_calibration(self.cards, review_threshold=0)


if __name__ == "__main__":
    unittest.main()
