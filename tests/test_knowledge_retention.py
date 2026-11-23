import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_store import KnowledgeStore
from open_ielts_strategy.knowledge_pipeline import (
    extract_source, list_semantic_items, purge_source_text,
)


class Provider:
    def extract(self, text):
        phrase = "Plan your IELTS Speaking answer before you begin."
        start = text.index(phrase)
        return {"summary": "Plan before answering.", "items": [{
            "kind": "recommendation", "text": phrase, "start_char": start,
            "end_char": start + len(phrase), "topic_tags": ["speaking"],
            "rationale": "Direct recommendation.",
        }]}


class KnowledgeRetentionTests(unittest.TestCase):
    def test_purge_requires_confirmation_and_reviewed_semantic_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "db.sqlite3") as store:
                source = store.ingest_text("Intro. Plan your IELTS Speaking answer before you begin.", title="Podcast")
                extract_source(store, source["source_id"], Provider(),
                               provider_name="test", model_name="fixture", prompt_version="v1")
                with self.assertRaises(ValueError):
                    purge_source_text(store, source["source_id"])
                with self.assertRaises(ValueError):
                    purge_source_text(store, source["source_id"], confirm=True)

    def test_purge_removes_raw_text_but_preserves_reviewed_items_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "db.sqlite3") as store:
                original = "Intro. Plan your IELTS Speaking answer before you begin."
                source = store.ingest_text(original, title="Podcast")
                extract_source(store, source["source_id"], Provider(),
                               provider_name="test", model_name="fixture", prompt_version="v1")
                items = list_semantic_items(store, source["source_id"])
                store._connection.execute(
                    "UPDATE semantic_items SET status='user_approved' WHERE item_id=?",
                    (items[0]["item_id"],),
                )
                store._connection.commit()
                result = purge_source_text(store, source["source_id"], confirm=True)
                self.assertFalse(result["raw_body_retained"])
                self.assertEqual(result["state"], "body_purged")
                source_after = store.get_source(source["source_id"], include_body=True)
                self.assertEqual(source_after["body"], "")
                self.assertTrue(all(segment["text"] == "" for segment in source_after["segments"]))
                retained = list_semantic_items(store, source["source_id"])
                self.assertEqual(retained[0]["text"], items[0]["text"])
                self.assertEqual(retained[0]["status"], "user_approved")
                self.assertEqual(retained[0]["source_text_state"], "body_purged")
                self.assertEqual(source_after["content_sha256"], source["content_sha256"])
                self.assertEqual(store.search("Plan IELTS Speaking"), [])

    def test_purged_semantic_knowledge_remains_searchable(self):
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "db.sqlite3") as store:
                source = store.ingest_text("Plan your IELTS Speaking answer before you begin.", title="Podcast")
                extract_source(store, source["source_id"], Provider(),
                               provider_name="test", model_name="fixture", prompt_version="v1")
                item = list_semantic_items(store, source["source_id"])[0]
                store._connection.execute(
                    "UPDATE semantic_items SET status='user_approved' WHERE item_id=?", (item["item_id"],)
                )
                store._connection.commit()
                purge_source_text(store, source["source_id"], confirm=True)
                from open_ielts_strategy.hybrid_retrieval import hybrid_search
                retained = list_semantic_items(store, source["source_id"])
                self.assertEqual(len(retained), 1)
                self.assertEqual(retained[0]["text"], item["text"])
                self.assertEqual(retained[0]["status"], "user_approved")
                results = hybrid_search(store, item["text"])
                self.assertTrue(results, "reviewed semantic item should remain in hybrid retrieval")
                self.assertEqual(results[0]["card_id"], item["item_id"])
                self.assertEqual(results[0]["source_text_state"], "body_purged")
