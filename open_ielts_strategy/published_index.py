"""Persistent, pack-scoped index cache for published records only.

The SQLite file is a disposable derived index. It contains no learner data,
private sources, reviews, or extraction state and is invalidated by either the
Knowledge Pack manifest digest or embedding-model fingerprint.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
from pathlib import Path
from typing import Any

from .published_retrieval import _document_text
from .knowledge_pack import KnowledgePack


class PublishedIndexStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            db_path = Path(self.path).expanduser()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.path = str(db_path)
        self.connection = sqlite3.connect(self.path)
        if self.path != ":memory:":
            os.chmod(self.path, 0o600)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS index_metadata (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                pack_version TEXT NOT NULL,
                manifest_sha256 TEXT NOT NULL,
                model_fingerprint TEXT NOT NULL,
                document_count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS indexed_documents (
                strategy_id TEXT PRIMARY KEY,
                document_text TEXT NOT NULL,
                embedding_json TEXT
            );
        """)
        self.connection.commit()

    def close(self):
        self.connection.close()

    def identity(self) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM index_metadata WHERE singleton=1").fetchone()
        if row is None:
            return None
        return {"pack_version": row[1], "manifest_sha256": row[2],
                "model_fingerprint": row[3], "document_count": row[4]}

    def build(self, pack: KnowledgePack, *, model_fingerprint: str = "bm25-only",
              embedding_provider=None, batch_size: int = 64) -> dict:
        if not isinstance(model_fingerprint, str) or not model_fingerprint.strip() or len(model_fingerprint) > 300:
            raise ValueError("model_fingerprint must be non-empty bounded text")
        if type(batch_size) is not int or not 1 <= batch_size <= 512:
            raise ValueError("batch_size must be between 1 and 512")
        if model_fingerprint == "bm25-only" and embedding_provider is not None:
            raise ValueError("an embedding provider requires an explicit non-default model fingerprint")
        if model_fingerprint != "bm25-only" and embedding_provider is None:
            raise ValueError("a non-default model fingerprint requires an embedding provider")
        identity = {"pack_version": pack.pack_version,
                    "manifest_sha256": pack.manifest_sha256,
                    "model_fingerprint": model_fingerprint,
                    "document_count": len(pack.strategies)}
        if self.identity() == identity:
            return {**identity, "rebuilt": False}
        documents = [(item["id"], _document_text(item)) for item in pack.strategies]
        vectors: list[list[float] | None] = [None] * len(documents)
        vector_dimensions = None
        if embedding_provider is not None:
            for start in range(0, len(documents), batch_size):
                batch = [text for _, text in documents[start:start + batch_size]]
                encoded = embedding_provider.encode(batch)
                if not isinstance(encoded, list) or len(encoded) != len(batch):
                    raise ValueError("embedding provider returned an unexpected vector count")
                for offset, vector in enumerate(encoded):
                    if not isinstance(vector, (list, tuple)) or not vector:
                        raise ValueError("embedding provider returned an invalid vector")
                    if any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in vector):
                        raise ValueError("embedding vector must contain only finite numeric values")
                    if vector_dimensions is None:
                        vector_dimensions = len(vector)
                    elif len(vector) != vector_dimensions:
                        raise ValueError("embedding provider returned inconsistent vector dimensions")
                    vectors[start + offset] = [float(value) for value in vector]
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.connection.execute("DELETE FROM indexed_documents")
            self.connection.executemany(
                "INSERT INTO indexed_documents(strategy_id,document_text,embedding_json) VALUES(?,?,?)",
                [(identifier, text, json.dumps(vectors[index]) if vectors[index] is not None else None)
                 for index, (identifier, text) in enumerate(documents)],
            )
            self.connection.execute("DELETE FROM index_metadata")
            self.connection.execute(
                "INSERT INTO index_metadata(singleton,pack_version,manifest_sha256,model_fingerprint,document_count) VALUES(1,?,?,?,?)",
                (pack.pack_version, pack.manifest_sha256, model_fingerprint, len(documents)),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return {**identity, "rebuilt": True}

    def embedding_provider(self, pack: KnowledgePack, *, model_fingerprint: str,
                           query_provider):
        if model_fingerprint == "bm25-only":
            raise ValueError("BM25-only indexes do not contain vectors; build with an explicit embedding model first")
        identity = self.identity()
        expected = (pack.pack_version, pack.manifest_sha256, model_fingerprint, len(pack.strategies))
        actual = None if identity is None else (identity["pack_version"], identity["manifest_sha256"],
                                                identity["model_fingerprint"], identity["document_count"])
        if actual != expected:
            raise ValueError("published index is stale or belongs to another model; rebuild it first")
        rows = self.connection.execute(
            "SELECT document_text,embedding_json FROM indexed_documents ORDER BY strategy_id"
        ).fetchall()
        vectors = {text: json.loads(vector) for text, vector in rows if vector is not None}
        class CachedProvider:
            def encode(self, texts):
                result = []
                missing, positions = [], []
                for index, text in enumerate(texts):
                    if text in vectors:
                        result.append(vectors[text])
                    else:
                        result.append(None)
                        missing.append(text)
                        positions.append(index)
                if missing:
                    encoded = query_provider.encode(missing)
                    if not isinstance(encoded, list) or len(encoded) != len(missing):
                        raise ValueError("query embedding provider returned an unexpected vector count")
                    for index, vector in zip(positions, encoded):
                        result[index] = vector
                return result
        return CachedProvider()
