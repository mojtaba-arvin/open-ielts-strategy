import json
import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pack_builder import build_knowledge_pack
from open_ielts_strategy.knowledge_pack import KnowledgePackError, load_knowledge_pack


def strategy():
    return {
        "id": "speaking.answer-development", "schema_version": "1.0",
        "title": "Answer Development", "skill": "speaking",
        "summary": "Develop a direct answer with relevant supporting detail.",
        "purpose": ["Make the response clear."],
        "reasoning": ["A direct answer gives the listener an immediate position."],
        "steps": ["Answer directly.", "Add one relevant detail."],
        "applicability": {"question_types": [], "parts": ["part_1"], "conditions": []},
        "limitations": ["Do not force this structure."], "common_mistakes": [],
        "examples": ["Original synthetic example."],
        "relationships": {"requires": [], "complements": [], "conflicts_with": [], "alternatives": []},
        "provenance": {"basis": "original", "public_references": []},
        "review": {"content_status": "approved", "publication_status": "approved"},
        "version": "1.0.0",
    }


class KnowledgePackBuilderTests(unittest.TestCase):
    def test_build_is_deterministic_and_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = build_knowledge_pack([strategy()], root / "pack-a", pack_version="1.0.0", human_confirmed=True)
            second = build_knowledge_pack([strategy()], root / "pack-b", pack_version="1.0.0", human_confirmed=True)
            self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
            self.assertEqual(
                (root / "pack-a/strategies/speaking/speaking.answer-development.json").read_bytes(),
                (root / "pack-b/strategies/speaking/speaking.answer-development.json").read_bytes(),
            )
            self.assertEqual(len(load_knowledge_pack(root / "pack-a").strategies), 1)
            self.assertFalse(first["committed_to_git"])

    def test_requires_explicit_human_confirmation_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(KnowledgePackError):
                build_knowledge_pack([strategy()], root / "pack", pack_version="1.0.0", human_confirmed=False)
            build_knowledge_pack([strategy()], root / "pack", pack_version="1.0.0", human_confirmed=True)
            with self.assertRaisesRegex(KnowledgePackError, "never overwrites"):
                build_knowledge_pack([strategy()], root / "pack", pack_version="1.0.0", human_confirmed=True)

    def test_source_derived_pack_requires_private_publication_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(KnowledgePackError, "SQLite store"):
                build_knowledge_pack(
                    [strategy()], root / "pack", pack_version="1.0.0",
                    human_confirmed=True,
                    source_item_ids_by_strategy={"speaking.answer-development": ["sitem_private"]},
                )


if __name__ == "__main__":
    unittest.main()
