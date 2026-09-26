#!/usr/bin/env python3
"""Snapshot the MediaBrain index into the Montage runtime volume, read-only.

Runs on the HOST (not inside a container). Opens the live media-brain SQLite
index in read-only URI mode and uses SQLite's online backup API, so the source
database is never locked for writes, never modified, and the snapshot is always
a consistent point-in-time copy - even while media-brain is actively indexing.

Typical host cron (every 15 minutes):

    */15 * * * * /usr/bin/python3 /opt/montage/scripts/sync_media_index_snapshot.py \
        /opt/media-brain/media-index.db \
        /srv/montage/projects/media-index.snapshot.db >> /var/log/media-index-snapshot.log 2>&1

The destination path must live inside the existing montage projects volume so
the API/worker containers can read it without any new bind mount.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import time


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: sync_media_index_snapshot.py <source.db> <snapshot.db>", file=sys.stderr)
        return 2
    source, target = argv[1], argv[2]
    if not os.path.isfile(source):
        print(f"source index not found: {source}", file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".media-index.", suffix=".tmp", dir=os.path.dirname(os.path.abspath(target)))
    os.close(fd)
    started = time.time()
    try:
        source_connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=30)
        try:
            target_connection = sqlite3.connect(temporary)
            try:
                source_connection.backup(target_connection)
            finally:
                target_connection.close()
            clips = source_connection.execute("SELECT count(*) FROM clips").fetchone()[0]
        finally:
            source_connection.close()
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    print(f"snapshot ok: {clips} clips -> {target} ({time.time() - started:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
