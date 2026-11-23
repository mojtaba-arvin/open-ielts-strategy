"""MCP adapter for published Knowledge Packs; intentionally SQLite-free."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .knowledge_pack import KnowledgePack, KnowledgePackError, load_knowledge_pack
from .published_retrieval import PublishedRetrievalEngine
from .published_learning import (get_published_learning_path, get_published_concept, create_published_study_plan,
                                 explain_published_strategy, generate_published_strategy_example)
from .text_generation import build_consumption_provider
from .published_practice import generate_published_practice_answer


def search_published_strategies(pack: KnowledgePack, query: str, *,
                                skill: str | None = None, limit: int = 10,
                                retriever: PublishedRetrievalEngine | None = None) -> dict:
    engine = retriever or PublishedRetrievalEngine(pack)
    results = engine.search(query, skill=skill, limit=limit)
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


def build_server(pack_path: str | Path, *, embedding_model_path: str | None = None,
                 provider_name: str | None = None, model: str | None = None,
                 endpoint: str | None = None, api_key_env: str = "OPENAI_API_KEY"):
    """Create an optional stdio MCP server backed only by a verified pack directory."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("install the optional MCP dependency: pip install '.[mcp]'") from exc

    pack = load_knowledge_pack(pack_path)
    embedding_provider = None
    if embedding_model_path:
        from .hybrid_retrieval import LocalSentenceTransformer
        embedding_provider = LocalSentenceTransformer(embedding_model_path)
    retriever = PublishedRetrievalEngine(pack, embedding_provider=embedding_provider)
    text_provider = None
    if provider_name is not None or model is not None:
        if provider_name is None or model is None:
            raise ValueError("both provider_name and model are required for generated MCP tools")
        provider_config = {"model": model}
        if endpoint:
            provider_config["endpoint"] = endpoint
        if provider_name == "openai-compatible":
            provider_config["api_key_env"] = api_key_env
        text_provider = build_consumption_provider(provider_name, **provider_config)
    server = FastMCP("Open IELTS Published Knowledge")

    @server.tool()
    def search_strategies(query: str, skill: str | None = None, limit: int = 10) -> dict:
        """Search approved strategies in the local published Knowledge Pack."""
        return search_published_strategies(pack, query, skill=skill, limit=limit, retriever=retriever)

    @server.tool()
    def get_strategy(strategy_id: str) -> dict:
        """Get one published strategy and its exact Knowledge Pack version."""
        return get_published_strategy(pack, strategy_id)

    @server.tool()
    def get_related_strategies(strategy_id: str) -> dict:
        """Get the typed relationships of one published strategy."""
        return get_related_published_strategies(pack, strategy_id)



    @server.tool()
    def get_concept(concept_id: str) -> dict:
        """Get a published concept and its linked strategy records."""
        return get_published_concept(pack, concept_id)

    @server.tool()
    def get_learning_path(path_id: str) -> dict:
        """Get a curated learning path with its strategy steps resolved."""
        return get_published_learning_path(pack, path_id)

    @server.tool()
    def create_study_plan(skill: str, limit: int = 5) -> dict:
        """Find published learning paths for an IELTS skill."""
        return create_published_study_plan(pack, skill=skill, limit=limit)

    if text_provider is not None:

        @server.tool()
        def answer_ielts_question(question: str, skill: str = "general", limit: int = 6) -> dict:
            """Generate an IELTS practice answer grounded in retrieved published strategies."""
            return generate_published_practice_answer(
                pack, question, skill=skill, provider=text_provider,
                limit=limit, retriever=retriever,
            )

        @server.tool()
        def explain_strategy(strategy_id: str, learner_question: str | None = None) -> dict:
            """Teach one published strategy with its limitations and an exercise."""
            return explain_published_strategy(
                pack, strategy_id, provider=text_provider, learner_question=learner_question
            )

        @server.tool()
        def generate_strategy_example(strategy_id: str, task: str) -> dict:
            """Generate a new example and reject long exact copies of existing examples."""
            return generate_published_strategy_example(
                pack, strategy_id, task, provider=text_provider
            )

    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", default="knowledge", help="Verified published Knowledge Pack directory")
    parser.add_argument("--embedding-model-path", help="Optional already-cached local sentence-transformer directory")
    parser.add_argument("--provider", choices=("ollama", "openai-compatible"))
    parser.add_argument("--model")
    parser.add_argument("--endpoint")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    args = parser.parse_args(argv)
    try:
        server = build_server(
            args.pack, embedding_model_path=args.embedding_model_path,
            provider_name=args.provider, model=args.model,
            endpoint=args.endpoint, api_key_env=args.api_key_env,
        )
        server.run(transport="stdio")
    except (OSError, RuntimeError, ValueError, KeyError, KnowledgePackError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
