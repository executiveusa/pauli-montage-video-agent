# PopeBot + Composio parity map

This map assigns each desired behavior to one canonical YAPPY owner. “Parity” means the behavior is covered through that owner; it does not authorize a second runtime or byte-for-byte copying.

| Desired behavior | Reference source | Canonical YAPPY owner | Delivery slice | Forbidden duplicate |
|---|---|---|---:|---|
| Director chat, streaming, suggestions, tool cards | PopeBot | Studio web Director surface + shared dispatcher | 3 | PopeBot backend/project database |
| Voice command preview, approval, undo | PopeBot patterns | Typed action request/result + StudioService | 2–3 | Voice-only business logic |
| Google Drive connection and browsing | Composio | SourceConnector adapter | 5 | Composio-owned project/media state |
| OneDrive connection and browsing | Composio | SourceConnector adapter | 6 | Provider-specific project schema |
| Durable owned media | Connector import outcome | Asset registry + approved object storage | 4–6 | Chat/data-URL media transport |
| Transcript, elements, candidates, edits | Existing product plans and references | Versioned StudioProject canonical contract used by every interface and engine | 2 | Adapter-native timeline state or exposed internal engine schemas |
| Documentary assembly | OpenMontage/VideoAgent concepts | Documentary service + canonical timeline | 7 | Second clip project/runtime |
| Candidate discovery | Local analysis and OpusClip | Candidate adapter contract | 8–9 | OpusClip as editor/source of truth |
| Paid generation | Kie, Fal, local routes | OmniRouter + jobs/approvals/costs | 10 | Direct UI provider calls |
| Story, UGC, and character continuity | Visual reference sources | Workflow packs + canon/continuity contracts | 11–12 | Parallel phase/pipeline engine |
| Operational visibility | uigen patterns | Schema-driven shared operations panels | 13 | Hand-coded provider dashboards |
| Release and completion | GRINIONS, Ralphy, Gauntlet | GitHub + GRINIONS evidence chain | 0–14 | Ralphy progress or critic verdict alone |

## Approval result

The map is accepted by ADR-002 and ADR-003. Any implementation that assigns durable state or business authority to a forbidden duplicate requires a superseding ADR and OpenSpec change before code is written.
