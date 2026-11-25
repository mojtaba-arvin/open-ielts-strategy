"""Promote a human-reviewed private strategy draft to a Pack-ready candidate."""
from __future__ import annotations

import argparse
import json
import sys

from .knowledge_store import DEFAULT_DB_PATH, KnowledgeStore
from .strategy_promotion import promote_strategy_draft


def build_parser():
    parser = argparse.ArgumentParser(prog="ielts knowledge-promote", description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--draft", required=True, help="Private .local strategy draft JSON")
    parser.add_argument("--destination", required=True, help="New private strategy JSON candidate path")
    parser.add_argument("--reviewer", required=True, help="Human reviewer identity")
    parser.add_argument("--review-note", required=True, help="Short note describing the content review")
    parser.add_argument("--confirm-content-review", action="store_true",
                        help="Confirm that the complete generated strategy was inspected and edited as needed")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        with KnowledgeStore(args.db) as store:
            result = promote_strategy_draft(
                store, args.draft, args.destination,
                reviewer=args.reviewer, review_note=args.review_note,
                confirm_content_review=args.confirm_content_review,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
