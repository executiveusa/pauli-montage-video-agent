# MediaBrain Library Source

The owner's MediaBrain footage index is wired into YAPPY-CLIPZ as a read-only
media source. Clips are discovered through a snapshot of the index and
registered into projects as provenance-carrying reference assets. Source
footage is never copied, moved, or deleted.

## Configuration

| Env | Default | Purpose |
| --- | --- | --- |
| `YAPPY_MEDIA_LIBRARY_ENABLED` | `false` | Master switch for the source. |
| `YAPPY_MEDIA_LIBRARY_INDEX` | `<project_root>/../media-index.snapshot.db` | SQLite snapshot path (must live inside an existing runtime volume). |
| `YAPPY_MEDIA_LIBRARY_HOST_ROOT` | `/mnt/mb-gdrive-samsung` | Host library root used to derive clip host paths. |
| `YAPPY_MEDIA_LIBRARY_MOUNT_VISIBLE` | `false` | Set `1` only after the owner approves the read-only library bind mount; unblocks render URI resolution for library assets. |

## Snapshot sync (host side)

`scripts/sync_media_index_snapshot.py` copies the live media-brain index into
the runtime volume using SQLite's online backup API opened read-only, so the
source database is never modified or locked and the snapshot is consistent even
while indexing runs. Run it from cron on the host, e.g. every 15 minutes:

```bash
/usr/bin/python3 scripts/sync_media_index_snapshot.py \
    /opt/media-brain/media-index.db \
    <montage-projects-volume>/media-index.snapshot.db
```

Every source action re-opens the snapshot, so refreshes and a growing index
are served fresh. `library.media.status` reports the snapshot age.

## Actions

- `library.media.status` (scope `asset:read`) - snapshot freshness, clip counts by kind/tier/vision, FTS availability.
- `library.media.list` (scope `asset:read`) - paged clip listing with kind/tier/account filters.
- `library.media.search` (scope `asset:read`) - FTS5 search with keyword fallback.
- `library.media.get` (scope `asset:read`) - one clip with its derived host path.
- `library.media.register` (scopes `asset:write`, `project:read`) - register-footage: adds clips to a project as reference assets. Idempotent per project (re-registering returns the existing asset). All clip ids are validated before any write.

## Asset shape and the deferred mount

Registered assets fit the canonical Asset v1 contract:

- `storage.type = provider`, `storage.key = medialibrary://<clip id>` - a
  namespaced reference, not a filesystem path.
- `source.type = imported`, `source.provider = medialibrary`, `sourceUrl` =
  the Drive link from the index.
- `checksum = null` on purpose: the index md5 is attestation metadata (kept in
  `extensions.medialibrary.md5`), not a verified checksum. Final renders
  require verified checksums, so they stay correctly blocked until bytes are
  verified against the library after the mount lands.
- `extensions.medialibrary.hostPath` - the derived host path
  (`host_root/<index path>/<index name>`), containment-checked at registration.

Renders of timeline items pointing at library assets fail closed with a clear
error until `YAPPY_MEDIA_LIBRARY_MOUNT_VISIBLE=1`, which is the config flag
that flips once the owner approves the read-only bind mount of
`/mnt/mb-gdrive-samsung` into the api/worker containers.
