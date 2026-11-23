import tempfile
import unittest
from pathlib import Path
import sqlite3

from open_ielts_strategy.knowledge_store import KnowledgeStore
from open_ielts_strategy.knowledge_mcp import (
    ReadOnlyKnowledgeStore, search_private_knowledge, prepare_private_practice_context,
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

    def test_missing_database_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises((OSError, ValueError)):
                ReadOnlyKnowledgeStore(Path(tmp) / "missing.sqlite3")
