"""Human-annotation benchmark utilities for extraction fidelity.

Scores source-span extraction only. It does not measure educational correctness or learner outcomes.
"""
from __future__ import annotations

from collections import Counter

VALID_KINDS = {
    "recommendation", "procedure", "claim", "rationale",
    "example", "exception", "warning", "open_question",
}


def _key(item: dict) -> tuple:
    return (item.get("kind"), item.get("start_char"), item.get("end_char"), item.get("text"))


def evaluate_extraction(predicted: list[dict], annotated: list[dict]) -> dict:
    """Compute exact-match micro precision/recall against independently reviewed annotations."""
    for collection in (predicted, annotated):
        if not isinstance(collection, list):
            raise ValueError("predicted and annotated must be lists")
        for item in collection:
            if not isinstance(item, dict) or item.get("kind") not in VALID_KINDS:
                raise ValueError("every item must have a supported kind")
            if type(item.get("start_char")) is not int or type(item.get("end_char")) is not int:
                raise ValueError("every item must have integer offsets")
            if item["start_char"] < 0 or item["end_char"] <= item["start_char"]:
                raise ValueError("invalid annotation offsets")
            if not isinstance(item.get("text"), str) or not item["text"]:
                raise ValueError("every item must have non-empty text")
    pred_keys = Counter(_key(item) for item in predicted)
    gold_keys = Counter(_key(item) for item in annotated)
    true_positive = sum((pred_keys & gold_keys).values())
    false_positive = len(predicted) - true_positive
    false_negative = len(annotated) - true_positive
    precision = true_positive / len(predicted) if predicted else (1.0 if not annotated else 0.0)
    recall = true_positive / len(annotated) if annotated else (1.0 if not predicted else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "metric": "exact-span-and-kind-match",
        "true_positive": true_positive, "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 6), "recall": round(recall, 6),
        "f1": round(f1, 6),
        "annotation_basis": "caller-supplied; reviewer qualifications are not authenticated",
        "educational_validity": "not-measured",
        "claim_eligible": False,
    }


def validate_annotation_set(source_text: str, annotations: list[dict]) -> list[dict]:
    """Verify that every human annotation is an exact source span."""
    if not isinstance(source_text, str) or not source_text:
        raise ValueError("source_text must be non-empty")
    result = []
    for item in annotations:
        if not isinstance(item, dict) or item.get("kind") not in VALID_KINDS:
            raise ValueError("annotation kind is unsupported")
        if type(item.get("start_char")) is not int or type(item.get("end_char")) is not int:
            raise ValueError("annotation offsets must be integers")
        if not isinstance(item.get("text"), str) or not item["text"]:
            raise ValueError("annotation text must be non-empty")
        start, end = item["start_char"], item["end_char"]
        if start < 0 or end <= start:
            raise ValueError("annotation offsets are invalid")
        if end > len(source_text) or source_text[start:end] != item["text"]:
            raise ValueError("annotation text does not match source offsets")
        result.append(dict(item))
    return result


def evaluate_source_extraction(store, source_id: str, annotations: list[dict], *,
                               model_name: str | None = None,
                               prompt_version: str | None = None) -> dict:
    """Evaluate the latest matching local extraction per segment; return metrics, never source text."""
    from .knowledge_pipeline import list_semantic_items

    source = store.get_source(source_id, include_body=True)
    if not source["body"]:
        raise ValueError("source body was purged; exact-span evaluation is no longer possible")
    gold = validate_annotation_set(source["body"], annotations)
    items = list_semantic_items(store, source_id)
    if model_name is not None:
        items = [item for item in items if item["model_name"] == model_name]
    if prompt_version is not None:
        items = [item for item in items if item["prompt_version"] == prompt_version]
    if not items:
        raise ValueError("no semantic extraction items match the requested source/model/prompt")
    latest_by_segment = {}
    for item in items:
        current = latest_by_segment.get(item["segment_id"])
        if current is None or item["created_at"] > current["created_at"]:
            latest_by_segment[item["segment_id"]] = item
    selected = list(latest_by_segment.values())
    model_names = sorted({item["model_name"] for item in selected})
    prompt_versions = sorted({item["prompt_version"] for item in selected})
    if len(model_names) != 1 or len(prompt_versions) != 1:
        raise ValueError("selected extraction items span multiple models or prompt versions; filter explicitly")
    predicted = [{
        "kind": item["kind"], "text": item["text"],
        "start_char": item["start_char"], "end_char": item["end_char"],
    } for item in selected]
    metrics = evaluate_extraction(predicted, gold)
    return {
        "source_id": source_id,
        "source_sha256": source["content_sha256"],
        "model_name": model_names[0],
        "prompt_version": prompt_versions[0],
        "evaluated_item_count": len(predicted),
        "annotation_count": len(gold),
        "metrics": metrics,
        "source_text_included_in_output": False,
    }
