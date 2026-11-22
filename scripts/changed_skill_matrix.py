"""Select only affected skill fixtures for pull-request runtime evaluation."""
import argparse
import json
import re
import subprocess

SKILL_IDS = (
    "ielts-writing-feedback",
    "ielts-speaking-transcript-feedback",
    "ielts-reading-strategy",
    "ielts-listening-strategy",
)
SHARED_PATHS = {
    ".github/workflows/runtime-evaluation.yml", "skills.lock",
    "open_ielts_strategy/runtime.py", "open_ielts_strategy/evaluation.py",
    "scripts/runtime_eval.py", "scripts/aggregate_runtime.py",
    "scripts/changed_skill_matrix.py", "tests/test_runtime.py",
    "tests/test_runtime_matrix.py",
}

def select_skill_ids(paths):
    """Return changed skills, or all skills for shared/unknown runtime changes."""
    if not isinstance(paths, (list, tuple, set)) or not paths:
        return list(SKILL_IDS)
    normalized = []
    for path in paths:
        if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/") or "\\" in path:
            raise ValueError("changed paths must be normalized repository-relative paths")
        normalized.append(path)
    if any(path in SHARED_PATHS for path in normalized):
        return list(SKILL_IDS)
    selected = [skill for skill in SKILL_IDS if any(path.startswith(f"skills/{skill}/") for path in normalized)]
    return selected or list(SKILL_IDS)

def changed_paths(base, head):
    for value in (base, head):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
            raise ValueError("base and head must be full Git commit SHAs")
    output = subprocess.check_output(["git", "diff", "--name-only", f"{base}...{head}"], text=True)
    return [line for line in output.splitlines() if line]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--head")
    args = parser.parse_args()
    if bool(args.base) != bool(args.head):
        parser.error("--base and --head must be supplied together")
    paths = changed_paths(args.base, args.head) if args.base else []
    print(json.dumps(select_skill_ids(paths), separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
