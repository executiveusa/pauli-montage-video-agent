# Acceptance: Phase 1 product contract and architecture

- A clean npm install succeeds from the committed lockfile and resolves Next.js 16.3.3.
- The Studio dependency set supports an ambient SOCKS proxy without import-time failure.
- Every active OpenSpec change validates strictly with telemetry disabled.
- StudioProject schemas validate and round-trip through existing contract tests.
- Shared StudioService CLI/API/MCP, tenant isolation, assets, operations, generation, and rendering tests pass.
- The studio TypeScript check and production build pass.
- Baseline and phase documents identify the exact starting SHA, inherited failures, scope, and rollback.
- No secrets, external provider execution, production data, deployment, or upgrade-roadmap mutation occurs.
