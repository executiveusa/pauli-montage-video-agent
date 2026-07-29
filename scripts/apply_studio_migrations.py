#!/usr/bin/env python3
"""Apply ordered YAPPY Studio SQL migrations."""
from __future__ import annotations
import os
from pathlib import Path
from yappy_clipz.postgres_repository import apply_migrations

url = os.environ.get("YAPPY_DATABASE_URL")
if not url:
    raise SystemExit("YAPPY_DATABASE_URL is required")
paths = sorted(Path("migrations").glob("*.sql"))
if not paths:
    raise SystemExit("no migrations found")
apply_migrations(url, paths)
print(f"applied {len(paths)} migration file(s)")
