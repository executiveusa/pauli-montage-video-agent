"""Read-only MediaBrain footage-library source for YAPPY-CLIPZ.

MediaBrain (on-box footage index) is the owner's curated, never-copied media
library. This adapter reads a SQLite *snapshot* of that index and registers
clips into StudioProject assets by reference. It never copies, moves, writes
to, or deletes library footage, and it never writes to the index database.

Design rules:
- The index is opened through SQLite's read-only URI mode on every call, so a
  refreshed snapshot (and a growing upstream index) is always served fresh.
- Clip file locations are derived, never accepted from callers: the absolute
  host path is always ``host_root / <index path> / <index name>`` and is
  rejected if it escapes the configured library root.
- Byte access is deferred by deployment policy: assets record
  ``byteAccess=deferred-mount-pending`` until the owner approves a read-only
  bind mount of the library into the runtime containers.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

_PROVIDER = "medialibrary"
_CLIP_COLUMNS = (
    "id", "account", "remote", "source", "name", "path", "mime", "bytes",
    "md5", "modtime", "capture_date", "date_basis", "link", "kind",
    "canonical_id", "vision", "tier",
)
_MAX_LIMIT = 500


class MediaLibraryError(RuntimeError):
    """Base error for media library source failures."""


class MediaLibraryNotConfigured(MediaLibraryError):
    """Raised when the snapshot is not configured or not synced yet."""


class ClipNotFound(MediaLibraryError):
    """Raised when one clip id is absent from the index snapshot."""


def _connect(index_path: Path) -> sqlite3.Connection:
    uri = f"file:{index_path}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def _like_terms(text: str) -> list[str]:
    """Split a query into LIKE patterns with %, _ and the escape char neutralised."""
    patterns = []
    for token in text.split():
        escaped = token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        patterns.append(f"%{escaped}%")
    return patterns


def _matched_tags(raw: Any, query: str) -> list[str]:
    try:
        tags = json.loads(raw) if isinstance(raw, str) else []
    except ValueError:
        return []
    words = [w.lower() for w in query.split()]
    return [t for t in tags if isinstance(t, str) and any(w in t.lower() for w in words)][:5]


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}


class MediaLibraryService:
    """Framework-independent read-only adapter over the MediaBrain index snapshot."""

    def __init__(self, *, index_path: Path | str | None, host_root: str, enabled: bool = True,
                 host_roots: dict[str, str] | None = None) -> None:
        self.index_path = Path(index_path).expanduser() if index_path else None
        self.host_root = PurePosixPath(host_root or "/mnt/mb-gdrive-samsung")
        self.enabled = enabled
        # Optional multi-root map: keys are "remote:<name>" or "account:<name>".
        # When set, every clip must match a key (remote first, then account);
        # unmatched clips fail closed instead of falling back to host_root.
        self.host_roots: dict[str, PurePosixPath] = {}
        for key, root in (host_roots or {}).items():
            kind, _, value = str(key).partition(":")
            if kind not in {"remote", "account"} or not value or not str(root).startswith("/"):
                raise MediaLibraryError("invalid media library root mapping: " + str(key))
            self.host_roots[f"{kind}:{value}"] = PurePosixPath(str(root))

    def _root_for(self, record: dict[str, Any]) -> PurePosixPath:
        if not self.host_roots:
            return self.host_root
        for kind in ("remote", "account"):
            value = record.get(kind)
            if value and f"{kind}:{value}" in self.host_roots:
                return self.host_roots[f"{kind}:{value}"]
        raise MediaLibraryError(
            "no library root is mapped for remote=%r account=%r" % (record.get("remote"), record.get("account"))
        )

    # -- connection ---------------------------------------------------------
    def _connection(self) -> sqlite3.Connection:
        if not self.enabled:
            raise MediaLibraryNotConfigured("media library source is disabled")
        if self.index_path is None:
            raise MediaLibraryNotConfigured("media library index snapshot path is not configured")
        if not self.index_path.is_file():
            raise MediaLibraryNotConfigured(
                "media library index snapshot is not synced yet: " + str(self.index_path)
            )
        try:
            return _connect(self.index_path)
        except sqlite3.Error as exc:
            raise MediaLibraryError("media library index snapshot is unreadable") from exc

    # -- normalization ------------------------------------------------------
    def _host_path(self, record: dict[str, Any]) -> str:
        rel = str(record.get("path") or "").strip().strip("/")
        name = str(record.get("name") or "").strip()
        if not name or "/" in name or name in {".", ".."}:
            raise MediaLibraryError("clip record has an unsafe file name")
        parts = [part for part in rel.split("/") if part] if rel else []
        if any(part in {".", ".."} for part in parts):
            raise MediaLibraryError("clip record path escapes the library root")
        root = self._root_for(record)
        candidate = PurePosixPath(root, *parts, name)
        root_text = str(root).rstrip("/")
        if not str(candidate).startswith(root_text + "/"):
            raise MediaLibraryError("clip record path escapes the library root")
        return str(candidate)

    def _normalize(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        record = {column: row[column] for column in _CLIP_COLUMNS if column in row.keys()} if isinstance(row, sqlite3.Row) else dict(row)
        clip = {
            "id": str(record.get("id") or ""),
            "account": record.get("account"),
            "remote": record.get("remote"),
            "name": record.get("name"),
            "path": record.get("path"),
            "mime": record.get("mime"),
            "bytes": int(record.get("bytes") or 0),
            "md5": record.get("md5"),
            "modtime": record.get("modtime"),
            "captureDate": record.get("capture_date"),
            "dateBasis": record.get("date_basis"),
            "link": record.get("link"),
            "kind": record.get("kind"),
            "canonicalId": record.get("canonical_id"),
            "vision": record.get("vision"),
            "tier": record.get("tier"),
            "provider": _PROVIDER,
        }
        clip["hostPath"] = self._host_path({"path": clip["path"], "name": clip["name"], "remote": clip["remote"], "account": clip["account"]})
        return clip

    # -- reads ----------------------------------------------------------------
    def status(self) -> dict[str, Any]:
        with self._connection() as connection:
            total = connection.execute("SELECT count(*) FROM clips").fetchone()[0]
            tables = _tables(connection)
            vision_present = {name: name in tables for name in ("photos", "frames", "vtags")}
            by_kind = {row[0] or "unknown": row[1] for row in connection.execute("SELECT kind, count(*) FROM clips GROUP BY kind")}
            by_tier = {row[0] or "unknown": row[1] for row in connection.execute("SELECT tier, count(*) FROM clips GROUP BY tier")}
            by_vision = {row[0] or "unknown": row[1] for row in connection.execute("SELECT vision, count(*) FROM clips GROUP BY vision")}
            fts_available = connection.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='clips_fts'"
            ).fetchone()[0] == 1
            meta: dict[str, str] = {}
            try:
                meta = {str(row[0]): str(row[1]) for row in connection.execute("SELECT key, value FROM meta")}
            except sqlite3.Error:
                meta = {}
        age_seconds = None
        if self.index_path is not None and self.index_path.is_file():
            age_seconds = max(0, int(time.time() - os.stat(self.index_path).st_mtime))
        return {
            "provider": _PROVIDER,
            "enabled": self.enabled,
            "snapshotPath": str(self.index_path) if self.index_path else None,
            "snapshotAgeSeconds": age_seconds,
            "hostRoot": str(self.host_root),
            "hostRoots": {key: str(root) for key, root in self.host_roots.items()},
            "visionTablesPresent": vision_present,
            "counts": {"clips": total, "byKind": by_kind, "byTier": by_tier, "byVision": by_vision},
            "ftsAvailable": fts_available,
            "meta": meta,
            "byteAccess": "deferred-mount-pending",
            "remoteWriteEnabled": False,
        }

    def list_clips(
        self,
        *,
        kind: str | None = None,
        tier: str | None = None,
        account: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit), _MAX_LIMIT))
        offset = max(0, int(offset))
        filters: list[str] = []
        params: list[Any] = []
        if kind:
            filters.append("kind = ?"); params.append(kind)
        if tier:
            filters.append("tier = ?"); params.append(tier)
        if account:
            filters.append("account = ?"); params.append(account)
        where = (" WHERE " + " AND ".join(filters)) if filters else ""
        with self._connection() as connection:
            total = connection.execute(f"SELECT count(*) FROM clips{where}", params).fetchone()[0]
            rows = connection.execute(
                f"SELECT rowid, * FROM clips{where} ORDER BY capture_date DESC, rowid DESC LIMIT ? OFFSET ?",
                (*params, limit, offset),
            ).fetchall()
        items = [self._normalize(row) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset, "remoteWriteEnabled": False}

    def search(self, *, query: str, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        text = (query or "").strip()
        if not text:
            raise MediaLibraryError("query is required")
        limit = max(1, min(int(limit), _MAX_LIMIT))
        offset = max(0, int(offset))
        with self._connection() as connection:
            fts_available = connection.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='clips_fts'"
            ).fetchone()[0] == 1
            rows: list[sqlite3.Row] = []
            mode = "like"
            if fts_available:
                match = " ".join(f'"{token}"' for token in text.split() if token)
                try:
                    rows = connection.execute(
                        "SELECT c.rowid, c.* FROM clips_fts f JOIN clips c ON c.rowid = f.rowid "
                        "WHERE clips_fts MATCH ? ORDER BY rank LIMIT ? OFFSET ?",
                        (match, limit, offset),
                    ).fetchall()
                    mode = "fts"
                except sqlite3.Error:
                    rows = []
                    mode = "like"
            if not rows and mode == "like":
                like = f"%{text}%"
                rows = connection.execute(
                    "SELECT rowid, * FROM clips WHERE name LIKE ? OR path LIKE ? OR vision LIKE ? "
                    "ORDER BY rowid DESC LIMIT ? OFFSET ?",
                    (like, like, like, limit, offset),
                ).fetchall()
        items = [self._normalize(row) for row in rows]
        return {"items": items, "query": text, "mode": mode, "limit": limit, "offset": offset, "remoteWriteEnabled": False}

    def search_vision(self, *, query: str, limit: int = 50) -> dict[str, Any]:
        """Search Takeout/vision metadata: vtags caption arrays and photo descriptions.

        Every query word must appear (AND, case-insensitive substring). Tables
        that are absent from the snapshot are skipped and reported, never an
        error. Embedding (frames.emb) similarity is not used here.
        """
        text = (query or "").strip()
        if not text:
            raise MediaLibraryError("query is required")
        limit = max(1, min(int(limit), _MAX_LIMIT))
        patterns = _like_terms(text)
        with self._connection() as connection:
            tables = _tables(connection)
            present = {name: name in tables for name in ("photos", "frames", "vtags")}
            clips: list[dict[str, Any]] = []
            photos: list[dict[str, Any]] = []
            if present["vtags"]:
                where = " AND ".join("v.tags LIKE ? ESCAPE '\\'" for _ in patterns)
                rows = connection.execute(
                    "SELECT c.rowid AS rowid, c.*, v.tags AS vtags_tags FROM vtags v JOIN clips c ON c.id = v.clip_id "
                    f"WHERE {where} ORDER BY c.rowid DESC LIMIT ?",
                    (*patterns, limit),
                ).fetchall()
                for row in rows:
                    clip = self._normalize(row)
                    clip["matchedTags"] = _matched_tags(row["vtags_tags"], text)
                    if present["frames"]:
                        clip["frameTimes"] = [
                            r[0] for r in connection.execute(
                                "SELECT t FROM frames WHERE clip_id = ? ORDER BY t LIMIT 50", (clip["id"],)
                            )
                        ]
                    clips.append(clip)
            if present["photos"]:
                where = " AND ".join(
                    "(coalesce(description,'') || ' ' || coalesce(name,'') || ' ' || coalesce(album,'')) LIKE ? ESCAPE '\\'"
                    for _ in patterns
                )
                for row in connection.execute(
                    "SELECT id, album, name, kind, bytes, taken, year, lat, lon, description, vision "
                    f"FROM photos WHERE {where} ORDER BY taken DESC LIMIT ?",
                    (*patterns, limit),
                ):
                    photos.append({
                        "id": row["id"], "album": row["album"], "name": row["name"], "kind": row["kind"],
                        "bytes": int(row["bytes"] or 0), "taken": row["taken"], "year": row["year"],
                        "lat": row["lat"], "lon": row["lon"], "description": row["description"],
                        "visionStatus": row["vision"], "provider": _PROVIDER,
                        "byteAccess": "takeout-archive-not-mounted",
                    })
        return {"query": text, "clips": clips, "photos": photos, "visionTablesPresent": present,
                "limit": limit, "remoteWriteEnabled": False}

    def get_clip(self, clip_id: str) -> dict[str, Any]:
        ident = str(clip_id or "").strip()
        if not ident:
            raise ClipNotFound("clip id is required")
        with self._connection() as connection:
            row = connection.execute("SELECT rowid, * FROM clips WHERE id = ?", (ident,)).fetchone()
        if row is None:
            raise ClipNotFound(f"clip not found in media library index: {ident}")
        return self._normalize(row)

    def get_clips(self, clip_ids: list[str]) -> Iterator[dict[str, Any]]:
        for clip_id in clip_ids:
            yield self.get_clip(clip_id)
