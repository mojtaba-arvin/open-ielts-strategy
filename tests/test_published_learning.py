import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pack import load_knowledge_pack
from open_ielts_strategy.published_learning import (
    create_published_study_plan, get_published_learning_path,
    explain_published_strategy, generate_published_strategy_example,
)
from open_ielts_strategy.text_generation import GenerationError


class FakeProvider:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        self.prompt = prompt
        return self.value


def make_pack(root):
    strategy = {
        "id": "speaking.answer-development", "schema_version": "1.0",
        "title": "Answer Development", "skill": "speaking",
        "summary": "Develop a direct answer with relevant supporting detail.",
        "purpose": ["Make the response clear."],
        "reasoning": ["A direct answer gives the listener an immediate position."],
        "steps": ["Answer directly.", "Add one relevant detail."],
        "applicability": {"question_types": [], "parts": ["part_1"], "conditions": []},
        "limitations": ["Do not force this structure."], "common_mistakes": [],
        "examples": ["An existing synthetic example that should not be copied verbatim."],
        "relationships": {"requires": [], "complements": [], "conflicts_with": [], "alternatives": []},
        "provenance": {"basis": "original", "public_references": []},
        "review": {"content_status": "approved", "publication_status": "approved"},
        "version": "1.0.0",
    }
    learning_path = {
        "id": "speaking.foundations", "schema_version": "1.0",
        "title": "Speaking Foundations", "skill": "speaking",
        "description": "A short introduction.", "objectives": ["Answer clearly."],
        "steps": [{"order": 1, "strategy_id": "speaking.answer-development",
                   "activity": "Practice direct answers."}],
        "prerequisites": [],
        "provenance": {"basis": "original", "public_references": []},
        "review": {"content_status": "approved", "publication_status": "approved"},
        "version": "1.0.0",
    }
    folder = root / "strategies" / "speaking"
    folder.mkdir(parents=True)
    records = {
        "strategies/speaking/answer-development.json": strategy,
        "learning-paths/speaking/foundations.json": learning_path,
    }
    entries = []
    for relative, record in records.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        path.write_bytes(payload)
        entries.append({"path": relative, "sha256": hashlib.sha256(payload).hexdigest()})
    (root / "manifest.json").write_text(json.dumps({
        "format": "open-ielts-knowledge-pack", "schema_version": "1.0",
        "pack_version": "1.0.0", "files": sorted(entries, key=lambda item: item["path"]),
    }), encoding="utf-8")


class PublishedLearningTests(unittest.TestCase):
    def test_study_plan_resolves_curated_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            pack = load_knowledge_pack(root)
            plan = create_published_study_plan(pack, skill="speaking")
            self.assertEqual(plan["status"], "ready")
            self.assertEqual(plan["learning_paths"][0]["resolved_steps"][0]["strategy_id"],
                             "speaking.answer-development")
            self.assertEqual(get_published_learning_path(pack, "speaking.foundations")["pack_version"], "1.0.0")

    def test_study_plan_handles_missing_published_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            pack = load_knowledge_pack(root)
            self.assertEqual(create_published_study_plan(pack, skill="writing")["status"],
                             "no-published-learning-path")

    def test_mentor_explanation_is_versioned_and_structured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            pack = load_knowledge_pack(root)
            provider = FakeProvider(json.dumps({
                "explanation": "Answer the question directly.",
                "when_to_use": "Use it for direct personal questions.",
                "limitations": "Do not force it onto every prompt.",
                "exercise": "Answer one short personal question.",
            }))
            result = explain_published_strategy(pack, "speaking.answer-development", provider=provider)
            self.assertEqual(result["pack_version"], "1.0.0")
            self.assertEqual(provider.calls, 1)

    def test_example_generation_rejects_exact_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            pack = load_knowledge_pack(root)
            example = "An original response that is distinct from the existing synthetic example."
            provider = FakeProvider(json.dumps({
                "example": example,
                "strategy_application": "It starts with a direct answer.",
                "learning_note": "Add one supporting detail.",
            }))
            result = generate_published_strategy_example(
                pack, "speaking.answer-development", "Describe a useful skill", provider=provider
            )
            self.assertEqual(result["strategy_id"], "speaking.answer-development")

    def test_example_generation_rejects_existing_example_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            pack = load_knowledge_pack(root)
            existing = pack.get_strategy("speaking.answer-development")["examples"][0]
            provider = FakeProvider(json.dumps({
                "example": existing,
                "strategy_application": "Copied.",
                "learning_note": "Copied.",
            }))
            with self.assertRaises(GenerationError):
                generate_published_strategy_example(
                    pack, "speaking.answer-development", "Describe a useful skill", provider=provider
                )


if __name__ == "__main__":
    unittest.main()
