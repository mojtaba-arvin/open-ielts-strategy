"""MCP adapter for published Knowledge Packs; intentionally SQLite-free."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .knowledge_pack import KnowledgePack, KnowledgePackError, load_knowledge_pack
from .published_retrieval import PublishedRetrievalEngine
from .published_learning import (get_published_learning_path, get_published_concept, create_published_study_plan,
                                 explain_published_strategy, generate_published_strategy_example,
                                 get_published_example)
from .text_generation import build_consumption_provider
from .embedding_providers import OpenAICompatibleEmbeddingProvider
from .published_practice import generate_published_practice_answer
from .mentor_sessions import continue_mentor_session
from .study_progression import build_study_progression


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
    typed_relationships = []
    for relationship in pack.relationships:
        if relationship["from_id"] == strategy_id:
            related_id, direction = relationship["to_id"], "outgoing"
        elif relationship["to_id"] == strategy_id:
            related_id, direction = relationship["from_id"], "incoming"
        else:
            continue
        related_entity = pack.get_strategy(related_id) or pack.get_concept(related_id)
        typed_relationships.append({
            "relationship_id": relationship["id"],
            "type": relationship["type"],
            "direction": direction,
            "rationale": relationship["rationale"],
            "related_entity": related_entity,
        })
    return {
        "strategy_id": strategy_id,
        "pack_version": pack.pack_version,
        "manifest_sha256": pack.manifest_sha256,
        "relationships": related,
        "typed_relationships": typed_relationships,
    }


def build_server(pack_path: str | Path, *, embedding_model_path: str | None = None,
                 embedding_provider_name: str | None = None,
                 embedding_model_name: str | None = None,
                 embedding_endpoint: str = "https://api.openai.com/v1/embeddings",
                 embedding_api_key_env: str = "OPENAI_API_KEY",
                 provider_name: str | None = None, model: str | None = None,
                 endpoint: str | None = None, api_key_env: str = "OPENAI_API_KEY"):
    """Create an optional stdio MCP server backed only by a verified pack directory."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("install the optional MCP dependency: pip install '.[mcp]'") from exc

    pack = load_knowledge_pack(pack_path)
    embedding_kind = embedding_provider_name or ("local" if embedding_model_path else None)
    embedding_provider = None
    if embedding_kind == "local":
        if not embedding_model_path or embedding_model_name:
            raise ValueError("local embeddings require --embedding-model-path only")
        from .hybrid_retrieval import LocalSentenceTransformer
        embedding_provider = LocalSentenceTransformer(embedding_model_path)
    elif embedding_kind == "openai-compatible":
        if embedding_model_path or not embedding_model_name:
            raise ValueError("remote embeddings require an embedding model name and no local model path")
        embedding_provider = OpenAICompatibleEmbeddingProvider(
            model=embedding_model_name, endpoint=embedding_endpoint,
            api_key_env=embedding_api_key_env,
        )
    elif embedding_model_name:
        raise ValueError("embedding_model_name requires the OpenAI-compatible embedding provider")
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
    def get_example(example_id: str) -> dict:
        """Get one separately reviewed published learning example."""
        return get_published_example(pack, example_id)

    @server.tool()
    def get_learning_path(path_id: str) -> dict:
        """Get a curated learning path with its strategy steps resolved."""
        return get_published_learning_path(pack, path_id)

    @server.tool()
    def create_study_plan(skill: str, limit: int = 5) -> dict:
        """Find published learning paths for an IELTS skill."""
        return create_published_study_plan(pack, skill=skill, limit=limit)

    @server.tool()
    def build_study_progression_tool(skill: str, completed_path_ids: list[str] | None = None,
                                     limit: int = 20) -> dict:
        """Build a prerequisite-aware Study plan; completion is caller-reported, not inferred."""
        return build_study_progression(
            pack, skill=skill, completed_path_ids=completed_path_ids or (), limit=limit
        )

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
        def mentor_turn(strategy_id: str, learner_message: str, history: list[dict] | None = None) -> dict:
            """Continue a bounded Mentor Mode conversation grounded in one published strategy."""
            return continue_mentor_session(
                pack, strategy_id, learner_message, provider=text_provider, history=history or ()
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
    parser.add_argument("--embedding-provider", choices=("local", "openai-compatible"))
    parser.add_argument("--embedding-model-path", help="Already-cached local sentence-transformer directory")
    parser.add_argument("--embedding-model-name", help="Remote embedding model name")
    parser.add_argument("--embedding-endpoint", default="https://api.openai.com/v1/embeddings")
    parser.add_argument("--embedding-api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--provider", choices=("ollama", "openai-compatible"))
    parser.add_argument("--model")
    parser.add_argument("--endpoint")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    args = parser.parse_args(argv)
    try:
        server = build_server(
            args.pack, embedding_model_path=args.embedding_model_path,
            embedding_provider_name=args.embedding_provider, embedding_model_name=args.embedding_model_name,
            embedding_endpoint=args.embedding_endpoint, embedding_api_key_env=args.embedding_api_key_env,
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
