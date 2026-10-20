# Hosted render repair contract

Mode: brownfield; USE, existing shared platform. Target: owner-operated Studio.
Outcome: upload -> edit -> save/reopen -> render -> verified private download.
Value: reliable client-video delivery without paid generation or lost edits.

Preserve StudioProject, existing jobs/Redis wake-up queue, tenant boundaries,
original source media and production. No schema migrations or new job system.

1. Create the immutable render manifest, job and idempotency mapping atomically.
   Same-key replay is read-only and refers to that original job across processes.
   Changed explicit request parameters conflict. Retry is an explicit new-key
   action linked to a failed job and reuses its accepted manifest.
2. Queued records are durable dispatch intent. Reserve a bounded publish window
   atomically; publish without stale post-publish document writes. Redis failure
   leaves a recoverable queued record and returns a fixed safe 503 message.
   Periodic reconciliation republishes queued jobs, including unmarked legacy
   orphans. Duplicate wake-ups are safe; queue backlog is not an execution lease.
3. Claim, renew, fail, cancel and finish under atomic job mutations. Each execution
   has a unique lease token and distinct output path. Duplicate deliveries do not
   fail active jobs. Expired/stale workers cannot publish canonical output. Stop
   heartbeats on every exit. Recovery targets render jobs only and rechecks leases.
4. Hosted UI uses the real action envelope; render/retry/status/private download
   are reachable. Polling handles terminal states and timeout without claiming
   success or cancelling a still-running job. Saved state is the render source.
5. Regression proof covers review failures, PostgreSQL races, Redis outages,
   worker crashes, source immutability and real FFmpeg output. Builds and local
   synthetic proof are distinct from authenticated staging/browser acceptance.

Rollback: revert this isolated repair and deploy previous staging image digests;
no data migration. Keep production unchanged until independent review, staging
acceptance, verified rollback and owner release approval.
