#!/usr/bin/env python3
"""Robots-aware metadata checker; never stores or ingests source content."""
import argparse
import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "OpenIELTSStrategyMetadataChecker/1.0"


def inspect_robots(url):
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    request = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            body = response.read(100000).decode("utf-8", "replace")
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(body.splitlines())
            allowed = parser.can_fetch(USER_AGENT, url)
            return {"present": True, "http_status": response.status,
                    "disallow_all": not allowed and parser.can_fetch(USER_AGENT, "/"),
                    "allowed": allowed}, allowed
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"present": False, "http_status": 404, "allowed": True}, True
        return {"present": False, "http_status": exc.code, "allowed": False,
                "error": "robots_http_error"}, False
    except Exception as exc:
        return {"present": False, "allowed": False,
                "error": type(exc).__name__}, False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--previous", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    registry = json.loads((ROOT / "registry/sources.json").read_text())
    source = next((item for item in registry["sources"] if item["id"] == args.source_id), None)
    if not source:
        raise SystemExit("unknown source id")

    url = source["source_url"]
    report = {
        "source_id": args.source_id, "url": url, "content_ingestion": "disabled",
        "approval": "not_approved", "legal_status": source.get("legal_status", "unknown"),
    }
    robots, allowed = inspect_robots(url)
    report["robots_txt"] = robots

    previous_hash = None
    if args.previous and Path(args.previous).is_file():
        previous_hash = json.loads(Path(args.previous).read_text()).get("content_sha256")
    report["previous_hash"] = previous_hash

    if not allowed:
        report.update(
            crawl_status="blocked_by_robots", http_status=None, content_sha256=None,
            license_metadata={"link_fields": [], "meta_fields": [], "cleared": False},
            changed=None, hash_diff=None, change_tag="SKIPPED_ROBOTS_DISALLOW",
        )
    else:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=25) as response:
                body = response.read(2000000)
                report.update(http_status=response.status,
                              content_sha256=hashlib.sha256(body).hexdigest())
            html = body.decode("utf-8", "replace")
            links = re.findall(
                r"""<link[^>]+rel=["'][^"']*license[^"']*["'][^>]+href=["']([^"']+)""",
                html, re.I,
            )
            metas = re.findall(
                r"""<meta[^>]+(?:name|property)=["'](?:license|dc.rights)["']"""
                r"""[^>]+content=["']([^"']+)""", html, re.I,
            )
            report["license_metadata"] = {
                "link_fields": links[:10], "meta_fields": metas[:10], "cleared": False,
            }
            current_hash = report["content_sha256"]
            changed = bool(previous_hash and previous_hash != current_hash)
            report.update(
                crawl_status="fetched_metadata_only", changed=changed,
                hash_diff={"before": previous_hash, "after": current_hash} if changed else None,
                change_tag="CONTENT_HASH_CHANGED" if changed else
                           ("FIRST_SEEN" if not previous_hash else "UNCHANGED"),
            )
        except Exception as exc:
            report.update(fetch_error=f"{type(exc).__name__}: {exc}",
                          crawl_status="fetch_failed", changed=None, change_tag="FETCH_FAILED")

    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
