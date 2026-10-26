# Synthia model integration for Montage

The chat-first Montage Director uses deterministic local timeline tools for trim/split/title/export. Unrecognized creative requests can be answered by an authenticated language model through the existing [executiveusa/synthia-gateway](https://github.com/executiveusa/synthia-gateway).

## Secure environment configuration

Add these **server-side** variables to the Vercel project:
- `SYNTHIA_GATEWAY_URL`: HTTPS base URL of a deployed instance of `synthia-gateway`; do not include `/v1`.
- `SYNTHIA_GATEWAY_API_KEY`: a high-entropy shared gateway key. Configure the same value as `GATEWAY_API_KEY` on Synthia.
- `MONTAGE_OWNER_EMAIL`, `MONTAGE_OWNER_PASSWORD_HASH`, `MONTAGE_SESSION_SECRET`: use the existing Montage owner login. AI API routes reject unauthenticated sessions.

On Synthia, set `GATEWAY_API_KEY`, and one or more provider keys (e.g. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Never use a ChatGPT or Claude web session token, password, or cookies as the API key. Neither ordinary ChatGPT Plus nor Claude Pro includes arbitrary third-party API usage. Use official provider API credentials and applicable billing. Synthia's existing Express JS gateway routes `POST /v1/chat/completions` and translates Anthropic message format.

The Director never submits the actual footage to AI; only filename, duration, number of clips, project title and user's typed message. Links in the prompt are treated as references, not automatically downloaded or ingested. The model can *propose* motion plans; it cannot yet perform arbitrary motions or import an external reference asset. The UI honestly preserves this boundary. The model chooser disables itself unless the server indicates configuration. This integration does not create or pay for provider accounts.

## Future tasks

Provider-specific model IDs should be checked against current provider catalogs before release. Consider adding a server-side model capability probe rather than a static picker. For production, require strict owner authentication and rate-limiting, enforce request quotas and monthly budgets, add explicit user approval for actions that spend credits, and translate structured model output into validated timeline commands only after preview and confirmation.
