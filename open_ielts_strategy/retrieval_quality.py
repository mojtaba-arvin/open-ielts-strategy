"""Offline relevance evaluation for published Knowledge Pack retrieval.

Judgments are supplied by the caller. Reports contain aggregate metrics and
case-suite fingerprints only; query text and retrieved content are omitted.
These metrics measure agreement with the supplied judgments, not IELTS validity.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def _validate_cases(cases: list[dict[str, Any]], known_ids: set[str]) -> list[dict[str, Any]]:
    if not isinstance(cases, list) or not cases or len(cases) > 10000:
        raise ValueError("cases must be a non-empty list of at most 10000 items")
    normalized = []
    seen = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("each case must be an object")
        case_id = case.get("id")
        query = case.get("query")
        skill = case.get("skill")
        relevance = case.get("relevance")
        if not isinstance(case_id, str) or not case_id.strip() or len(case_id) > 200 or case_id in seen:
            raise ValueError("case IDs must be unique, non-empty bounded strings")
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            raise ValueError("each query must contain 1..1000 characters")
        if skill is not None and (not isinstance(skill, str) or skill not in {"speaking", "writing", "reading", "listening", "general"}):
            raise ValueError("case skill is unsupported")
        if not isinstance(relevance, dict) or not relevance:
            raise ValueError("each case requires at least one relevance judgment")
        if any(not isinstance(key, str) or key not in known_ids for key in relevance):
            raise ValueError("relevance judgments reference an unknown strategy ID")
        if any(type(grade) is not int or not 1 <= grade <= 3 for grade in relevance.values()):
            raise ValueError("relevance grades must be integers from 1 to 3")
        seen.add(case_id)
        normalized.append({"id": case_id, "query": query, "skill": skill,
                           "relevance": dict(sorted(relevance.items()))})
    return normalized


def _case_metrics(ranked_ids: list[str], relevance: dict[str, int], k: int) -> dict[str, float]:
    ranked = ranked_ids[:k]
    relevant = {item for item, grade in relevance.items() if grade > 0}
    hits = [item for item in ranked if item in relevant]
    reciprocal_rank = next((1.0 / (rank + 1) for rank, item in enumerate(ranked)
                            if item in relevant), 0.0)
    dcg = sum((2 ** relevance[item] - 1) / math.log2(rank + 2)
              for rank, item in enumerate(ranked) if item in relevance)
    ideal_grades = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum((2 ** grade - 1) / math.log2(rank + 2)
               for rank, grade in enumerate(ideal_grades))
    return {
        "recall": len(hits) / len(relevant),
        "precision": len(hits) / k,
        "mrr": reciprocal_rank,
        "ndcg": dcg / idcg if idcg else 0.0,
    }


def evaluate_retrieval(engine: Any, cases: list[dict[str, Any]], *,
                       ks: tuple[int, ...] = (1, 3, 5, 10)) -> dict:
    """Evaluate ranked strategy IDs against caller-supplied graded judgments."""
    if not isinstance(ks, tuple) or not ks or any(type(k) is not int or not 1 <= k <= 100 for k in ks):
        raise ValueError("ks must be a non-empty tuple of integers from 1 to 100")
    if len(set(ks)) != len(ks):
        raise ValueError("ks must not contain duplicates")
    known_ids = {item["id"] for item in engine.pack.strategies}
    validated = _validate_cases(cases, known_ids)
    canonical = json.dumps(validated, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    per_k = {k: [] for k in ks}
    for case in validated:
        results = engine.search(case["query"], skill=case["skill"], limit=max(ks))
        ranked_ids = [item["strategy_id"] for item in results]
        if len(ranked_ids) != len(set(ranked_ids)):
            raise ValueError("retrieval engine returned duplicate strategy IDs")
        for k in ks:
            per_k[k].append(_case_metrics(ranked_ids, case["relevance"], k))
    metrics = {}
    for k, rows in per_k.items():
        metrics[str(k)] = {
            name: round(sum(row[name] for row in rows) / len(rows), 6)
            for name in ("recall", "precision", "mrr", "ndcg")
        }
    identity = engine.index_identity
    return {
        "benchmark": "published-retrieval-relevance",
        "pack_version": identity["pack_version"],
        "manifest_sha256": identity["manifest_sha256"],
        "strategy_count": identity["document_count"],
        "retrieval_mode": "hybrid" if engine.embedding_provider is not None else "bm25",
        "case_count": len(validated),
        "case_suite_sha256": hashlib.sha256(canonical).hexdigest(),
        "metrics_at_k": metrics,
        "query_text_included": False,
        "judgments_included": False,
        "educational_quality_measured": False,
        "claim_boundary": "Agreement with caller-supplied relevance judgments only; not IELTS validity or learning outcomes.",
    }
