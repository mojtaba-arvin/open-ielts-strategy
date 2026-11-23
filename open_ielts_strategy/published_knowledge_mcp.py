"""MCP adapter for published Knowledge Packs; intentionally SQLite-free."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .knowledge_pack import KnowledgePack, KnowledgePackError, load_knowledge_pack


def search_published_strategies(pack: KnowledgePack, query: str, *,
                                skill: str | None = None, limit: int = 10) -> dict:
    results = pack.search_strategies(query, skill=skill, limit=limit)
    return {
        "pack_version": pack.pack_version,
        "schema_version": pack.schema_version,
        "manifest_sha256": pack.manifest_sha256,
        "results": results,
        "result_count": len(results),
        "evidence_basis": "published_knowledge_pack",
        "note": "Retrieval relevance is not proof of educational validity.",
    }


def get_published_strategy(pack: KnowledgePack, strategy_id: str) -> dict:
    strategy = pack.get_strategy(strategy_id)
    if strategy is None:
        raise KeyError(f"unknown published strategy: {strategy_id}")
    return {
        "pack_version": pack.pack_version,
        "schema_version": pack.schema_version,
        "manifest_sha256": pack.manifest_sha256,
        "strategy": strategy,
    }


def get_related_published_strategies(pack: KnowledgePack, strategy_id: str) -> dict:
    strategy = pack.get_strategy(strategy_id)
    if strategy is None:
        raise KeyError(f"unknown published strategy: {strategy_id}")
    relations = strategy["relationships"]
    related = {}
    for relation_type, identifiers in relations.items():
        related[relation_type] = [
            pack.get_strategy(identifier) for identifier in identifiers
        ]
    return {
        "strategy_id": strategy_id,
        "pack_version": pack.pack_version,
        "manifest_sha256": pack.manifest_sha256,
        "relationships": related,
    }


def build_server(pack_path: str | Path):
    """Create an optional stdio MCP server backed only by a verified pack directory."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("install the optional MCP dependency: pip install '.[mcp]'") from exc

    pack = load_knowledge_pack(pack_path)
    server = FastMCP("Open IELTS Published Knowledge")

    @server.tool()
    def search_strategies(query: str, skill: str | None = None, limit: int = 10) -> dict:
        """Search approved strategies in the local published Knowledge Pack."""
        return search_published_strategies(pack, query, skill=skill, limit=limit)

    @server.tool()
    def get_strategy(strategy_id: str) -> dict:
        """Get one published strategy and its exact Knowledge Pack version."""
        return get_published_strategy(pack, strategy_id)

    @server.tool()
    def get_related_strategies(strategy_id: str) -> dict:
        """Get the typed relationships of one published strategy."""
        return get_related_published_strategies(pack, strategy_id)

    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", default="knowledge", help="Verified published Knowledge Pack directory")
    args = parser.parse_args(argv)
    try:
        server = build_server(args.pack)
        server.run(transport="stdio")
    except (OSError, RuntimeError, ValueError, KeyError, KnowledgePackError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
