import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pipeline import extract_source, list_semantic_items, review_semantic_item
from open_ielts_strategy.knowledge_store import KnowledgeStore


class FakeProvider:
    def extract(self, text):
        return {
            "summary": "Candidate planning advice.",
            "items": [{
                "kind": "recommendation", "text": text,
                "start_char": 0, "end_char": len(text),
                "topic_tags": ["writing_task_2"], "rationale": "A source recommendation.",
            }],
        }


class KnowledgePipelineTests(unittest.TestCase):
    def test_extraction_is_persisted_with_absolute_offsets_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "db.sqlite3") as store:
                original = "Intro.\n\nFor IELTS Writing Task 2, plan before drafting."
                source = store.ingest_text(original, title="Podcast")
                results = extract_source(
                    store, source["source_id"], FakeProvider(),
                    provider_name="test-provider", model_name="local-test",
                    prompt_version="extract-v1",
                )
                self.assertEqual(len(results), 2)
                items = list_semantic_items(store, source["source_id"])
                self.assertEqual(len(items), 2)
                for item in items:
                    self.assertEqual(original[item["start_char"]:item["end_char"]], item["text"])
                    self.assertEqual(item["status"], "needs_review")
                    self.assertEqual(item["provider_name"], "test-provider")
                    self.assertEqual(item["prompt_version"], "extract-v1")

    def test_semantic_item_review_is_persisted_and_preserves_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "db.sqlite3") as store:
                source = store.ingest_text("Speaking answer structure.", title="Podcast")
                outputs = extract_source(
                    store, source["source_id"], FakeProvider(),
                    provider_name="test-provider", model_name="local-test",
                    prompt_version="extract-v1",
                )
                items = list_semantic_items(store, source["source_id"])
                reviewed = review_semantic_item(store, items[0]["item_id"], "user_approved", "Useful for my practice.")
                self.assertEqual(reviewed["status"], "user_approved")
                refreshed = list_semantic_items(store, source["source_id"])[0]
                self.assertEqual(refreshed["status"], "user_approved")
                self.assertEqual(refreshed["text"], "Speaking answer structure.")

    def test_unknown_semantic_item_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "db.sqlite3") as store:
                with self.assertRaises(KeyError):
                    review_semantic_item(store, "sitem_missing", "user_approved")

    def test_unknown_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "db.sqlite3") as store:
                with self.assertRaises(KeyError):
                    list_semantic_items(store, "missing")
