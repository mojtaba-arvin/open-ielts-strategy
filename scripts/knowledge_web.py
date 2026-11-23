#!/usr/bin/env python3
"""Launch the private loopback-only knowledge library UI."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.knowledge_web import serve

parser = argparse.ArgumentParser()
parser.add_argument("--db", default=".local/knowledge.sqlite3")
parser.add_argument("--port", type=int, default=8765)
args = parser.parse_args()
serve(args.db, port=args.port)
