"""Reproducible baseline/skill runtime; model and independent judge are separately metered."""
import hashlib,json,os,urllib.request,warnings
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def _chat(messages,model,key,base,json_mode=False):
 payload={"model":model,"messages":messages,"temperature":0,"max_tokens":500}
 if json_mode: payload["response_format"]={"type":"json_object"}
 req=urllib.request.Request(base.rstrip("/")+"/chat/completions",data=json.dumps(payload).encode(),headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=90) as r: return json.loads(r.read())["choices"][0]["message"]["content"]
def run_arm(arm,cases,mode,budget=0):
 if arm not in {"baseline","skill"}: raise ValueError("invalid arm")
 skill=(ROOT/"skills/ielts-writing-feedback/SKILL.md").read_text() if arm=="skill" else ""
 model=os.getenv("OPENAI_MODEL","gpt-4o-mini"); judge_model=os.getenv("JUDGE_MODEL") or "gpt-4o-mini"
 if mode=="openai":
  if budget < 2*len(cases): raise RuntimeError(f"budget must cover two calls per case; need at least {2*len(cases)}")
  if not os.getenv("OPENAI_API_KEY"): raise RuntimeError("OPENAI_API_KEY is required")
  if not os.getenv("JUDGE_API_KEY"): raise RuntimeError("JUDGE_API_KEY is required for independent scoring")
  if not os.getenv("JUDGE_MODEL"): print("WARNING: JUDGE_MODEL unset; using low-cost default gpt-4o-mini.")
 rows=[]; calls=0
 for c in cases:
  if mode=="mock":
   output="FIXTURE_RESPONSE: "+c["expected"]; score=.5; passed=True; rationale="Deterministic fixture; not a quality judgment."
  elif mode=="openai":
   system="Give concise IELTS writing feedback; do not claim official scoring."
   if skill: system+="\n\nApply this skill:\n"+skill
   output=_chat([{"role":"system","content":system},{"role":"user","content":c["input"]}],model,os.environ["OPENAI_API_KEY"],os.getenv("OPENAI_BASE_URL","https://api.openai.com/v1")); calls+=1
   judge_system="You are an independent evaluator. Score how well the assistant feedback satisfies the expected behavior and rubric. Return JSON with score from 0 to 1 and rationale. Be strict and evidence-based."
   judge_input={"case_input":c["input"],"expected_behavior":c["expected"],"rubric":c.get("rubric",{}),"assistant_feedback":output}
   raw=_chat([{"role":"system","content":judge_system},{"role":"user","content":json.dumps(judge_input)}],judge_model,os.environ["JUDGE_API_KEY"],os.getenv("JUDGE_BASE_URL","https://api.openai.com/v1"),True); calls+=1
   judged=json.loads(raw); score=float(judged["score"])
   if not 0<=score<=1: raise ValueError("judge score must be between 0 and 1")
   passed=score>=.7; rationale=str(judged.get("rationale",""))
  else: raise ValueError("mode must be mock or openai")
  rows.append({"case_id":c["id"],"input_sha256":hashlib.sha256(c["input"].encode()).hexdigest(),"output":output,"score":score,"passed":passed,"rationale":rationale,"arm":arm,"mode":mode})
 return {"schema_version":1,"arm":arm,"mode":mode,"model":model if mode=="openai" else "fixture","judge_model":judge_model if mode=="openai" else "fixture","calls":calls,"case_ids":[c["id"] for c in cases],"results":rows}
def aggregate(base,skill):
 if base["case_ids"]!=skill["case_ids"] or [x["input_sha256"] for x in base["results"]]!=[x["input_sha256"] for x in skill["results"]]: raise ValueError("arms did not receive identical inputs")
 if base["mode"]!=skill["mode"]: raise ValueError("arm modes differ")
 if base["mode"]=="mock": return {"schema_version":1,"validation":"wiring-only","real_skill_lift":None,"case_count":len(base["case_ids"]),"note":"Fixture output is not a model judgment; no Skill Lift is claimed."}
 if [x["case_id"] for x in base["results"]]!=[x["case_id"] for x in skill["results"]]: raise ValueError("scorecard case IDs differ")
 b=sum(x["score"] for x in base["results"])/len(base["results"]); s=sum(x["score"] for x in skill["results"])/len(skill["results"])
 return {"schema_version":1,"validation":"independently-judged","baseline_mean_score":round(b,4),"with_skill_mean_score":round(s,4),"real_skill_lift":round(s-b,4),"baseline_resolution_rate":round(sum(x["passed"] for x in base["results"])/len(base["results"]),4),"with_skill_resolution_rate":round(sum(x["passed"] for x in skill["results"])/len(skill["results"]),4),"case_count":len(base["case_ids"]),"judge_model":base["judge_model"]}
