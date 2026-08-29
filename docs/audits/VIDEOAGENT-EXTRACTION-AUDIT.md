# VideoAgent extraction audit

Source donor: `executiveusa/MAXX-Video-Agent` (fork of HKUDS/VideoAgent)
Target product: `executiveusa/pauli-montage-video-agent`

## Decision

VideoAgent remains a donor/reference repository, not a production runtime. Montage keeps canonical project/timeline truth and Hermes remains the operator. Capabilities are ported only when they improve documentary retrieval, finishing, or creator usability without introducing a second orchestration/state system.

## Capability map

| VideoAgent capability | Evidence in donor | Montage disposition | Reason |
| --- | --- | --- | --- |
| Intent decomposition | README System Overview | ADAPT | High leverage for natural-language editing requests. Implement as deterministic storyboard query planning before optional LLM refinement. |
| Graph workflow planning | README Autonomous Tool Use & Planning; `environment/agents/multi.py` | ADAPT, NOT COPY | Hermes/Montage already own orchestration. Keep capability graph concepts, reject a second agent runtime. |
| Two-step self-evaluation / reflection | README evaluation + planning description | ADAPT | Useful as a bounded plan-review pass, but builders cannot approve themselves. Human/gauntlet remains final authority. |
| Storyboard Agent / fine-grained visual subqueries | README Multi-Modal Understanding | PORT | Core missing retrieval feature. Added `storyboard_query_planner` to turn broad requests into visual/editorial search clauses. |
| Pre-captioned video-bank retrieval | README Storyboard Agent | PORT THROUGH MONTAGE INDEX | Use `documentary_index` manifests + visual observations as the bank. No separate VideoAgent DB. |
| ImageBind cross-modal retrieval | `tools/ImageBind` | ADAPTER LATER | Useful for text/image/audio embeddings, but heavy dependency. Add behind retrieval interface only when benchmark proves value over current VLM/embedding path. |
| VideoRAG | `tools/videorag` | ADAPTER LATER | Valuable for large archive semantic retrieval; should consume Montage manifests and timestamps, not own source truth. |
| Video Q&A / summarization | README Key Features | ALREADY COVERED | Montage has `video_understand`, visual QA, scene detection, frame sampling, transcripts and documentary index. |
| Scene/temporal understanding without transcript | README multimodal retrieval goal | ALREADY COVERED + UPGRADE | `documentary_index` is transcript-optional and samples scene-guided frames. Storyboard planning now makes it queryable at intent level. |
| Movie/clip editing | README | ALREADY COVERED | Montage timeline + FFmpeg/Remotion are canonical. |
| Video overview generation | README | ADAPT | Build from documentary manifest + storyboard planner + canonical timeline, not donor workflow runtime. |
| Beat-synced edits | README feature table | KEEP AS FUTURE FINISHING CAPABILITY | Useful for social/music workflows; not documentary-core. Must write canonical timeline operations. |
| Sound-effects tools | README feature table | KEEP AS FUTURE FINISHING CAPABILITY | Useful, but lower priority than archive understanding/search. |
| Audio extraction | `environment/roles/audio_extractor.py` | ALREADY COVERED/FFMPEG | No reason to copy wrapper. |
| Loudness normalization | `environment/roles/loudness_normalizer.py` | PORT AS FINISHING TOOL IF MISSING | Production-value feature; deterministic FFmpeg implementation is preferable. |
| Audio mixing | `environment/roles/mixer.py` | ALREADY/ADAPT | Keep within canonical render graph. |
| Resampling | `environment/roles/resampler.py` | ALREADY/FFMPEG | Commodity operation; do not duplicate wrapper. |
| Source separation | `environment/roles/separator.py` | ADAPTER LATER | Useful for dialogue/music cleanup; model/dependency heavy. Keep optional. |
| Transcription | `environment/roles/transcriber.py` | ALREADY COVERED | Montage local Faster-Whisper path already exists. |
| Voice generation / TTS | `environment/roles/tts`, `tools/CosyVoice`, `tools/fish-speech` | ADAPTER LATER | Provider capability only; do not vendor large runtimes. |
| Voice conversion | `tools/seed-vc`, role SVC modules | REJECT FROM CORE | High complexity and not needed for documentary search/editing core. Optional future provider. |
| Singing / DiffSinger | `tools/DiffSinger` | REJECT | Outside MONTAGE core product. |
| Cross-talk / stand-up adaptation demos | `environment/roles/cross_talk`, `stand_up` | REJECT AS PRODUCT CORE | Demo-specific content transformations, not core editor primitives. Reuse only generic timing/audio techniques if needed. |
| Meme/music/cross-cultural remake workflows | README demos/features | PARK | Potential templates after core product is production-grade. |

## What the upgraded patch adds now

1. A deterministic Storyboard Query Planner inspired by VideoAgent's intent decomposition and storyboard agent.
2. Explicit separation between visual subjects, environments, actions, camera/motion, editorial function, chronology, exclusions, and requested duration.
3. Retrieval-ready subqueries suitable for silent footage, B-roll, timelapse, interviews, and mixed archives.
4. No new database, no new agent runtime, and no duplicate timeline state.

## Next donor adapters, in order

1. Retrieval scorer over `documentary_index` manifests and visual captions.
2. Optional ImageBind/embedding adapter benchmarked against the existing visual stack.
3. Optional VideoRAG adapter for very large archives.
4. Deterministic loudness normalization if not already exposed through Montage finishing tools.
5. Beat-sync/SFX as timeline-native finishing operations.

## Explicit rejects

- Do not copy `environment/agents/multi.py` as a second orchestrator.
- Do not make VideoAgent state authoritative.
- Do not vendor CosyVoice, fish-speech, seed-vc, DiffSinger, or other large model repos into Montage core.
- Do not create a second cut-list/timeline schema.
- Do not let self-reflection replace acceptance tests or human approval.

## Retirement condition for MAXX-Video-Agent

The donor can be parked as reference-only when every row above is either implemented, attached as an optional adapter, or explicitly rejected with rationale and Montage's retrieval scorer passes the documentary gauntlet on silent, spoken, timelapse, and mixed B-roll footage.