# Proposal: Sprint Phase 5 media ingestion and asset library

## Why

The canonical asset service already reserves signed transfers and stores provenance, but the hosted browser path rejects uploads and binary proxying buffers large files. Users cannot complete the real upload-to-preview-to-timeline journey.

## What changes

- stream signed upload and download bodies through local or S3-compatible storage
- validate media MIME families and deduplicate active sources by verified SHA-256
- add a hosted library with progress, cancellation, retry, signed preview, timeline use, and safe archive
- keep tenant/project scope and canonical Asset v1 provenance as the only ownership model

## Impact

The public Next application gains an authenticated binary transfer proxy. The API gains file-stream storage methods and one idempotent asset-to-timeline action. No database migration or public media URL is introduced.
