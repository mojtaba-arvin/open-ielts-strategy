#!/usr/bin/env python3
"""Metadata-only crawl skeleton: hashes response bytes but never stores source content."""
import argparse,hashlib,json,re,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(); p.add_argument("--source-id",required=True); p.add_argument("--previous",default=""); p.add_argument("--output",required=True); a=p.parse_args()
 registry=json.loads((ROOT/"registry/sources.json").read_text()); src=next((x for x in registry["sources"] if x["id"]==a.source_id),None)
 if not src: raise SystemExit("unknown source id")
 url=src["source_url"]; report={"source_id":a.source_id,"url":url,"content_ingestion":"disabled","approval":"not_approved","legal_status":src.get("legal_status","unknown")}
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"OpenIELTSStrategyMetadataChecker/1.0"})
  with urllib.request.urlopen(req,timeout=25) as r: body=r.read(2000000); report.update(http_status=r.status,content_sha256=hashlib.sha256(body).hexdigest())
  u=urlsplit(url); robots=f"{u.scheme}://{u.netloc}/robots.txt"
  try:
   with urllib.request.urlopen(urllib.request.Request(robots,headers={"User-Agent":"OpenIELTSStrategyMetadataChecker/1.0"}),timeout=12) as r:
    rb=r.read(100000).decode("utf-8","replace"); report["robots_txt"]={"present":True,"http_status":r.status,"disallow_all":"Disallow: /" in rb}
  except Exception as e: report["robots_txt"]={"present":False,"error":type(e).__name__}
  html=body.decode("utf-8","replace")
  links=re.findall(r'<link[^>]+rel=["\'][^"\']*license[^"\']*["\'][^>]+href=["\']([^"\']+)',html,re.I)
  metas=re.findall(r'<meta[^>]+(?:name|property)=["\'](?:license|dc.rights)["\'][^>]+content=["\']([^"\']+)',html,re.I)
  report["license_metadata"]={"link_fields":links[:10],"meta_fields":metas[:10],"cleared":False}
  old=json.loads(Path(a.previous).read_text()).get("content_sha256") if a.previous and Path(a.previous).is_file() else None
  report["previous_hash"]=old; report["changed"]=bool(old and old!=report["content_sha256"])
  report["change_tag"]="CONTENT_HASH_CHANGED" if report["changed"] else ("FIRST_SEEN" if not old else "UNCHANGED")
 except Exception as e: report.update(fetch_error=f"{type(e).__name__}: {e}",changed=None,change_tag="FETCH_FAILED")
 Path(a.output).write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report,indent=2))
 return 0
if __name__=="__main__": raise SystemExit(main())
