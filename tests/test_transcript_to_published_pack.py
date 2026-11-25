import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pack import load_knowledge_pack
from open_ielts_strategy.knowledge_pack_builder import build_knowledge_pack
from open_ielts_strategy.knowledge_pipeline import (
    extract_source,
    list_semantic_items,
    review_publication_item,
    review_semantic_item,
)
from open_ielts_strategy.knowledge_store import KnowledgeStore


class DeterministicExtractionProvider:
    """Offline fixture provider; never calls a model or network."""

    def extract(self, text):
        return {
            "summary": "A private draft summary for the acceptance fixture.",
            "items": [{
                "kind": "recommendation",
                "text": text,
                "start_char": 0,
                "end_char": len(text),
                "topic_tags": ["speaking"],
                "rationale": "Extracted from learner-authored notes.",
            }],
        }


def published_strategy():
    return {
        "id": "speaking.answer-development",
        "schema_version": "1.0",
        "title": "Answer Development",
        "skill": "speaking",
        "summary": "Lead with a concise response, then extend it with one relevant supporting point.",
        "purpose": ["Make the response easy to follow."],
        "reasoning": ["A direct opening gives the listener a clear answer before supporting detail."],
        "steps": ["Respond to the question directly.", "Add one relevant supporting detail."],
        "applicability": {"question_types": [], "parts": ["part_1"], "conditions": []},
        "limitations": ["Do not force the structure when the question calls for a different response."],
        "common_mistakes": [],
        "examples": ["I enjoy walking because it helps me clear my mind after work."],
        "relationships": {
            "requires": [],
            "complements": [],
            "conflicts_with": [],
            "alternatives": [],
        },
        "provenance": {"basis": "original", "public_references": []},
        "review": {"content_status": "approved", "publication_status": "approved"},
        "version": "1.0.0",
    }


class TranscriptToPublishedPackAcceptanceTests(unittest.TestCase):
    def test_private_notes_to_reviewed_portable_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private_db = root / "private" / "knowledge.sqlite3"
            private_notes = (
                "In my own speaking practice, I first answer the question directly. "
                "After that, I add one specific detail that explains my answer."
            )

            with KnowledgeStore(private_db) as store:
                imported = store.ingest_text(
                    private_notes,
                    title="My speaking practice notes",
                    source_type="personal_notes",
                    language="en",
                    rights_status="self_authored",
                )
                extracted = extract_source(
                    store,
                    imported["source_id"],
                    DeterministicExtractionProvider(),
                    provider_name="offline-fixture",
                    model_name="deterministic-test",
                    prompt_version="acceptance-v1",
                )
                self.assertEqual(len(extracted), 1)
                self.assertEqual(extracted[0]["status"], "needs_review")

                items = list_semantic_items(store, imported["source_id"])
                self.assertEqual(len(items), 1)
                item_id = items[0]["item_id"]
                self.assertEqual(items[0]["text"], private_notes)
                self.assertEqual(items[0]["status"], "needs_review")

                review_semantic_item(
                    store, item_id, "user_approved",
                    "Reviewed as a useful personal speaking practice strategy.",
                )
                review_publication_item(
                    store, item_id, "approved",
                    reviewer="maintainer",
                    rights_basis="self_authored",
                    note="The source notes are my own; the published wording is independently authored.",
                )

                result = build_knowledge_pack(
                    [published_strategy()],
                    root / "candidate-pack",
                    pack_version="1.0.0",
                    human_confirmed=True,
                    store=store,
                    source_item_ids_by_strategy={
                        "speaking.answer-development": [item_id],
                    },
                )
                self.assertEqual(result["strategy_count"], 1)
                pack = load_knowledge_pack(root / "candidate-pack")
                self.assertEqual(pack.pack_version, "1.0.0")
                self.assertEqual(pack.strategies[0]["id"], "speaking.answer-development")

                public_strategy = (
                    root / "candidate-pack" / "strategies" / "speaking"
                    / "speaking.answer-development.json"
                ).read_text(encoding="utf-8")
                self.assertNotIn(imported["source_id"], public_strategy)
                self.assertNotIn(item_id, public_strategy)
                self.assertNotIn(private_notes, public_strategy)
                self.assertNotIn("private/knowledge.sqlite3", public_strategy)

            # The published artifact remains independently loadable after the
            # private SQLite connection has been closed.
            self.assertTrue(private_db.is_file())
            pack = load_knowledge_pack(root / "candidate-pack")
            self.assertEqual(pack.strategies[0]["id"], "speaking.answer-development")


if __name__ == "__main__":
    unittest.main()
