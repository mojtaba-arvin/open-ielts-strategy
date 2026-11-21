"""Deterministic evaluation primitives; no model calls or network access."""
from dataclasses import dataclass
from typing import Iterable

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

def validate_case(case: dict) -> list[str]:
    errors = [f"missing required field: {key}" for key in ("id", "category", "input", "expected") if not case.get(key)]
    if case.get("category") not in {"routing_positive", "routing_negative", "boundary", "behavioral"}:
        errors.append("invalid category")
    if case.get("category") == "behavioral" and not case.get("rubric"):
        errors.append("behavioral cases require a rubric")
    return errors
