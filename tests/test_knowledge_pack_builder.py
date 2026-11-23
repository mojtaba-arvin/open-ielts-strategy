import json
import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pack_builder import build_knowledge_pack
from open_ielts_strategy.knowledge_pack import KnowledgePackError, load_knowledge_pack
from open_ielts_strategy.knowledge_pipeline import (
    persist_segment_extraction, review_semantic_item, review_publication_item,
)
from open_ielts_strategy.knowledge_store import KnowledgeStore


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


    def test_source_derived_build_requires_both_reviews_and_exports_no_private_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with KnowledgeStore(root / "private.sqlite3") as store:
                source = store.ingest_text(
                    "This private source recommends a direct answer.",
                    title="Private source", rights_status="permission_confirmed",
                )
                segment = store.get_source(source["source_id"])["segments"][0]
                persisted = persist_segment_extraction(
                    store, source["source_id"], segment["segment_id"],
                    {"summary": "Private summary.", "items": [{
                        "kind": "recommendation", "text": segment["text"],
                        "start_char": 0, "end_char": len(segment["text"]),
                        "topic_tags": ["speaking"], "rationale": "Private rationale.",
                    }]},
                    provider_name="fixture", model_name="test", prompt_version="v1",
                )
                item_id = persisted["item_ids"][0]
                review_semantic_item(store, item_id, "user_approved")
                review_publication_item(
                    store, item_id, "approved", reviewer="maintainer",
                    rights_basis="permission_confirmed", note="Private rights evidence checked.",
                )
                record = strategy()
                record["provenance"] = {"basis": "permissioned", "public_references": []}
                result = build_knowledge_pack(
                    [record], root / "public-pack", pack_version="1.0.0",
                    human_confirmed=True, store=store,
                    source_item_ids_by_strategy={"speaking.answer-development": [item_id]},
                )
                self.assertEqual(result["strategy_count"], 1)
                public_bytes = (root / "public-pack/strategies/speaking/speaking.answer-development.json").read_bytes()
                public_text = public_bytes.decode("utf-8")
                self.assertNotIn(source["source_id"], public_text)
                self.assertNotIn(item_id, public_text)
                self.assertNotIn("Private source", public_text)
                self.assertNotIn("Private rights evidence", public_text)
                self.assertEqual(load_knowledge_pack(root / "public-pack").strategies[0]["id"],
                                 "speaking.answer-development")

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
