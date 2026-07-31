# fal.ai provider boundary

YAPPY-CLIPZ integrates fal through a server-side queue adapter, not through browser code and not through provider-specific business logic.

## Security defaults

- `FAL_KEY` remains server-side.
- Provider execution is disabled unless `YAPPY_ENABLE_PAID_PROVIDERS=1` is set server-side.
- Every submission requires an explicit approval flag and idempotency key.
- Request plans redact credentials.
- Provider and model IDs are allowlisted by `providers/fal/manifest.json`.
- Unknown fields, local/private URLs, excessive references, invalid durations, and unsupported enum values fail before any request.
- `X-Fal-Store-IO` defaults to `0`; it can be changed only by server configuration.
- Webhooks must be public HTTPS URLs without embedded credentials.

## Environment

```text
FAL_KEY=<server-only secret>
YAPPY_ENABLE_PAID_PROVIDERS=0
YAPPY_FAL_STORE_IO=0
YAPPY_FAL_QUEUE_BASE_URL=https://queue.fal.run
YAPPY_FAL_TIMEOUT_SECONDS=30
```

No key value is returned by health, discovery, provider descriptions, errors, or plans.

## Stable actions

```text
provider.list
provider.get
provider.request.plan
provider.request.submit
provider.request.status
provider.request.result
provider.request.cancel
```

`provider.request.plan` is safe and does not require a key. It validates the payload and returns an estimated cost with source and verification date.

`provider.request.submit` is experimental and paid. It returns a provider queue receipt. YAPPY's later durable job layer remains responsible for canonical idempotency, retries, events, budgets, artifact ingestion, and reconciliation.

## Initial allowlisted Seedance endpoints

- standard and fast text-to-video;
- standard and fast image-to-video;
- standard and fast reference-to-video.

The manifest is data, not application code. Additional fal models can be added after schema, cost, policy, and output-normalization review.

## Media handling

The Phase 06 adapter accepts only public HTTPS media URLs. Production uploads will be added through the Asset Registry and short-lived signed object-storage URLs. Provider output URLs must later be ingested into YAPPY-owned storage before they are treated as durable project assets.
