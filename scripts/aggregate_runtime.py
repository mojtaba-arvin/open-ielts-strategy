#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from open_ielts_strategy.runtime import aggregate
p=argparse.ArgumentParser(); p.add_argument("--baseline",required=True); p.add_argument("--skill",required=True); p.add_argument("--output",required=True); a=p.parse_args()
r=aggregate(json.loads(Path(a.baseline).read_text()),json.loads(Path(a.skill).read_text())); Path(a.output).write_text(json.dumps(r,indent=2)+"\n"); print(json.dumps(r,indent=2))
