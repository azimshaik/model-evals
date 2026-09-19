# Run summary — 2026-09-19 · Frontier Friday (local rig edition)

**Task:** home organization & inventory web app (see `../../tasks/home-inventory-app.md`)
**Serving:** local OpenAI-compatible endpoints only — vLLM (TP4) and llama.cpp CUDA — **no cloud API used to generate or judge anything**
**Params:** temperature 0.2 · max_tokens 16384 · thinking disabled where the model supports it (see notes)
**Verification:** each generated app was loaded in a real browser and driven with real input events
**Hardware:** 4× RTX 2080 Ti 22 GB (Turing sm_75, PCIe-only, no NVLink) · Xeon E5-2680 v4 · 64 GB DDR4-2400 ECC · 175 W per-card power cap

| Model | served on | decode tok/s | rig W | tok/s per W | app | browser test |
|---|---|---|---|---|---|---|
| Qwen3.5-35B-A3B (MoE, ~3B active) UD-IQ4_XS | llama.cpp, 1 card | **90.7** | 187 | **0.485** | 24.5 KiB | ✅ pass |
| Qwen3-8B Q4_K_M | llama.cpp, 1 card | 81.8 | 185 | 0.442 | 14.5 KiB | ✅ pass |
| Qwen3.5-9B UD-Q4_K_XL | llama.cpp, 1 card | 73.1 | 187 | 0.391 | 21.3 KiB | ✅ pass |
| Qwen3.8-27B-NVFP4 (daily engine) | vLLM TP4, 4 cards | 39.2 † | **690** | 0.057 | 39.0 KiB | ✅ pass (richest UI) |
| Ternary Bonsai 2 27B PTQ1_0 (5.95 GB) | llama.cpp-prism, 1 card | 29.3 | 191 | 0.153 | 33.0 KiB | ❌ add-item broken |

† effective rate during this build run (token count estimated from reply length); the same engine
measures **49.4 tok/s** on a clean sustained decode test at the same 175 W cap.

**Energy to build one app:** 0.0035 kWh (35B MoE, 1 card) vs 0.0477 kWh (dense 27B, 4 cards) — 13×.

## Key findings

1. **Sparsity beat card count.** A 35B MoE with ~3B active parameters on *one* card delivered 1.8×
   the decode speed of the 4-card dense 27B, 13× less energy per app, and three cards left idle at
   32–45 °C — while passing the same functional tests. The dense 27B won only on output size/polish.
2. **Thinking mode is a liability for code-generation tasks on the big models.** The dense 27B with
   thinking on consumed its *entire* budget in the reasoning channel and emitted **zero code** —
   twice (16k then 24k tokens). With thinking off it produced the best-looking app of the field in
   249 s. The ternary 27B failed identically (54,646 chars of reasoning, no code) — the same failure
   mode this repo saw from `qwen/qwen3.8-flash` on 2026-08-30, now reproduced locally.
3. **The finishers declared their own exit.** All three models that delivered ended their planning
   with an explicit hand-off ("Final Output: proceeding to generate the HTML string"; "Final Review
   against Requirements: … Single file? Yes."). The two failures planned in prose, wrote markup,
   CSS and JS *inside* the reasoning channel, and were still tuning colour palettes when the budget
   died. Full transcripts in `thinking/`.
4. **Cheapest per token ≠ usable.** The ternary model is coolest and cheapest per token and uses
   the least VRAM (6.4 GB on one card), but its app clears the item form and stores nothing on save,
   and it was the slowest of the five.
5. **All five apps passed the static checks** (complete file, valid JS via `node --check`, every
   feature marker present). Only the live browser tests separated them — static inspection is not
   evidence of a working app.

## Files

- `manifest.json` — per-model: serving config, tokens, decode rate, watts, tok/s per W, energy, app size, browser verdict
- `<model>.txt` — raw model replies (unedited)
- `apps/<run>/` — `index.html` (the app), `metrics.json`, `check.json` (static checks), `verification.json` (browser tests)
- `thinking/<run>.txt` — full reasoning transcripts (up to 83 k chars)
- `reports/` — the four full rig reports this run is built on (health diagnostics, ternary-vs-vLLM power study, build sweep, reasoning analysis)
- `../../articles/2026-09-19-frontier-friday-local.md` — write-up
- `../../harness/local/` — the harness used (works against any OpenAI-compatible endpoint)

## Notes on method

- Watts are **GPU-side** totals sampled from `nvidia-smi` every 1–2 s during generation, not wall
  power (wall adds roughly 100–150 W for CPU, disks and PSU losses).
- Speeds for llama.cpp runs are the server's own `eval time` counters; the vLLM run's token count is
  estimated from reply length (see †).
- "Pass" means: loads in Chromium, demo data fills, an item is added with real input events, search
  filters, and the item survives a page reload. It is not a code-quality review.
