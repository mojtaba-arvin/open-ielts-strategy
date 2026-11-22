#!/usr/bin/env python3
"""Read-only main branch protection and repository ruleset inventory via gh."""
import json,os,subprocess
from pathlib import Path
def gh(path):
 p=subprocess.run(["gh","api",path],capture_output=True,text=True)
 if p.returncode:
  error=p.stderr.strip()[:500]
  return {"available":False,"status":"not_configured" if "HTTP 404" in error or "Not Found" in error else "unavailable","error":error}
 try: return {"available":True,"status":"configured","data":json.loads(p.stdout)}
 except ValueError: return {"available":True,"status":"configured","data":p.stdout[:1000]}
repo=os.getenv("GITHUB_REPOSITORY","mojtaba-arvin/open-ielts-strategy")
r={"repository":repo,"branch":"main","branch_protection":gh(f"repos/{repo}/branches/main/protection"),"repository_rulesets":gh(f"repos/{repo}/rulesets"),"read_only":True}
Path("security-report.json").write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps({"repository":repo,"branch":r["branch"],"branch_protection_status":r["branch_protection"]["status"],"rulesets_status":r["repository_rulesets"]["status"]},indent=2))
