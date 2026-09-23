#!/usr/bin/env python3
"""Apply ordered YAPPY Studio SQL migrations once each, tracked in a ledger table.

Safe to run on every container start: already-applied files are skipped, so
non-idempotent statements (CREATE POLICY) never run twice.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg  # noqa: E402

url = os.environ.get("YAPPY_DATABASE_URL")
if not url:
    raise SystemExit("YAPPY_DATABASE_URL is required")
paths = sorted((ROOT / "migrations").glob("*.sql"))
if not paths:
    raise SystemExit("no migrations found")
applied_now = 0
with psycopg.connect(url, autocommit=True) as conn:
    conn.execute("SELECT pg_advisory_lock(727001)")
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS yappy_schema_migrations ("
            "filename text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        done = {row[0] for row in conn.execute("SELECT filename FROM yappy_schema_migrations")}
        for path in paths:
            if path.name in done:
                continue
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO yappy_schema_migrations (filename) VALUES (%s)", (path.name,))
            applied_now += 1
    finally:
        conn.execute("SELECT pg_advisory_unlock(727001)")
print(f"migrations: {applied_now} applied now, {len(paths)} total")
