import tempfile
import unittest
from pathlib import Path
import sqlite3

from open_ielts_strategy.knowledge_store import KnowledgeStore
from open_ielts_strategy.knowledge_mcp import (
    ReadOnlyKnowledgeStore, search_private_knowledge, prepare_private_practice_context,
    ingest_private_source, review_private_semantic_item, list_private_semantic_items,
)


class KnowledgeMCPTests(unittest.TestCase):
    def test_read_only_store_allows_search_but_rejects_mutations(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.sqlite3"
            with KnowledgeStore(path) as store:
                source = store.ingest_text(
                    "For IELTS Speaking, organize the answer with a clear beginning and example.",
                    title="Speaking notes",
                )
                card = store.search("Speaking answer")[0]
                store.review_card(card["card_id"], "user_approved", "My practice preference.")
            with ReadOnlyKnowledgeStore(path) as reader:
                result = search_private_knowledge(reader, "Speaking answer")
                self.assertEqual(result["result_count"], 1)
                self.assertEqual(result["results"][0]["source_id"], source["source_id"])
                with self.assertRaises(sqlite3.OperationalError):
                    reader._connection.execute("DELETE FROM sources")

    def test_mcp_practice_context_uses_approved_strategy_and_source_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.sqlite3"
            with KnowledgeStore(path) as store:
                source = store.ingest_text(
                    "For IELTS Speaking, organize the answer with a clear beginning and example.",
                    title="Speaking notes",
                )
                card = store.search("Speaking answer")[0]
                store.review_card(card["card_id"], "user_approved")
            with ReadOnlyKnowledgeStore(path) as reader:
                result = prepare_private_practice_context(
                    reader, "Describe a person", skill="speaking"
                )
                self.assertEqual(result["evidence_count"], 1)
                self.assertEqual(result["evidence"][0]["source"]["source_id"], source["source_id"])


    def test_opt_in_ingest_tool_writes_only_to_fixed_local_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "private" / "library.sqlite3"
            result = ingest_private_source(
                str(path), "For IELTS Speaking, use a clear structure.",
                "Private podcast", source_type="podcast_transcript",
                rights_status="personal_copy_unverified",
            )
            self.assertTrue(result["stored_locally"])
            self.assertEqual(result["segment_count"], 1)
            with KnowledgeStore(path) as store:
                source = store.get_source(result["source_id"], include_body=True)
                self.assertEqual(source["body"], "For IELTS Speaking, use a clear structure.")

    def test_opt_in_review_tool_updates_semantic_item_state(self):
        from open_ielts_strategy.knowledge_pipeline import persist_segment_extraction
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "private.sqlite3"
            with KnowledgeStore(path) as store:
                source = store.ingest_text("Use a clear structure for IELTS Speaking.", title="Private")
                segment = store.get_source(source["source_id"])["segments"][0]
                persisted = persist_segment_extraction(
                    store, source["source_id"], segment["segment_id"],
                    {"summary": "Structure.", "items": [{
                        "kind": "recommendation", "text": segment["text"],
                        "start_char": 0, "end_char": len(segment["text"]),
                        "topic_tags": ["speaking"], "rationale": "Source advice.",
                    }]}, provider_name="test", model_name="fixture", prompt_version="v1",
                )
            result = review_private_semantic_item(
                str(path), persisted["item_ids"][0], "user_approved", "Personal preference."
            )
            self.assertEqual(result["status"], "user_approved")


    def test_mcp_lists_semantic_items_without_exposing_source_body(self):
        from open_ielts_strategy.knowledge_pipeline import persist_segment_extraction
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "private.sqlite3"
            with KnowledgeStore(path) as store:
                source = store.ingest_text("For IELTS Speaking, use a clear opening.", title="Private podcast")
                segment = store.get_source(source["source_id"])["segments"][0]
                persist_segment_extraction(
                    store, source["source_id"], segment["segment_id"],
                    {"summary": "A useful opening.", "items": [{
                        "kind": "recommendation", "text": segment["text"],
                        "start_char": 0, "end_char": len(segment["text"]),
                        "topic_tags": ["speaking"], "rationale": "The speaker recommends an opening.",
                    }]}, provider_name="test", model_name="fixture", prompt_version="v1",
                )
            with ReadOnlyKnowledgeStore(path) as reader:
                result = list_private_semantic_items(reader, source["source_id"])
                self.assertEqual(result["item_count"], 1)
                self.assertEqual(result["items"][0]["status"], "needs_review")
                self.assertEqual(result["items"][0]["source_text_state"], "retained")
                self.assertNotIn("body", result)

    def test_missing_database_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises((OSError, ValueError)):
                ReadOnlyKnowledgeStore(Path(tmp) / "missing.sqlite3")
