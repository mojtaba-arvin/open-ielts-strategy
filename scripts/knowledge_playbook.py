#!/usr/bin/env python3
"""Compare selected local knowledge cards or draft a cited study playbook."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.knowledge_store import DEFAULT_DB_PATH, KnowledgeStore
from open_ielts_strategy.strategy_composition import build_playbook, compare_recommendations


def load_cards(store, card_ids):
    if not card_ids or len(card_ids) > 100 or len(set(card_ids)) != len(card_ids):
        raise ValueError("provide 1..100 unique --card-id values")
    cards = []
    for card_id in card_ids:
        row = store._connection.execute(
            """SELECT c.card_id, c.status, c.kind, c.title, c.topic_tags_json,
                      g.text, g.start_char, g.end_char, g.locator_json,
                      s.source_id, s.title AS source_title
               FROM knowledge_cards c JOIN segments g ON g.segment_id=c.segment_id
               JOIN sources s ON s.source_id=c.source_id WHERE c.card_id=?""",
            (card_id,),
        ).fetchone()
        if row is None:
            semantic_table = store._connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='semantic_items'"
            ).fetchone()
            if semantic_table:
                row = store._connection.execute(
                    """SELECT i.item_id AS card_id, i.status, i.kind,
                              substr(i.text,1,160) AS title, i.topic_tags_json,
                              i.text, g.start_char, g.end_char, g.locator_json,
                              s.source_id, s.title AS source_title
                       FROM semantic_items i
                       JOIN segments g ON g.segment_id=i.segment_id
                       JOIN sources s ON s.source_id=i.source_id
                       WHERE i.item_id=?""",
                    (card_id,),
                ).fetchone()
        if row is None:
            raise KeyError(f"unknown card_id: {card_id}")
        cards.append(dict(row))
    return cards


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("command", choices=["compare", "playbook"])
    parser.add_argument("--card-id", action="append", required=True)
    parser.add_argument("--title", default="My IELTS strategy draft")
    parser.add_argument("--preferences-json", help="JSON object stored separately from source claims")
    args = parser.parse_args(argv)
    try:
        preferences = json.loads(args.preferences_json) if args.preferences_json else {}
        with KnowledgeStore(args.db) as store:
            cards = load_cards(store, args.card_id)
            if args.command == "compare":
                ids = {card["card_id"] for card in cards}
                relations = [
                    relation for relation in store.list_relations()
                    if relation["from_card_id"] in ids and relation["to_card_id"] in ids
                ]
                result = compare_recommendations(cards, relations)
            else:
                result = build_playbook(cards, title=args.title, preferences=preferences)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
