import unittest

from open_ielts_strategy.knowledge_benchmark import evaluate_extraction, validate_annotation_set


class KnowledgeBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.source = "Plan before drafting. Avoid memorized essays."
        self.gold = [{
            "kind": "recommendation", "text": "Plan before drafting.",
            "start_char": 0, "end_char": 22,
        }]

    def test_exact_match_metrics_are_computed(self):
        result = evaluate_extraction(self.gold, self.gold)
        self.assertEqual(result["precision"], 1.0)
        self.assertEqual(result["recall"], 1.0)
        self.assertFalse(result["claim_eligible"])
        self.assertEqual(result["educational_validity"], "not-measured")

    def test_partial_extraction_penalizes_false_negative(self):
        result = evaluate_extraction([], self.gold)
        self.assertEqual(result["recall"], 0.0)
        self.assertEqual(result["false_negative"], 1)

    def test_wrong_span_is_not_an_exact_match(self):
        wrong = [{**self.gold[0], "start_char": 1, "end_char": 23, "text": "lan before drafting."}]
        result = evaluate_extraction(wrong, self.gold)
        self.assertEqual(result["f1"], 0.0)

    def test_annotation_must_match_exact_source(self):
        self.assertEqual(validate_annotation_set(self.source, self.gold), self.gold)
        with self.assertRaises(ValueError):
            validate_annotation_set(self.source, [{**self.gold[0], "text": "different"}])

    def test_invalid_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_extraction([{"kind": "band_score", "text": "x", "start_char": 0, "end_char": 1}], [])
