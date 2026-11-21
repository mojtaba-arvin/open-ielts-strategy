#!/usr/bin/env python3
"""Resolve explicitly selected skills; this is not an automatic semantic router."""
import argparse, json
from pathlib import Path
from open_ielts_strategy.composition import resolve_dependencies

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--select",nargs="+",required=True,help="skill IDs to compose")
    args=parser.parse_args()
    lock=json.loads((ROOT/"skills.lock").read_text(encoding="utf-8"))
    ordered=resolve_dependencies(args.select,lock.get("skills",[]))
    selected={entry["name"]:entry for entry in lock.get("skills",[])}
    result=[{"name":name,"version":selected[name]["version"],"path":selected[name]["path"],"environment_contracts":selected[name].get("environment_contracts",[])} for name in ordered]
    print(json.dumps({"composition_version":1,"skills":result},indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
