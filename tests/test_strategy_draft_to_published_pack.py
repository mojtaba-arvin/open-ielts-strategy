import json
import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pack import load_knowledge_pack
from open_ielts_strategy.knowledge_pack_builder import build_knowledge_pack
from open_ielts_strategy.knowledge_pipeline import (
    extract_source, list_semantic_items, review_publication_item, review_semantic_item,
)
from open_ielts_strategy.knowledge_store import KnowledgeStore
from open_ielts_strategy.strategy_drafts import generate_strategy_draft
from open_ielts_strategy.strategy_promotion import promote_strategy_draft


class FakeExtractionProvider:
    def extract(self, text):
        return {
            "summary": "A private learner-authored note.",
            "items": [{
                "kind": "recommendation",
                "text": text,
                "start_char": 0,
                "end_char": len(text),
                "topic_tags": ["speaking"],
                "rationale": "The note describes a response structure.",
            }],
        }


class FakeGenerationProvider:
    def generate(self, prompt):
        self.prompt = prompt
        return json.dumps({
            "title": "Focused response with supporting explanation",
            "summary": "Use a focused opening followed by one supporting explanation.",
            "purpose": ["Keep the response clear and relevant."],
            "reasoning": ["A focused opening establishes relevance before supporting detail."],
            "steps": [
                "Give a direct response to the prompt.",
                "Explain the response with one specific supporting point.",
            ],
            "applicability": {
                "question_types": [],
                "parts": ["part_1"],
                "conditions": [],
            },
            "limitations": ["Adapt the structure when the question needs a different response."],
            "common_mistakes": ["Adding details that do not support the main response."],
            "examples": ["I prefer mornings because I can concentrate before the day gets busy."],
            "relationships": {
                "requires": [],
                "complements": [],
                "conflicts_with": [],
                "alternatives": [],
            },
        })


class StrategyDraftToPublishedPackAcceptanceTests(unittest.TestCase):
    def test_private_source_to_generated_strategy_to_independent_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private_db = root / ".local" / "knowledge.sqlite3"
            private_notes = (
                "For my speaking practice, I keep the opening concise and then "
                "explain my choice with one relevant detail."
            )
            with KnowledgeStore(private_db) as store:
                source = store.ingest_text(
                    private_notes,
                    title="My speaking practice notes",
                    source_type="personal_notes",
                    language="en",
                    rights_status="self_authored",
                )
                extract_source(
                    store, source["source_id"], FakeExtractionProvider(),
                    provider_name="offline-fixture",
                    model_name="deterministic-extractor",
                    prompt_version="acceptance-v1",
                )
                item = list_semantic_items(store, source["source_id"])[0]
                self.assertEqual(item["status"], "needs_review")
                review_semantic_item(
                    store, item["item_id"], "user_approved",
                    "Reviewed as a useful personal practice note.",
                )

                provider = FakeGenerationProvider()
                generated = generate_strategy_draft(
                    store, source["source_id"], provider,
                    provider_name="offline-fixture",
                    model_name="deterministic-generator",
                    strategy_id="speaking.focused-response",
                    skill="speaking",
                    output_dir=root / ".local" / "strategy-drafts",
                )
                self.assertFalse(generated["publishable"])
                self.assertNotIn(source["source_id"], provider.prompt)
                self.assertNotIn(item["item_id"], provider.prompt)

                draft_path = Path(generated["private_path"])
                draft = json.loads(draft_path.read_text(encoding="utf-8"))
                self.assertEqual(draft["status"], "needs_human_review")
                self.assertEqual(draft["review"]["approved"], False)
                # Human edit is confined to the strategy content. Private
                # mapping, generation metadata, and review state stay intact.
                draft["strategy"]["summary"] = (
                    "Begin with a clear response and then justify it with one relevant reason."
                )
                draft_path.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")

                review_publication_item(
                    store, item["item_id"], "approved",
                    reviewer="rights-reviewer",
                    rights_basis="self_authored",
                    note="Learner-authored notes; public strategy wording reviewed separately.",
                )
                promoted = promote_strategy_draft(
                    store, draft_path, root / ".local" / "strategy-candidates" / "focused-response.json",
                    reviewer="content-reviewer",
                    review_note="Reviewed accuracy, clarity, applicability, and wording.",
                    confirm_content_review=True,
                    receipt_dir=root / ".local" / "strategy-drafts" / "promotions",
                )
                candidate = json.loads(Path(promoted["candidate_path"]).read_text(encoding="utf-8"))
                self.assertEqual(candidate["provenance"]["basis"], "original")
                self.assertEqual(candidate["review"]["content_status"], "approved")
                self.assertNotIn(source["source_id"], json.dumps(candidate))
                self.assertNotIn(item["item_id"], json.dumps(candidate))

                result = build_knowledge_pack(
                    [candidate],
                    root / "candidate-pack",
                    pack_version="1.0.0",
                    human_confirmed=True,
                    store=store,
                    source_item_ids_by_strategy={
                        "speaking.focused-response": [item["item_id"]],
                    },
                )
                self.assertEqual(result["strategy_count"], 1)
                self.assertTrue(result["exact_leak_scan"]["passed"])
                self.assertFalse(result["committed_to_git"])
                self.assertFalse(result["pushed_to_remote"])

            # The public pack is independently usable after the private
            # database connection is closed.
            self.assertTrue(private_db.is_file())
            pack = load_knowledge_pack(root / "candidate-pack")
            self.assertEqual(pack.pack_version, "1.0.0")
            self.assertEqual(pack.strategies[0]["id"], "speaking.focused-response")
            public_json = (
                root / "candidate-pack" / "strategies" / "speaking"
                / "speaking.focused-response.json"
            ).read_text(encoding="utf-8")
            self.assertNotIn(source["source_id"], public_json)
            self.assertNotIn(item["item_id"], public_json)
            self.assertNotIn(private_notes, public_json)
            self.assertNotIn("knowledge.sqlite3", public_json)


if __name__ == "__main__":
    unittest.main()
