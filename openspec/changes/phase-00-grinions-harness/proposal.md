# Change: Phase 00 GRINIONS durable control plane

## Why

YAPPY-CLIPZ is a multi-phase brownfield consolidation project. Long autonomous execution must survive worker failure, preserve approvals and evidence, avoid duplicate external side effects, and prevent implementation agents from bypassing release gates.

## What changes

- Add a dedicated `ops/grinions/` control-plane package using Absurd as a Postgres-backed durable execution adapter.
- Add checkpointed phase execution for context hydration, specification validation, baseline/rollback capture, bounded Bead execution, verification, PR watching, judging, squash merge, post-merge verification, and attestation.
- Add a Ralphy adapter that always uses isolated task branches and disables Ralphy merge authority.
- Add OpenSpec project/change scaffolding and a reproducible Beads/Absurd/Ralphy bootstrap contract.
- Add deterministic tests for checkpoint replay and simulated restart behavior.
- Add a real Absurd/Postgres integration test in CI.

## Non-goals

- No YAPPY-CLIPZ customer runtime feature.
- No video provider/model integration.
- No SaaS auth, billing, or tenant data.
- No autonomous high-risk merges.
- No dependency on Absurd APIs outside the GRINIONS adapter boundary.

## Impact

This is build/release infrastructure only. It adds an optional control-plane package and CI workflow without changing existing OpenMontage production behavior.

## Risk

Medium. The harness can create PRs and perform merges when explicitly run with authenticated CLIs, so merge authority remains gated and high-risk phases stop before merge.
