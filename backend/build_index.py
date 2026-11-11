"""CLI: rebuild the SQLite index from docs/rules/*.md

Usage (from backend/):  python build_index.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.indexer import rebuild  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(rebuild(), ensure_ascii=False, indent=2))
