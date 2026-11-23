import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pipeline import persist_segment_extraction
from open_ielts_strategy.knowledge_store import KnowledgeStore
from open_ielts_strategy.strategy_composition import build_playbook
from scripts.knowledge_playbook import load_cards


class SemanticPlaybookCliTests(unittest.TestCase):
    def test_semantic_item_can_be_selected_for_source_cited_playbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "library.sqlite3") as store:
                source = store.ingest_text(
                    "For IELTS Speaking, give a direct answer and add one personal example.",
                    title="Speaking podcast",
                )
                segment = store.get_source(source["source_id"])["segments"][0]
                result = persist_segment_extraction(
                    store, source["source_id"], segment["segment_id"],
                    {"summary": "Direct answer and personal example.", "items": [{
                        "kind": "recommendation", "text": segment["text"],
                        "start_char": 0, "end_char": len(segment["text"]),
                        "topic_tags": ["speaking"], "rationale": "The speaker recommends a direct answer.",
                    }]}, provider_name="test", model_name="fixture", prompt_version="v1",
                )
                item_id = result["item_ids"][0]
                store._connection.execute(
                    "UPDATE semantic_items SET status='user_approved' WHERE item_id=?", (item_id,)
                )
                store._connection.commit()
                cards = load_cards(store, [item_id])
                self.assertEqual(cards[0]["card_id"], item_id)
                self.assertEqual(cards[0]["source_id"], source["source_id"])
                playbook = build_playbook(cards, title="My Speaking approach")
                self.assertEqual(playbook["steps"][0]["source"]["card_id"], item_id)
                self.assertFalse(playbook["steps"][0]["requires_personal_review"])
