import json
import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pipeline import (
    extract_source, list_semantic_items, review_publication_item, review_semantic_item,
)
from open_ielts_strategy.knowledge_store import KnowledgeStore
from open_ielts_strategy.strategy_drafts import generate_strategy_draft
from open_ielts_strategy.strategy_promotion import (
    StrategyPromotionError, promote_strategy_draft,
)


class FakeProvider:
    def __init__(self, output):
        self.output = output

    def generate(self, prompt):
        return self.output


def model_strategy_content():
    return {
        "title": "Direct answer with one supporting detail",
        "summary": "Answer directly, then add one relevant supporting detail.",
        "purpose": ["Make the response clear."],
        "reasoning": ["A direct opening establishes relevance."],
        "steps": ["Answer directly.", "Add one specific detail."],
        "applicability": {"question_types": [], "parts": ["part_1"], "conditions": []},
        "limitations": ["Do not force the structure on every question."],
        "common_mistakes": ["Adding unrelated details."],
        "examples": ["I enjoy walking because it helps me relax."],
        "relationships": {"requires": [], "complements": [], "conflicts_with": [], "alternatives": []},
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
        self.item_id = list_semantic_items(self.store, self.source["source_id"])[0]["item_id"]
        review_semantic_item(self.store, self.item_id, "user_approved")
        generated = generate_strategy_draft(
            self.store, self.source["source_id"],
            FakeProvider(json.dumps(model_strategy_content())),
            provider_name="fake", model_name="offline",
            strategy_id="speaking.direct-answer", skill="speaking",
            output_dir=self.root / ".local" / "strategy-drafts",
        )
        self.draft = Path(generated["private_path"])

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _approve_publication(self):
        review_publication_item(
            self.store, self.item_id, "approved",
            reviewer="rights-reviewer", rights_basis="self_authored",
        )

    def test_promotion_requires_explicit_strategy_content_review(self):
        self._approve_publication()
        with self.assertRaisesRegex(StrategyPromotionError, "confirm-content-review"):
            promote_strategy_draft(
                self.store, self.draft, self.root / "candidate.json",
                reviewer="human", review_note="Reviewed strategy", confirm_content_review=False,
            )

    def test_promotion_requires_persisted_source_publication_approval(self):
        with self.assertRaisesRegex(StrategyPromotionError, "publication approval"):
            promote_strategy_draft(
                self.store, self.draft, self.root / "candidate.json",
                reviewer="human", review_note="Reviewed strategy", confirm_content_review=True,
            )

    def test_promotion_derives_provenance_and_keeps_private_mapping_out_of_candidate(self):
        self._approve_publication()
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
        row = self.store._connection.execute(
            "SELECT status, content_reviewer FROM private_strategy_drafts WHERE draft_id=?",
            (json.loads(self.draft.read_text())["draft_id"],),
        ).fetchone()
        self.assertEqual(row["status"], "promoted")
        self.assertEqual(row["content_reviewer"], "human")

    def test_tampered_private_mapping_is_rejected_against_sqlite_record(self):
        self._approve_publication()
        envelope = json.loads(self.draft.read_text(encoding="utf-8"))
        envelope["private_source"]["semantic_item_ids"] = ["sitem_" + "f" * 32]
        self.draft.write_text(json.dumps(envelope), encoding="utf-8")
        with self.assertRaisesRegex(StrategyPromotionError, "authoritative SQLite record"):
            promote_strategy_draft(
                self.store, self.draft, self.root / "candidate.json",
                reviewer="human", review_note="Reviewed strategy", confirm_content_review=True,
            )


if __name__ == "__main__":
    unittest.main()
