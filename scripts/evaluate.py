#!/usr/bin/env python3
"""Validate eval definitions and optionally compare pre-judged baseline/skill results."""
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from open_ielts_strategy.evaluation import CaseResult, resolution_rate, skill_lift, validate_case

def load_results(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data,list): raise ValueError(f"{path}: expected a JSON array")
    results=[]; seen=set()
    for row in data:
        cid=row.get("case_id")
        if not cid or cid in seen: raise ValueError(f"{path}: missing or duplicate case_id {cid!r}")
        if not isinstance(row.get("passed"),bool): raise ValueError(f"{path}: {cid}: passed must be boolean")
        seen.add(cid)
        results.append(CaseResult(cid,row["passed"],float(row.get("score",1.0 if row["passed"] else 0.0)),str(row.get("notes",""))))
    return results

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--skill",required=True)
    parser.add_argument("--with-skill",help="JSON result array produced by an external runner/judge")
    parser.add_argument("--without-skill",help="JSON baseline result array")
    args=parser.parse_args()
    path=ROOT/"skills"/args.skill/"evals/cases.json"
    if not path.is_file(): parser.error(f"unknown skill or missing cases: {args.skill}")
    cases=json.loads(path.read_text(encoding="utf-8"))
    errors=[f"{c.get('id','?')}: {e}" for c in cases for e in validate_case(c)]
    if errors: print("FAILED\n"+"\n".join(errors)); return 1
    counts={}
    for case in cases: counts[case["category"]]=counts.get(case["category"],0)+1
    print(f"CASE SUITE VALID: {len(cases)} cases")
    for category,count in sorted(counts.items()): print(f"  {category}: {count}")
    if bool(args.with_skill) != bool(args.without_skill):
        parser.error("--with-skill and --without-skill must be supplied together")
    if args.with_skill:
        baseline=load_results(args.without_skill); enabled=load_results(args.with_skill)
        expected={c["id"] for c in cases}
        for label,rows in (("baseline",baseline),("with-skill",enabled)):
            ids={r.case_id for r in rows}
            if ids != expected: raise ValueError(f"{label}: case IDs do not exactly match suite (missing={sorted(expected-ids)}, extra={sorted(ids-expected)})")
        print(f"baseline resolution rate: {resolution_rate(baseline):.3f} ({sum(r.passed for r in baseline)}/{len(baseline)})")
        print(f"with-skill resolution rate: {resolution_rate(enabled):.3f} ({sum(r.passed for r in enabled)}/{len(enabled)})")
        print(f"skill_lift: {skill_lift(enabled,baseline):+.3f}")
    else:
        print("NOTE: case integrity only; pass --with-skill and --without-skill to compare externally generated results.")
    return 0

if __name__=="__main__": raise SystemExit(main())
