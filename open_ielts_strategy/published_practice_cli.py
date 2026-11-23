"""Generate an IELTS practice answer using only a published Knowledge Pack."""
from __future__ import annotations

import argparse
import json
import sys

from .knowledge_pack import load_knowledge_pack
from .published_practice import generate_published_practice_answer
from .text_generation import build_consumption_provider
from .published_retrieval import PublishedRetrievalEngine
from .hybrid_retrieval import LocalSentenceTransformer
from .embedding_providers import OpenAICompatibleEmbeddingProvider
from .enhanced_published_retrieval import (EnhancedPublishedRetrievalEngine, ModelQueryRewriter, LocalCrossEncoderReranker)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--pack", default="knowledge")
    parser.add_argument("--skill", choices=("speaking", "writing", "reading", "listening", "general"), default="general")
    parser.add_argument("--provider", choices=("ollama", "openai-compatible"), default="ollama")
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--session-db", help="Optional local SQLite path for persisting this practice attempt")
    parser.add_argument("--embedding-provider", choices=("local", "openai-compatible"), help="Optional local or remote embedding backend")
    parser.add_argument("--embedding-model-path", help="Already-cached local sentence-transformer directory")
    parser.add_argument("--embedding-model-name", help="Embedding model name for the OpenAI-compatible provider")
    parser.add_argument("--embedding-endpoint", default="https://api.openai.com/v1/embeddings")
    parser.add_argument("--embedding-api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--index-db", help="Optional persistent public-only embedding cache SQLite path")
    parser.add_argument("--embedding-model-fingerprint", help="Required stable model/version fingerprint when --index-db is used")
    parser.add_argument("--query-rewriting", action="store_true", help="Opt in to model-assisted query expansion using the selected generation provider")
    parser.add_argument("--reranker-model-path", help="Optional already-cached local cross-encoder model directory")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    index_store = None
    try:
        pack = load_knowledge_pack(args.pack)
        config = {"model": args.model}
        if args.endpoint:
            config["endpoint"] = args.endpoint
        if args.provider == "openai-compatible":
            config["api_key_env"] = args.api_key_env
        provider = build_consumption_provider(args.provider, **config)
        retriever = None
        embedding_kind = args.embedding_provider or ("local" if args.embedding_model_path else None)
        embeddings = None
        if embedding_kind == "local":
            if not args.embedding_model_path:
                raise ValueError("local embeddings require --embedding-model-path")
            if args.embedding_model_name:
                raise ValueError("--embedding-model-name is only used with the OpenAI-compatible provider")
            embeddings = LocalSentenceTransformer(args.embedding_model_path)
        elif embedding_kind == "openai-compatible":
            if args.embedding_model_path:
                raise ValueError("--embedding-model-path cannot be combined with a remote embedding provider")
            if not args.embedding_model_name:
                raise ValueError("remote embeddings require --embedding-model-name")
            embeddings = OpenAICompatibleEmbeddingProvider(
                model=args.embedding_model_name, endpoint=args.embedding_endpoint,
                api_key_env=args.embedding_api_key_env,
            )
        elif args.embedding_model_name:
            raise ValueError("--embedding-model-name requires --embedding-provider openai-compatible")
        if args.index_db and embeddings is None:
            raise ValueError("--index-db requires an embedding provider")
        if args.index_db and not args.embedding_model_fingerprint:
            raise ValueError("--index-db requires --embedding-model-fingerprint")
        if args.embedding_model_fingerprint and not args.index_db:
            raise ValueError("--embedding-model-fingerprint requires --index-db")
        if embeddings is not None:
            if args.index_db:
                from .published_index import PublishedIndexStore
                index_store = PublishedIndexStore(args.index_db)
                index_store.build(
                    pack, model_fingerprint=args.embedding_model_fingerprint,
                    embedding_provider=embeddings,
                )
                cached_embeddings = index_store.embedding_provider(
                    pack, model_fingerprint=args.embedding_model_fingerprint,
                    query_provider=embeddings,
                )
                retriever = PublishedRetrievalEngine(pack, embedding_provider=cached_embeddings)
            else:
                retriever = PublishedRetrievalEngine(pack, embedding_provider=embeddings)
        if args.query_rewriting or args.reranker_model_path:
            baseline = retriever or PublishedRetrievalEngine(pack)
            retriever = EnhancedPublishedRetrievalEngine(
                baseline,
                query_rewriter=ModelQueryRewriter(provider) if args.query_rewriting else None,
                reranker=LocalCrossEncoderReranker(args.reranker_model_path) if args.reranker_model_path else None,
            )
        result = generate_published_practice_answer(
            pack, args.question, skill=args.skill, provider=provider,
            limit=args.limit, retriever=retriever,
        )
        if args.session_db and result.get("status") == "generated":
            from .practice_sessions import PracticeSessionStore
            with PracticeSessionStore(args.session_db) as store:
                session = store.create_session(
                    args.question, skill=args.skill, pack_version=pack.pack_version
                )
                attempt = store.record_attempt(
                    session["id"], result["answer"],
                    feedback=(result["reasoning_explanation"] + "\\n\\n" + result["practice_suggestion"])[:12000],
                    strategy_ids=[item["strategy_id"] for item in result["strategy_attribution"]],
                )
                result["persistence"] = {
                    "session_id": session["id"], "attempt_id": attempt["id"],
                    "storage": "local_sqlite",
                }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        if index_store is not None:
            index_store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
