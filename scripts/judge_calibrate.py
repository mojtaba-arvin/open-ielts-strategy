#!/usr/bin/env python3
"""Run the independent judge and compare it with trusted human ratings."""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.judge import DIMENSIONS, judge


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        for index in order[i:j]:
            result[index] = (i + 1 + j) / 2
        i = j
    return result


def rho(x, y):
    rank_x, rank_y = ranks(x), ranks(y)
    mean_x, mean_y = sum(rank_x) / len(rank_x), sum(rank_y) / len(rank_y)
    denominator = math.sqrt(
        sum((value - mean_x) ** 2 for value in rank_x)
        * sum((value - mean_y) ** 2 for value in rank_y)
    )
    return (
        sum((a - mean_x) * (b - mean_y) for a, b in zip(rank_x, rank_y))
        / denominator
        if denominator
        else None
    )


def select_calibration_items(items, budget):
    """Select a deterministic, task-stratified sample without exhausting one task first."""
    if budget < 0 or budget > len(items):
        raise ValueError("budget must be between zero and the number of items")
    groups = {}
    for item in items:
        groups.setdefault(item["task"], []).append(item)

    selected = []
    offsets = {task: 0 for task in groups}
    task_order = list(groups)
    while len(selected) < budget:
        progressed = False
        for task in task_order:
            index = offsets[task]
            if index < len(groups[task]) and len(selected) < budget:
                selected.append(groups[task][index])
                offsets[task] += 1
                progressed = True
        if not progressed:
            break
    return selected


def collect_human_ratings(comments, item_ids, trusted_rater):
    """Accept one unambiguous rating per item from the explicitly trusted account."""
    accepted = {}
    duplicates = set()
    valid_ids = set(item_ids)

    if not isinstance(comments, list):
        raise ValueError("comments must be a list")
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        user = comment.get("user") or {}
        if not isinstance(user, dict):
            continue
        if comment.get("author_association") not in {"OWNER", "MEMBER", "COLLABORATOR"}:
            continue
        if (user.get("login") or "").casefold() != trusted_rater.casefold():
            continue

        body = comment.get("body")
        if not isinstance(body, str) or not body:
            continue
        match = re.search(
            r'\{\s*"item_id"\s*:\s*"cal-\d+".*?\}',
            body,
            re.S,
        )
        if not match:
            continue
        try:
            row = json.loads(match.group())
        except (TypeError, ValueError):
            continue

        item_id = row.get("item_id")
        if item_id not in valid_ids:
            continue
        if not all(type(row.get(key)) is int and 1 <= row[key] <= 9 for key in DIMENSIONS):
            continue
        if item_id in accepted:
            duplicates.add(item_id)
        else:
            accepted[item_id] = row

    for item_id in duplicates:
        accepted.pop(item_id, None)
    return accepted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--budget", type=int, default=0)
    parser.add_argument("--issue-number", type=int, default=0)
    parser.add_argument("--trusted-rater", default="")
    parser.add_argument("--output", default="judge-scorecard.json")
    args = parser.parse_args()

    items = json.loads(
        (Path(__file__).resolve().parents[1] / "data/calibration/items.json").read_text()
    )["items"]
    if len(items) < 20:
        raise RuntimeError("at least 20 calibration items required")

    if args.dry_run:
        Path(args.output).write_text(
            json.dumps(
                {
                    "status": "fixture-validation-only",
                    "items": len(items),
                    "human_rated_n": 0,
                    "reliability": None,
                },
                indent=2,
            )
            + "\n"
        )
        print("20-item calibration fixture valid; no model calls.")
        return 0

    if args.budget < 1:
        raise RuntimeError("live judging requires --budget >= 1")
    if args.budget > len(items):
        raise RuntimeError(f"budget cannot exceed the {len(items)} available items")
    if args.issue_number < 1:
        raise RuntimeError("live judging requires a positive --issue-number")
    if not args.trusted_rater:
        raise RuntimeError("live judging requires --trusted-rater")
    if not os.getenv("GITHUB_TOKEN"):
        raise RuntimeError("GITHUB_TOKEN required to read human issue ratings")

    repo = os.getenv("GITHUB_REPOSITORY", "mojtaba-arvin/open-ielts-strategy")
    raw = subprocess.check_output(
        [
            "gh",
            "api",
            f"repos/{repo}/issues/{args.issue_number}/comments",
            "--paginate",
            "--slurp",
        ],
        text=True,
    )
    pages = json.loads(raw)
    comments = (
        [comment for page in pages for comment in page]
        if pages and isinstance(pages[0], list)
        else pages
    )
    human = collect_human_ratings(
        comments, [item["id"] for item in items], args.trusted_rater
    )

    scored = []
    selected_items = select_calibration_items(items, args.budget)
    for item in selected_items:
        scored.append(
            {
                "item_id": item["id"],
                **judge(
                    item["essay"],
                    item["task"],
                    {"dimensions": list(DIMENSIONS)},
                ),
                "human": human.get(item["id"]),
            }
        )

    paired = [item for item in scored if item["human"]]
    report = {
        "status": "completed",
        "items_judged": len(scored),
        "human_rated_n": len(paired),
        "trusted_rating_source": {
            "issue_number": args.issue_number,
            "author": args.trusted_rater,
            "accepted_author_associations": ["OWNER", "MEMBER", "COLLABORATOR"],
        },
        "judge_model": scored[0]["model"] if scored else None,
        "reliability": {},
    }
    for dimension in DIMENSIONS:
        human_scores = [item["human"][dimension] for item in paired]
        judge_scores = [item["scores"][dimension] for item in paired]
        if len(human_scores) < 3:
            report["reliability"][dimension] = {
                "metric": "Spearman rho",
                "n": len(human_scores),
                "value": None,
                "reason": "at least 3 paired human ratings required",
            }
            continue

        correlation = rho(human_scores, judge_scores)
        if correlation is None:
            report["reliability"][dimension] = {
                "metric": "Spearman rho",
                "n": len(human_scores),
                "rho": None,
                "confidence_interval_95": None,
                "reason": "correlation is undefined when either score vector has no variance",
            }
            continue

        confidence_interval = None
        valid_bootstrap_replicates = 0
        if len(human_scores) >= 10:
            import random

            rng = random.Random(20261122)
            samples = []
            for _ in range(1000):
                indices = [rng.randrange(len(human_scores)) for _ in human_scores]
                estimate = rho(
                    [human_scores[index] for index in indices],
                    [judge_scores[index] for index in indices],
                )
                if estimate is not None:
                    samples.append(estimate)
            valid_bootstrap_replicates = len(samples)
            if valid_bootstrap_replicates >= 800:
                samples.sort()
                confidence_interval = [
                    round(samples[int(0.025 * (len(samples) - 1))], 4),
                    round(samples[int(0.975 * (len(samples) - 1))], 4),
                ]

        report["reliability"][dimension] = {
            "metric": "Spearman rho",
            "n": len(human_scores),
            "rho": round(correlation, 4),
            "confidence_interval_95": confidence_interval,
            "bootstrap_valid_replicates": valid_bootstrap_replicates,
            **(
                {"confidence_interval_reason": "fewer than 800 valid bootstrap replicates"}
                if len(human_scores) >= 10 and confidence_interval is None
                else {}
            ),
        }

    Path(args.output).write_text(
        json.dumps({"report": report, "scorecards": scored}, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
