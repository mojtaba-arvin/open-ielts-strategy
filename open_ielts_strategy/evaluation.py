"""Deterministic evaluation primitives; no model calls or network access."""
from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Any

@dataclass(frozen=True)
class CaseResult:
    case_id: str
    passed: bool
    score: float
    notes: str = ""

def resolution_rate(results: Iterable[CaseResult]) -> float:
    items = list(results)
    return sum(item.passed for item in items) / len(items) if items else 0.0

def skill_lift(with_skill: Iterable[CaseResult], without_skill: Iterable[CaseResult]) -> float:
    """Difference in resolution rates, bounded by [-1, 1]."""
    return resolution_rate(with_skill) - resolution_rate(without_skill)

def validate_case(case: Any) -> list[str]:
    """Validate one evaluation case without assuming parsed JSON has the expected shape."""
    if not isinstance(case, dict):
        return ["case must be a JSON object"]

    errors = []
    for key in ("id", "category", "input", "expected"):
        value = case.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key} must be a non-empty string")

    categories = {"routing_positive", "routing_negative", "boundary", "behavioral"}
    category = case.get("category")
    if isinstance(category, str) and category not in categories:
        errors.append("invalid category")

    rubric = case.get("rubric")
    if category == "behavioral":
        if not isinstance(rubric, dict) or not rubric:
            errors.append("behavioral cases require a non-empty rubric object")
    if rubric is not None:
        if not isinstance(rubric, dict) or not rubric:
            errors.append("rubric must be a non-empty object when provided")
        else:
            for key, weight in rubric.items():
                if not isinstance(key, str) or not key.strip():
                    errors.append("rubric keys must be non-empty strings")
                    continue
                if isinstance(weight, bool) or not isinstance(weight, (int, float)) or weight <= 0 or (isinstance(weight, float) and not isfinite(weight)):
                    errors.append(f"rubric weight for {key!r} must be a finite positive number")
    return errors
