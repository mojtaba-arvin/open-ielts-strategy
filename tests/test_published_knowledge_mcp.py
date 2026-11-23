import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pack import load_knowledge_pack
from open_ielts_strategy.published_knowledge_mcp import (
    search_published_strategies, get_published_strategy,
    get_related_published_strategies,
)


def make_pack(root):
    strategy = {
        "id": "speaking.answer-development", "schema_version": "1.0",
        "title": "Answer Development", "skill": "speaking",
        "summary": "Develop a direct answer with supporting detail.",
        "purpose": ["Make the response clear."],
        "reasoning": ["A direct answer establishes the response."],
        "steps": ["Answer directly.", "Add a relevant detail."],
        "applicability": {"question_types": [], "parts": ["part_1"], "conditions": []},
        "limitations": ["Do not force a template."], "common_mistakes": [],
        "examples": ["Synthetic example."],
        "relationships": {"requires": [], "complements": [], "conflicts_with": [], "alternatives": []},
        "provenance": {"basis": "original", "public_references": []},
        "review": {"content_status": "approved", "publication_status": "approved"},
        "version": "1.0.0",
    }
    folder = root / "strategies" / "speaking"
    folder.mkdir(parents=True)
    payload = json.dumps(strategy, sort_keys=True, separators=(",", ":")).encode()
    (folder / "answer-development.json").write_bytes(payload)
    manifest = {
        "format": "open-ielts-knowledge-pack", "schema_version": "1.0",
        "pack_version": "1.2.0",
        "files": [{"path": "strategies/speaking/answer-development.json",
                   "sha256": hashlib.sha256(payload).hexdigest()}],
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


class PublishedKnowledgeMCPTests(unittest.TestCase):
    def test_search_and_get_tools_use_pack_version_and_no_private_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            pack = load_knowledge_pack(root)
            search = search_published_strategies(pack, "direct answer", skill="speaking")
            self.assertEqual(search["result_count"], 1)
            self.assertEqual(search["pack_version"], "1.2.0")
            detail = get_published_strategy(pack, "speaking.answer-development")
            self.assertEqual(detail["strategy"]["id"], "speaking.answer-development")
            self.assertNotIn("source_id", json.dumps(detail))

    def test_related_strategy_lookup_is_typed_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            pack = load_knowledge_pack(root)
            result = get_related_published_strategies(pack, "speaking.answer-development")
            self.assertEqual(result["relationships"]["requires"], [])

    def test_unknown_strategy_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            pack = load_knowledge_pack(root)
            with self.assertRaises(KeyError):
                get_published_strategy(pack, "missing.strategy")


if __name__ == "__main__":
    unittest.main()
