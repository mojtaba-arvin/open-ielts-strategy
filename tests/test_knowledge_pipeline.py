import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pipeline import extract_source, list_semantic_items
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
                original = "Intro.\\n\\nFor IELTS Writing Task 2, plan before drafting."
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

    def test_unknown_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "db.sqlite3") as store:
                with self.assertRaises(KeyError):
                    list_semantic_items(store, "missing")
