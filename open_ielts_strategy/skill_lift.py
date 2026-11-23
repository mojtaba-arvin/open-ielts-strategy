"""Paired, provenance-labelled Skill comparison; no model calls or network access."""
from collections import defaultdict
from math import isfinite


def _normalize(rows, label):
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{label} results must be a non-empty list")
    indexed = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{label} row {index} must be an object")
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip() or case_id != case_id.strip():
            raise ValueError(f"{label} case_id must be canonical non-empty text")
        if case_id in indexed:
            raise ValueError(f"{label} contains duplicate case_id {case_id}")
        passed = row.get("passed")
        if type(passed) is not bool:
            raise ValueError(f"{label} passed must be boolean")
        category = row.get("category", "uncategorized")
        if not isinstance(category, str) or not category.strip():
            raise ValueError(f"{label} category must be non-empty text")
        score = row.get("score")
        if score is not None:
            if type(score) not in (int, float) or not isfinite(score) or not 0 <= score <= 1:
                raise ValueError(f"{label} score must be a finite number from 0 to 1")
        indexed[case_id] = {"passed": passed, "category": category, "score": score}
    return indexed


def compare_skill_lift(baseline, with_skill, *, mode="fixture"):
    """Compare paired cases and label fixture results so they cannot be claimed as real lift."""
    if mode not in {"fixture", "live"}:
        raise ValueError("mode must be fixture or live")
    base = _normalize(baseline, "baseline")
    skill = _normalize(with_skill, "skill")
    if set(base) != set(skill):
        raise ValueError("baseline and skill must contain exactly the same case IDs")
    ids = sorted(base)
    if any(base[item]["category"] != skill[item]["category"] for item in ids):
        raise ValueError("baseline and skill categories must match for every case")

    def summarize(left, right, selected):
        count = len(selected)
        base_pass = sum(left[item]["passed"] for item in selected)
        skill_pass = sum(right[item]["passed"] for item in selected)
        base_scores = [left[item]["score"] for item in selected if left[item]["score"] is not None]
        skill_scores = [right[item]["score"] for item in selected if right[item]["score"] is not None]
        return {
            "n": count,
            "baseline_passes": base_pass,
            "skill_passes": skill_pass,
            "baseline_resolution_rate": round(base_pass / count, 4),
            "skill_resolution_rate": round(skill_pass / count, 4),
            "resolution_rate_delta": round((skill_pass - base_pass) / count, 4),
            "baseline_mean_score": round(sum(base_scores) / len(base_scores), 4) if base_scores else None,
            "skill_mean_score": round(sum(skill_scores) / len(skill_scores), 4) if skill_scores else None,
            "score_delta": round(sum(skill_scores) / len(skill_scores) - sum(base_scores) / len(base_scores), 4)
                if base_scores and skill_scores and len(base_scores) == len(skill_scores) else None,
        }

    categories = {}
    for category in sorted({base[item]["category"] for item in ids}):
        selected = [item for item in ids if base[item]["category"] == category]
        categories[category] = summarize(base, skill, selected)
    return {
        "schema_version": 1,
        "status": "simulated-fixture" if mode == "fixture" else "descriptive-live-evaluation",
        "mode": mode,
        "case_ids": ids,
        "overall": summarize(base, skill, ids),
        "by_category": categories,
        "claim_eligible": False,
        "interpretation": (
            "Fixture arithmetic validates the comparison pipeline only; it is not evidence of learner improvement."
            if mode == "fixture" else
            "Descriptive model evaluation only; this is not human-validated educational evidence or a release claim."
        ),
    }
