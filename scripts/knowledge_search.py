#!/usr/bin/env python3
"""Search the private library lexically or with an already-installed local embedding model."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.hybrid_retrieval import LocalSentenceTransformer, hybrid_search
from open_ielts_strategy.knowledge_store import DEFAULT_DB_PATH, KnowledgeStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--status")
    parser.add_argument("--topic")
    parser.add_argument("--embedding-model-path", help="Existing local model directory; never downloaded")
    args = parser.parse_args(argv)
    try:
        provider = LocalSentenceTransformer(args.embedding_model_path) if args.embedding_model_path else None
        with KnowledgeStore(args.db) as store:
            results = hybrid_search(
                store, args.query, provider=provider, limit=args.limit,
                status=args.status, topic=args.topic,
            )
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
