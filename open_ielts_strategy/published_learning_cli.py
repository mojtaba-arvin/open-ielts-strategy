"""Published IELTS Study, Mentor, and Example CLI."""
from __future__ import annotations

import argparse
import json
import sys

from .knowledge_pack import load_knowledge_pack
from .published_learning import (
    create_published_study_plan, explain_published_strategy,
    generate_published_strategy_example, get_published_example,
)
from .text_generation import build_consumption_provider
from .mentor_sessions import continue_mentor_session
from .study_progression import build_study_progression


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    study = commands.add_parser("study", help="List curated published learning paths")
    study.add_argument("--pack", default="knowledge")
    study.add_argument("--skill", choices=("speaking", "writing", "reading", "listening", "general"), required=True)
    study.add_argument("--limit", type=int, default=20)
    study.add_argument("--completed-path", action="append", default=[], help="Previously completed learning path ID; repeatable")
    study.add_argument("--state-db", help="Private local SQLite database for learner progress")
    study.add_argument("--learner-id", help="Stable local learner scope; required with --state-db")
    study.add_argument("--complete-path", action="append", default=[], help="Mark a published path complete; repeatable")

    get_example = commands.add_parser("get-example", help="Retrieve a separately reviewed published example")
    get_example.add_argument("--pack", default="knowledge")
    get_example.add_argument("--example-id", required=True)

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
    chat = commands.add_parser("mentor-chat", help="Continue a bounded multi-turn mentor conversation")
    chat.add_argument("--pack", default="knowledge")
    chat.add_argument("--strategy-id", required=True)
    chat.add_argument("--message", required=True)
    chat.add_argument("--history-json", default="[]", help="JSON array of prior learner/mentor turns")
    chat.add_argument("--state-db", help="Private local SQLite database for Mentor history")
    chat.add_argument("--learner-id", help="Stable local learner scope; required with --state-db")
    chat.add_argument("--provider", choices=("ollama", "openai-compatible"), default="ollama")
    chat.add_argument("--model", required=True)
    chat.add_argument("--endpoint")
    chat.add_argument("--api-key-env", default="OPENAI_API_KEY")

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        pack = load_knowledge_pack(args.pack)
        if args.command == "study":
            if args.state_db and not args.learner_id:
                raise ValueError("--learner-id is required with --state-db")
            if args.complete_path and not args.state_db:
                raise ValueError("--complete-path requires --state-db")
            if args.state_db:
                from .learner_state import LearnerStateStore
            state = LearnerStateStore(args.state_db) if args.state_db else None
            try:
                known = {item["id"] for item in pack.learning_paths}
                unknown = set(args.complete_path) - known
                if unknown:
                    raise ValueError("unknown learning paths: " + ", ".join(sorted(unknown)))
                if state:
                    for path_id in args.complete_path:
                        state.mark_path_completed(args.learner_id, pack.pack_version, path_id)
                completed = set(args.completed_path)
                if state:
                    completed.update(state.completed_paths(args.learner_id, pack.pack_version))
                result = build_study_progression(pack, skill=args.skill, limit=args.limit,
                                                  completed_path_ids=completed)
                if state:
                    result["learner_state"] = {"storage": "local_sqlite", "learner_id": args.learner_id,
                                               "completed_path_count": len(completed)}
            finally:
                if state:
                    state.close()
        elif args.command == "get-example":
            result = get_published_example(pack, args.example_id)
        else:
            config = {"model": args.model}
            if args.endpoint:
                config["endpoint"] = args.endpoint
            if args.provider == "openai-compatible":
                config["api_key_env"] = args.api_key_env
            provider = build_consumption_provider(args.provider, **config)
            if args.command == "mentor-chat":
                if args.state_db and not args.learner_id:
                    raise ValueError("--learner-id is required with --state-db")
                if args.state_db:
                    from .learner_state import LearnerStateStore
                state = LearnerStateStore(args.state_db) if args.state_db else None
                try:
                    try:
                        history = json.loads(args.history_json)
                    except json.JSONDecodeError as exc:
                        raise ValueError("--history-json must be a JSON array") from exc
                    if state:
                        if history:
                            raise ValueError("--history-json cannot be combined with persisted state")
                        history = state.mentor_history(args.learner_id, pack.pack_version, args.strategy_id)
                    result = continue_mentor_session(
                        pack, args.strategy_id, args.message, provider=provider, history=history
                    )
                    if state:
                        state.append_mentor_turn(args.learner_id, pack.pack_version, args.strategy_id,
                                                 args.message, result["answer"])
                        result["learner_state"] = {"storage": "local_sqlite", "learner_id": args.learner_id,
                                                   "persisted_turns": True}
                finally:
                    if state:
                        state.close()
            elif args.command == "mentor":
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
