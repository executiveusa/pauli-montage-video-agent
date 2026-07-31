# Phase 08 Proposal — Asset Registry, Media Ingest, and Provenance

## Outcome
Implement signed tenant-scoped transfers, local and S3-compatible object storage adapters, canonical Asset v1 lifecycle operations, checksums, metadata, source lineage, rights, versions, derivatives, archive state, and ICM-safe asset references.

## Safety
Incomplete uploads, size mismatches, checksum failures, private path traversal, and cross-tenant transfer tokens fail before canonical project mutation. No customer media or storage credentials are committed.
