#!/usr/bin/env python3
"""Read-only main branch protection and repository ruleset inventory via gh."""
import json,os,subprocess
from pathlib import Path
def gh(path):
 p=subprocess.run(["gh","api",path],capture_output=True,text=True)
 if p.returncode: return {"available":False,"error":p.stderr.strip()[:500]}
 try: return {"available":True,"data":json.loads(p.stdout)}
 except ValueError: return {"available":True,"data":p.stdout[:1000]}
repo=os.getenv("GITHUB_REPOSITORY","mojtaba-arvin/open-ielts-strategy")
r={"repository":repo,"branch":"main","branch_protection":gh(f"repos/{repo}/branches/main/protection"),"repository_rulesets":gh(f"repos/{repo}/rulesets"),"read_only":True}
Path("security-report.json").write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps({"branch":r["branch"],"protection_available":r["branch_protection"]["available"],"protection_error":r["branch_protection"].get("error"),"rulesets_available":r["repository_rulesets"]["available"],"rulesets_error":r["repository_rulesets"].get("error")},indent=2))
