import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pack import load_knowledge_pack
from open_ielts_strategy.published_practice import generate_published_practice_answer
from open_ielts_strategy.text_generation import GenerationError, build_consumption_provider


class FakeProvider:
    def __init__(self, output):
        self.output = output
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        self.prompt = prompt
        return self.output


def pack_fixture(root):
    record = {
        "id": "speaking.answer-development", "schema_version": "1.0",
        "title": "Answer Development", "skill": "speaking",
        "summary": "Develop a direct answer with relevant supporting detail.",
        "purpose": ["Make the response clear."],
        "reasoning": ["A direct answer gives the listener an immediate position."],
        "steps": ["Answer the question directly.", "Add one relevant detail."],
        "applicability": {"question_types": ["personal_experience"], "parts": ["part_1"], "conditions": []},
        "limitations": ["Do not force this structure."], "common_mistakes": [],
        "examples": ["Synthetic example."],
        "relationships": {"requires": [], "complements": [], "conflicts_with": [], "alternatives": []},
        "provenance": {"basis": "original", "public_references": []},
        "review": {"content_status": "approved", "publication_status": "approved"},
        "version": "1.0.0",
    }
    folder = root / "strategies" / "speaking"
    folder.mkdir(parents=True)
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    (folder / "answer-development.json").write_bytes(payload)
    (root / "manifest.json").write_text(json.dumps({
        "format": "open-ielts-knowledge-pack", "schema_version": "1.0",
        "pack_version": "2.0.0",
        "files": [{"path": "strategies/speaking/answer-development.json",
                   "sha256": hashlib.sha256(payload).hexdigest()}],
    }), encoding="utf-8")


class PublishedPracticeTests(unittest.TestCase):
    def test_answer_is_attributed_to_retrieved_strategy_and_pack_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack_fixture(root)
            pack = load_knowledge_pack(root)
            provider = FakeProvider(json.dumps({
                "answer": "I would describe a meaningful journey.",
                "strategy_ids_used": ["speaking.answer-development"],
                "reasoning_explanation": "The strategy supports a direct opening.",
                "practice_suggestion": "Add one relevant detail.",
            }))
            result = generate_published_practice_answer(
                pack, "How can I give a direct answer?", skill="speaking", provider=provider
            )
            self.assertEqual(result["context"]["knowledge_version"], "2.0.0")
            self.assertEqual(result["strategy_attribution"][0]["strategy_id"], "speaking.answer-development")
            self.assertEqual(provider.calls, 1)

    def test_no_evidence_means_no_model_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack_fixture(root)
            pack = load_knowledge_pack(root)
            provider = FakeProvider("{}")
            result = generate_published_practice_answer(
                pack, "completely unrelated xyz query", skill="speaking", provider=provider
            )
            self.assertEqual(result["status"], "no-published-evidence")
            self.assertEqual(provider.calls, 0)

    def test_model_cannot_attribute_unknown_strategy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack_fixture(root)
            pack = load_knowledge_pack(root)
            provider = FakeProvider(json.dumps({
                "answer": "Sample.", "strategy_ids_used": ["private.source.id"],
                "reasoning_explanation": "Because.", "practice_suggestion": "Try again.",
            }))
            with self.assertRaises(GenerationError):
                generate_published_practice_answer(
                    pack, "Describe a memorable journey", skill="speaking", provider=provider
                )

    def test_consumption_registry_is_independent_from_extraction_registry(self):
        provider = build_consumption_provider("ollama", model="qwen3:8b")
        self.assertEqual(provider.model, "qwen3:8b")
        with self.assertRaises(ValueError):
            build_consumption_provider("openai-compatible", model="m", endpoint="http://insecure.example")


if __name__ == "__main__":
    unittest.main()
