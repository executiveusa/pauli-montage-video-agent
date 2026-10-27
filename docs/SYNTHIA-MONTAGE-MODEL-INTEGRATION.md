# Montage Director: model suggestions, chat gateway, and production adapters

## Current implementation and boundaries

The chat-first Montage Director still executes **deterministic local** operations: import, trim, split, add titles and export browser review previews. Selecting a model does not make its weights available, download footage, generate new video, upload assets, or automatically change the timeline.

The model dropdown now defaults to **JoyAI Video Edit** and includes **LTX-2.5** alongside related model suggestions. All video/3D models are explicitly **integration required**. The Synthia gateway at `executiveusa/synthia-gateway` currently exposes *chat-completions*, not JoyAI/LTX video-inference or 3D workflows. These choices do not call Synthia and cannot incur inference charges until a separate reviewed worker/inference adapter is implemented.

| ID | Capability | Status |
| --- | --- | --- |
| `jdopensource/JoyAI-Video-Edit` | Video-to-video instruction-guided editing | Default suggestion; adapter not connected |
| `Lightricks/LTX-2.5` | Synchronized audio/video generation and multi-shot sequences | Suggestion; adapter not connected |
| `Wan-AI/Wan2.2-Animate-2-14B` | Character animation | Suggestion; adapter not connected |
| `microsoft/TRELLIS.2-4B` | Image-to-3D assets | Suggestion; adapter not connected |
| `ccore/Qwen3.5-4B-3D-Coder` | Three.js scene code | Suggestion; adapter not connected |
| `Qwen/Qwen3.8-Flash-Next` | Multimodal reasoning | Suggestion; Synthia provider/model alias not configured |
| `Qwen/Qwen3.8-27B` | General reasoning and coding | Suggestion; Synthia provider/model alias not configured |
| `gpt-4.1-mini`, `gpt-4.1`, `claude-sonnet-4-5`, `claude-haiku-4-5` | Creative chat via Synthia | Gateway may be configured, but upstream entitlement has not been verified |

Model references: [JoyAI](https://huggingface.co/jdopensource/JoyAI-Video-Edit), [LTX](https://huggingface.co/Lightricks/LTX-2.5), [Wan](https://huggingface.co/Wan-AI/Wan2.2-Animate-2-14B), [TRELLIS.2](https://huggingface.co/microsoft/TRELLIS.2-4B), [Qwen Flash](https://huggingface.co/Qwen/Qwen3.8-Flash-Next).

LTX-2.5 has community commercial licensing conditions, including a revenue threshold. Validate eligibility and `LICENSE` before any paid deployment. JoyAI lists Apache 2.0. Model weights, GPU infrastructure, provider accounts and media ingestion are **not** installed by this change.

## Secure chat setup (optional, not automatically activated)

Configure **server-side** environment variables:
- `SYNTHIA_GATEWAY_URL`: HTTPS base of your Synthia gateway, without `/v1`.
- `SYNTHIA_GATEWAY_API_KEY`: a shared gateway credential, matching Synthia's `GATEWAY_API_KEY`.
- `MONTAGE_OWNER_EMAIL`, `MONTAGE_OWNER_PASSWORD_HASH`, `MONTAGE_SESSION_SECRET`: existing Montage owner authentication; avoid a plaintext owner password.

The Synthia gateway must be independently deployed and have provider keys such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. Do not use browser cookies or subscription credentials in place of official provider APIs. Credentials are never sent to the browser.

When a connected chat model is selected, the UI requests a **non-billable cost preview** from Montage's `POST /api/director`, displays an estimated upper cost, and asks for explicit user approval. The server issues a signed five-minute quote tied to the specific prompt, bounded conversation history, selected model, and cost estimate. Only an authenticated call with a matching approved quote is forwarded to Synthia. The estimate uses public list prices plus a conservative UTF-8 budget and is **not a provider billing guarantee**.

History is capped at eight turns, 1,200 characters per turn, with 5,000 characters for the latest message and 650 output tokens. Model creative questions now work without uploaded footage if a chat provider is configured. Source footage stays local; the endpoint sends only the written prompt, bounded chat history and basic project metadata. Links are untrusted references and are **never automatically fetched**.

## Next integration slice

Implement **one** bounded JoyAI video-to-video worker first: uploaded asset handling with opt-in media transfer; provider-side license and GPU proof; signed job IDs; pre-render visual cost quote and explicit approval; durable queue/status/retries; safe output storage; preview-only results; and rollback. Follow with a separate LTX-2.5 audio/video generation adapter. The generic Synthia chat-completions endpoint is *not* a valid substitute for those jobs.

Do not label JoyAI or LTX as active until a full authenticated upload → inference → preview → acceptance test succeeds on a real project. Existing deterministic editor must remain functional if model services are absent.

## Production acceptance

- Run build and typecheck for `apps/studio-web` and the existing CI.
- Verify the JoyAI default and the LTX option appear, both marked `setup required`.
- Verify an unconfigured model sends no paid call; local trim/split/title/export still work.
- Verify a creative prompt with no uploaded footage reaches the configured chat provider only after cost approval.
- Verify changed prompt/history/model cannot replay a different signed quote, and an expired quote is rejected.
- Confirm video/3D dropdown entries cannot be mistaken for chat-completions models.
- Inspect Vercel deployment separately: a merge is not proof of production rollout.
