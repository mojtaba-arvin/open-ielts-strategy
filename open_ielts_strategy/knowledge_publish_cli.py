"""Build a local published Knowledge Pack after explicit human confirmation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .knowledge_pack_builder import build_knowledge_pack
from .knowledge_store import DEFAULT_DB_PATH, KnowledgeStore


def _parse_source_item(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("source item must use STRATEGY_ID=SITEM_ID")
    strategy_id, item_id = value.split("=", 1)
    if not strategy_id or not item_id:
        raise argparse.ArgumentTypeError("source item must use STRATEGY_ID=SITEM_ID")
    return strategy_id, item_id


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", action="append", required=True,
                        help="Private local JSON strategy draft; repeat for each strategy")
    parser.add_argument("--destination", required=True)
    parser.add_argument("--version", required=True, dest="pack_version")
    parser.add_argument("--source-item", action="append", type=_parse_source_item, default=[],
                        help="Map source-derived strategy to a reviewed item: STRATEGY_ID=SITEM_ID")
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--confirm-human-review", action="store_true",
                        help="Confirm content, rights, and publication review were completed")
    args = parser.parse_args(argv)
    try:
        strategies = []
        for filename in args.strategy:
            path = Path(filename).expanduser().resolve(strict=True)
            if not path.is_file() or path.stat().st_size > 256_000:
                raise ValueError(f"strategy draft must be a regular file no larger than 256 KB: {filename}")
            strategies.append(json.loads(path.read_text(encoding="utf-8")))
        mappings: dict[str, list[str]] = {}
        for strategy_id, item_id in args.source_item:
            mappings.setdefault(strategy_id, []).append(item_id)
        if mappings:
            with KnowledgeStore(args.db) as store:
                result = build_knowledge_pack(
                    strategies, args.destination, pack_version=args.pack_version,
                    human_confirmed=args.confirm_human_review, store=store,
                    source_item_ids_by_strategy=mappings,
                )
        else:
            result = build_knowledge_pack(
                strategies, args.destination, pack_version=args.pack_version,
                human_confirmed=args.confirm_human_review,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
