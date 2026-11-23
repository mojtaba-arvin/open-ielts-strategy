import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.hybrid_retrieval import hybrid_search, suggest_overlaps
from open_ielts_strategy.knowledge_store import KnowledgeStore


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
