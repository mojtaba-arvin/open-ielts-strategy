"""Compare independently produced judge scorecards without treating either as truth."""
from itertools import combinations

from open_ielts_strategy.judge import DIMENSIONS

def analyze_judge_disagreement(scorecards):
    """Report pairwise agreement and score distance across judge model outputs."""
    if not isinstance(scorecards, list) or len(scorecards) < 2:
        raise ValueError("at least two judge scorecards are required")
    normalized = {}
    for index, card in enumerate(scorecards):
        if not isinstance(card, dict):
            raise ValueError(f"scorecard {index} must be an object")
        model = card.get("model")
        if not isinstance(model, str) or not model.strip() or model != model.strip():
            raise ValueError(f"scorecard {index} model must be canonical non-empty text")
        key = model.casefold()
        if key in normalized:
            raise ValueError("judge model identifiers must be unique")
        rows = card.get("results")
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{model}: results must be a non-empty list")
        indexed = {}
        for row_index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(f"{model}: result {row_index} must be an object")
            item_id = row.get("item_id")
            if not isinstance(item_id, str) or not item_id.strip() or item_id != item_id.strip():
                raise ValueError(f"{model}: item_id must be canonical non-empty text")
            if item_id in indexed:
                raise ValueError(f"{model}: duplicate item_id {item_id}")
            scores = row.get("scores")
            if not isinstance(scores, dict) or set(scores) != set(DIMENSIONS):
                raise ValueError(f"{model}: scores must contain exactly the four rubric dimensions")
            if any(type(value) is not int or not 1 <= value <= 9 for value in scores.values()):
                raise ValueError(f"{model}: dimension scores must be integers from 1 to 9")
            indexed[item_id] = scores
        normalized[key] = {"model": model, "results": indexed}
    models = list(normalized.values())
    common_ids = set.intersection(*(set(card["results"]) for card in models))
    if not common_ids:
        raise ValueError("judge scorecards have no common item IDs")
    pairwise = []
    for left, right in combinations(models, 2):
        item_ids = sorted(common_ids)
        dimensions = {}
        for dimension in DIMENSIONS:
            differences = [abs(left["results"][item][dimension] - right["results"][item][dimension]) for item in item_ids]
            dimensions[dimension] = {
                "n": len(differences),
                "exact_agreement_rate": round(sum(value == 0 for value in differences) / len(differences), 4),
                "mean_absolute_difference": round(sum(differences) / len(differences), 4),
                "max_absolute_difference": max(differences),
            }
        pairwise.append({"judge_a": left["model"], "judge_b": right["model"], "n_items": len(item_ids), "dimensions": dimensions})
    return {
        "status": "descriptive-disagreement-analysis",
        "judge_count": len(models),
        "common_item_count": len(common_ids),
        "common_item_ids": sorted(common_ids),
        "pairwise": pairwise,
        "interpretation": "Judge agreement is not accuracy, human agreement, or ground truth.",
    }
