#!/usr/bin/env python3
"""Validate evaluation definitions; does not claim to run an LLM judge."""
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from open_ielts_strategy.evaluation import validate_case

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--skill",required=True)
    args=parser.parse_args()
    path=ROOT/"skills"/args.skill/"evals/cases.json"
    if not path.is_file(): parser.error(f"unknown skill or missing cases: {args.skill}")
    cases=json.loads(path.read_text())
    errors=[f"{c.get('id','?')}: {e}" for c in cases for e in validate_case(c)]
    if errors: print("FAILED\n"+"\n".join(errors)); return 1
    counts={}
    for case in cases: counts[case["category"]]=counts.get(case["category"],0)+1
    print(f"CASE SUITE VALID: {len(cases)} cases")
    for category,count in sorted(counts.items()): print(f"  {category}: {count}")
    print("NOTE: case integrity only; no LLM execution or behavioral-quality claim.")
    return 0

if __name__=="__main__": raise SystemExit(main())
