"""Generate private IELTS strategy drafts from reviewed local semantic items."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from .knowledge_store import DEFAULT_DB_PATH, KnowledgeStore
from .strategy_drafts import generate_strategy_draft
from .text_generation import build_consumption_provider

DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"
DEFAULT_API_ENDPOINT = "https://api.openai.com/v1/chat/completions"


def build_parser():
    parser = argparse.ArgumentParser(prog="ielts knowledge-draft", description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--strategy-id", required=True)
    parser.add_argument("--skill", required=True, choices=("speaking", "writing", "reading", "listening", "general"))
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--provider", required=True, choices=("ollama", "openai-compatible"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--output-dir", default=".local/strategy-drafts")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        config = {"model": args.model}
        if args.provider == "ollama":
            endpoint = args.endpoint or DEFAULT_OLLAMA_ENDPOINT
            config["endpoint"] = endpoint
        else:
            endpoint = args.endpoint or DEFAULT_API_ENDPOINT
            config["endpoint"] = endpoint
            config["api_key_env"] = args.api_key_env
        provider = build_consumption_provider(args.provider, **config)
        with KnowledgeStore(args.db) as store:
            result = generate_strategy_draft(
                store, args.source_id, provider,
                provider_name=args.provider, model_name=args.model,
                strategy_id=args.strategy_id, skill=args.skill, version=args.version,
                output_dir=args.output_dir,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError, KeyError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
