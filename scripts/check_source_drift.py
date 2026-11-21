#!/usr/bin/env python3
"""Check registry verification timestamps without fetching source content."""
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--max-age-days",type=int,default=180)
    p.add_argument("--strict",action="store_true",help="fail for stale or unverified cleared/licensed sources")
    a=p.parse_args(); data=json.loads((ROOT/"registry/sources.json").read_text(encoding="utf-8"))
    now=datetime.now(timezone.utc); issues=[]
    for source in data.get("sources",[]):
        stamp=source.get("last_verified_at")
        if not stamp: issues.append((source["id"],"missing last_verified_at",source.get("legal_status"))); continue
        verified=datetime.fromisoformat(stamp.replace("Z","+00:00"))
        age=(now-verified).days
        if age>a.max_age_days: issues.append((source["id"],f"verification is {age} days old",source.get("legal_status")))
    if not issues: print("SOURCE METADATA FRESH"); return 0
    for sid,reason,status in issues: print(f"REVIEW: {sid}: {reason}; status={status}")
    if a.strict and any(status in {"cleared","licensed"} for _,_,status in issues): return 1
    print("No source content was fetched. Review flags are metadata-only."); return 0
if __name__=="__main__": raise SystemExit(main())
