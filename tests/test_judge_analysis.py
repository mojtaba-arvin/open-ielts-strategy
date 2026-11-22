import unittest
from open_ielts_strategy.judge import DIMENSIONS
from open_ielts_strategy.judge_analysis import analyze_judge_disagreement

def card(model, values):
    return {"model": model, "results": [
        {"item_id": item_id, "scores": {dimension: score for dimension in DIMENSIONS}}
        for item_id, score in values
    ]}

class JudgeDisagreementTests(unittest.TestCase):
    def test_perfect_agreement_is_reported_as_agreement_not_accuracy(self):
        report = analyze_judge_disagreement([card("judge-a", [("x", 6), ("y", 7)]), card("judge-b", [("x", 6), ("y", 7)])])
        metric = report["pairwise"][0]["dimensions"]["task_response"]
        self.assertEqual(metric["exact_agreement_rate"], 1.0)
        self.assertEqual(metric["mean_absolute_difference"], 0.0)
        self.assertIn("not accuracy", report["interpretation"])

    def test_reports_dimension_specific_disagreement(self):
        left = {"model": "judge-a", "results": [{"item_id": "x", "scores": {d: 5 for d in DIMENSIONS}}]}
        right_scores = {d: 5 for d in DIMENSIONS}
        right_scores["lexical_resource"] = 8
        right = {"model": "judge-b", "results": [{"item_id": "x", "scores": right_scores}]}
        report = analyze_judge_disagreement([left, right])
        self.assertEqual(report["pairwise"][0]["dimensions"]["lexical_resource"]["mean_absolute_difference"], 3.0)
        self.assertEqual(report["pairwise"][0]["dimensions"]["grammar_accuracy"]["mean_absolute_difference"], 0.0)

    def test_uses_only_intersection_of_item_ids(self):
        left = card("judge-a", [("x", 5), ("y", 6)])
        right = card("judge-b", [("y", 6), ("z", 7)])
        report = analyze_judge_disagreement([left, right])
        self.assertEqual(report["common_item_ids"], ["y"])
        self.assertEqual(report["common_item_count"], 1)

    def test_rejects_duplicate_models_and_duplicate_items(self):
        left = card("judge-a", [("x", 5)])
        with self.assertRaisesRegex(ValueError, "unique"):
            analyze_judge_disagreement([left, card("JUDGE-A", [("x", 5)])])
        duplicate = card("judge-b", [("x", 5), ("x", 6)])
        with self.assertRaisesRegex(ValueError, "duplicate item_id"):
            analyze_judge_disagreement([left, duplicate])

    def test_rejects_malformed_scores(self):
        left = card("judge-a", [("x", 5)])
        right = card("judge-b", [("x", 5)])
        right["results"][0]["scores"]["grammar_accuracy"] = True
        with self.assertRaisesRegex(ValueError, "integers from 1 to 9"):
            analyze_judge_disagreement([left, right])

    def test_requires_two_judges_and_shared_items(self):
        with self.assertRaisesRegex(ValueError, "at least two"):
            analyze_judge_disagreement([card("judge-a", [("x", 5)])])
        with self.assertRaisesRegex(ValueError, "no common item IDs"):
            analyze_judge_disagreement([card("judge-a", [("x", 5)]), card("judge-b", [("y", 5)])])

if __name__ == "__main__":
    unittest.main()
