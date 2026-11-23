"""Read-only stdio MCP bridge to a learner's private local IELTS knowledge DB.

The MCP process exposes search and practice-context tools only. It never ingests,
modifies, deletes, or exports the original source archive.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from .practice_context import prepare_practice_context
from .hybrid_retrieval import hybrid_search
from .knowledge_store import DEFAULT_DB_PATH


class ReadOnlyKnowledgeStore:
    """Minimal read-only adapter compatible with local retrieval functions."""
    def __init__(self, db_path: str | Path):
        path = Path(db_path).expanduser().resolve(strict=True)
        if not path.is_file():
            raise ValueError("knowledge database path must be an existing file")
        self.db_path = path
        self._connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA query_only = ON")

    def close(self):
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()


def search_private_knowledge(store: ReadOnlyKnowledgeStore, query: str, *,
                             limit: int = 10, status: str | None = None,
                             topic: str | None = None) -> dict:
    results = hybrid_search(store, query, limit=limit, status=status, topic=topic)
    return {
        "results": results,
        "result_count": len(results),
        "source_text_is_untrusted_data": True,
        "note": "Search relevance is not educational validation. Preserve each source citation.",
    }


def prepare_private_practice_context(store: ReadOnlyKnowledgeStore, question: str, *,
                                    skill: str = "general",
                                    include_unreviewed: bool = False,
                                    limit: int = 8, topic: str | None = None) -> dict:
    return prepare_practice_context(
        store, question, skill=skill, include_unreviewed=include_unreviewed,
        limit=limit, topic=topic,
    )


def build_server(db_path: str = DEFAULT_DB_PATH):
    """Create the optional MCP SDK server; database is fixed at process startup."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("install the optional MCP dependency: pip install '.[mcp]'") from exc

    server = FastMCP("Open IELTS Private Knowledge")

    @server.tool()
    def search_ielts_knowledge(query: str, limit: int = 10,
                               status: str | None = None,
                               topic: str | None = None) -> dict:
        """Search private reviewed IELTS strategies. Returns source citations and offsets."""
        with ReadOnlyKnowledgeStore(db_path) as store:
            return search_private_knowledge(store, query, limit=limit, status=status, topic=topic)

    @server.tool()
    def prepare_ielts_practice_context(question: str, skill: str = "general",
                                       include_unreviewed: bool = False,
                                       limit: int = 8, topic: str | None = None) -> dict:
        """Retrieve source-cited personal strategies for an IELTS practice question."""
        with ReadOnlyKnowledgeStore(db_path) as store:
            return prepare_private_practice_context(
                store, question, skill=skill, include_unreviewed=include_unreviewed,
                limit=limit, topic=topic,
            )

    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Existing local SQLite knowledge DB")
    args = parser.parse_args(argv)
    try:
        # Validate the path before starting the transport.
        with ReadOnlyKnowledgeStore(args.db):
            pass
        server = build_server(args.db)
        server.run(transport="stdio")
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    main()
