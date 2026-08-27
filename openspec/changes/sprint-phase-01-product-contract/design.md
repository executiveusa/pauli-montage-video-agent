# Design: Reproducible product-contract verification

## Authority

The current Git tree and canonical GitHub `main` establish repository reality. `ops/upgrade/roadmap.json` remains the upgrade initiative authority. This sprint change adds a separate owner-requested release-verification layer and does not redefine upgrade identities or completion evidence.

## Dependency correction

`package-lock.json` is regenerated from the existing root and workspace manifests without changing declared product versions. A clean offline npm install must resolve Next.js 16.3.3 and its matching platform packages.

`requirements-studio.txt` declares `httpx[socks]` so application startup remains valid when an operator intentionally configures a SOCKS proxy. Provider execution remains disabled unless its existing server-side gates and credentials are enabled.

## Evidence

Unlazy gates run with explicit repository-root working directories. OpenSpec telemetry is disabled during validation. The phase proves clean npm installation, strict active-spec validation, contract round trips, tenant-aware shared services, web type checking, and production build behavior.
