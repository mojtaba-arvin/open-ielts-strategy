"""Unified product CLI; delegates to the supported focused command handlers."""
from __future__ import annotations
import argparse

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ielts", description="Open IELTS Strategy product command line.")
    parser.add_argument("command", choices=("knowledge-status", "study", "mentor", "mentor-chat", "practice", "practice-evaluate", "mcp"))
    args, remainder = parser.parse_known_args(argv)
    if args.command == "knowledge-status":
        from .knowledge_pack_status import main as run
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
