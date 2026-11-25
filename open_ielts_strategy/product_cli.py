"""Unified product CLI; delegates to focused, explicitly scoped command handlers."""
from __future__ import annotations

import argparse


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ielts",
        description="Open IELTS Strategy product command line.",
        epilog=(
            "Scope: library/extract/knowledge-draft/knowledge-promote/knowledge-answer "
            "use the private local authoring database; practice/study/mentor/mcp use "
            "the published Knowledge Pack. knowledge-publish/diff/release bridge "
            "the two only through explicit human approval. Run `ielts preflight --help` "
            "to check the local setup."
        ),
    )
    parser.add_argument(
        "command",
        choices=(
            "preflight", "library", "extract", "knowledge-draft", "knowledge-promote", "knowledge-answer",
            "knowledge-status", "knowledge-init", "adapter-status",
            "knowledge-publish", "knowledge-diff", "knowledge-release",
            "study", "mentor", "mentor-chat", "practice",
            "practice-evaluate", "mcp",
        ),
    )
    args, remainder = parser.parse_known_args(argv)

    if args.command == "preflight":
        from .preflight_cli import main as run
    elif args.command == "library":
        from .knowledge_library_cli import main as run
    elif args.command == "extract":
        from .knowledge_extract_cli import main as run
    elif args.command == "knowledge-draft":
        from .knowledge_draft_cli import main as run
    elif args.command == "knowledge-promote":
        from .knowledge_promote_cli import main as run
    elif args.command == "knowledge-answer":
        from .knowledge_answer_cli import main as run
    elif args.command == "knowledge-status":
        from .knowledge_pack_status import main as run
    elif args.command == "knowledge-init":
        from .knowledge_init_cli import main as run
    elif args.command == "adapter-status":
        from .integration_adapters_cli import main as run
    elif args.command == "knowledge-publish":
        from .knowledge_publish_cli import main as run
    elif args.command == "knowledge-diff":
        from .knowledge_diff_cli import main as run
    elif args.command == "knowledge-release":
        from .knowledge_release import main as run
    elif args.command in {"study", "mentor", "mentor-chat"}:
        from .published_learning_cli import main as run
        remainder.insert(0, args.command)
    elif args.command == "practice":
        from .published_practice_cli import main as run
    elif args.command == "practice-evaluate":
        from .practice_response_cli import main as run
    else:
        from .published_knowledge_mcp import main as run
    return run(remainder)


if __name__ == "__main__":
    raise SystemExit(main())
