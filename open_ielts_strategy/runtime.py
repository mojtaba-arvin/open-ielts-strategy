"""Reproducible baseline/skill runtime with fixture and OpenAI-compatible adapters."""
import hashlib,json,os,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def _chat(messages,model,key,base):
 body=json.dumps({"model":model,"messages":messages,"temperature":0,"max_tokens":500}).encode()
 req=urllib.request.Request(base.rstrip("/")+"/chat/completions",data=body,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=90) as r: return json.loads(r.read())["choices"][0]["message"]["content"]
def run_arm(arm,cases,mode,budget=0):
 if arm not in {"baseline","skill"}: raise ValueError("invalid arm")
 skill=(ROOT/"skills/ielts-writing-feedback/SKILL.md").read_text() if arm=="skill" else ""
 model=os.getenv("OPENAI_MODEL","gpt-4o-mini"); rows=[]; calls=0
 for c in cases:
  if mode=="mock": output="FIXTURE_RESPONSE: "+c["expected"]; score=.5; passed=True
  elif mode=="openai":
   if calls>=budget: raise RuntimeError(f"request budget exhausted ({budget})")
   key=os.getenv("OPENAI_API_KEY")
   if not key: raise RuntimeError("OPENAI_API_KEY is required for live evaluation")
   system="Give concise IELTS writing feedback; do not claim official scoring."
   if skill: system+="\n\nApply this skill:\n"+skill
   output=_chat([{"role":"system","content":system},{"role":"user","content":c["input"]}],model,key,os.getenv("OPENAI_BASE_URL","https://api.openai.com/v1")); calls+=1
   score=0.0; passed=False
  else: raise ValueError("mode must be mock or openai")
  rows.append({"case_id":c["id"],"input_sha256":hashlib.sha256(c["input"].encode()).hexdigest(),"output":output,"score":score,"passed":passed,"arm":arm,"mode":mode})
 return {"schema_version":1,"arm":arm,"mode":mode,"model":model if mode=="openai" else "fixture","calls":calls,"case_ids":[c["id"] for c in cases],"results":rows}
def aggregate(base,skill):
 if base["case_ids"]!=skill["case_ids"] or [x["input_sha256"] for x in base["results"]]!=[x["input_sha256"] for x in skill["results"]]: raise ValueError("arms did not receive identical inputs")
 if base["mode"]!=skill["mode"]: raise ValueError("arm modes differ")
 return {"schema_version":1,"validation":"wiring-only" if base["mode"]=="mock" else "outputs-captured-awaiting-judge","real_skill_lift":None,"case_count":len(base["case_ids"]),"note":"Fixture output is not a model judgment; Skill Lift is not claimed." if base["mode"]=="mock" else "Judge both arms before computing behavioral Skill Lift."}
