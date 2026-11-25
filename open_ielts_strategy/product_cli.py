"""Unified product CLI; delegates to focused, explicitly scoped command handlers."""
from __future__ import annotations

import argparse
import sys


COMMANDS = (
    "preflight", "library", "extract", "knowledge-draft", "knowledge-promote", "knowledge-answer",
    "knowledge-status", "knowledge-init", "adapter-status",
    "knowledge-publish", "knowledge-diff", "knowledge-release",
    "study", "mentor", "mentor-chat", "practice",
    "practice-evaluate", "mcp",
)


def _root_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="ielts",
        add_help=False,
        description="Open IELTS Strategy product command line.",
        epilog=(
            "Command help is delegated to the selected handler: run "
            "`ielts library --help`, `ielts practice --help`, etc.\n"
            "Persistent command/data boundaries: docs/product-cli.md and "
            "docs/continuation-decisions.md."
        ),
    )


def _print_root_help() -> None:
    parser = _root_parser()
    parser.add_argument("command", choices=COMMANDS, nargs="?")
    parser.print_help()
    print(
        "\nData scope (important):\n"
        "  Private authoring DB: library, extract, knowledge-draft,\n"
        "    knowledge-promote, knowledge-answer.\n"
        "  Published Knowledge Pack: knowledge-status, practice, study,\n"
        "    mentor, mentor-chat, mcp.\n"
        "  Explicit review/release bridge: knowledge-publish, knowledge-diff,\n"
        "    knowledge-release. These never bypass human approval.\n"
        "  Setup/inspection: preflight, knowledge-init, adapter-status.\n"
        "\nUse the command-specific --help before destructive or release actions."
    )


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help", "help"}:
        _print_root_help()
        return 0

    parser = _root_parser()
    parser.add_argument("command", choices=COMMANDS)
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
