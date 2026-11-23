"""Generate an IELTS practice answer using only a published Knowledge Pack."""
from __future__ import annotations

import argparse
import json
import sys

from .knowledge_pack import load_knowledge_pack
from .published_practice import generate_published_practice_answer
from .text_generation import build_consumption_provider
from .published_retrieval import PublishedRetrievalEngine
from .hybrid_retrieval import LocalSentenceTransformer


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--pack", default="knowledge")
    parser.add_argument("--skill", choices=("speaking", "writing", "reading", "listening", "general"), default="general")
    parser.add_argument("--provider", choices=("ollama", "openai-compatible"), default="ollama")
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--embedding-model-path", help="Optional already-cached local sentence-transformer directory")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        pack = load_knowledge_pack(args.pack)
        config = {"model": args.model}
        if args.endpoint:
            config["endpoint"] = args.endpoint
        if args.provider == "openai-compatible":
            config["api_key_env"] = args.api_key_env
        provider = build_consumption_provider(args.provider, **config)
        retriever = None
        if args.embedding_model_path:
            embeddings = LocalSentenceTransformer(args.embedding_model_path)
            retriever = PublishedRetrievalEngine(pack, embedding_provider=embeddings)
        result = generate_published_practice_answer(
            pack, args.question, skill=args.skill, provider=provider,
            limit=args.limit, retriever=retriever,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
