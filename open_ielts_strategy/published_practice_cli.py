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
from .published_index import PublishedIndexStore
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
    parser.add_argument("--embedding-model-path", help="Optional already-cached local sentence-transformer directory")
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
        if args.index_db and not args.embedding_model_path:
            raise ValueError("--index-db requires --embedding-model-path")
        if args.index_db and not args.embedding_model_fingerprint:
            raise ValueError("--index-db requires --embedding-model-fingerprint")
        if args.embedding_model_path:
            embeddings = LocalSentenceTransformer(args.embedding_model_path)
            if args.index_db:
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
