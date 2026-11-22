"""Deterministic MVP semantic routing and conflict resolution."""
import re
from datetime import datetime, timezone

WRITING = "ielts-writing-feedback"


def route(text):
    normalized = text.lower()
    if re.search(r"\b(speaking|listening|reading)\b", normalized):
        return {"skill_id": None, "confidence": 0.98, "reason": "non-writing IELTS task"}
    task = bool(re.search(
        r"\b(task\s*[12]|task one|task two|chart|graph|table|essay|opinion|discuss both)\b",
        normalized,
    ))
    draft = bool(re.search(
        r"\b(essay|draft|my writing|my response|report|paragraph)\b",
        normalized,
    ))
    if task and draft:
        return {
            "skill_id": WRITING,
            "confidence": 0.94,
            "reason": "IELTS writing task and learner draft detected",
        }
    if draft and "ielts" in normalized:
        return {
            "skill_id": WRITING,
            "confidence": 0.72,
            "reason": "IELTS learner draft; clarify task",
        }
    return {"skill_id": None, "confidence": 0.35, "reason": "insufficient evidence"}


def resolve_conflicts(candidates):
    if not candidates:
        return None

    required = {"skill_id", "priority", "confidence", "validated_at"}
    ranked = []
    for candidate in candidates:
        if not required.issubset(candidate):
            raise ValueError("candidate missing conflict metadata")
        if type(candidate["priority"]) is not int:
            raise ValueError("priority must be an integer")
        try:
            confidence = float(candidate["confidence"])
        except (TypeError, ValueError) as exc:
            raise ValueError("confidence must be between 0 and 1") from exc
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        try:
            validated_at = datetime.fromisoformat(
                str(candidate["validated_at"]).replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValueError("validated_at must be timezone-aware ISO-8601") from exc
        if validated_at.tzinfo is None or validated_at.utcoffset() is None:
            raise ValueError("validated_at must be timezone-aware ISO-8601")
        ranked.append((
            (candidate["priority"], confidence, validated_at.astimezone(timezone.utc)),
            candidate,
        ))

    best_rank = max(rank for rank, _ in ranked)
    return min(
        (candidate for rank, candidate in ranked if rank == best_rank),
        key=lambda candidate: str(candidate["skill_id"]),
    )
