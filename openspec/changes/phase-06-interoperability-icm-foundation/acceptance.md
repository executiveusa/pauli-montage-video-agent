# Phase 06 acceptance criteria

## Contract acceptance

### Capability registry

- Given the Phase 06 registry, when it is validated, then every stable public action has a unique ID, valid schemas, lifecycle metadata, scopes, risk, execution type, idempotency policy, ICM mapping, and CLI/API/MCP mappings.
- Given an invalid or duplicate capability record, when the application or CI loads the registry, then startup/validation fails closed with a deterministic problem.
- Given the same source tree, when the registry snapshot is generated twice, then the output is byte-for-byte deterministic.

### Universal actions

- Given a current project or timeline operation, when it is invoked through the generic dispatcher, then the domain result matches the verified Phase 05 service behavior.
- Given the same mutation and idempotency key, when it is submitted twice, then no duplicate canonical mutation or job is created.
- Given a stale timeline version, when it is invoked through CLI, API, and MCP, then every transport returns the same conflict code and equivalent version details.
- Given insufficient scope, when an action is invoked, then the handler is not called and every transport returns equivalent authorization denial.

### CLI

- Given an agent with no repository knowledge, when it runs capability discovery, then it can list and describe exact schemas and invocation metadata.
- Given non-TTY JSON mode, when any command succeeds or fails, then the CLI emits exactly one machine-readable result or problem document and never prompts interactively.
- Given a long-action contract, when `--wait` is absent, then the CLI returns a job receipt rather than blocking indefinitely.

### API

- Given the OpenAPI document, when it is generated on the same source tree, then it matches the approved snapshot.
- Given a protected hosted route, when no verified principal exists, then caller-provided tenant headers do not authorize access.
- Given an idempotent mutation, when `Idempotency-Key` is absent, then the API returns the documented validation problem.
- Given a correlation ID, when a request succeeds or fails, then the result/problem and emitted evidence preserve the same ID.

### MCP

- Given an MCP client, when it lists tools, then capability discovery and generic action execution are present.
- Given a named convenience tool, when it is invoked, then it delegates to the same dispatcher and schemas as the generic action.
- Given a tool failure, when the client receives the result, then it contains the same standardized problem code as CLI/API.

## ICM acceptance

### Workspace and run identity

- Given an authenticated tenant and project, when an ICM run is created, then its path is tenant/project/run scoped and no caller-controlled path segment can escape the root.
- Given the same create request and idempotency key, when repeated, then the same run is returned or an explicit idempotency conflict occurs; duplicate runs are not silently created.

### Stage structure

- Given a new run, when initialized, then all eleven canonical stages contain `CONTEXT.md`, `CONTRACT.json`, `CHECKLIST.md`, input/output manifests, evidence/log directories, and `handoff.json`.
- Given reinitialization, when stage files contain completed human/agent evidence, then the initializer does not overwrite them.

### Context compilation

- Given a stage contract and canonical refs, when context is compiled, then only declared stage refs and capabilities are included.
- Given identity, consent, rights, approved dialogue, shot intent, continuity, budget, or safety constraints, when context is compressed, then those constraints remain explicitly represented.
- Given a binary media asset, when context is compiled, then the package contains a reference and safe metadata/summary rather than copying the binary into active context.

### Digests and staleness

- Given a prepared stage, when an input ref/version/digest changes, then the stage or dependent output is marked stale before handoff.
- Given unchanged inputs, when verification is repeated, then digests and verification output are deterministic.

### Handoff and resume

- Given a verified stage, when a handoff is created, then it contains run/project/stage identity, input/output digests, action IDs, actor/client evidence, decision/approval/job/event/artifact refs, verification evidence, blockers, cost fields, and next-stage context.
- Given a valid handoff and no original chat transcript, when another compatible agent resumes, then it can discover allowed capabilities, resolve inputs, identify blockers/approvals, and continue safely.
- Given an invalid or stale handoff, when resume is requested, then execution fails closed or requires explicit human resolution.

### Migration

- Given a v1 workspace, when migration runs, then a v2 run is created without overwriting v1 evidence and all eleven stage names are preserved.
- Given migration is repeated, then it is idempotent.

## Cross-transport parity acceptance

The following matrix must be generated and contain no blank CLI/API/MCP cells for stable public actions:

| Action ID | CLI | API | MCP | Input schema | Output schema | Error map | ICM stage |
|---|---|---|---|---|---|---|---|

Required proof flows:

1. create project through API, list through CLI, get/validate through MCP;
2. get timeline through MCP, replace through CLI, reopen through API;
3. create ICM run through CLI, prepare through API, verify/handoff through MCP;
4. resolve the same handoff reference through all transports;
5. submit equivalent invalid, unauthorized, stale, and duplicate requests through all transports and compare problem documents.

## Security acceptance

- No secret values appear in registry snapshots, OpenAPI snapshots, MCP schemas, CLI output, ICM context, handoffs, logs, or CI artifacts.
- Remote authorization never trusts a caller-supplied tenant ID as authority.
- Tenant/project/run ownership is checked before resolving context or artifacts.
- Path traversal, absolute paths, symlink escape, malformed IDs, and cross-tenant refs fail closed.
- Stable errors do not disclose whether a project exists under another tenant.

## Documentation acceptance

- Repository documents identify YAPPY-CLIPZ as the canonical product and `pauli-montage-video-agent` as the canonical repository.
- Documents state that Phase 05 is merged and production is READY.
- Documents identify the public editor as YAPPY-owned/neutral and preserve Twick's private/reference licensing boundary.
- Documents use one canonical ICM hierarchy.
- `icm/README.md` no longer describes Phase 02 as future work.

## Release acceptance

- Strict OpenSpec passes.
- All current Phase 00-05 gates remain green.
- Registry/schema/parity/ICM migration/staleness/path-safety/snapshot tests pass.
- No unresolved valid review thread remains.
- Exact final PR head has READY Vercel preview.
- Phase 06 is squash merged.
- Merged `main` produces a READY production deployment.
- Production `/` and `/studio` remain 200.
- Protected project operations remain fail closed until Phase 07 hosted identity/API is explicitly enabled.
- Rollback to Phase 05 is documented and tested.
