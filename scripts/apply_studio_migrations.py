#!/usr/bin/env python3
"""Apply ordered YAPPY Studio SQL migrations."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from yappy_clipz.postgres_repository import apply_migrations

url = os.environ.get("YAPPY_DATABASE_URL")
if not url:
    raise SystemExit("YAPPY_DATABASE_URL is required")
paths = sorted((ROOT / "migrations").glob("*.sql"))
if not paths:
    raise SystemExit("no migrations found")
apply_migrations(url, paths)
print(f"applied {len(paths)} migration file(s)")
