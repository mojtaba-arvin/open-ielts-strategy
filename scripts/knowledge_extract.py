#!/usr/bin/env python3
"""Explicitly run the optional local Ollama extractor on an imported source."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.knowledge_pipeline import extract_source
from open_ielts_strategy.knowledge_store import DEFAULT_DB_PATH, KnowledgeStore
from open_ielts_strategy.semantic_extraction import OllamaLocalProvider


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--model", required=True, help="Name of a model already installed in local Ollama")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/generate")
    parser.add_argument("--prompt-version", default="knowledge-extract-v1")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        provider = OllamaLocalProvider(model=args.model, endpoint=args.endpoint)
        with KnowledgeStore(args.db) as store:
            result = extract_source(
                store, args.source_id, provider,
                provider_name="ollama", model_name=args.model,
                prompt_version=args.prompt_version,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
