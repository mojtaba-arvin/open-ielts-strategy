"""Opt-in retrieval orchestration with bounded query rewriting and reranking.

Providers are injected explicitly. The baseline PublishedRetrievalEngine remains
fully deterministic and offline; this wrapper never silently calls a model.
"""
from __future__ import annotations

from typing import Protocol, Any

from .published_retrieval import PublishedRetrievalEngine


class QueryRewriter(Protocol):
    def rewrite(self, query: str, *, skill: str | None = None) -> list[str]: ...


class Reranker(Protocol):
    def score(self, query: str, documents: list[str]) -> list[float]: ...


class EnhancedPublishedRetrievalEngine:
    def __init__(self, baseline: PublishedRetrievalEngine, *,
                 query_rewriter: QueryRewriter | None = None,
                 reranker: Reranker | None = None,
                 candidate_limit: int = 30,
                 rewrite_limit: int = 3):
        if type(candidate_limit) is not int or not 1 <= candidate_limit <= 100:
            raise ValueError("candidate_limit must be between 1 and 100")
        if type(rewrite_limit) is not int or not 0 <= rewrite_limit <= 5:
            raise ValueError("rewrite_limit must be between 0 and 5")
        self.baseline = baseline
        self.query_rewriter = query_rewriter
        self.reranker = reranker
        self.candidate_limit = candidate_limit
        self.rewrite_limit = rewrite_limit

    def search(self, query: str, *, skill: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            raise ValueError("query must contain 1..1000 characters")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        queries = [query]
        if self.query_rewriter is not None and self.rewrite_limit:
            rewrites = self.query_rewriter.rewrite(query, skill=skill)
            if not isinstance(rewrites, list):
                raise ValueError("query rewriter must return a list")
            for item in rewrites[:self.rewrite_limit]:
                if isinstance(item, str) and item.strip() and len(item) <= 1000 and item.casefold() not in {q.casefold() for q in queries}:
                    queries.append(item.strip())
        merged: dict[str, dict] = {}
        for rewritten in queries:
            for rank, result in enumerate(self.baseline.search(rewritten, skill=skill, limit=self.candidate_limit), 1):
                key = result["strategy_id"]
                current = merged.get(key)
                reciprocal_rank = 1.0 / (60 + rank)
                if current is None:
                    merged[key] = {**result, "rrf_score": reciprocal_rank, "matched_queries": [rewritten]}
                else:
                    current["rrf_score"] += reciprocal_rank
                    current["matched_queries"].append(rewritten)
        candidates = sorted(merged.values(), key=lambda item: (-item["rrf_score"], item["strategy_id"]))
        if self.reranker is not None and candidates:
            documents = [
                " ".join((item["strategy"]["title"], item["strategy"]["summary"],
                          " ".join(item["strategy"]["reasoning"]), " ".join(item["strategy"]["steps"])))
                for item in candidates
            ]
            scores = self.reranker.score(query, documents)
            if not isinstance(scores, list) or len(scores) != len(candidates):
                raise ValueError("reranker returned an unexpected score count")
            if any(type(score) not in (int, float) for score in scores):
                raise ValueError("reranker scores must be numeric")
            for item, score in zip(candidates, scores):
                item["reranker_score"] = float(score)
            candidates.sort(key=lambda item: (-item["reranker_score"], -item["rrf_score"], item["strategy_id"]))
        for item in candidates:
            item["retrieval_pipeline"] = {
                "query_rewriting": self.query_rewriter is not None,
                "reranking": self.reranker is not None,
                "candidate_limit": self.candidate_limit,
            }
        return candidates[:limit]
