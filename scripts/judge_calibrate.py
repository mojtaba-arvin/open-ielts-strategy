#!/usr/bin/env python3
"""Run independent judge and compare issue-comment human scores."""
import argparse,json,math,os,subprocess,re
from pathlib import Path
from open_ielts_strategy.judge import judge,DIMENSIONS
def ranks(v):
 order=sorted(range(len(v)),key=lambda i:v[i]); out=[0.0]*len(v); i=0
 while i<len(order):
  j=i+1
  while j<len(order) and v[order[j]]==v[order[i]]: j+=1
  for z in order[i:j]: out[z]=(i+1+j)/2
  i=j
 return out
def rho(x,y):
 a,b=ranks(x),ranks(y); ma=sum(a)/len(a); mb=sum(b)/len(b)
 den=math.sqrt(sum((z-ma)**2 for z in a)*sum((z-mb)**2 for z in b))
 return sum((u-ma)*(v-mb) for u,v in zip(a,b))/den if den else 0.0
def main():
 p=argparse.ArgumentParser(); p.add_argument("--dry-run",action="store_true"); p.add_argument("--budget",type=int,default=0); p.add_argument("--output",default="judge-scorecard.json"); a=p.parse_args()
 items=json.loads((Path(__file__).resolve().parents[1]/"data/calibration/items.json").read_text())["items"]
 if len(items)<20: raise RuntimeError("at least 20 calibration items required")
 if a.dry_run:
  Path(a.output).write_text(json.dumps({"status":"fixture-validation-only","items":len(items),"human_rated_n":0,"reliability":None},indent=2)+"\n"); print("20-item calibration fixture valid; no model calls."); return 0
 if a.budget<1: raise RuntimeError("live judging requires --budget >= 1")
 token=os.getenv("GITHUB_TOKEN")
 if not token: raise RuntimeError("GITHUB_TOKEN required to read human issue ratings")
 repo=os.getenv("GITHUB_REPOSITORY","mojtaba-arvin/open-ielts-strategy")
 raw=subprocess.check_output(["gh","api",f"repos/{repo}/issues/comments","--paginate"],text=True)
 human={}
 for c in json.loads(raw):
  m=re.search(r"\{\s*\"item_id\"\s*:\s*\"cal-\d+\".*?\}",c.get("body",""),re.S)
  if not m: continue
  try: row=json.loads(m.group())
  except ValueError: continue
  if row.get("item_id") in {x["id"] for x in items} and all(type(row.get(k))==int and 1<=row[k]<=9 for k in DIMENSIONS): human[row["item_id"]]=row
 scored=[]
 for item in items[:a.budget]:
  scored.append({"item_id":item["id"],**judge(item["essay"],item["task"],{"dimensions":list(DIMENSIONS)}),"human":human.get(item["id"])})
 paired=[x for x in scored if x["human"]]
 report={"status":"completed","items_judged":len(scored),"human_rated_n":len(paired),"judge_model":scored[0]["model"] if scored else None,"reliability":{}}
 for dim in DIMENSIONS:
  xs=[x["human"][dim] for x in paired]; ys=[x["scores"][dim] for x in paired]
  if len(xs)<3: report["reliability"][dim]={"metric":"Spearman rho","n":len(xs),"value":None,"reason":"at least 3 paired human ratings required"}
  else:
   r=rho(xs,ys); ci=None
   if len(xs)>=10:
    # Deterministic percentile bootstrap; resample paired observations.
    import random
    rng=random.Random(20261122); samples=[]
    for _ in range(1000):
     ix=[rng.randrange(len(xs)) for _ in xs]
     try: samples.append(rho([xs[i] for i in ix],[ys[i] for i in ix]))
     except ZeroDivisionError: pass
    samples.sort()
    if samples: ci=[round(samples[int(.025*(len(samples)-1))],4),round(samples[int(.975*(len(samples)-1))],4)]
   report["reliability"][dim]={"metric":"Spearman rho","n":len(xs),"rho":round(r,4),"confidence_interval_95":ci or "insufficient_sample_for_CI"}
 Path(a.output).write_text(json.dumps({"report":report,"scorecards":scored},indent=2)+"\n"); print(json.dumps(report,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
