# YAPPY-CLIPZ Capability Matrix

Status: Phase 01 repository-truth baseline.

Rule: every durable capability has exactly one canonical owner. Source repositories may contribute adapters, algorithms, tests, or specialist engines, but they do not become competing owners of project state or orchestration.

| Capability | Canonical owner | Source(s) considered | Decision | Boundary |
|---|---|---|---|---|
| Product/project source of truth | `StudioProject v1` in YAPPY-CLIPZ | OpenMontage artifacts, Twick timeline state, ViMax sessions | EXTEND/BUILD | External engine formats translate through StudioProject; none becomes the public schema. |
| Production orchestration | OpenMontage core | ViMax agent runtime, VideoAgent workflow graph, Sovereign Video Agent | KEEP | One production control plane only. Specialists return typed artifacts/capabilities. |
| Pipeline manifests and director skills | OpenMontage | Sovereign Video Agent, ViMax workflows | KEEP/EXTEND | Add skills/pipelines; do not create another orchestrator service. |
| Research and reference-video planning | OpenMontage | VideoAgent understanding | KEEP/EXTEND | VideoAgent may provide analysis tools but not own project planning. |
| Checkpoints, cost estimates, approvals, production QA | OpenMontage | Sovereign Video Agent | KEEP/EXTEND | Product-production governance stays in OpenMontage. GRINIONS is separate build/release governance. |
| Build/release orchestration | GRINIONS control plane | Absurd, Ralphy, OpenSpec, Beads | KEEP | Never make this a customer runtime dependency. |
| Provider/model capability registry | OpenMontage tool registry → OmniRouter | Sovereign routing, provider SDKs | EXTEND | One typed routing layer; provider-specific adapters remain replaceable. |
| Image generation/editing | OmniRouter + YAPPY provider adapters | Open-clipz Gemini patterns, Fal/direct APIs | EXTEND/HARVEST | No browser-side secret/provider ownership. |
| Cloud video generation | OmniRouter + provider adapters | Kling, Seedance, Veo and other providers | EXTEND | Same job/project contract regardless of provider. |
| Local/rented-GPU video generation | LTX-2 worker adapter | Lightricks/LTX-2 | ADAPT | Separate GPU worker; license policy enforced by deployment/customer mode. |
| Story/script/novel to storyboard planning | ViMax specialist adapter | HKUDS/ViMax | ADAPT | Use planning/continuity capabilities; do not adopt ViMax Web UI or project store. |
| Multi-shot character/world continuity planning | ViMax specialist adapter + YAPPY Element/Canon system | HKUDS/ViMax | ADAPT/EXTEND | StudioProject/Element Registry remains source of truth. |
| Multimodal video understanding | YAPPY analysis service with selective VideoAgent adapter | HKUDS/VideoAgent, OpenMontage tools | ADAPT/EXTEND | Import only bounded capabilities; avoid default installation of the entire research stack. |
| Semantic retrieval/remake analysis | YAPPY analysis service | HKUDS/VideoAgent | ADAPT | Output typed analysis/retrieval artifacts. |
| Professional browser timeline/editor | YAPPY-owned Studio Editor contract | pauli-twick-video-editor | BUILD/HARVEST | Twick code requires commercial agreement for hosted SaaS; no mandatory SaaS dependency without rights. |
| Internal/private visual editor | Twick fork | pauli-twick-video-editor | OWNER-ONLY pending rights | Useful for owner/internal workflows and as behavioral reference. |
| Deterministic composition | OpenMontage Remotion + FFmpeg | Twick renderer, ClipCannon renderer | KEEP | Twick timeline projects into canonical render plan; renderer remains replaceable. |
| Deep local footage analysis / EDL | ClipCannon plugin | ChrisRoyse/clipcannon | OWNER-ONLY | BSL prohibits competing commercial Video Production Service until license change/rights. |
| Clip/highlight factory | OpenMontage Clip Factory | AI YouTube Shorts Generator, ClipCannon | EXTEND | Keep one clipping pipeline; use external virality criteria as benchmark only until licensing is verified. |
| Virality ranking | OpenMontage scoring module | AI YouTube Shorts Generator | HARVEST CONCEPTS | Reimplement/test concepts; do not vendor source without a verifiable license file. |
| Gemini/Veo experiment UI | None | executiveusa/Open-clipz | ARCHIVE | Harvest provider/UX patterns only after provenance review; no separate product runtime. |
| Simple Pexo-style “make a video” director | OpenMontage meta skill | Sovereign Video Agent artifact | EXTEND/HARVEST | Fold brief→storyboard→estimate→generate→assemble→verify behavior into canonical skill/pipeline. |
| Voice synthesis | YAPPY Voice service + provider/local adapters | OpenMontage tools, future permissive sources, ClipCannon owner-only | EXTEND | Permission/consent records and provider replaceability required. |
| Lip sync/avatar performance | YAPPY Avatar service | OpenMontage tools, future permissive models, ClipCannon owner-only | EXTEND | ClipCannon cannot be mandatory commercial path; consent and quality gates required. |
| Asset storage/provenance | YAPPY application services + object storage | all sources | BUILD | Stable asset IDs, tenant isolation, provenance, source rights. |
| CLI/API/MCP surfaces | YAPPY application service layer | OpenMontage CLI-style tools, Twick MCP experiment | BUILD | All interfaces call the same services; no duplicated business logic. |
| Web studio/landing page | `apps/studio-web` | Twick UX reference, Open-clipz prototype | BUILD | Commercially clean YAPPY-owned frontend. |
| Infinite planning canvas | Infinote Canvas | future canvas libraries/reference systems | BUILD | Nodes map directly to StudioProject; no decorative second state store. |

## Architectural invariants

1. `StudioProject` owns durable product/project truth.
2. OpenMontage owns production orchestration.
3. GRINIONS owns build/release orchestration only.
4. No external UI/runtime may become a mandatory commercial dependency unless its license explicitly permits the intended SaaS use.
5. A specialist engine can be removed without invalidating StudioProject, CLI, API, MCP, or the web product.
