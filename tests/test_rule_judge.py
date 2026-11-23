import unittest
from open_ielts_strategy.rule_judge import DIMENSIONS, evaluate_writing


class RuleJudgeTests(unittest.TestCase):
    def test_is_deterministic_and_explicitly_simulated(self):
        text = "Firstly, cities need parks. However, housing is also important. Therefore, careful planning is necessary."
        first = evaluate_writing(text)
        self.assertEqual(first, evaluate_writing(text))
        self.assertEqual(first["status"], "simulated-heuristic")
        self.assertEqual(set(first["scores"]), set(DIMENSIONS))
        self.assertIsInstance(first["overall_heuristic_index"], float)

    def test_reports_observable_evidence(self):
        result = evaluate_writing("First sentence. Second sentence.\n\nAnother paragraph.")
        self.assertEqual(result["evidence"]["paragraph_count"], 2)
        self.assertEqual(result["evidence"]["sentence_count"], 3)
        self.assertGreater(result["evidence"]["word_count"], 0)

    def test_never_labels_index_as_ielts_band(self):
        result = evaluate_writing("A sufficiently long synthetic response for a deterministic test.")
        self.assertNotIn("ielts_band", result)
        self.assertIn("Not an IELTS band score", result["limitations"][0])

    def test_rejects_empty_or_invalid_inputs(self):
        for value in ("", "   ", None, 7):
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate_writing(value)
        with self.assertRaises(ValueError):
            evaluate_writing("essay", task=" ")

    def test_scores_are_bounded(self):
        result = evaluate_writing(("word " * 500) + ".")
        self.assertTrue(all(type(score) is int and 1 <= score <= 9 for score in result["scores"].values()))


if __name__ == "__main__":
    unittest.main()
