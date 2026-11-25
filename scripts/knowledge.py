#!/usr/bin/env python3
"""Backward-compatible script entrypoint for the unified private library CLI."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.knowledge_library_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
