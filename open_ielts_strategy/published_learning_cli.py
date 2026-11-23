"""Published IELTS Study, Mentor, and Example CLI."""
from __future__ import annotations

import argparse
import json
import sys

from .knowledge_pack import load_knowledge_pack
from .published_learning import (
    create_published_study_plan, explain_published_strategy,
    generate_published_strategy_example,
)
from .text_generation import build_consumption_provider


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    study = commands.add_parser("study", help="List curated published learning paths")
    study.add_argument("--pack", default="knowledge")
    study.add_argument("--skill", choices=("speaking", "writing", "reading", "listening", "general"), required=True)
    study.add_argument("--limit", type=int, default=5)

    mentor = commands.add_parser("mentor", help="Explain a published strategy")
    mentor.add_argument("--pack", default="knowledge")
    mentor.add_argument("--strategy-id", required=True)
    mentor.add_argument("--question")
    mentor.add_argument("--provider", choices=("ollama", "openai-compatible"), default="ollama")
    mentor.add_argument("--model", required=True)
    mentor.add_argument("--endpoint")
    mentor.add_argument("--api-key-env", default="OPENAI_API_KEY")

    example = commands.add_parser("example", help="Generate an original example for a published strategy")
    example.add_argument("--pack", default="knowledge")
    example.add_argument("--strategy-id", required=True)
    example.add_argument("--task", required=True)
    example.add_argument("--provider", choices=("ollama", "openai-compatible"), default="ollama")
    example.add_argument("--model", required=True)
    example.add_argument("--endpoint")
    example.add_argument("--api-key-env", default="OPENAI_API_KEY")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        pack = load_knowledge_pack(args.pack)
        if args.command == "study":
            result = create_published_study_plan(pack, skill=args.skill, limit=args.limit)
        else:
            config = {"model": args.model}
            if args.endpoint:
                config["endpoint"] = args.endpoint
            if args.provider == "openai-compatible":
                config["api_key_env"] = args.api_key_env
            provider = build_consumption_provider(args.provider, **config)
            if args.command == "mentor":
                result = explain_published_strategy(
                    pack, args.strategy_id, provider=provider,
                    learner_question=args.question,
                )
            else:
                result = generate_published_strategy_example(
                    pack, args.strategy_id, args.task, provider=provider
                )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
