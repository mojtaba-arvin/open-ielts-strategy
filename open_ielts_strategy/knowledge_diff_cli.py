"""Generate a review-only diff between two verified Knowledge Pack directories."""
from __future__ import annotations

import argparse
import json
import sys

from .knowledge_pack_diff import diff_pack_directories


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", required=True)
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args(argv)
    try:
        result = diff_pack_directories(args.current, args.candidate)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
