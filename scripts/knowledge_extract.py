#!/usr/bin/env python3
"""Explicitly run a selected local or remote extraction provider on a private source."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.knowledge_pipeline import extract_source
from open_ielts_strategy.knowledge_store import DEFAULT_DB_PATH, KnowledgeStore
from open_ielts_strategy.provider_registry import build_extraction_provider

DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--provider", choices=("ollama", "openai-compatible"), default="ollama")
    parser.add_argument("--model", required=True, help="Local Ollama model or remote API model name")
    parser.add_argument("--endpoint", default=DEFAULT_OLLAMA_ENDPOINT, help="Provider endpoint; remote endpoints must use HTTPS")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY",
                        help="Environment variable containing the explicitly configured remote API key")
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--prompt-version", default="knowledge-extract-v1")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        config = {"model": args.model}
        if args.provider == "ollama":
            if args.endpoint:
                config["endpoint"] = args.endpoint
        else:
            if args.endpoint != DEFAULT_OLLAMA_ENDPOINT:
                config["endpoint"] = args.endpoint
            config["api_key_env"] = args.api_key_env
            config["max_retries"] = args.max_retries
        provider = build_extraction_provider(args.provider, **config)
        with KnowledgeStore(args.db) as store:
            result = extract_source(
                store, args.source_id, provider,
                provider_name=args.provider, model_name=args.model,
                prompt_version=args.prompt_version,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
