import json
import os
import subprocess
import sys
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
                    learning_paths=[{
                        "id": "speaking.part1.foundation",
                        "schema_version": "1.0",
                        "title": "Speaking Part 1 Foundations",
                        "skill": "speaking",
                        "description": "A short sequence for focused Part 1 responses.",
                        "objectives": ["Answer the prompt clearly and support the response."],
                        "steps": [{
                            "order": 1,
                            "strategy_id": "speaking.focused-response",
                            "activity": "Practise a concise response with one supporting explanation.",
                        }],
                        "prerequisites": [],
                        "provenance": {"basis": "original", "public_references": []},
                        "review": {"content_status": "approved", "publication_status": "approved"},
                        "version": "1.0.0",
                    }],
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

            # Simulate a fresh consumer workspace: copy only the published
            # pack, then exercise the public runtime adapters in a new process.
            consumer = root / "fresh-consumer"
            consumer.mkdir()
            consumer_pack = consumer / "knowledge"
            import shutil
            shutil.copytree(root / "candidate-pack", consumer_pack)
            consumer_script = r"""
import json
import sys
from open_ielts_strategy.knowledge_pack import load_knowledge_pack
from open_ielts_strategy.published_knowledge_mcp import (
    get_published_strategy, search_published_strategies,
)
from open_ielts_strategy.published_learning import (
    explain_published_strategy, generate_published_strategy_example,
)
from open_ielts_strategy.published_practice import generate_published_practice_answer
from open_ielts_strategy.study_progression import build_study_progression

class FakeProvider:
    def generate(self, prompt):
        if prompt.startswith("Act as an IELTS learning mentor."):
            return json.dumps({
                "explanation": "Start with a clear response, then support it.",
                "when_to_use": "Use this for suitable short speaking prompts.",
                "limitations": "Adapt it when the prompt needs a different structure.",
                "exercise": "Answer three prompts and add one relevant reason to each.",
            })
        if prompt.startswith("Create a new original IELTS learning example."):
            return json.dumps({
                "example": "I usually read before breakfast because the quiet helps me focus.",
                "strategy_application": "The response is direct and supported by one reason.",
                "learning_note": "Keep the supporting reason relevant to the answer.",
            })
        if prompt.startswith("You are an IELTS learning mentor. Produce an original response"):
            return json.dumps({
                "answer": "I prefer studying early because I can focus before other tasks begin.",
                "strategy_ids_used": ["speaking.focused-response"],
                "reasoning_explanation": "The response gives a clear preference and supports it.",
                "practice_suggestion": "Try the same structure with two different preferences.",
            })
        raise AssertionError("unexpected model prompt")

pack = load_knowledge_pack(sys.argv[1])
strategy_id = "speaking.focused-response"
assert get_published_strategy(pack, strategy_id)["strategy"]["id"] == strategy_id
mcp = search_published_strategies(pack, "focused response supporting explanation", skill="speaking")
assert mcp["result_count"] >= 1
study = build_study_progression(pack, skill="speaking")
assert study["status"] == "ready"
assert "speaking.part1.foundation" in study["available_path_ids"]
provider = FakeProvider()
mentor = explain_published_strategy(pack, strategy_id, provider=provider)
assert mentor["strategy_id"] == strategy_id
example = generate_published_strategy_example(
    pack, strategy_id, "Give a short preference answer.", provider=provider
)
assert example["example"]
practice = generate_published_practice_answer(
    pack, "What time of day do you prefer to study?", skill="speaking", provider=provider
)
assert practice["status"] == "generated"
assert practice["strategy_attribution"][0]["strategy_id"] == strategy_id
print("fresh-consumer-ok")
"""
            env = os.environ.copy()
            repository_root = str(Path(__file__).resolve().parents[1])
            env["PYTHONPATH"] = os.pathsep.join(
                value for value in (repository_root, env.get("PYTHONPATH", "")) if value
            )
            process = subprocess.run(
                [sys.executable, "-c", consumer_script, str(consumer_pack)],
                cwd=consumer, env=env, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertIn("fresh-consumer-ok", process.stdout)
            self.assertFalse((consumer / ".local" / "knowledge.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
