import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_pack import load_knowledge_pack
from open_ielts_strategy.published_retrieval import PublishedRetrievalEngine


class FakeEmbeddings:
    def encode(self, texts):
        vectors = []
        for text in texts:
            lowered = text.casefold()
            vectors.append([1.0 if "speaking" in lowered else 0.0,
                            1.0 if "answer" in lowered else 0.0])
        return vectors


def make_pack(root):
    records = [{
        "id": "speaking.answer-development", "schema_version": "1.0",
        "title": "Answer Development", "skill": "speaking",
        "summary": "Develop a direct answer with relevant supporting detail.",
        "purpose": ["Make the response clear."],
        "reasoning": ["A direct answer gives the listener an immediate position."],
        "steps": ["Answer directly.", "Add one relevant detail."],
        "applicability": {"question_types": ["personal_experience"], "parts": ["part_1"], "conditions": []},
        "limitations": ["Do not force this structure."], "common_mistakes": [],
        "examples": ["Synthetic example."],
        "relationships": {"requires": [], "complements": [], "conflicts_with": [], "alternatives": []},
        "provenance": {"basis": "original", "public_references": []},
        "review": {"content_status": "approved", "publication_status": "approved"},
        "version": "1.0.0",
    }]
    folder = root / "strategies" / "speaking"
    folder.mkdir(parents=True)
    payload = json.dumps(records[0], sort_keys=True, separators=(",", ":")).encode()
    (folder / "strategy.json").write_bytes(payload)
    (root / "manifest.json").write_text(json.dumps({
        "format": "open-ielts-knowledge-pack", "schema_version": "1.0",
        "pack_version": "3.1.0",
        "files": [{"path": "strategies/speaking/strategy.json",
                   "sha256": hashlib.sha256(payload).hexdigest()}],
    }), encoding="utf-8")


class PublishedRetrievalTests(unittest.TestCase):
    def test_bm25_search_is_pack_scoped_and_versioned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            pack = load_knowledge_pack(root)
            engine = PublishedRetrievalEngine(pack)
            results = engine.search("How do I develop a direct answer?", skill="speaking")
            self.assertEqual(results[0]["strategy_id"], "speaking.answer-development")
            self.assertEqual(results[0]["retrieval_mode"], "bm25")
            self.assertEqual(results[0]["pack_version"], "3.1.0")
            self.assertEqual(results[0]["manifest_sha256"], pack.manifest_sha256)

    def test_dense_hybrid_search_uses_separate_embedding_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            pack = load_knowledge_pack(root)
            engine = PublishedRetrievalEngine(pack, embedding_provider=FakeEmbeddings())
            results = engine.search("Describe your speaking answer", skill="speaking")
            self.assertEqual(results[0]["retrieval_mode"], "hybrid")
            self.assertIsNotNone(results[0]["semantic_score"])

    def test_skill_filter_and_no_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            engine = PublishedRetrievalEngine(load_knowledge_pack(root))
            self.assertEqual(engine.search("direct answer", skill="writing"), [])
            self.assertEqual(engine.search("unrelated xyz", skill="speaking"), [])

    def test_inconsistent_embedding_vectors_are_rejected(self):
        class BadProvider:
            def encode(self, texts):
                return [[1.0], [1.0, 2.0]][:len(texts)]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            with self.assertRaises(ValueError):
                PublishedRetrievalEngine(load_knowledge_pack(root), embedding_provider=BadProvider())


if __name__ == "__main__":
    unittest.main()
