"""Offline audit of judge-version scorecards and explicitly supplied reference labels."""
from itertools import combinations
import re

DIMENSIONS = ("task_response", "coherence_cohesion", "lexical_resource", "grammar_accuracy")


def _scorecard(card):
    if not isinstance(card, dict):
        raise ValueError("scorecard must be an object")
    version = card.get("judge_version")
    rubric = card.get("rubric_sha256")
    if not isinstance(version, str) or not version.strip() or version != version.strip():
        raise ValueError("judge_version must be canonical non-empty text")
    if not isinstance(rubric, str) or not re.fullmatch(r"[0-9a-f]{64}", rubric):
        raise ValueError("rubric_sha256 must be a lowercase SHA-256 digest")
    rows = card.get("results")
    if not isinstance(rows, list) or not rows:
        raise ValueError("scorecard results must be a non-empty list")
    indexed = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"result {index} must be an object")
        item_id = row.get("item_id")
        if not isinstance(item_id, str) or not item_id.strip() or item_id != item_id.strip():
            raise ValueError("item_id must be canonical non-empty text")
        if item_id in indexed:
            raise ValueError(f"duplicate item_id {item_id}")
        scores = row.get("scores")
        if not isinstance(scores, dict) or set(scores) != set(DIMENSIONS):
            raise ValueError("scores must contain exactly the four rubric dimensions")
        if any(type(value) is not int or not 1 <= value <= 9 for value in scores.values()):
            raise ValueError("dimension scores must be integers from 1 to 9")
        indexed[item_id] = scores
    return {"version": version, "rubric": rubric, "results": indexed}


def audit_calibration(scorecards, *, review_threshold=2, human_reference=None):
    """Compare judge versions; human-reference comparison is optional and provenance-labelled."""
    if not isinstance(scorecards, list) or len(scorecards) < 2:
        raise ValueError("at least two versioned scorecards are required")
    if type(review_threshold) is not int or not 1 <= review_threshold <= 8:
        raise ValueError("review_threshold must be an integer from 1 to 8")
    cards = [_scorecard(card) for card in scorecards]
    identities = [(card["version"].casefold(), card["rubric"]) for card in cards]
    if len(identities) != len(set(identities)):
        raise ValueError("judge version and rubric combinations must be unique")

    comparisons = []
    flagged = []
    for left, right in combinations(cards, 2):
        common = sorted(set(left["results"]) & set(right["results"]))
        if not common:
            raise ValueError("scorecards have no common item IDs")
        dimension_report = {}
        for dimension in DIMENSIONS:
            diffs = [abs(left["results"][item][dimension] - right["results"][item][dimension]) for item in common]
            changed = [item for item in common if left["results"][item][dimension] != right["results"][item][dimension]]
            dimension_report[dimension] = {
                "n": len(diffs),
                "exact_agreement_rate": round(sum(diff == 0 for diff in diffs) / len(diffs), 4),
                "mean_absolute_difference": round(sum(diffs) / len(diffs), 4),
                "max_absolute_difference": max(diffs),
                "changed_item_ids": changed,
            }
            for item, diff in zip(common, diffs):
                if diff >= review_threshold:
                    flagged.append({
                        "item_id": item, "dimension": dimension, "absolute_difference": diff,
                        "judge_a": left["version"], "judge_b": right["version"],
                        "reason": "version score delta meets review threshold",
                    })
        comparisons.append({
            "judge_a": left["version"], "judge_b": right["version"],
            "rubric_a_sha256": left["rubric"], "rubric_b_sha256": right["rubric"],
            "common_item_ids": common, "dimensions": dimension_report,
        })

    reference_report = None
    if human_reference is not None:
        if not isinstance(human_reference, dict):
            raise ValueError("human_reference must be an object")
        provenance = human_reference.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError("human reference requires provenance")
        for field in ("reviewer", "reviewed_at", "method"):
            value = provenance.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"human reference provenance requires {field}")
        reference_rows = human_reference.get("results")
        if not isinstance(reference_rows, list) or not reference_rows:
            raise ValueError("human reference results must be a non-empty list")
        reference = {}
        for row in reference_rows:
            if not isinstance(row, dict):
                raise ValueError("human reference row must be an object")
            item = row.get("item_id")
            scores = row.get("scores")
            if not isinstance(item, str) or not item.strip() or item in reference:
                raise ValueError("human reference item IDs must be unique non-empty text")
            if not isinstance(scores, dict) or set(scores) != set(DIMENSIONS):
                raise ValueError("human reference scores must contain exactly the four dimensions")
            if any(type(value) is not int or not 1 <= value <= 9 for value in scores.values()):
                raise ValueError("human reference scores must be integers from 1 to 9")
            reference[item] = scores
        per_version = []
        for card in cards:
            common = sorted(set(card["results"]) & set(reference))
            if not common:
                continue
            metrics = {}
            for dimension in DIMENSIONS:
                diffs = [abs(card["results"][item][dimension] - reference[item][dimension]) for item in common]
                metrics[dimension] = {
                    "n": len(diffs),
                    "exact_agreement_rate": round(sum(diff == 0 for diff in diffs) / len(diffs), 4),
                    "mean_absolute_difference": round(sum(diffs) / len(diffs), 4),
                    "max_absolute_difference": max(diffs),
                }
            per_version.append({"judge_version": card["version"], "common_item_ids": common, "dimensions": metrics})
        reference_report = {
            "status": "reference-comparison-descriptive",
            "provenance": provenance,
            "comparisons": per_version,
            "interpretation": "Reference agreement is descriptive; provenance fields do not independently authenticate reviewer qualifications.",
        }
    return {
        "schema_version": 1,
        "status": "simulated-audit" if human_reference is None else "audit-with-reference",
        "review_threshold": review_threshold,
        "comparisons": comparisons,
        "flagged_for_review": sorted(flagged, key=lambda row: (-row["absolute_difference"], row["item_id"], row["dimension"])),
        "human_reference": reference_report,
        "interpretation": "Score differences identify review candidates; neither agreement nor disagreement establishes which score is correct.",
    }
