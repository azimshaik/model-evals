# Run summary — 2026-08-30 · Frontier Friday

**Task:** ISBN-10 validator (see `../../tasks/isbn10-validator.md`)
**API:** OpenRouter · **Params:** temperature 0.3, max_tokens 1200
**Verification:** every model's code executed against the 9-case suite

| Model | Tests | Format ✓ | Latency | Cost (USD) | Notes |
|---|---|---|---|---|---|
| deepseek/deepseek-v4-flash | 8/9 | ✅ | 8.7s | 0.000262 | clean baseline (only misses whitespace bonus) |
| meta-llama/llama-4-maverick | 8/9 | ✅ | 12.2s | 0.000274 | solid, no drama |
| qwen/qwen3.8-flash | — | ❌ | 11.6s | 0.000600 | leaked full chain-of-thought, never emitted final answer, truncated |

**Intended but unavailable:**
- `stealth/ox-alpha` — **removed from OpenRouter** since the 2026-08-22 run (404). The mystery model vanished.
- `meta/muse-spark-1.3` — listed but **403 Forbidden** (gated; requires Meta BYOK/plan).

## Key findings

1. The week's hyped releases underdelivered: Ox Alpha pulled, Muse Spark gated, Qwen3.8-Flash unpolished (reasoning leak + no structured output — same failure mode as GLM-5.3 on 2026-08-22).
2. DeepSeek v4-flash remains the value/quality baseline.
3. Qwen3.8-Flash's leaked draft logic was actually correct — the failure is delivery/format discipline, not reasoning (may be a preview quirk; retry with reasoning disabled / larger cap for a fair second shot).

## Files

- `manifest.json` — per-model usage/cost/latency
- `<model>.txt` — raw outputs (unedited; qwen file shows the full reasoning leak)
