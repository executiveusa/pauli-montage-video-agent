# YAPPY-CLIPZ Prompt Locker

The Prompt Locker is the versioned, provider-neutral source of reusable production prompts and workflows.

## Laws

- Prompts are checked-in JSON contracts with stable IDs and versions.
- Workflows compile prompts and exact candidate provider payloads; compilation never submits paid work.
- Every paid step declares `requiresApproval: true` and must pass through the universal action dispatcher.
- Template values are explicit. Unknown or missing variables fail closed.
- Media references remain typed lists rather than being flattened into prompt text.
- Prompt source/provenance is retained.
- Real-person identity references require authorization and consent.
- The full compiled prompt and payload are reviewable before execution.

## Structure

```text
prompt_locker/
  prompts/<family>/*.json
  workflows/<family>/*.json
```

## Stable actions

```text
prompt.list
prompt.get
prompt.compile
workflow.list
workflow.get
workflow.compile
```

All actions are available through CLI, REST, and MCP via the shared dispatcher.

## Initial Seedance library

Prompts:

- `seedance.ugc.podcast-authority`
- `seedance.ugc.creator-review`
- `seedance.ugc.lifestyle-demo`
- `seedance.ugc.greenscreen-hook`
- `seedance.cinematic.multi-shot`
- `seedance.character.reference-scene`

Workflows:

- `seedance.ugc.ab-test`
- `seedance.character.consistency`
- `seedance.product.launch`

The uploaded Seedance references were treated as user-supplied research. YAPPY uses original rewritten contracts and does not import the supplied client implementation.

## Timing compiler

For durations from four to fifteen seconds, the compiler derives:

```text
00:00–00:01              silent opening
00:01–00:(duration - 2)  dialogue/action window
00:(duration - 2)–end    silent closing
```

It also exposes a conservative dialogue word budget for downstream validation.

## Example

```bash
yappy-clipz action run workflow.compile --input compile.json
```

```json
{
  "workflowId": "seedance.ugc.ab-test",
  "variables": {
    "dialogue": "A short approved line.",
    "setting": "a working edit studio",
    "wardrobe": "a charcoal overshirt",
    "tone": "calm and specific",
    "duration": 8,
    "image_urls": ["https://signed.example/product.jpg"],
    "audio_urls": []
  }
}
```

The result contains complete prompt text and candidate payloads. It does not contact fal or another provider.
