# Phase receipts

GRINIONS writes machine-readable completion receipts here only after merge and post-merge verification succeed.

Git/GitHub remain canonical release truth. A receipt is a compact, versioned evidence index for later agents and operators.

## Schema v1

Required fields:

```json
{
  "schemaVersion": 1,
  "phaseId": "05",
  "openspecId": "phase-05-twick-round-trip",
  "risk": "medium",
  "completedAt": "2026-07-22T01:00:00Z",
  "baselineMainSha": "...",
  "beads": [],
  "pullRequest": {
    "number": 42,
    "url": null,
    "headSha": "..."
  },
  "judgment": {
    "passed": true,
    "unresolvedReviewThreads": 0
  },
  "merge": {
    "sha": "...",
    "mergedAt": "..."
  },
  "postMerge": {
    "passed": true,
    "mainSha": "..."
  },
  "rollback": {
    "baselineCaptured": true,
    "receiptPath": "ops/rollback/phase-05.json"
  }
}
```

`phaseId`, `openspecId`, `risk`, `completedAt`, `baselineMainSha`, `beads`, a passed `judgment`, `merge.sha`, a passed `postMerge`, and `postMerge.mainSha` are required.

PR number/URL, merge timestamp, unresolved-thread count, and per-Bead head/status fields may be null when the upstream tool cannot provide them, but the receipt may not claim completion without verified merge and post-merge evidence.

The implementation contract lives in `ops/grinions/src/receipt.mjs`. `attest` must build and validate the versioned receipt before writing it. Arbitrary internal objects such as workspace paths, credentials, provider secrets, or full tool payloads must not be spread into the receipt.
