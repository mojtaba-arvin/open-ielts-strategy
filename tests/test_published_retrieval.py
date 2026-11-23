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

    def test_unexpected_embedding_vector_count_is_rejected(self):
        class BadProvider:
            def encode(self, texts):
                return []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            with self.assertRaises(ValueError):
                PublishedRetrievalEngine(load_knowledge_pack(root), embedding_provider=BadProvider())


if __name__ == "__main__":
    unittest.main()


from open_ielts_strategy.published_index import PublishedIndexStore


class CountingEmbeddings:
    def __init__(self):
        self.batch_sizes = []

    def encode(self, texts):
        self.batch_sizes.append(len(texts))
        return [[float(len(text)), 1.0] for text in texts]


def add_second_strategy(root):
    source_path = root / "strategies/speaking/strategy.json"
    strategy = json.loads(source_path.read_text(encoding="utf-8"))
    second = dict(strategy)
    second["id"] = "speaking.supporting-detail"
    second["title"] = "Supporting Detail"
    second["summary"] = "Add one relevant supporting detail."
    second_path = root / "strategies/speaking/supporting-detail.json"
    second_path.write_text(json.dumps(second, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = second_path.read_bytes()
    manifest["files"].append({
        "path": "strategies/speaking/supporting-detail.json",
        "sha256": hashlib.sha256(payload).hexdigest(),
    })
    manifest["files"].sort(key=lambda item: item["path"])
    manifest["pack_version"] = "3.2.0"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def revise_first_strategy(root):
    source_path = root / "strategies/speaking/strategy.json"
    strategy = json.loads(source_path.read_text(encoding="utf-8"))
    strategy["summary"] = "Develop a direct answer and support it with a precise relevant detail."
    payload = json.dumps(strategy, sort_keys=True, separators=(",", ":")).encode()
    source_path.write_bytes(payload)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["pack_version"] = "3.3.0"
    for item in manifest["files"]:
        if item["path"] == "strategies/speaking/strategy.json":
            item["sha256"] = hashlib.sha256(payload).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


class PublishedIndexIncrementalTests(unittest.TestCase):
    def test_only_changed_records_are_reembedded_after_pack_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            add_second_strategy(root)
            provider = CountingEmbeddings()
            store = PublishedIndexStore(root / "index.sqlite")
            try:
                first_pack = load_knowledge_pack(root)
                first = store.build(first_pack, model_fingerprint="fake-v1", embedding_provider=provider)
                self.assertEqual(first["embedded_documents"], 2)
                self.assertEqual(provider.batch_sizes, [2])

                revise_first_strategy(root)
                second_pack = load_knowledge_pack(root)
                second = store.build(second_pack, model_fingerprint="fake-v1", embedding_provider=provider)
                self.assertEqual(provider.batch_sizes, [2, 1])
                self.assertEqual(second["reused_documents"], 1)
                self.assertEqual(second["updated_documents"], 1)
                self.assertEqual(second["embedded_documents"], 1)
                self.assertEqual(second["removed_documents"], 0)
                self.assertEqual(store.connection.execute(
                    "SELECT COUNT(*) FROM indexed_documents"
                ).fetchone()[0], 2)
            finally:
                store.close()

    def test_embedding_failure_keeps_previous_index_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_pack(root)
            store = PublishedIndexStore(root / "index.sqlite")
            provider = CountingEmbeddings()
            try:
                first_pack = load_knowledge_pack(root)
                store.build(first_pack, model_fingerprint="fake-v1", embedding_provider=provider)
                old_identity = store.identity()
                revise_first_strategy(root)
                revised_pack = load_knowledge_pack(root)

                class BrokenProvider:
                    def encode(self, texts):
                        raise RuntimeError("provider unavailable")

                with self.assertRaises(RuntimeError):
                    store.build(revised_pack, model_fingerprint="fake-v1", embedding_provider=BrokenProvider())
                self.assertEqual(store.identity(), old_identity)
                self.assertEqual(store.connection.execute(
                    "SELECT COUNT(*) FROM indexed_documents"
                ).fetchone()[0], 1)
            finally:
                store.close()
