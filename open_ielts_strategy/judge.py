"""Independent IELTS writing rubric judge; credentials/model are separate from agent runtime."""
import json,os,urllib.request
DIMENSIONS=("task_response","coherence_cohesion","lexical_resource","grammar_accuracy")
def judge(essay,task,rubric,api_key=None):
 key=api_key or os.getenv("JUDGE_API_KEY")
 if not key: raise RuntimeError("JUDGE_API_KEY is required for live judging")
 model=os.getenv("JUDGE_MODEL")
 if not model:
  model="gpt-4o-mini"; print("WARNING: JUDGE_MODEL unset; using low-cost default gpt-4o-mini.")
 prompt={"task":task,"essay":essay,"rubric":rubric,"dimensions":list(DIMENSIONS),"instruction":"Return JSON only: scores with integer 1..9 per dimension, overall integer 1..9, rationale with evidence-grounded text per dimension. Not an official IELTS score."}
 body=json.dumps({"model":model,"temperature":0,"response_format":{"type":"json_object"},"messages":[{"role":"system","content":"Assess IELTS writing conservatively. Do not invent evidence."},{"role":"user","content":json.dumps(prompt)}]}).encode()
 req=urllib.request.Request(os.getenv("JUDGE_BASE_URL","https://api.openai.com/v1").rstrip("/")+"/chat/completions",data=body,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=90) as r: data=json.loads(r.read())
 out=json.loads(data["choices"][0]["message"]["content"])
 if set(out.get("scores",{}))!=set(DIMENSIONS): raise ValueError("judge dimensions mismatch")
 if any(type(v)!=int or not 1<=v<=9 for v in out["scores"].values()): raise ValueError("scores must be integers 1..9")
 if type(out.get("overall"))!=int or not 1<=out["overall"]<=9 or not isinstance(out.get("rationale"),dict): raise ValueError("invalid judge output")
 return {"model":model,"scores":out["scores"],"overall":out["overall"],"rationale":out["rationale"]}
