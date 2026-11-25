import json
import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pipeline import (
    extract_source, review_publication_item, review_semantic_item,
)
from open_ielts_strategy.knowledge_store import KnowledgeStore
from open_ielts_strategy.strategy_promotion import (
    StrategyPromotionError, promote_strategy_draft,
)


def strategy_content():
    return {
        "id": "speaking.direct-answer",
        "schema_version": "1.0",
        "title": "Direct answer with one supporting detail",
        "skill": "speaking",
        "summary": "Answer directly, then add one relevant supporting detail.",
        "purpose": ["Make the response clear."],
        "reasoning": ["A direct opening establishes relevance."],
        "steps": ["Answer directly.", "Add one specific detail."],
        "applicability": {"question_types": [], "parts": ["part_1"], "conditions": []},
        "limitations": ["Do not force the structure on every question."],
        "common_mistakes": ["Adding unrelated details."],
        "examples": ["I enjoy walking because it helps me relax."],
        "relationships": {"requires": [], "complements": [], "conflicts_with": [], "alternatives": []},
        "version": "0.1.0",
    }


class StrategyPromotionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = KnowledgeStore(self.root / "private" / "knowledge.sqlite3")
        self.source = self.store.ingest_text(
            "My notes: answer directly, then explain one specific reason.",
            title="My speaking notes", source_type="personal_notes",
            rights_status="self_authored",
        )
        class Extractor:
            def extract(inner, text):
                return {"summary": "summary", "items": [{
                    "kind": "recommendation", "text": text, "start_char": 0,
                    "end_char": len(text), "topic_tags": ["speaking"],
                    "rationale": "The note describes a response structure.",
                }]}
        extract_source(
            self.store, self.source["source_id"], Extractor(),
            provider_name="fixture", model_name="fixture", prompt_version="test",
        )
        self.item_id = self.store._connection.execute(
            "SELECT item_id FROM semantic_items WHERE source_id=?",
            (self.source["source_id"],),
        ).fetchone()["item_id"]
        self.draft = self.root / "draft.json"
        self.draft.write_text(json.dumps({
            "draft_format": "open-ielts-private-strategy-draft",
            "draft_version": 1,
            "draft_id": "draft_0123456789abcdef0123456789abcdef",
            "status": "needs_human_review",
            "strategy": strategy_content(),
            "private_source": {
                "source_id": self.source["source_id"],
                "semantic_item_ids": [self.item_id],
                "semantic_item_statuses": ["user_approved"],
            },
            "generation": {"provider": "fake", "model": "offline", "prompt_version": "test"},
            "review": {"content_status": "pending", "publication_status": "pending", "approved": False},
        }), encoding="utf-8")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _approve_source(self):
        review_semantic_item(self.store, self.item_id, "user_approved")
        review_publication_item(
            self.store, self.item_id, "approved",
            reviewer="rights-reviewer", rights_basis="self_authored",
        )

    def test_promotion_requires_explicit_strategy_content_review(self):
        self._approve_source()
        with self.assertRaisesRegex(StrategyPromotionError, "confirm-content-review"):
            promote_strategy_draft(
                self.store, self.draft, self.root / "candidate.json",
                reviewer="human", review_note="Reviewed strategy", confirm_content_review=False,
            )

    def test_promotion_requires_both_persisted_source_approvals(self):
        review_semantic_item(self.store, self.item_id, "user_approved")
        with self.assertRaisesRegex(StrategyPromotionError, "publication approval"):
            promote_strategy_draft(
                self.store, self.draft, self.root / "candidate.json",
                reviewer="human", review_note="Reviewed strategy", confirm_content_review=True,
            )

    def test_promotion_derives_provenance_and_keeps_private_mapping_out_of_candidate(self):
        self._approve_source()
        result = promote_strategy_draft(
            self.store, self.draft, self.root / "candidate.json",
            reviewer="human", review_note="Checked accuracy, clarity, and applicability.",
            confirm_content_review=True, receipt_dir=self.root / ".local" / "receipts",
        )
        candidate = json.loads(Path(result["candidate_path"]).read_text(encoding="utf-8"))
        self.assertEqual(candidate["provenance"], {"basis": "original", "public_references": []})
        self.assertEqual(candidate["review"], {
            "content_status": "approved", "publication_status": "approved",
        })
        serialized = json.dumps(candidate)
        self.assertNotIn(self.source["source_id"], serialized)
        self.assertNotIn(self.item_id, serialized)
        self.assertTrue(Path(result["promotion_receipt"]).is_file())
        self.assertEqual(Path(result["candidate_path"]).stat().st_mode & 0o777, 0o600)
        self.assertEqual(Path(result["promotion_receipt"]).stat().st_mode & 0o777, 0o600)
        self.assertFalse(result["published"])
        self.assertEqual(result["source_item_args"], [
            f"--source-item speaking.direct-answer={self.item_id}",
        ])


if __name__ == "__main__":
    unittest.main()
