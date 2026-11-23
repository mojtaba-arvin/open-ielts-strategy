#!/usr/bin/env python3
"""Evaluate private semantic extraction against a local human annotation file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.knowledge_benchmark import evaluate_source_extraction
from open_ielts_strategy.knowledge_store import DEFAULT_DB_PATH, KnowledgeStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--annotations", required=True, help="Local JSON file containing an annotations array")
    parser.add_argument("--model-name")
    parser.add_argument("--prompt-version")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(Path(args.annotations).read_text(encoding="utf-8"))
        annotations = payload.get("annotations") if isinstance(payload, dict) else payload
        if not isinstance(annotations, list):
            raise ValueError("annotation file must be a list or an object with an annotations list")
        with KnowledgeStore(args.db) as store:
            result = evaluate_source_extraction(
                store, args.source_id, annotations,
                model_name=args.model_name, prompt_version=args.prompt_version,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
