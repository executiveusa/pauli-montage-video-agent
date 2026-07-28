# Phase 06 implementation amendment

The implementation file allowlist is extended to include:

```text
.github/workflows/phase06-interoperability-gates.yml
```

## Reason

The existing GRINIONS workflow runs when application source changes, but Prompt Locker definitions, provider manifests, and capability snapshots are durable public contracts that can change independently. A dedicated workflow is required so prompt-only or provider-manifest pull requests cannot bypass schema, snapshot, offline adapter, paid-execution-default, and full Studio compatibility tests.

## Constraints

- no secrets are added to CI;
- `YAPPY_ENABLE_PAID_PROVIDERS=0` is enforced;
- tests use a fake HTTP client and make no paid or external provider calls;
- the workflow does not deploy or modify production.
