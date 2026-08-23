# Run summary — 2026-08-22 · The Stealth Ox Bake-Off

**Task:** ISBN-10 validator (see `../../tasks/isbn10-validator.md`)
**API:** OpenRouter · **Params:** temperature 0.3, max_tokens 1200
**Verification:** every model's code executed against the 9-case suite

| Model | Tests | Latency | Cost (USD) | Format ✓ | Notes |
|---|---|---|---|---|---|
| stealth/ox-alpha | 9/9 | 30.1s | 0.000000 | ✅ | best explanation (full transposition proof); whitespace-strip bonus |
| anthropic/claude-opus-4.8 | 8/9 | 8.6s | 0.016260 | ✅ | fastest; elegant general proof |
| deepseek/deepseek-v4-flash | 8/9 | 14.4s | 0.000102 | ✅ | adjacent-swap proof; value king |
| z-ai/glm-5.3 | 8/9 | 23.0s | 0.005385 | ❌ | most defensive code (Unicode-digit trap); ignored format, leaked reasoning, truncated |

**Total cost:** $0.0217

## Key findings

1. Free ≠ bad: Ox Alpha produced the best answer in the field for $0.00.
2. Latency is the hidden cost of free: 30s vs Claude's 8.6s.
3. Format compliance is a quality signal — only GLM failed it.
4. Behaviorally, Ox Alpha looks nothing like its alleged parent (GLM-5.3): crisp proof-driven output vs verbose deliberative rambling.

## Files

- `manifest.json` — full API response metadata (usage, cost, latency) per model
- `<model>.txt` — raw model outputs (unedited)
