"""Offline latency benchmark for published Knowledge Pack retrieval.

The report contains pack/model identity and aggregate timings only; raw learner
queries and retrieved content are never written to the report.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

from open_ielts_strategy.knowledge_pack import load_knowledge_pack
from open_ielts_strategy.published_retrieval import PublishedRetrievalEngine
from open_ielts_strategy.published_index import PublishedIndexStore
from open_ielts_strategy.hybrid_retrieval import LocalSentenceTransformer


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("cannot calculate a percentile from an empty sample")
    if not 0 < quantile <= 1:
        raise ValueError("quantile must be in (0, 1]")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)]


def benchmark(pack_path: str, *, queries: list[str] | None = None,
              iterations: int = 5, warmup: int = 2,
              embedding_model_path: str | None = None,
              index_db: str | None = None,
              model_fingerprint: str | None = None) -> dict:
    if type(iterations) is not int or not 1 <= iterations <= 1000:
        raise ValueError("iterations must be between 1 and 1000")
    if type(warmup) is not int or not 0 <= warmup <= 100:
        raise ValueError("warmup must be between 0 and 100")
    pack = load_knowledge_pack(pack_path)
    if queries is None:
        queries = [f"{item['title']} {item['summary']}" for item in pack.strategies[:50]]
    if not isinstance(queries, list) or not queries or any(
        not isinstance(query, str) or not query.strip() or len(query) > 1000 for query in queries
    ):
        raise ValueError("queries must be a non-empty list of bounded text queries")
    if index_db and not embedding_model_path:
        raise ValueError("--index-db requires --embedding-model-path")
    if index_db and not model_fingerprint:
        raise ValueError("--index-db requires --model-fingerprint")
    embedding_provider = LocalSentenceTransformer(embedding_model_path) if embedding_model_path else None
    index_build_seconds = None
    store = None
    try:
        if index_db:
            store = PublishedIndexStore(index_db)
            started = time.perf_counter()
            store.build(pack, model_fingerprint=model_fingerprint,
                        embedding_provider=embedding_provider)
            index_build_seconds = time.perf_counter() - started
            embedding_provider = store.embedding_provider(
                pack, model_fingerprint=model_fingerprint,
                query_provider=embedding_provider,
            )
        engine_started = time.perf_counter()
        engine = PublishedRetrievalEngine(pack, embedding_provider=embedding_provider)
        engine_build_seconds = time.perf_counter() - engine_started
        for _ in range(warmup):
            for query in queries:
                engine.search(query, limit=10)
        samples = []
        for _ in range(iterations):
            for query in queries:
                started = time.perf_counter()
                engine.search(query, limit=10)
                samples.append(time.perf_counter() - started)
        total = len(samples)
        elapsed = sum(samples)
        return {
            "benchmark": "published-retrieval-latency",
            "pack_version": pack.pack_version,
            "manifest_sha256": pack.manifest_sha256,
            "strategy_count": len(pack.strategies),
            "retrieval_mode": "hybrid" if embedding_provider is not None else "bm25",
            "model_fingerprint": model_fingerprint if embedding_model_path else None,
            "query_count": len(queries),
            "iterations": iterations,
            "warmup_iterations": warmup,
            "measured_searches": total,
            "index_build_seconds": round(index_build_seconds, 6) if index_build_seconds is not None else None,
            "engine_build_seconds": round(engine_build_seconds, 6),
            "latency_seconds": {
                "mean": round(statistics.fmean(samples), 6),
                "p50": round(percentile(samples, .50), 6),
                "p95": round(percentile(samples, .95), 6),
                "max": round(max(samples), 6),
            },
            "throughput_queries_per_second": round(total / elapsed, 3) if elapsed else None,
            "query_text_included": False,
            "educational_quality_measured": False,
        }
    finally:
        if store is not None:
            store.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", default="knowledge")
    parser.add_argument("--queries-json", help="Optional JSON file containing a list of search queries")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--embedding-model-path", help="Optional already-cached local embedding model")
    parser.add_argument("--index-db", help="Optional persistent public-only embedding cache")
    parser.add_argument("--model-fingerprint", help="Stable local model/version identity for the persistent cache")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args(argv)
    try:
        queries = json.loads(Path(args.queries_json).read_text(encoding="utf-8")) if args.queries_json else None
        result = benchmark(
            args.pack, queries=queries, iterations=args.iterations, warmup=args.warmup,
            embedding_model_path=args.embedding_model_path, index_db=args.index_db,
            model_fingerprint=args.model_fingerprint,
        )
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            destination = Path(args.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(payload + "\n", encoding="utf-8")
        print(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError, KeyError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
