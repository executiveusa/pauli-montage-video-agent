# YAPPY-CLIPZ Source Migration Map

Phase 01 decisions. These are architectural integration classifications, not commands to copy repositories wholesale.

## `executiveusa/pauli-montage-video-agent` — KEEP / EXTEND

### Keep

- pipeline manifests;
- director/meta skills;
- tool registry and capability discovery;
- checkpoint/cost/approval/review patterns;
- real-footage retrieval;
- Remotion and FFmpeg composition;
- existing production tools that pass license/provider policy.

### Extend

- neutral `StudioProject` projection layer;
- application service facade;
- OmniRouter policy/route evidence;
- anime/character/avatar/documentary packs;
- versioned product APIs.

### Do not

Do not fork orchestration into another backend.

---

## `executiveusa/pauli-twick-video-editor` — OWNER-ONLY / HARVEST / COMMERCIAL AGREEMENT REQUIRED

### Useful pieces

- timeline interaction patterns;
- synchronized player/canvas behaviors;
- caption/effects/media UX;
- editor package boundaries;
- MCP interaction experiments.

### Commercial boundary

The actual repository license restricts hosted SaaS/video-editing backend use without a separate commercial agreement.

### Migration

1. Define a YAPPY-owned Studio Editor interface and neutral Timeline contract.
2. Use Twick privately/reference-only while building the public studio.
3. Independently implement or adopt commercially clean components behind the contract.
4. If commercial rights are obtained later, Twick can be enabled as one implementation without changing StudioProject.

Decision: `OWNER-ONLY` now; `ADAPT` only after rights; `HARVEST` architecture/UX ideas where legally safe.

---

## `HKUDS/ViMax` — ADAPT

### Use

- idea/script/novel planning;
- story/scene/shot decomposition;
- storyboard generation;
- multi-shot continuity concepts;
- character/cameo/reference workflows;
- parallel generation planning.

### Reject

- duplicate Web UI as customer product;
- duplicate project/session source of truth;
- independent provider ownership when OmniRouter already selected a route.

### Adapter contract

`StudioProject canon/script/requirements → ViMax specialist → storyboard/scenes/shots/continuity artifacts → StudioProject`

Decision: `ADAPT` as isolated planning/continuity specialist.

---

## `HKUDS/VideoAgent` — ADAPT SELECTIVELY / HARVEST

### Use selectively

- intent decomposition;
- multimodal video understanding;
- semantic retrieval;
- workflow-proposal ideas;
- remake/edit analysis;
- self-evaluation patterns.

### Avoid

- default installation of the full large research ML dependency stack;
- second global orchestrator;
- second public project/workflow graph as product truth.

### Migration

Extract a capability inventory first, then implement only bounded adapters whose value exceeds their dependency/runtime cost.

Decision: `ADAPT SELECTIVELY`, otherwise `HARVEST` patterns.

---

## `Lightricks/LTX-2` — ADAPT WITH LICENSE POLICY

### Use

- local/rented-GPU synchronized audio/video generation;
- image/video conditioned generation supported by the current model line;
- open-weight sovereign execution path.

### Boundary

Dedicated worker container/service. No model package in Vercel/frontend. License eligibility evaluated per organization/deployment.

Decision: `ADAPT` behind OmniRouter with `commercial_eligibility` policy.

---

## `Lightricks/LTX-Video` — ARCHIVE / REJECT NEW INTEGRATION

Superseded by the current LTX-2 line for new development.

Decision: `ARCHIVE` as historical reference; `REJECT` new product integration.

---

## `ChrisRoyse/clipcannon` — OWNER-ONLY

### Useful owner capabilities

- deep local footage analysis;
- semantic/vector search;
- EDL editing;
- smart crop/captions/platform profiles;
- local voice/avatar/audio stack;
- MCP operations.

### Boundary

Current BSL use limitation prevents use as a competing third-party commercial Video Production Service until applicable change license/date or separate rights.

Decision: `OWNER-ONLY` plugin, feature-flagged off in customer SaaS. Reimplement/replace any commercially needed capability through eligible components.

---

## `executiveusa/Open-clipz` — HARVEST / ARCHIVE

### Useful patterns

- Gemini API interaction examples;
- Veo text/image-to-video experiment flow;
- image analysis/edit/transcription/TTS UI experiments.

### Problems

- prototype architecture;
- browser-oriented provider calls;
- no root license found;
- duplicates the real studio surface.

Decision: `HARVEST` behavioral/provider patterns through independent implementation, then `ARCHIVE` repository after parity.

---

## `SamurAIGPT/AI-Youtube-Shorts-Generator` — HARVEST CONCEPTS / REJECT RUNTIME

### Useful concepts

- transcript content-type/density classification;
- long-video chunking with overlap;
- hook/emotional/opinion/revelation/conflict/quote/story/value virality signals;
- score-based highlight dedupe;
- vertical crop pipeline.

### Problems

- duplicates OpenMontage Clip Factory;
- root LICENSE file not found despite README MIT claim.

Decision: independently implement/test equivalent scoring inside canonical Clip Factory; `REJECT` runtime/source vendoring until license artifact is resolved.

---

## Sovereign Video Agent artifact — EXTEND OPENMONTAGE / ARCHIVE AS STANDALONE

### Keep behavior

- simple brief normalization;
- storyboard before spend;
- direct provider selection;
- explicit cost approval;
- smallest-shot regeneration;
- FFmpeg local post;
- machine-readable output verification;
- owner-controlled provider credentials/artifacts.

### Migration

Convert into an OpenMontage meta/director skill plus provider-routing/verification tests. Do not maintain a second project manifest/runtime once StudioProject exists.

Decision: `EXTEND` OpenMontage; `ARCHIVE` standalone backend concept after behavior is absorbed.

---

# Migration order

1. Phase 02: define StudioProject/Element/Asset/Job/Timeline contracts before adapters.
2. Phase 03: shared application services and CLI/API/MCP.
3. Phase 04: build commercially clean web studio shell.
4. Phase 05: prove neutral editor round trip; Twick may be used privately as reference, not assumed public SaaS dependency.
5. Phase 07: OmniRouter becomes the single provider/capability routing layer.
6. Phase 08+: add generation adapters.
7. Phase 09: ViMax adapter and canon/continuity system.
8. Phase 10: selective VideoAgent/documentary adapters and canonical Clip Factory improvements.
9. Phase 11: commercially eligible avatar/voice/lipsync path; ClipCannon remains owner-only unless rights change.
10. Archive superseded experiments only after equivalent canonical capability and rollback evidence exist.
