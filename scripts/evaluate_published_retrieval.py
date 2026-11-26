"""Evaluate published retrieval against a caller-supplied relevance judgment file."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from open_ielts_strategy.knowledge_pack import load_knowledge_pack
from open_ielts_strategy.published_retrieval import PublishedRetrievalEngine
from open_ielts_strategy.retrieval_quality import evaluate_retrieval
from open_ielts_strategy.hybrid_retrieval import LocalSentenceTransformer


MAX_CASES_FILE_BYTES = 5 * 1024 * 1024


def _read_cases_file(path: Path):
    """Read a bounded UTF-8 judgment file without an unbounded allocation."""
    with path.open("rb") as source:
        payload = source.read(MAX_CASES_FILE_BYTES + 1)
    if len(payload) > MAX_CASES_FILE_BYTES:
        raise ValueError("cases JSON file exceeds the 5 MiB size limit")
    return json.loads(payload.decode("utf-8"))


def _reject_output_overwrite(cases_path: Path, output_path: Path | None) -> None:
    """Prevent a report from replacing its source judgments, including symlink aliases."""
    if output_path is not None and cases_path.resolve() == output_path.resolve():
        raise ValueError("--output must not resolve to the same file as --cases-json")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", default="knowledge")
    parser.add_argument("--cases-json", required=True,
                        help="JSON array: {id, query, optional skill, relevance: {strategy_id: grade 1..3}}")
    parser.add_argument("--embedding-model-path",
                        help="Optional already-cached local SentenceTransformer model")
    parser.add_argument("--k", type=int, nargs="+", default=[1, 3, 5, 10])
    parser.add_argument("--output", help="Optional aggregate JSON report path")
    args = parser.parse_args(argv)
    try:
        cases_path = Path(args.cases_json)
        output_path = Path(args.output) if args.output else None
        _reject_output_overwrite(cases_path, output_path)
        cases = _read_cases_file(cases_path)
        pack = load_knowledge_pack(args.pack)
        provider = LocalSentenceTransformer(args.embedding_model_path) if args.embedding_model_path else None
        engine = PublishedRetrievalEngine(pack, embedding_provider=provider)
        report = evaluate_retrieval(engine, cases, ks=tuple(args.k))
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(payload + "\\n", encoding="utf-8")
        print(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError, KeyError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
