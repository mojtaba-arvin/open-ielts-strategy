"""Unified CLI for the private, local-only knowledge library."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from .document_import import import_document
from .knowledge_pipeline import (
    list_semantic_items,
    purge_source_text,
    review_publication_item,
    review_semantic_item,
)
from .knowledge_store import (
    DEFAULT_DB_PATH,
    CARD_STATUSES,
    RELATION_TYPES,
    RIGHTS_STATUSES,
    SOURCE_TYPES,
    KnowledgeStore,
)


def _emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(
        prog="ielts library",
        description="Import, search, curate, and manage private IELTS learning sources.",
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="Import a local file or stdin ('-')")
    ingest.add_argument("input")
    ingest.add_argument("--title")
    ingest.add_argument("--type", dest="source_type", choices=sorted(SOURCE_TYPES), default="other")
    ingest.add_argument("--author")
    ingest.add_argument("--url", dest="source_url")
    ingest.add_argument("--published-at")
    ingest.add_argument("--language")
    ingest.add_argument("--notes")
    ingest.add_argument("--rights-status", choices=sorted(RIGHTS_STATUSES), default="unknown")

    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--status", choices=sorted(CARD_STATUSES))
    search.add_argument("--topic")

    listing = commands.add_parser("sources")
    listing.add_argument("--limit", type=int, default=50)

    show = commands.add_parser("show")
    show.add_argument("source_id")

    review = commands.add_parser("review")
    review.add_argument("card_id")
    review.add_argument("--status", required=True, choices=sorted(CARD_STATUSES))
    review.add_argument("--note", default="")

    link = commands.add_parser("link")
    link.add_argument("from_card_id")
    link.add_argument("to_card_id")
    link.add_argument("--relation", required=True, choices=sorted(RELATION_TYPES))
    link.add_argument("--note", default="")

    relations = commands.add_parser("relations")
    relations.add_argument("--source-id")
    relations.add_argument("--limit", type=int, default=200)

    delete = commands.add_parser("delete-source")
    delete.add_argument("source_id")
    delete.add_argument("--confirm", action="store_true")

    semantic = commands.add_parser("semantic-items")
    semantic.add_argument("source_id")

    semantic_review = commands.add_parser("review-semantic")
    semantic_review.add_argument("item_id")
    semantic_review.add_argument("--status", required=True, choices=sorted(CARD_STATUSES))
    semantic_review.add_argument("--note", default="")

    publication = commands.add_parser("review-publication")
    publication.add_argument("item_id")
    publication.add_argument("--status", required=True, choices=("pending", "approved", "rejected"))
    publication.add_argument("--reviewer", required=True)
    publication.add_argument("--rights-basis", choices=(
        "self_authored", "permission_confirmed", "public_domain", "independently_authored"
    ))
    publication.add_argument("--note", default="")

    purge = commands.add_parser("purge-source-text")
    purge.add_argument("source_id")
    purge.add_argument("--confirm", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        with KnowledgeStore(args.db) as store:
            if args.command == "ingest":
                document = None
                if args.input == "-":
                    body = sys.stdin.read()
                else:
                    document = import_document(args.input)
                    body = document["text"]
                notes = "; ".join(part for part in (
                    args.notes,
                    f"Imported file: {document['filename']} ({document['format']}); "
                    f"file SHA-256: {document['file_sha256']}" if document else None,
                ) if part)
                _emit(store.ingest_text(
                    body, title=args.title, source_type=args.source_type, author=args.author,
                    source_url=args.source_url, published_at=args.published_at,
                    language=args.language, rights_status=args.rights_status, notes=notes,
                ))
            elif args.command == "search":
                _emit(store.search(args.query, limit=args.limit, status=args.status, topic=args.topic))
            elif args.command == "sources":
                _emit(store.list_sources(args.limit))
            elif args.command == "show":
                _emit(store.get_source(args.source_id))
            elif args.command == "review":
                _emit(store.review_card(args.card_id, args.status, args.note))
            elif args.command == "link":
                _emit(store.link_cards(args.from_card_id, args.to_card_id, args.relation, args.note))
            elif args.command == "relations":
                _emit(store.list_relations(source_id=args.source_id, limit=args.limit))
            elif args.command == "delete-source":
                if not args.confirm:
                    raise ValueError("source deletion is destructive; pass --confirm to proceed")
                _emit(store.delete_source(args.source_id))
            elif args.command == "semantic-items":
                _emit(list_semantic_items(store, args.source_id))
            elif args.command == "review-semantic":
                _emit(review_semantic_item(store, args.item_id, args.status, args.note))
            elif args.command == "review-publication":
                _emit(review_publication_item(
                    store, args.item_id, args.status, reviewer=args.reviewer,
                    rights_basis=args.rights_basis, note=args.note,
                ))
            elif args.command == "purge-source-text":
                _emit(purge_source_text(store, args.source_id, confirm=args.confirm))
    except (OSError, UnicodeError, ValueError, KeyError, RuntimeError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
