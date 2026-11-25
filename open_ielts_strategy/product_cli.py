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
        "  Published Knowledge Pack: knowledge-status, practice, practice-evaluate,\n"
        "    study, mentor, mentor-chat, mcp.\n"
        "  Optional local session storage: practice/practice-evaluate --session-db.\n"
        "  Explicit review/release bridge: knowledge-publish, knowledge-diff,\n"
        "    knowledge-release. These never bypass human approval.\n"
        "  Setup/inspection: preflight, knowledge-init, adapter-status.\n"
        "\nUse the command-specific --help before destructive or release actions."
    )


COMMAND_SCOPES = {
    "preflight": "author mode checks the private authoring environment; consume mode checks only the published Knowledge Pack",
    "library": "private local authoring database",
    "extract": "private local authoring database; explicitly selected provider may receive selected source segments",
    "knowledge-draft": "private local authoring database and private draft files",
    "knowledge-promote": "private local authoring database and private promotion receipt",
    "knowledge-answer": "private local authoring database",
    "knowledge-status": "published Knowledge Pack directory",
    "knowledge-init": "local private authoring workspace; creates no approved published content",
    "adapter-status": "installed local capability adapters; no learner content",
    "knowledge-publish": "private authoring database and local candidate output; publication approvals remain mandatory",
    "knowledge-diff": "local current/candidate Knowledge Pack directories; review only",
    "knowledge-release": "signed local release authorization and a non-default Git release branch",
    "study": "published Knowledge Pack; optional progress storage is local",
    "mentor": "published Knowledge Pack; explicitly selected provider receives the requested prompt and retrieved evidence",
    "mentor-chat": "published Knowledge Pack; optional session storage is local",
    "practice": "published Knowledge Pack; optional session storage is local",
    "practice-evaluate": "published Knowledge Pack; optional session storage is local",
    "mcp": "published Knowledge Pack only; private authoring database is not exposed",
}


def _print_command_scope(command: str) -> None:
    scope = COMMAND_SCOPES.get(command)
    if scope:
        print(f"Command data scope: {scope}.", file=sys.stderr)


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
    try:
        exit_code = run(remainder)
    except SystemExit as exc:
        if exc.code not in (None, 0):
            _print_command_scope(args.command)
        raise
    if isinstance(exit_code, int) and exit_code != 0:
        _print_command_scope(args.command)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
