#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from open_ielts_strategy.runtime import run_arm

SKILLS = (
    "ielts-writing-feedback",
    "ielts-speaking-transcript-feedback",
    "ielts-reading-strategy",
    "ielts-listening-strategy",
)

parser = argparse.ArgumentParser()
parser.add_argument("--arm", choices=["baseline", "skill"], required=True)
parser.add_argument("--skill-id", choices=SKILLS, default="ielts-writing-feedback")
parser.add_argument("--mode", choices=["mock", "openai"], default="mock")
parser.add_argument("--budget", type=int, default=0)
parser.add_argument("--output", required=True)
args = parser.parse_args()

case_path = ROOT / "skills" / args.skill_id / "evals" / "cases.json"
cases = json.loads(case_path.read_text())
result = run_arm(args.arm, cases, args.mode, args.budget, args.skill_id)
Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({
    "skill_id": args.skill_id,
    "arm": args.arm,
    "mode": args.mode,
    "cases": len(cases),
    "calls": result["calls"],
}))
