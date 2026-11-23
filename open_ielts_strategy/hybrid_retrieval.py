"""Offline hybrid retrieval with a strict local-embedding adapter boundary."""
from __future__ import annotations

import math
import re
from typing import Protocol
from pathlib import Path


class EmbeddingProvider(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE))


def _validated_vector(vector) -> list[float]:
    import math
    if not isinstance(vector, (list, tuple)) or not vector:
        raise ValueError("embedding vectors must be non-empty numeric sequences")
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in vector):
        raise ValueError("embedding vectors must contain only finite numbers")
    return [float(value) for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        raise ValueError("embedding vectors must have the same non-zero dimension")
    dot = sum(a * b for a, b in zip(left, right))
    norms = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(x * x for x in right))
    return dot / norms if norms else 0.0


class LocalSentenceTransformer:
    """Load an already-cached local model; never download weights from the network."""
    def __init__(self, model_path: str):
        if not isinstance(model_path, str) or not model_path.strip() or not Path(model_path).expanduser().is_dir():
            raise ValueError("model_path must point to an existing local model directory; remote model IDs are not accepted")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("install the optional local embedding dependency first") from exc
        self._model = SentenceTransformer(model_path, local_files_only=True, trust_remote_code=False)

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not isinstance(texts, list) or any(not isinstance(x, str) for x in texts):
            raise ValueError("texts must be a list of strings")
        vectors = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return [vector.tolist() for vector in vectors]


def hybrid_search(store, query: str, *, provider: EmbeddingProvider | None = None,
                  limit: int = 10, status: str | None = None, topic: str | None = None) -> list[dict]:
    """Search all locally stored cards; lexical fallback always works without embeddings."""
    if not isinstance(query, str) or not query.strip() or len(query) > 1000:
        raise ValueError("query must contain 1..1000 characters")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if status is not None and status not in {"needs_review", "supported", "conflicting", "user_approved", "superseded", "rejected"}:
        raise ValueError("invalid status")
    sql = """SELECT c.card_id, c.kind, c.title, c.topic_tags_json, c.status, c.review_reason,
                    c.review_note, c.extraction_method, g.segment_id, g.text, g.ordinal,
                    g.start_char, g.end_char, g.locator_json, s.source_id, s.title AS source_title,
                    s.source_type, s.author, s.source_url, s.rights_status
             FROM knowledge_cards c JOIN segments g ON g.segment_id=c.segment_id
             JOIN sources s ON s.source_id=c.source_id"""
    params = ()
    if status:
        sql += " WHERE c.status=?"
        params = (status,)
    sql += " LIMIT 5000"
    rows = list(store._connection.execute(sql, params).fetchall())
    # Semantic extraction records are a second source-linked candidate stream.
    # Older databases without the optional tables continue to work unchanged.
    semantic_table = store._connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='semantic_items'"
    ).fetchone()
    if semantic_table:
        semantic_sql = """SELECT i.item_id AS card_id, i.kind, substr(i.text,1,160) AS title,
                    i.topic_tags_json, i.status, i.rationale AS review_reason,
                    i.rationale AS review_note, e.prompt_version AS extraction_method,
                    g.segment_id, i.text, g.ordinal, i.start_char, i.end_char,
                    g.locator_json, s.source_id, s.title AS source_title,
                    s.source_type, s.author, s.source_url, s.rights_status
             FROM semantic_items i
             JOIN semantic_extractions e ON e.extraction_id=i.extraction_id
             JOIN segments g ON g.segment_id=i.segment_id
             JOIN sources s ON s.source_id=i.source_id"""
        semantic_params = ()
        if status:
            semantic_sql += " WHERE i.status=?"
            semantic_params = (status,)
        semantic_sql += " LIMIT 5000"
        rows.extend(store._connection.execute(semantic_sql, semantic_params).fetchall())
    records = []
    qtokens = _tokens(query)
    for row in rows:
        tags = __import__("json").loads(row["topic_tags_json"])
        if topic and topic not in tags:
            continue
        text = row["title"] + " " + row["text"] + " " + " ".join(tags)
        tokens = _tokens(text)
        overlap = len(qtokens & tokens)
        lexical = overlap / max(1, len(qtokens))
        if lexical == 0 and provider is None:
            continue
        records.append((row, tags, text, lexical))
    semantic_scores = [0.0] * len(records)
    if provider is not None and records:
        vectors = provider.encode([query] + [record[2] for record in records])
        if len(vectors) != len(records) + 1:
            raise ValueError("embedding provider returned an unexpected vector count")
        vectors = [_validated_vector(vector) for vector in vectors]
        query_vector = vectors[0]
        semantic_scores = [_cosine(query_vector, vector) for vector in vectors[1:]]
    results = []
    for index, (row, tags, text, lexical) in enumerate(records):
        semantic = semantic_scores[index]
        # Reciprocal-style bounded fusion; missing semantic provider is lexical-only.
        score = lexical if provider is None else (0.55 * lexical + 0.45 * max(0.0, semantic))
        results.append({
            "score": round(score, 6), "lexical_score": round(lexical, 6),
            "semantic_score": round(semantic, 6) if provider is not None else None,
            "retrieval_mode": "hybrid-local" if provider is not None else "lexical-fallback",
            "card_id": row["card_id"], "segment_id": row["segment_id"],
            "kind": row["kind"], "title": row["title"], "topic_tags": tags,
            "status": row["status"], "review_reason": row["review_reason"],
            "review_note": row["review_note"], "extraction_method": row["extraction_method"],
            "excerpt": row["text"][:600], "source_id": row["source_id"],
            "source_title": row["source_title"], "source_type": row["source_type"],
            "author": row["author"], "source_url": row["source_url"],
            "rights_status": row["rights_status"], "ordinal": row["ordinal"],
            "start_char": row["start_char"], "end_char": row["end_char"],
            "locator": __import__("json").loads(row["locator_json"]),
        })
    results.sort(key=lambda item: (-item["score"], item["source_id"], item["ordinal"]))
    return results[:limit]


def suggest_overlaps(cards: list[dict], *, threshold: float = 0.5) -> list[dict]:
    """Suggest similar wording for human review; never labels a pair as a contradiction."""
    if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    suggestions = []
    for i, left in enumerate(cards):
        left_tokens = _tokens(left.get("text", ""))
        for right in cards[i + 1:]:
            right_tokens = _tokens(right.get("text", ""))
            union = left_tokens | right_tokens
            similarity = len(left_tokens & right_tokens) / len(union) if union else 0.0
            if similarity >= threshold:
                suggestions.append({
                    "left_id": left.get("card_id"), "right_id": right.get("card_id"),
                    "similarity": round(similarity, 6),
                    "suggestion": "possible_overlap_review",
                    "relation_created": False,
                })
    return suggestions
