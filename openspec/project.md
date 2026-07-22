# YAPPY-CLIPZ OpenSpec Project Context

YAPPY-CLIPZ is the canonical video-production product inside Yappyverse Studio.

## Engineering rules

- Read `AGENTS.md` and `AGENT_GUIDE.md` before implementation.
- One GRINIONS phase maps to one OpenSpec change and one final squash-merged PR.
- Reuse existing capabilities before introducing dependencies or duplicate services.
- CLI, API, MCP, and web surfaces must share application services rather than duplicate business logic.
- Protect owner sovereignty, tenant isolation, provider replaceability, rollback, and evidence.
- High-risk auth, payments, destructive migrations, secrets, identity/voice consent, and irreversible customer-data actions require explicit approval immediately before the consequential action.
- Generated media and project workspaces stay out of Git.
- Public claims must be backed by verified behavior.
