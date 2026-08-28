# Phase 5 — Media ingestion and asset library

## Outcome

Connect the hosted Studio to the canonical Asset v1 service so an authenticated workspace owner can stream supported media into tenant-owned storage, watch upload progress, cancel or retry, reopen a durable library, preview the original, place it on the project timeline, and archive it without silently destroying bytes or edit history.

## User journey

From a hosted project, the owner chooses a video, audio, or image file. Montage reserves a signed tenant/project transfer, streams the file through the authenticated proxy, verifies byte count and SHA-256 evidence, deduplicates an identical active source, and records provenance only after storage verification. The library restores from canonical project state after refresh. Signed previews remain private. “Use in timeline” creates one deterministic asset item; repeated use is idempotent. “Archive” hides the item while retaining the original and references.

## Storage and large-file boundary

- upload and download bodies stream in bounded chunks instead of being loaded wholly into API memory
- local storage writes through an fsynced temporary file and atomic replacement
- S3-compatible storage uses managed file upload and object metadata checksums
- browser progress and cancellation are provided by `XMLHttpRequest`; retry creates a fresh signed reservation
- maximum upload size and transfer expiry remain operator-configured
- signed transfer claims bind operation, tenant, project, asset, key, MIME, byte limit, and optional checksum

## Supported media and previews

Phase 5 accepts browser-declared `video/*`, `audio/*`, and `image/*` sources whose MIME family matches the requested canonical kind. The library uses signed original-media previews and video metadata frames as thumbnails. Transcoding, proxy derivatives, waveform generation, and content-level malware inspection belong to persistent worker hardening rather than the Vercel frontend.

## Deletion semantics

The user-facing removal action is archive: canonical history and object bytes are retained so timeline references do not break. Irreversible purge remains an operator retention action for Phase 13, after export, legal-retention, derivative-reference, and backup policies are verified.

## Non-goals

- no unauthenticated public media URLs
- no GPU transcription or generated proxy media (Phase 6)
- no complete timeline editing surface (Phase 7)
- no external URL/provider imports (Phase 11)
- no claim that S3 or a persistent production API is currently deployed

## Verification boundary

Executable tests use two authenticated workspaces and real byte transfers to prove cross-tenant rejection, streamed upload/download, persistence after runtime reconstruction, signed preview, timeline use, checksum deduplication, safe archive, MIME rejection, incomplete-transfer rejection, and browser progress/cancel/retry contracts. The cloud browser cannot reach the workspace loopback server, so no screenshot acceptance is claimed.

## Rollback

Revert the Phase 5 merge to `40ca2ec3517b25bf39a2671c6587181e84c38410`. The phase adds no migration. Archived assets and stored originals remain readable after rollback.
