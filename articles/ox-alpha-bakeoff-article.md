# The Stealth Ox Bake-Off: Testing the Mystery AI Model Against the Field

**Date:** Aug 22, 2026 · **Setup:** Azim Shaik's Mac via OpenRouter · **Total cost of experiment: $0.022**

---

## Background: who is Ox Alpha?

On Aug 20, 2026, OpenRouter quietly listed a model called **`stealth/ox-alpha`** — free ($0/M input, $0/M output), with a **1M-token context window**, multimodal input, and no named creator. It sits under the generic "Stealth" provider. Serving-layer forensics (Aug 22) point to **Zhipu AI (Z.AI)**, possibly a hidden variant of **GLM-5.3**: a leaked Java stack trace naming Zhipu's internal API classes, a shared error-code dialect, and 30/30 tokenizer matches. Zhipu has neither confirmed nor denied.

We decided to stop speculating and start testing — pitting Ox Alpha against three reference models on the exact same task, through the same API, with the same parameters.

## Methodology

- **Task:** Implement ISBN-10 validation (hyphens allowed, weighted checksum mod 11, 'X' = 10 in final position), explain the checksum math, and name one edge case. Strict output format: `CODE:` / `EXPLANATION:` / `EDGE_CASE:`.
- **Models:** `deepseek/deepseek-v4-flash` (daily driver) · `anthropic/claude-opus-4.8` (premium frontier) · `stealth/ox-alpha` (the mystery) · `z-ai/glm-5.3` (the alleged parent).
- **Params:** temperature 0.3, max_tokens 1200, identical prompt, all via OpenRouter.
- **Verification:** every model's code was **extracted and executed** against a 9-case test suite (valid/invalid, X placement, length, whitespace) — scores below are from real execution, not eyeballing.

## Results

| Model | Tests | Latency | Cost | Format ✓ | Explanation | Edge case |
|---|---|---|---|---|---|---|
| **stealth/ox-alpha** | **9/9** | 30.1s | **$0.00** | ✅ | Full proof (all transpositions) | X-position + type guard |
| **claude-opus-4.8** | 8/9 | **8.6s** | $0.016 | ✅ | Elegant general proof | X-position + case |
| **deepseek-v4-flash** | 8/9 | 14.4s | **$0.0001** | ✅ | Correct (adjacent-swap proof) | X-position + case |
| **z-ai/glm-5.3** | 8/9 | 23.0s | $0.005 | ❌ ignored format, leaked reasoning, truncated | Good but rambling | **Best: Unicode digits + X-position + lowercase** |

*The 9th test was trailing-whitespace tolerance — beyond spec, but Ox Alpha handled it; the others didn't. All four pass the spec itself.*

## What each model revealed

**🥇 stealth/ox-alpha — the mystery delivers.** The most rigorous explanation of the four: it proved that *every* transposition (not just adjacent) breaks divisibility, using the prime-11 argument correctly. It added a defensive `isinstance` check, stripped whitespace, and followed the format to the letter. **9/9 tests. Zero dollars.** Its only weakness: 30 seconds — the slowest of the field.

**🥈 claude-opus-4.8 — the polished professional.** Fastest (8.6s), cleanest prose, equally correct math. This is what paying $0.016 buys: same quality, 3.5× faster. The reference standard.

**🥉 deepseek-v4-flash — the value king.** 8/9 tests, correct code and explanation, for **one-tenth of a cent**. It's 98% of Claude's output at 0.6% of the price — which is exactly why it's the default model on this machine.

**🤔 z-ai/glm-5.3 — the plot twist.** Its *code* was arguably the most defensive (rejects Unicode digits like Arabic-Indic numerals — a genuinely subtle bug most implementations miss; uses explicit ASCII range checks). But it **ignored the requested output format**, exposed its internal deliberation in the final answer (reasoning leakage), and got truncated mid-example. Also: its verbose, thinking-out-loud style is **nothing like Ox Alpha's crisp, proof-driven output**. Behaviorally, the alleged parent and child look like strangers.

## Learnings

1. **Free ≠ bad.** Ox Alpha produced the best answer in the field for $0.00. For coding/agentic workloads with slack on latency, it's a legitimate default-tier option.
2. **The 1M context is the real headline.** A free model that can ingest a million tokens changes what you can point an agent at (whole repos, long transcripts).
3. **Latency is the hidden cost of free.** At 30s vs Claude's 8.6s, Ox Alpha costs time, not money. For interactive work, that matters more than price.
4. **Format compliance is a quality signal.** Three models followed the output contract exactly; GLM didn't. When you're building agents, instruction-following *is* the capability.
5. **The Zhipu theory needs more evidence.** Tokenizer fingerprints say GLM family; behavior says otherwise. Ox Alpha may be a heavily-distilled or substantially-modified GLM — or someone else entirely. Until Zhipu speaks, treat it as: *fingerprints say GLM, prose says not-GLM.*
6. **Verified beats vibes.** All four *looked* correct; execution separated them. The whitespace test nobody but Ox Alpha passed wouldn't have surfaced in a read-through.

## Bottom line

Ox Alpha is the most interesting free model in a long time — genuinely frontier-adjacent on a focused coding task, with a context window no paid model matches at that price. It's not a Claude-killer (the latency gap is real), and it's not proven to be Zhipu's child (behavior says otherwise). But for $0, it earns a permanent slot in the toolbox.

---

*Run on: DeepSeek v4-flash, Claude Opus 4.8, Ox Alpha, GLM-5.3 via OpenRouter · full outputs in `~/ox-test/eval/` · harness in `~/ox-test/eval_models.py`*
