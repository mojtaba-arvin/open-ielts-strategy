import unittest

from open_ielts_strategy.knowledge_benchmark import evaluate_extraction, validate_annotation_set, evaluate_source_extraction
from open_ielts_strategy.knowledge_pipeline import extract_source
from open_ielts_strategy.knowledge_store import KnowledgeStore
import tempfile
from pathlib import Path


class KnowledgeBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.source = "Plan before drafting. Avoid memorized essays."
        self.gold = [{
            "kind": "recommendation", "text": "Plan before drafting.",
            "start_char": 0, "end_char": 21,
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


    def test_private_source_evaluation_returns_metrics_without_source_text(self):
        class Provider:
            def extract(self, text):
                return {"summary": "Advice.", "items": [{
                    "kind": "recommendation", "text": text, "start_char": 0,
                    "end_char": len(text), "topic_tags": ["speaking"],
                    "rationale": "Source advice.",
                }]}
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "library.sqlite3") as store:
                original = "For IELTS Speaking, answer the question directly."
                source = store.ingest_text(original, title="Private podcast")
                extract_source(store, source["source_id"], Provider(),
                               provider_name="ollama", model_name="local-model",
                               prompt_version="eval-v1")
                result = evaluate_source_extraction(
                    store, source["source_id"], [{
                        "kind": "recommendation", "text": original,
                        "start_char": 0, "end_char": len(original),
                    }], model_name="local-model", prompt_version="eval-v1",
                )
                self.assertEqual(result["metrics"]["f1"], 1.0)
                self.assertFalse(result["source_text_included_in_output"])
                self.assertNotIn("source_text", result)

    def test_private_source_evaluation_requires_original_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "library.sqlite3") as store:
                source = store.ingest_text("A source sentence.", title="Private")
                with store._connection:
                    store._connection.execute("UPDATE sources SET body='' WHERE source_id=?", (source["source_id"],))
                with self.assertRaises(ValueError):
                    evaluate_source_extraction(store, source["source_id"], [])

    def test_invalid_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_extraction([{"kind": "band_score", "text": "x", "start_char": 0, "end_char": 1}], [])

    def test_malformed_annotation_record_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_annotation_set(self.source, [None])
        with self.assertRaises(ValueError):
            validate_annotation_set(self.source, [{"kind": "claim", "text": "x", "start_char": True, "end_char": 1}])
