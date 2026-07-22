# YAPPY-CLIPZ Dependency Register

Phase 01 truth baseline. This register covers the approved consolidation sources. It is not permission to vendor or ship a dependency; each later integration phase must re-check the exact version, model/checkpoint terms, and commercial mode.

| Source | Role | Runtime mode | License truth | Commercial position | Decision | Removal / replacement path |
|---|---|---|---|---|---|---|
| `executiveusa/pauli-montage-video-agent` / OpenMontage | Production pipelines, skills, tools, provider registry, cost/checkpoints, Remotion/FFmpeg | Core/open source service | AGPLv3 | Network use of modified covered work carries AGPL source obligations | KEEP | Canonical production core; preserve open-core/source-compliance boundary. |
| `executiveusa/pauli-twick-video-editor` | React timeline/canvas/player/editor and MCP experiment | Browser/editor packages | Sustainable Use License 1.0 in repo | Hosted SaaS / substantial-revenue use requires commercial agreement; bundled app use is conditioned by license | OWNER-ONLY / COMMERCIAL-AGREEMENT-REQUIRED | Build YAPPY-owned editor contract; replace source implementation without changing StudioProject. |
| `HKUDS/ViMax` | Idea/script/novel planning, storyboard, multi-shot continuity, Web/TUI agent workflows | Isolated Python specialist service/worker | MIT | Commercial use permitted under MIT notices | ADAPT | Remove adapter; retain StudioProject story/canon artifacts. |
| `HKUDS/VideoAgent` | Intent decomposition, workflow graph, multimodal understanding/retrieval/edit/remake research stack | Optional isolated analysis service | Root LICENSE is MIT; project metadata has historically contained inconsistent license text | Use only after preserving MIT notice and resolving any third-party/model licenses | ADAPT SELECTIVELY | Replace individual analysis tools; do not couple default API to full dependency stack. |
| `Lightricks/LTX-2` | Local/rented-GPU synchronized audio-video generation | Dedicated GPU worker | LTX-2 Community License Agreement | SaaS/remote hosting allowed subject to agreement/use restrictions; ≥$10M annual revenue requires paid commercial license; attribution/acceptable-use requirements apply | ADAPT WITH POLICY | Swap worker/model through OmniRouter; StudioProject/job contract unchanged. |
| `ChrisRoyse/clipcannon` | Deep local analysis, EDL, captions/crop, voice, avatar, music, MCP tools | Owner/private GPU plugin | Business Source License 1.1 | Current license prohibits offering a competing commercial Video Production Service to third parties until change date/license or separate rights | OWNER-ONLY | Disable plugin in customer/SaaS mode; replace capabilities with permissive/direct implementations. |
| `executiveusa/Open-clipz` | Gemini/Veo/image/transcription UI prototype | Prototype only | No root LICENSE found; `package.json` is private Vite/React prototype | Do not assume redistribution/commercial rights | ARCHIVE / HARVEST PATTERNS ONLY | Recreate needed provider adapters/UX under canonical licensed code; archive repo after parity. |
| `SamurAIGPT/AI-Youtube-Shorts-Generator` | Highlight scoring, long-video chunking, dedupe, crop, CLI | Benchmark/reference | README claims MIT/white-label; no root LICENSE file found during audit | Treat source as license-unclear until repository license artifact is resolved | HARVEST CONCEPTS / REJECT RUNTIME | Reimplement/test algorithms inside OpenMontage Clip Factory; no runtime dependency. |
| Sovereign Video Agent artifact | Pexo-style brief→storyboard→routing→generation→FFmpeg→verify skill | Skill/reference artifact | Self-authored MIT skill; inspired by MIT Pexo public skills | Commercially usable subject to included notices and provider terms | HARVEST / EXTEND OPENMONTAGE | Fold behavior into canonical meta skill; no second backend. |
| `Lightricks/LTX-Video` (older line) | Previous LTX generation runtime | Superseded | Historical code license differs from current LTX-2 terms | Do not design new integration against superseded runtime | ARCHIVE/REJECT NEW WORK | Use current official LTX-2 worker adapter. |

## Dependency admission gate

A new runtime dependency must document:

- capability replaced or gap filled;
- exact version/commit/model checkpoint;
- code license and model/checkpoint license separately;
- customer/SaaS/private eligibility;
- secrets/network/GPU requirements;
- data leaving owner-controlled infrastructure;
- expected cost/latency;
- fallback;
- removal path;
- tenant/data-isolation impact.

## Default service boundary

External specialist repos are adapted as services/packages behind YAPPY contracts. They do not receive authority over authentication, billing, tenant ownership, project truth, or global provider routing.
