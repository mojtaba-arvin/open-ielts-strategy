#!/usr/bin/env python3
"""Backward-compatible script entrypoint for unified semantic extraction."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.knowledge_extract_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
