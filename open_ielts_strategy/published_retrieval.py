"""In-memory BM25 + optional dense retrieval over published Knowledge Packs."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol, Any

from .hybrid_retrieval import _cosine, _validated_vector
from .knowledge_pack import KnowledgePack

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "can", "do", "for", "from",
    "how", "i", "in", "is", "it", "of", "on", "or", "the", "this", "to",
    "what", "when", "where", "which", "who", "with", "you",
}


class EmbeddingProvider(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


def _tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text.casefold()) if token not in _STOPWORDS]


def _document_text(strategy: dict[str, Any]) -> str:
    applicability = strategy["applicability"]
    return " ".join((
        strategy["id"], strategy["title"], strategy["summary"],
        " ".join(strategy["purpose"]), " ".join(strategy["reasoning"]),
        " ".join(strategy["steps"]), " ".join(strategy["limitations"]),
        " ".join(strategy["common_mistakes"]),
        " ".join(applicability["question_types"]),
        " ".join(applicability["parts"]),
        " ".join(applicability["conditions"]),
    ))


class PublishedRetrievalEngine:
    """A read-only, in-memory index scoped to one immutable Knowledge Pack revision."""

    def __init__(self, pack: KnowledgePack, *, embedding_provider: EmbeddingProvider | None = None):
        self.pack = pack
        self.embedding_provider = embedding_provider
        self._strategies = list(pack.strategies)
        self._texts = [_document_text(item) for item in self._strategies]
        self._tokens = [_tokens(text) for text in self._texts]
        self._term_frequencies = [Counter(tokens) for tokens in self._tokens]
        self._lengths = [len(tokens) for tokens in self._tokens]
        self._average_length = sum(self._lengths) / max(1, len(self._lengths))
        self._document_frequency = Counter()
        for tokens in self._tokens:
            self._document_frequency.update(set(tokens))
        self._document_count = len(self._strategies)
        self._document_vectors = None
        if embedding_provider is not None and self._texts:
            vectors = embedding_provider.encode(self._texts)
            if not isinstance(vectors, list) or len(vectors) != len(self._texts):
                raise ValueError("embedding provider returned an unexpected document vector count")
            self._document_vectors = [_validated_vector(vector) for vector in vectors]
            dimensions = {len(vector) for vector in self._document_vectors}
            if len(dimensions) != 1:
                raise ValueError("embedding provider returned inconsistent vector dimensions")

    @property
    def index_identity(self) -> dict:
        return {
            "pack_version": self.pack.pack_version,
            "schema_version": self.pack.schema_version,
            "manifest_sha256": self.pack.manifest_sha256,
            "document_count": self._document_count,
        }

    def _bm25(self, query_tokens: list[str], index: int) -> float:
        frequencies = self._term_frequencies[index]
        length = self._lengths[index]
        score = 0.0
        for term in query_tokens:
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            document_frequency = self._document_frequency[term]
            inverse_frequency = math.log(
                1 + (self._document_count - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * length / max(1, self._average_length))
            score += inverse_frequency * (frequency * 2.5) / denominator
        return score

    def search(self, query: str, *, skill: str | None = None, limit: int = 10) -> list[dict]:
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            raise ValueError("query must contain 1..1000 characters")
        if skill is not None and (not isinstance(skill, str) or skill not in {"speaking", "writing", "reading", "listening", "general"}):
            raise ValueError("unsupported IELTS skill")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        candidates = [
            index for index, item in enumerate(self._strategies)
            if skill is None or item["skill"] == skill
        ]
        query_tokens = _tokens(query)
        bm25_scores = [self._bm25(query_tokens, index) for index in candidates]
        max_bm25 = max(bm25_scores, default=0.0)
        lexical_scores = [score / max_bm25 if max_bm25 else 0.0 for score in bm25_scores]
        semantic_scores = [0.0] * len(candidates)
        if self.embedding_provider is not None and candidates:
            query_vectors = self.embedding_provider.encode([query])
            if not isinstance(query_vectors, list) or len(query_vectors) != 1:
                raise ValueError("embedding provider returned an unexpected query vector count")
            query_vector = _validated_vector(query_vectors[0])
            for position, index in enumerate(candidates):
                semantic_scores[position] = max(0.0, _cosine(query_vector, self._document_vectors[index]))
        results = []
        for position, index in enumerate(candidates):
            lexical = lexical_scores[position]
            semantic = semantic_scores[position]
            score = lexical if self.embedding_provider is None else 0.55 * lexical + 0.45 * semantic
            if score <= 0:
                continue
            strategy = self._strategies[index]
            results.append({
                "score": round(score, 6),
                "lexical_score": round(lexical, 6),
                "semantic_score": round(semantic, 6) if self.embedding_provider is not None else None,
                "retrieval_mode": "hybrid" if self.embedding_provider is not None else "bm25",
                "strategy_id": strategy["id"],
                "strategy_version": strategy["version"],
                "strategy": strategy,
                **self.index_identity,
            })
        results.sort(key=lambda item: (-item["score"], item["strategy_id"]))
        return results[:limit]
