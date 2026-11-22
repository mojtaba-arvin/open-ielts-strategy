#!/usr/bin/env python3
"""Validate eval definitions and optionally compare pre-judged baseline/skill results."""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_RESULT_NOTES_CHARS = 4096
sys.path.insert(0, str(ROOT))
from open_ielts_strategy.evaluation import CaseResult, resolution_rate, skill_lift, validate_case


def load_results(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON array")

    results = []
    seen = set()
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: row {index} must be an object")

        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"{path}: row {index}: case_id must be a non-empty string")
        if case_id in seen:
            raise ValueError(f"{path}: duplicate case_id {case_id!r}")

        passed = row.get("passed")
        if type(passed) is not bool:
            raise ValueError(f"{path}: {case_id}: passed must be boolean")

        raw_score = row.get("score", 1.0 if passed else 0.0)
        if type(raw_score) not in (int, float):
            raise ValueError(f"{path}: {case_id}: score must be a JSON number")
        try:
            score = float(raw_score)
            finite_score = math.isfinite(score)
        except (OverflowError, ValueError):
            finite_score = False
            score = 0.0
        if not finite_score or not 0.0 <= score <= 1.0:
            raise ValueError(f"{path}: {case_id}: score must be finite and between 0 and 1")

        notes = row.get("notes", "")
        if not isinstance(notes, str):
            raise ValueError(f"{path}: {case_id}: notes must be a string")
        if len(notes) > MAX_RESULT_NOTES_CHARS:
            raise ValueError(
                f"{path}: {case_id}: notes exceed {MAX_RESULT_NOTES_CHARS} characters"
            )

        seen.add(case_id)
        results.append(CaseResult(case_id, passed, score, notes))
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", required=True)
    parser.add_argument("--with-skill", help="JSON result array produced by an external runner/judge")
    parser.add_argument("--without-skill", help="JSON baseline result array")
    args = parser.parse_args()
    path = ROOT / "skills" / args.skill / "evals/cases.json"
    if not path.is_file():
        parser.error(f"unknown skill or missing cases: {args.skill}")
    cases = json.loads(path.read_text(encoding="utf-8"))
    errors = [f"{c.get('id', '?')}: {e}" for c in cases for e in validate_case(c)]
    if errors:
        print("FAILED\n" + "\n".join(errors))
        return 1
    counts = {}
    for case in cases:
        counts[case["category"]] = counts.get(case["category"], 0) + 1
    print(f"CASE SUITE VALID: {len(cases)} cases")
    for category, count in sorted(counts.items()):
        print(f"  {category}: {count}")
    if bool(args.with_skill) != bool(args.without_skill):
        parser.error("--with-skill and --without-skill must be supplied together")
    if args.with_skill:
        baseline = load_results(args.without_skill)
        enabled = load_results(args.with_skill)
        expected = {case["id"] for case in cases}
        for label, rows in (("baseline", baseline), ("with-skill", enabled)):
            ids = {result.case_id for result in rows}
            if ids != expected:
                raise ValueError(
                    f"{label}: case IDs do not exactly match suite "
                    f"(missing={sorted(expected - ids)}, extra={sorted(ids - expected)})"
                )
        print(
            f"baseline resolution rate: {resolution_rate(baseline):.3f} "
            f"({sum(result.passed for result in baseline)}/{len(baseline)})"
        )
        print(
            f"with-skill resolution rate: {resolution_rate(enabled):.3f} "
            f"({sum(result.passed for result in enabled)}/{len(enabled)})"
        )
        print(f"skill_lift: {skill_lift(enabled, baseline):+.3f}")
    else:
        print(
            "NOTE: case integrity only; pass --with-skill and --without-skill "
            "to compare externally generated results."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
