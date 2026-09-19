# Higgsfield Pay-Per-Use Fan-Out

> How to generate video with minimum spend per accepted take: one prompt fanned
> out to Seedance, Kling, and MiniMax; the cheapest passing take wins; every run
> writes a cost receipt.

## Tool

`higgsfield_payperuse` (`tools/video/higgsfield_payperuse.py`)

## How it works

1. The same prompt (and duration) is fanned out concurrently to the three
   pay-per-use providers, all reached through fal.ai (`FAL_KEY`).
2. Each attempt is validated: the tool call must succeed AND produce a real
   artifact (a non-empty file or a video URL).
3. Among the attempts that PASS, the cheapest one wins. The winning clip is
   copied to `output_path`.
4. A cost receipt JSON is written per run to `receipt_dir`
   (`higgsfield-payperuse-<run_id>.json`).

## Receipt fields

| Field | Meaning |
|-------|---------|
| `run_id` | Unique id for the run |
| `ts` | UTC timestamp |
| `prompt_sha256` | Hash of the prompt (full prompt text is never written to receipts) |
| `prompt_preview` | First 40 characters, for human scanning |
| `attempts[]` | Per-provider: status (`pass`/`fail`/`error`), `cost_usd`, `latency_s`, `error` |
| `winner` / `winner_cost_usd` | Cheapest passing provider and its cost |
| `total_spend_usd` | Sum of ALL attempts (failures still cost money) |
| `most_expensive_pass_usd` / `saved_vs_premium_usd` | What the premium passing option would have cost, and what picking the cheapest saved |

## Cost guidance (from provider estimate tables, 5s clip)

| Provider | ~Cost |
|----------|-------|
| Kling (standard) | ~$0.10 |
| MiniMax (standard) | ~$0.10 |
| Seedance (standard) | ~$1.52 |

Fan-out spends on all three, so it is for takes where a failed render would
cost more than the extra $0.20 - or where you need a take NOW and any
provider will do. For known-good prompts on a budget, call a single provider
tool directly.

## Example

```python
from tools.video.higgsfield_payperuse import HiggsfieldPayPerUse

tool = HiggsfieldPayPerUse()
result = tool.execute({
    "prompt": "a raven flies over Skagit Valley at dusk, cinematic",
    "duration": "5",
    "output_path": "out/raven.mp4",
    "receipt_dir": "receipts",
})
# result.data["winner"]            -> cheapest passing provider
# result.data["receipt_path"]      -> the per-run cost receipt
# result.data["total_spend_usd"]   -> full fan-out spend
```

## Notes

- Providers that report themselves unavailable (missing API key) are skipped
  before any spend.
- `providers: ["kling", "minimax"]` restricts the fan-out to a subset.
- Failed attempts still appear on the receipt with their cost: that is real
  spend, and the receipt is the audit trail for it.
