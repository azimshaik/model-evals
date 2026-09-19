# Overnight model build sweep — 2026-09-19

Same machine, same prompt, one model at a time. Every model was asked to build the same
single-file web app: a **Home Organization & Inventory manager** (rooms CRUD, items with
quantity/category/room/notes, search + filters, low-stock highlight, localStorage
persistence, JSON export/import, demo data, responsive, no frameworks, no CDNs, output as
one complete HTML file). Prompt: `PROMPT.txt` (identical bytes for every model).

**No cloud model was used to build or to judge any of this.** Every line of code in the four
apps was produced by the local model under test; DeepSeek (or any API) was not involved in
generating or scoring them. The checks below are mechanical (HTML/JS parsing + a real browser
driving the UI) — your eyes are the final judge.

## Results

| model / config | engine, cards | decode tok/s | rig watts | tok/s per watt | energy to build the app | output | browser verdict |
|---|---|---|---|---|---|---|---|
| **Qwen3.5-35B-A3B (MoE, ~3B active)** IQ4_XS | llama.cpp, **1 card** | **90.7** | 187 W | **0.485** | **0.0035 kWh** | 24.5 KiB, 6,018 tok, 67 s | PASS — demo data, add item (toast "Item added"), persists after reload |
| Qwen3-8B Q4_K_M | llama.cpp, 1 card | 81.8 | 185 W | 0.442 | 0.0023 kWh | 14.5 KiB, 3,552 tok, 44 s | PASS — add item + reload + search filter all verified |
| Qwen3.5-9B UD-Q4_K_XL | llama.cpp, 1 card | 73.1 | 187 W | 0.391 | 0.0048 kWh | 21.3 KiB, 6,666 tok, 92 s | PASS — add item, search filter, persistence verified |
| **Qwen3.8-27B-NVFP4 (your daily engine)** | vLLM TP4, **4 cards** | 49.4 (clean test) | **690 W** | 0.071 | 0.0477 kWh | **39.0 KiB**, ≈9.7k tok (est.), 249 s | PASS — best product: demo, add item, search, persistence, richest UI |
| Ternary Bonsai 2 27B PTQ1_0 (5.95 GB) | llama.cpp-prism, 1 card | 29.3 | 191 W | 0.153 | 0.0178 kWh | 33.0 KiB, 9,816 tok, 336 s | FAIL — renders fine, demo data loads, but **adding an item does nothing** |

Rig-side thermals were benign throughout: single-card runs kept three GPUs asleep at 32-45 °C
and the working card at 63-68 °C / fans 68-84 %; the 4-card vLLM run held 68-75 °C, fans 50-91 %,
all under the 89 °C operating limit with the 175 W per-card cap in place.

## The headline findings

1. **The 35B MoE is the efficiency winner by a wide margin.** 90.7 tok/s on **one** card at
   187 W for the whole rig — 1.8× the daily engine's speed, ~13× less electricity per app built,
   three cards left idle and cool. Its app also works end to end (24.5 KiB).
2. **More cards did not buy a better app — they bought a longer one.** Your daily 27B produced the
   richest UI (39 KiB, stat cards, styled item cards) but at 4× the power and 4 GPUs, and its
   effective throughput during the build was unremarkable. The MoE produced a smaller, plainer
   app that passes the same functional tests.
3. **Thinking mode is a trap for this workload on the daily engine.** With the model's default
   (thinking on) it spent the *entire* 16k-token budget on reasoning and emitted **zero code**
   (finish_reason=length, 344 s). With thinking disabled the same model wrote a complete app in
   249 s. Keep `enable_thinking: false` for code tasks.
4. **The compressed (ternary) 27B still isn't ready.** It renders a complete-looking app, but its
   add-item path clears the form and stores nothing (verified with real typed input, real clicks,
   after dismissing dialogs; the file contains no `alert()` so it isn't a dialog artifact — its
   own `saveItem()` validation runs against an empty form). Cheapest, coolest, and the only
   functional failure.

## Where the products are

```
~/models/sweep/app-build/<model>/
    index.html          <- the app the model built (open this)
    raw.txt             <- the model's full reply
    reasoning.txt       <- thinking text (if any)
    metrics.json        <- prompt/completion tokens, TTFT, wall time, tok/s, per-GPU temps/power/fans
    check.json          <- objective HTML/JS checks (completeness, feature markers, node --check)
    verification.json   <- browser + functional test results written by hand-crafted tests
    telem.csv           <- the raw telemetry samples taken during generation
```
A click-through gallery of all four apps: **http://127.0.0.1:8094/GALLERY.html**
(if that server is gone: `cd ~/models/sweep/app-build && python3 -m http.server 8094`)

Models downloaded for this (kept for reuse): `~/models/sweep/` — Qwen3.5-35B-A3B UD-IQ4_XS
(17.5 GB), Qwen3.5-9B UD-Q4_K_XL (6.0 GB), Qwen3-8B Q4_K_M (5.0 GB). Plus the pre-existing
ternary Bonsai 2 27B in `~/models/bonsai2/`.

## Caveats (so nothing here is overstated)

- Token counts for the vLLM run are estimated from the reply length (vLLM streamed without usage
  reporting on that call); the llama.cpp runs use the server's own counters. Speeds for the
  llama.cpp runs are the server's `eval time` values, not wall-clock guesses.
- "PASS" means: the app loads in Chromium, the demo button fills data, an item can be added with
  real input events, search filters, and the new item survives a page reload. It does not mean the
  app is good-looking or complete beyond the stated requirements — look at the screenshots.
- Two apps call `alert()`/`confirm()`, which blocks headless automation until dismissed or stubbed;
  that was an automation problem, not an app defect, and it was re-tested properly before judging.
- Watts are GPU-side totals sampled from `nvidia-smi` (not wall power). GPU-side underestimates
  wall draw by the CPU, disks and PSU losses (roughly +100-150 W).

## Rig state at the end

All model engines and the static file server for the gallery were stopped; the four cards were
left idle. The daily engine is **not** running — bring it back with:

```bash
systemctl --user reset-failed vllm27b.service; systemctl --user start vllm27b.service
```
(It needs `reset-failed` first if a start attempt failed; the unit allows 3 starts per 30 minutes.)
Note that something on the box has also been restarting that unit on its own after a stop.
