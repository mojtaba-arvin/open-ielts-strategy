import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pipeline import (
    assert_items_publishable, persist_segment_extraction,
    review_publication_item, review_semantic_item, get_publication_review,
    list_publication_review_history,
)
from open_ielts_strategy.knowledge_store import KnowledgeStore


class PublicationGovernanceTests(unittest.TestCase):
    def make_item(self, store):
        source = store.ingest_text(
            "For IELTS Speaking, answer directly and add one relevant example.",
            title="Private notes", rights_status="permission_confirmed",
        )
        segment = store.get_source(source["source_id"])["segments"][0]
        result = persist_segment_extraction(
            store, source["source_id"], segment["segment_id"],
            {"summary": "Candidate speaking guidance.", "items": [{
                "kind": "recommendation", "text": segment["text"],
                "start_char": 0, "end_char": len(segment["text"]),
                "topic_tags": ["speaking"], "rationale": "A candidate recommendation.",
            }]},
            provider_name="fixture", model_name="test", prompt_version="test-v1",
        )
        return result["item_ids"][0]

    def test_publication_approval_is_independent_and_requires_content_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "private.sqlite3") as store:
                item_id = self.make_item(store)
                with self.assertRaisesRegex(ValueError, "content approval"):
                    review_publication_item(
                        store, item_id, "approved", reviewer="maintainer",
                        rights_basis="permission_confirmed",
                    )
                review_semantic_item(store, item_id, "user_approved", "Content review note.")
                history = list_publication_review_history(store, item_id)
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]["publication_status"], "rejected")
                with self.assertRaisesRegex(ValueError, "publication approval"):
                    assert_items_publishable(store, [item_id])
                with self.assertRaisesRegex(ValueError, "rights basis"):
                    review_publication_item(store, item_id, "approved", reviewer="maintainer")
                result = review_publication_item(
                    store, item_id, "approved", reviewer="maintainer",
                    rights_basis="permission_confirmed", note="Private evidence checked.",
                )
                self.assertEqual(result["content_status"], "user_approved")
                self.assertEqual(result["publication_status"], "approved")
                eligible = assert_items_publishable(store, [item_id])
                self.assertEqual(eligible[0]["rights_basis"], "permission_confirmed")
                self.assertNotIn("note", eligible[0])
                self.assertEqual(get_publication_review(store, item_id)["note"], "Private evidence checked.")
                history = list_publication_review_history(store, item_id)
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]["publication_status"], "approved")
                self.assertEqual(history[0]["note"], "Private evidence checked.")
                self.assertEqual(
                    store._connection.execute(
                        "SELECT status FROM semantic_items WHERE item_id=?", (item_id,)
                    ).fetchone()["status"],
                    "user_approved",
                )

    def test_rejected_publication_review_blocks_pack_eligibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            with KnowledgeStore(Path(tmp) / "private.sqlite3") as store:
                item_id = self.make_item(store)
                review_semantic_item(store, item_id, "supported")
                review_publication_item(
                    store, item_id, "rejected", reviewer="maintainer",
                    note="Rights are not cleared.",
                )
                with self.assertRaisesRegex(ValueError, "publication approval"):
                    assert_items_publishable(store, [item_id])


if __name__ == "__main__":
    unittest.main()
