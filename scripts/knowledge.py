#!/usr/bin/env python3
"""Local CLI for importing, searching, and reviewing IELTS learning sources."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.document_import import import_document
from open_ielts_strategy.knowledge_store import (
    DEFAULT_DB_PATH,
    CARD_STATUSES,
    RELATION_TYPES,
    RIGHTS_STATUSES,
    SOURCE_TYPES,
    KnowledgeStore,
)


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Offline private knowledge base for your IELTS learning sources."
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help=f"SQLite database path (default: {DEFAULT_DB_PATH})")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="Import a UTF-8 text file, or '-' to read pasted text from stdin")
    ingest.add_argument("input", help="Path to a UTF-8 .txt/.md file, or '-' for stdin")
    ingest.add_argument("--title")
    ingest.add_argument("--type", dest="source_type", choices=sorted(SOURCE_TYPES), default="other")
    ingest.add_argument("--author")
    ingest.add_argument("--url", dest="source_url")
    ingest.add_argument("--published-at")
    ingest.add_argument("--language")
    ingest.add_argument("--notes")
    ingest.add_argument("--rights-status", choices=sorted(RIGHTS_STATUSES), default="unknown")

    search = commands.add_parser("search", help="Search source passages and their candidate cards")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--status", choices=sorted(CARD_STATUSES))
    search.add_argument("--topic")

    listing = commands.add_parser("sources", help="List imported source metadata")
    listing.add_argument("--limit", type=int, default=50)

    show = commands.add_parser("show", help="Show source metadata and source-linked segments")
    show.add_argument("source_id")

    review = commands.add_parser("review", help="Set a human review state on a candidate card")
    review.add_argument("card_id")
    review.add_argument("--status", required=True, choices=sorted(CARD_STATUSES))
    review.add_argument("--note", default="")

    link = commands.add_parser("link", help="Record a human-reviewed relationship between two cards")
    link.add_argument("from_card_id")
    link.add_argument("to_card_id")
    link.add_argument("--relation", required=True, choices=sorted(RELATION_TYPES))
    link.add_argument("--note", default="")

    relations = commands.add_parser("relations", help="List explicitly reviewed relationships between cards")
    relations.add_argument("--source-id")
    relations.add_argument("--limit", type=int, default=200)

    delete = commands.add_parser("delete-source", help="Delete a source and all derived cards/relations")
    delete.add_argument("source_id")
    delete.add_argument("--confirm", action="store_true", help="Required confirmation for destructive deletion")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        with KnowledgeStore(args.db) as store:
            if args.command == "ingest":
                if args.input == "-":
                    body = sys.stdin.read()
                else:
                    body = import_document(args.input)["text"]
                result = store.ingest_text(
                    body,
                    title=args.title,
                    source_type=args.source_type,
                    author=args.author,
                    source_url=args.source_url,
                    published_at=args.published_at,
                    language=args.language,
                    notes=args.notes,
                    rights_status=args.rights_status,
                )
                emit(result)
            elif args.command == "search":
                emit(store.search(args.query, limit=args.limit, status=args.status, topic=args.topic))
            elif args.command == "sources":
                emit(store.list_sources(args.limit))
            elif args.command == "show":
                emit(store.get_source(args.source_id))
            elif args.command == "review":
                emit(store.review_card(args.card_id, args.status, args.note))
            elif args.command == "link":
                emit(store.link_cards(args.from_card_id, args.to_card_id, args.relation, args.note))
            elif args.command == "relations":
                emit(store.list_relations(source_id=args.source_id, limit=args.limit))
            elif args.command == "delete-source":
                if not args.confirm:
                    raise ValueError("source deletion is destructive; pass --confirm to proceed")
                emit(store.delete_source(args.source_id))
    except (OSError, UnicodeError, ValueError, KeyError, RuntimeError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
