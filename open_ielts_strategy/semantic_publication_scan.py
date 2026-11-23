"""Optional embedding-assisted publication leakage screening.

This is a conservative similarity heuristic, not paraphrase proof or legal
clearance. It emits source identifiers and offsets only, never matched text.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _chunks(text: str, size: int = 512, overlap: int = 128):
    if not isinstance(text, str):
        return
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunk = text[start:end].strip()
        if len(chunk) >= 80:
            yield start, chunk
        if end == len(text):
            break
        start = end - overlap


def _cosine(left, right):
    if len(left) != len(right):
        raise ValueError("embedding dimensions do not match")
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def scan_semantic_publication_leaks(payloads: list[str], private_sources: list[dict],
                                    embedding_provider, *, threshold: float = 0.93,
                                    max_chunks: int = 10000, batch_size: int = 64) -> dict:
    if not 0.5 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0.5 and 1.0")
    if type(max_chunks) is not int or not 1 <= max_chunks <= 50000:
        raise ValueError("max_chunks must be between 1 and 50000")
    if type(batch_size) is not int or not 1 <= batch_size <= 512:
        raise ValueError("batch_size must be between 1 and 512")
    public_chunks, source_chunks = [], []
    for payload_index, payload in enumerate(payloads):
        if not isinstance(payload, str):
            raise ValueError("public payloads must be strings")
        public_chunks.extend((payload_index, offset, chunk) for offset, chunk in _chunks(payload))
    for source in private_sources:
        if not isinstance(source, dict) or not isinstance(source.get("source_id"), str):
            continue
        body = source.get("text")
        if not isinstance(body, str):
            continue
        source_chunks.extend((source["source_id"], offset, chunk) for offset, chunk in _chunks(body))
    if len(public_chunks) + len(source_chunks) > max_chunks:
        raise ValueError("semantic scan chunk budget exceeded; reduce inputs or raise the explicit limit")
    if not public_chunks or not source_chunks:
        return {"passed": True, "semantic_findings": [], "public_chunk_count": len(public_chunks),
                "private_chunk_count": len(source_chunks), "threshold": threshold,
                "method": "local-embedding-cosine-screen", "matched_text_included": False,
                "not_legal_clearance": True}
    source_vectors = []
    public_vectors = []
    def encode_batched(chunks):
        vectors = []
        for start in range(0, len(chunks), batch_size):
            batch = [item[2] for item in chunks[start:start + batch_size]]
            encoded = embedding_provider.encode(batch)
            if not isinstance(encoded, list) or len(encoded) != len(batch):
                raise ValueError("embedding provider returned an unexpected vector count")
            vectors.extend(encoded)
        return vectors
    source_vectors = encode_batched(source_chunks)
    public_vectors = encode_batched(public_chunks)
    findings = {}
    for p_index, (payload_index, public_offset, _) in enumerate(public_chunks):
        best = None
        for s_index, (source_id, source_offset, _) in enumerate(source_chunks):
            score = _cosine(public_vectors[p_index], source_vectors[s_index])
            if score >= threshold and (best is None or score > best[0]):
                best = (score, source_id, source_offset)
        if best:
            score, source_id, source_offset = best
            key = (source_id, payload_index)
            findings.setdefault(key, []).append({"source_offset": source_offset,
                                                  "payload_offset": public_offset,
                                                  "similarity": round(score, 6)})
    report = [{"source_id": source_id, "payload_index": payload_index,
               "match_count": len(matches), "matches": matches[:100]}
              for (source_id, payload_index), matches in sorted(findings.items())]
    return {"passed": not report, "semantic_findings": report,
            "public_chunk_count": len(public_chunks), "private_chunk_count": len(source_chunks),
            "threshold": threshold, "method": "local-embedding-cosine-screen",
            "matched_text_included": False, "not_legal_clearance": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="append", required=True, help="candidate text/JSON file; repeatable")
    parser.add_argument("--private-sources", required=True, help="private JSON array of {source_id,text}; keep local")
    parser.add_argument("--embedding-model-path", required=True, help="already-cached local sentence-transformer model")
    parser.add_argument("--threshold", type=float, default=0.93)
    parser.add_argument("--max-chunks", type=int, default=10000)
    args = parser.parse_args(argv)
    try:
        from .hybrid_retrieval import LocalSentenceTransformer
        sources = json.loads(Path(args.private_sources).read_text(encoding="utf-8"))
        if not isinstance(sources, list):
            raise ValueError("private-sources file must contain a JSON array")
        payloads = [Path(path).read_text(encoding="utf-8") for path in args.candidate]
        provider = LocalSentenceTransformer(args.embedding_model_path)
        report = scan_semantic_publication_leaks(payloads, sources, provider,
                                                 threshold=args.threshold, max_chunks=args.max_chunks)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["passed"] else 1
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
