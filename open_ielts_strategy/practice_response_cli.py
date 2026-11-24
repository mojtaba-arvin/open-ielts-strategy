"""Evaluate a learner-submitted response against published strategy evidence."""
from __future__ import annotations
import argparse
import json
import sys
from .knowledge_pack import load_knowledge_pack
from .practice_response_evaluation import evaluate_published_response
from .text_generation import build_consumption_provider


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", default="knowledge")
    parser.add_argument("--skill", choices=("speaking", "writing", "reading", "listening", "general"), required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--answer", required=True)
    parser.add_argument("--provider", choices=("ollama", "openai-compatible"), default="ollama")
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--session-db", help="Private local SQLite database")
    parser.add_argument("--session-id", help="Append this attempt to an existing session in --session-db")
    args = parser.parse_args(argv)
    store = None
    try:
        if args.session_id and not args.session_db:
            raise ValueError("--session-id requires --session-db")
        pack = load_knowledge_pack(args.pack)
        session = None
        if args.session_db:
            from .practice_sessions import PracticeSessionStore
            store = PracticeSessionStore(args.session_db)
            if args.session_id:
                session = store.get_session(args.session_id)
                expected = {
                    "question": args.question,
                    "skill": args.skill,
                    "pack_version": pack.pack_version,
                }
                actual = {key: session[key] for key in expected}
                if actual != expected:
                    raise ValueError(
                        "existing session does not match question, skill, and Knowledge Pack version"
                    )
        config = {"model": args.model}
        if args.endpoint:
            config["endpoint"] = args.endpoint
        if args.provider == "openai-compatible":
            config["api_key_env"] = args.api_key_env
        provider = build_consumption_provider(args.provider, **config)
        result = evaluate_published_response(pack, args.question, args.answer,
                                             skill=args.skill, provider=provider, limit=args.limit)
        if store and result["status"] == "evaluated":
            if session is None:
                session = store.create_session(
                    args.question, skill=args.skill, pack_version=pack.pack_version
                )
            attempt = store.record_attempt(
                session["id"], args.answer,
                feedback="\n".join(result["next_steps"]),
                strategy_ids=result["strategy_ids_used"], assessment=result,
            )
            result["persistence"] = {
                "storage": "local_sqlite",
                "session_id": session["id"],
                "attempt_id": attempt["id"],
                "attempt_count": store.get_session(session["id"])["attempt_count"],
            }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        if store:
            store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
