"""Evaluate published retrieval against a caller-supplied relevance judgment file."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from open_ielts_strategy.knowledge_pack import load_knowledge_pack
from open_ielts_strategy.published_retrieval import PublishedRetrievalEngine
from open_ielts_strategy.retrieval_quality import evaluate_retrieval
from open_ielts_strategy.hybrid_retrieval import LocalSentenceTransformer


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", default="knowledge")
    parser.add_argument("--cases-json", required=True,
                        help="JSON array: {id, query, optional skill, relevance: {strategy_id: grade 1..3}}")
    parser.add_argument("--embedding-model-path",
                        help="Optional already-cached local SentenceTransformer model")
    parser.add_argument("--k", type=int, nargs="+", default=[1, 3, 5, 10])
    parser.add_argument("--output", help="Optional aggregate JSON report path")
    args = parser.parse_args(argv)
    try:
        cases = json.loads(Path(args.cases_json).read_text(encoding="utf-8"))
        pack = load_knowledge_pack(args.pack)
        provider = LocalSentenceTransformer(args.embedding_model_path) if args.embedding_model_path else None
        engine = PublishedRetrievalEngine(pack, embedding_provider=provider)
        report = evaluate_retrieval(engine, cases, ks=tuple(args.k))
        payload = json.dumps(report, ensure_ascii=False, indent=2)
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
