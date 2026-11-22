#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from open_ielts_strategy.runtime import run_arm
p=argparse.ArgumentParser(); p.add_argument("--arm",choices=["baseline","skill"],required=True); p.add_argument("--mode",choices=["mock","openai"],default="mock"); p.add_argument("--budget",type=int,default=0); p.add_argument("--output",required=True); a=p.parse_args()
cases=json.loads((Path(__file__).resolve().parents[1]/"skills/ielts-writing-feedback/evals/cases.json").read_text())
r=run_arm(a.arm,cases,a.mode,a.budget); Path(a.output).write_text(json.dumps(r,indent=2)+"\n"); print(json.dumps({"arm":a.arm,"mode":a.mode,"cases":len(cases),"calls":r["calls"]}))
