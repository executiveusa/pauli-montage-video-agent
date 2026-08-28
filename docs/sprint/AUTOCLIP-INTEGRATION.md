# AutoClip capability harvest

## Source and boundary

- Upstream: `zhouxiaoka/autoclip`
- Audited revision: `17100c05536d875b0ee93ef5f096630635e94f97`
- License: MIT
- Integration rule: preserve Montage as the sole product, StudioProject as canonical state, and YAPPY-CLIPZ services as the ownership/job boundary. Do not import AutoClip's duplicate React/Vite frontend, SQLite domain model, Celery control plane, or Tauri release machinery.

AutoClip reports one real packaged end-to-end run for Bilibili download → subtitle → DashScope analysis → scoring → title → five clips. Its repository tests could not be executed in this workspace without installing its separate dependency graph, so no broader upstream production claim is made.

## Parity decision

| AutoClip capability | Montage evidence today | Decision | Sprint target |
|---|---|---|---|
| Local upload, FFmpeg cuts, captions, Whisper | Already implemented through canonical assets, Montage Local Engine, transcript evidence, reversible operations, and verified render output | Keep Montage implementation | Existing / Phases 5–7 |
| YouTube and generic URL download through `yt-dlp` | `tools/analysis/video_downloader.py` already detects providers and downloads video/audio/subtitles, but the Studio does not expose a canonical link-import journey | Wire existing Montage downloader into an authenticated, provenance-aware import job | Phase 11 |
| Bilibili URL validation, metadata, subtitle fallback, and download progress | No Bilibili-specific Studio adapter or user journey | Reimplement as a provider adapter behind the same canonical import contract; never store browser passwords | Phase 11 |
| Outline → topic ranges → clip scoring → title generation | Montage has transcript, scene/vision analysis, timeline operations, provider scoring, and prompt locking, but no single automatic highlight-plan application service | Add a deterministic `HighlightPlan` contract and a job-backed service that produces suggested timeline ranges before any edit is applied | Phases 7 and 9 |
| Ordered collections of clips | Montage has timelines and export versions but no first-class reusable clip collection | Model collections as ordered references to canonical timeline ranges/assets, with provenance and reversible reorder | Phases 7 and 12 |
| WebSocket progress topics | Montage already has durable tenant-scoped jobs/events, retry, cancellation, idempotency, approvals, and cost records; AutoClip's `user_id` query connection is weaker than Montage's auth boundary | Add authenticated event streaming over Montage's existing durable event log; polling remains fallback | Phases 9 and 12 |
| Desktop-local queue and offline packaging | Montage already has a stronger local-engine separation and web control plane; duplicating Tauri now would split the product | Park; reconsider only after the web/local golden path is commercially validated | PARKED |
| Bilibili upload/account management | Upstream marks portions incomplete and it expands credential/compliance risk | Do not import in this sprint | PARKED |
| AutoClip Ant Design/Vite UI | Conflicts with the Next.js Studio and current Phase 2 design system | Do not import | REJECTED |

## Integration acceptance

The harvest is complete only when later phase gates prove:

1. a URL import creates a canonical asset with source URL, provider, external ID, checksum, and rights fields;
2. unsupported/private/cookie-required sources fail without leaking credentials or leaving partial canonical state;
3. an automatic highlight plan references exact transcript/source time ranges and remains a suggestion until applied;
4. collections contain ordered canonical references and survive save/reload/reorder;
5. progress events are tenant-scoped, resumable after reconnect, and backed by the durable job log;
6. every imported idea has Montage-native tests and rollback evidence.

## Attribution

Any substantial copied implementation must retain AutoClip's MIT copyright notice. The current harvest uses architectural observations and does not copy upstream source bodies.
