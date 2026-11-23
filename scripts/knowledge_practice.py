#!/usr/bin/env python3
"""Build a cited, private-knowledge context pack for an IELTS practice question."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.hybrid_retrieval import LocalSentenceTransformer
from open_ielts_strategy.knowledge_store import DEFAULT_DB_PATH, KnowledgeStore
from open_ielts_strategy.practice_context import prepare_practice_context


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--skill", choices=["speaking", "writing", "reading", "listening", "general"], default="general")
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--topic")
    parser.add_argument("--include-unreviewed", action="store_true")
    parser.add_argument("--embedding-model-path", help="Optional existing local model directory")
    args = parser.parse_args(argv)
    try:
        provider = LocalSentenceTransformer(args.embedding_model_path) if args.embedding_model_path else None
        with KnowledgeStore(args.db) as store:
            result = prepare_practice_context(
                store, args.question, skill=args.skill, provider=provider,
                include_unreviewed=args.include_unreviewed, limit=args.limit, topic=args.topic,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
