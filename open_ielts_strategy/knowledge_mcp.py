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
from .knowledge_store import DEFAULT_DB_PATH, KnowledgeStore


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


def ingest_private_source(db_path: str, text: str, title: str, *,
                          source_type: str = "other", author: str | None = None,
                          language: str | None = None,
                          rights_status: str = "unknown") -> dict:
    """Write user-supplied text to the fixed private DB; no file/path inputs are accepted."""
    if not isinstance(text, str) or len(text) > 5_000_000:
        raise ValueError("text must be no longer than 5 million characters")
    with KnowledgeStore(db_path) as store:
        result = store.ingest_text(
            text, title=title, source_type=source_type, author=author,
            language=language, rights_status=rights_status,
        )
    return {
        "source_id": result["source_id"], "content_sha256": result["content_sha256"],
        "segment_count": result["segment_count"], "candidate_count": result.get("candidate_count", result["segment_count"]),
        "stored_locally": True, "duplicate": result.get("duplicate", False),
    }


def extract_private_source(db_path: str, source_id: str, model: str) -> list[dict]:
    """Run the explicitly selected locally installed Ollama model over a private source."""
    from .knowledge_pipeline import extract_source
    from .semantic_extraction import OllamaLocalProvider
    provider = OllamaLocalProvider(model=model)
    with KnowledgeStore(db_path) as store:
        return extract_source(
            store, source_id, provider, provider_name="ollama",
            model_name=model, prompt_version="knowledge-extract-v1",
        )


def review_private_semantic_item(db_path: str, item_id: str, status: str, note: str = "") -> dict:
    from .knowledge_pipeline import review_semantic_item
    with KnowledgeStore(db_path) as store:
        return review_semantic_item(store, item_id, status, note)


def build_server(db_path: str = DEFAULT_DB_PATH, *, enable_write_tools: bool = False):
    """Create the optional MCP SDK server; DB path is fixed at process startup."""
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

    if enable_write_tools:
        @server.tool()
        def ingest_ielts_source(text: str, title: str, source_type: str = "other",
                                author: str | None = None, language: str | None = None,
                                rights_status: str = "unknown") -> dict:
            """Store a learner-supplied transcript in the private local library."""
            return ingest_private_source(
                db_path, text, title, source_type=source_type, author=author,
                language=language, rights_status=rights_status,
            )

        @server.tool()
        def extract_ielts_source(source_id: str, model: str) -> list[dict]:
            """Extract review-required strategies using an already-installed local Ollama model."""
            return extract_private_source(db_path, source_id, model)

        @server.tool()
        def review_ielts_semantic_item(item_id: str, status: str, note: str = "") -> dict:
            """Set the personal review state for one extracted strategy item."""
            return review_private_semantic_item(db_path, item_id, status, note)

    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Local SQLite knowledge DB")
    parser.add_argument("--enable-write-tools", action="store_true",
                        help="Opt in to local source ingestion, extraction, and review MCP tools")
    args = parser.parse_args(argv)
    try:
        # Validate an existing DB for read-only mode; write mode may create the DB.
        if not args.enable_write_tools:
            with ReadOnlyKnowledgeStore(args.db):
                pass
        else:
            with KnowledgeStore(args.db):
                pass
        server = build_server(args.db, enable_write_tools=args.enable_write_tools)
        server.run(transport="stdio")
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    main()
