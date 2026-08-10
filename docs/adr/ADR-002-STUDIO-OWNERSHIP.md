# ADR-002: PopeBot is a control surface, Composio is a connector

- Status: accepted
- Date: 2026-08-09

## Decision

YAPPY-CLIPZ retains one `StudioProject` and one shared application-service layer. PopeBot contributes a Director conversation surface that emits typed previewable actions into those services. It does not introduce a second project model, SQLite authority, agent runtime, media transport, or GitHub delivery system.

Composio provides scoped authentication and source-toolkit access for Google Drive and OneDrive. Imported media is copied into owner-controlled canonical asset storage, fingerprinted, and represented by the existing Asset/StudioProject contracts. Composio is not the project database, job bus, asset store, approval authority, or provenance authority.

Large media moves through signed or resumable storage transfers. It never travels as a chat attachment or data URL.

## Consequences

- Web, voice, CLI, API, and MCP surfaces dispatch the same action IDs.
- Connector revocation prevents new source access but does not orphan already-owned assets.
- A source provider can be replaced without changing StudioProject or downstream editing contracts.
- Credential, scope, and destructive actions remain server-side and approval-gated.
