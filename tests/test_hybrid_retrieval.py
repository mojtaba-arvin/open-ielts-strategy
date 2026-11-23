import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.hybrid_retrieval import hybrid_search, suggest_overlaps
from open_ielts_strategy.knowledge_store import KnowledgeStore
from open_ielts_strategy.knowledge_pipeline import extract_source, list_semantic_items
from open_ielts_strategy.practice_context import prepare_practice_context


class FakeEmbedding:
    def encode(self, texts):
        return [[1.0, 0.0] if "planning" in text.lower() or "plan" in text.lower() else [0.0, 1.0] for text in texts]


class HybridRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = KnowledgeStore(Path(self.tmp.name) / "library.sqlite3")
        self.store.ingest_text("For IELTS Writing Task 2, plan before drafting.", title="Planning")
        self.store.ingest_text("For IELTS Speaking, practice fluency every day.", title="Fluency")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_lexical_fallback_keeps_provenance(self):
        results = hybrid_search(self.store, "Writing plan")
        self.assertEqual(results[0]["retrieval_mode"], "lexical-fallback")
        self.assertIn("source_id", results[0])
        self.assertIn("start_char", results[0])

    def test_local_embedding_reranks_and_can_retrieve_nonlexical_candidates(self):
        results = hybrid_search(self.store, "essay preparation", provider=FakeEmbedding())
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["retrieval_mode"], "hybrid-local")
        self.assertIsNotNone(results[0]["semantic_score"])

    def test_invalid_embedding_count_fails_closed(self):
        class Bad:
            def encode(self, texts): return []
        with self.assertRaises(ValueError):
            hybrid_search(self.store, "anything", provider=Bad())

    def test_non_finite_embedding_values_are_rejected(self):
        class Bad:
            def encode(self, texts): return [[float("nan")], *([[1.0]] * (len(texts) - 1))]
        with self.assertRaises(ValueError):
            hybrid_search(self.store, "anything", provider=Bad())

    def test_embedding_dimension_mismatch_is_rejected(self):
        class Bad:
            def encode(self, texts): return [[1.0, 0.0], *([[1.0]] * (len(texts) - 1))]
        with self.assertRaises(ValueError):
            hybrid_search(self.store, "anything", provider=Bad())

    def test_overlap_suggestions_do_not_create_relations(self):
        cards = [
            {"card_id": "a", "text": "Plan your IELTS essay before drafting."},
            {"card_id": "b", "text": "Plan your essay before writing."},
        ]
        suggestions = suggest_overlaps(cards, threshold=0.3)
        self.assertEqual(suggestions[0]["suggestion"], "possible_overlap_review")
        self.assertFalse(suggestions[0]["relation_created"])


    def test_semantic_items_are_searchable_with_original_source_anchors(self):
        class SemanticProvider:
            def extract(self, text):
                phrase = "Use a clear structure for IELTS Speaking."
                start = text.index(phrase)
                return {"summary": "Structure advice.", "items": [{
                    "kind": "recommendation", "text": phrase, "start_char": start,
                    "end_char": start + len(phrase), "topic_tags": ["speaking"],
                    "rationale": "Explicit recommendation in the source.",
                }]}
        source = self.store.ingest_text(
            "Introductory discussion. " + "Use a clear structure for IELTS Speaking.",
            title="Speaking source",
        )
        extract_source(self.store, source["source_id"], SemanticProvider(),
                       provider_name="test", model_name="fixture", prompt_version="v1")
        items = list_semantic_items(self.store, source["source_id"])
        self.store._connection.execute(
            "UPDATE semantic_items SET status='user_approved' WHERE item_id=?", (items[0]["item_id"],)
        )
        self.store._connection.commit()
        results = hybrid_search(self.store, "clear structure speaking")
        self.assertTrue(any(result["card_id"] == items[0]["item_id"] for result in results))
        match = next(result for result in results if result["card_id"] == items[0]["item_id"])
        self.assertEqual(match["text"] if "text" in match else match["excerpt"], "Use a clear structure for IELTS Speaking.")
        self.assertEqual(match["start_char"], len("Introductory discussion. "))

    def test_practice_context_uses_reviewed_cards_and_carries_citations(self):
        source = self.store.ingest_text("For IELTS Speaking, structure your answer clearly.", title="Speaking guide")
        card = self.store.search("Speaking structure")[0]
        self.store.review_card(card["card_id"], "user_approved", "I want to practice this.")
        result = prepare_practice_context(self.store, "How should I answer a cue card?", skill="speaking")
        self.assertEqual(result["evidence_count"], 1)
        self.assertEqual(result["evidence"][0]["source"]["source_id"], source["source_id"])
        self.assertEqual(result["answer_generation"], "not_performed")

    def test_practice_context_excludes_unreviewed_by_default(self):
        source = self.store.ingest_text("For IELTS Speaking, structure your answer clearly.", title="Speaking guide")
        result = prepare_practice_context(self.store, "How should I answer?", skill="speaking")
        self.assertEqual(result["evidence_count"], 0)
        draft = prepare_practice_context(self.store, "How should I answer?", skill="speaking", include_unreviewed=True)
        self.assertGreaterEqual(draft["evidence_count"], 1)
        self.assertTrue(any(item["source"]["source_id"] == source["source_id"] for item in draft["evidence"]))

    def test_threshold_validation(self):
        with self.assertRaises(ValueError):
            suggest_overlaps([], threshold=2)

    def test_local_embedding_adapter_rejects_remote_model_ids(self):
        from open_ielts_strategy.hybrid_retrieval import LocalSentenceTransformer
        with self.assertRaises(ValueError):
            LocalSentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    def test_query_length_is_bounded(self):
        with self.assertRaises(ValueError):
            hybrid_search(self.store, "x" * 1001)
