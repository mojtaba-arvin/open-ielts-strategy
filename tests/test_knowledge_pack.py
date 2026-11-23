import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pack import KnowledgePackError, load_knowledge_pack


def strategy(**overrides):
    value = {
        "id": "speaking.answer-development",
        "schema_version": "1.0",
        "title": "Answer Development",
        "skill": "speaking",
        "summary": "Develop a direct answer with relevant supporting detail.",
        "purpose": ["Make the response clear."],
        "reasoning": ["A direct answer gives the listener an immediate position."],
        "steps": ["Answer the question directly.", "Add one relevant detail."],
        "applicability": {"question_types": ["personal_experience"], "parts": ["part_1", "part_2"], "conditions": []},
        "limitations": ["Do not force this structure onto every prompt."],
        "common_mistakes": ["Adding unrelated details."],
        "examples": ["Original synthetic example."],
        "relationships": {"requires": [], "complements": [], "conflicts_with": [], "alternatives": []},
        "provenance": {"basis": "original", "public_references": []},
        "review": {"content_status": "approved", "publication_status": "approved"},
        "version": "1.0.0",
    }
    value.update(overrides)
    return value


class PublishedKnowledgePackTests(unittest.TestCase):
    def make_pack(self, root, record=None):
        strategy_path = root / "strategies" / "speaking"
        strategy_path.mkdir(parents=True)
        payload = json.dumps(record or strategy(), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        file_path = strategy_path / "answer-development.json"
        file_path.write_bytes(payload)
        manifest = {
            "format": "open-ielts-knowledge-pack",
            "schema_version": "1.0",
            "pack_version": "0.1.0",
            "files": [{
                "path": "strategies/speaking/answer-development.json",
                "sha256": hashlib.sha256(payload).hexdigest(),
            }],
        }
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_loads_approved_pack_without_private_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_pack(root)
            pack = load_knowledge_pack(root)
            self.assertEqual(pack.pack_version, "0.1.0")
            self.assertEqual(pack.get_strategy("speaking.answer-development")["skill"], "speaking")
            self.assertEqual(len(pack.search_strategies("direct answer", skill="speaking")), 1)

    def test_rejects_checksum_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_pack(root)
            (root / "strategies/speaking/answer-development.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(KnowledgePackError, "checksum mismatch"):
                load_knowledge_pack(root)

    def test_rejects_unapproved_content_or_publication(self):
        for review in (
            {"content_status": "needs_review", "publication_status": "approved"},
            {"content_status": "approved", "publication_status": "pending"},
        ):
            with self.subTest(review=review), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.make_pack(root, strategy(review=review))
                with self.assertRaises(KnowledgePackError):
                    load_knowledge_pack(root)

    def test_rejects_private_provenance_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_pack(root, strategy(provenance={
                "basis": "original", "public_references": [], "source_ids": ["src_private"]
            }))
            with self.assertRaisesRegex(KnowledgePackError, "private field"):
                load_knowledge_pack(root)

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_pack(root)
            manifest = json.loads((root / "manifest.json").read_text())
            manifest["files"][0]["path"] = "../outside.json"
            (root / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaises(KnowledgePackError):
                load_knowledge_pack(root)


    def test_loader_import_does_not_load_private_database_or_extraction_modules(self):
        code = (
            "import sys; import open_ielts_strategy.knowledge_pack; "
            "assert 'sqlite3' not in sys.modules; "
            "assert 'open_ielts_strategy.knowledge_store' not in sys.modules; "
            "assert 'open_ielts_strategy.semantic_extraction' not in sys.modules"
        )
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_malformed_field_types_without_leaking_type_errors(self):
        for record in (strategy(skill=[]), strategy(id=[]), strategy(schema_version=[])):
            with self.subTest(record=record), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.make_pack(root, record)
                with self.assertRaises(KnowledgePackError):
                    load_knowledge_pack(root)

    def test_rejects_symlinked_pack_entries(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            self.make_pack(root)
            target = Path(outside) / "external.json"
            target.write_text(json.dumps(strategy()), encoding="utf-8")
            item = root / "strategies/speaking/answer-development.json"
            item.unlink()
            try:
                item.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable on this platform")
            manifest = json.loads((root / "manifest.json").read_text())
            manifest["files"][0]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(KnowledgePackError):
                load_knowledge_pack(root)

    def test_rejects_unknown_relationship_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = strategy(relationships={
                "requires": ["missing.strategy"], "complements": [],
                "conflicts_with": [], "alternatives": [],
            })
            self.make_pack(root, record)
            with self.assertRaisesRegex(KnowledgePackError, "unknown strategies"):
                load_knowledge_pack(root)


if __name__ == "__main__":
    unittest.main()
