"""Manage local human reviews and reviewer-agreement reports."""
from __future__ import annotations

import argparse
import json
import sys

from .practice_evaluation import PracticeReviewStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="private local SQLite review database")
    sub = parser.add_subparsers(dest="command", required=True)
    register = sub.add_parser("register")
    register.add_argument("--item-id", required=True)
    register.add_argument("--pack-version", required=True)
    register.add_argument("--manifest-sha256", required=True)
    register.add_argument("--output-sha256", required=True)
    review = sub.add_parser("review")
    review.add_argument("--item-id", required=True)
    review.add_argument("--reviewer-id", required=True)
    review.add_argument("--scores-json", required=True, help="JSON object containing all five rubric scores (1..5)")
    review.add_argument("--rationale", default="")
    sub.add_parser("report")
    args = parser.parse_args(argv)
    store = None
    try:
        store = PracticeReviewStore(args.db)
        if args.command == "register":
            store.register_output(args.item_id, pack_version=args.pack_version,
                                  manifest_sha256=args.manifest_sha256, output_sha256=args.output_sha256)
            print(json.dumps({"registered": args.item_id}))
        elif args.command == "review":
            scores = json.loads(args.scores_json)
            store.submit_review(args.item_id, args.reviewer_id, scores, rationale=args.rationale)
            print(json.dumps({"reviewed": args.item_id, "reviewer_id": args.reviewer_id}))
        else:
            print(json.dumps(store.calibration_report(), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        if store is not None:
            store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
