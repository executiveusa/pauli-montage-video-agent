# Acceptance: Architecture and delivery contract

- Exactly one machine-readable roadmap contains Slices 00–14 with unique titles and immutable OpenSpec IDs.
- ADRs establish PopeBot, Composio, owned storage, StudioProject, adapters, Ralphy, Gauntlet, GRINIONS, and GitHub ownership boundaries.
- The parity map assigns every requested behavior to one canonical YAPPY owner and names forbidden duplicates.
- All extraction sources are pinned to exact upstream commits with license evidence or explicit no-copy treatment.
- Ralphy's supported YAML fields are parser-tested; GRINIONS pins sequential execution, branch-per-task, exact base branch, retries, browser policy, and no-merge behavior through tested CLI arguments.
- Execution-tool versions are recorded.
- Completion evidence requires globally unique exact canonical PR, head, merge/tree/main, independent judgment, post-merge, Slice OpenSpec, and rollback facts; Git verification targets fetched `origin/main`, never feature `HEAD`.
- Generated progress reports only Slice 00 complete and rejects false or stale completion claims.
- Governance tests and strict OpenSpec validation pass.
- No runtime, provider, database, Supabase, OpenAI API, deployment, secrets, or customer data changes occur.
