"""Deterministic MVP semantic routing and conflict resolution."""
import re
WRITING="ielts-writing-feedback"
def route(text):
 s=text.lower()
 if re.search(r"\b(speaking|listening|reading)\b",s): return {"skill_id":None,"confidence":.98,"reason":"non-writing IELTS task"}
 task=bool(re.search(r"\b(task\s*[12]|task one|task two|chart|graph|table|essay|opinion|discuss both)\b",s))
 draft=bool(re.search(r"\b(essay|draft|my writing|my response|report|paragraph)\b",s))
 if task and draft: return {"skill_id":WRITING,"confidence":.94,"reason":"IELTS writing task and learner draft detected"}
 if draft and "ielts" in s: return {"skill_id":WRITING,"confidence":.72,"reason":"IELTS learner draft; clarify task"}
 return {"skill_id":None,"confidence":.35,"reason":"insufficient evidence"}
def resolve_conflicts(candidates):
 if not candidates: return None
 required={"skill_id","priority","confidence","validated_at"}
 for c in candidates:
  if not required.issubset(c): raise ValueError("candidate missing conflict metadata")
  if not 0<=float(c["confidence"])<=1: raise ValueError("confidence must be between 0 and 1")
 return sorted(candidates,key=lambda c:(-int(c["priority"]),-float(c["confidence"]),-str(c["validated_at"]),str(c["skill_id"])))[0]
