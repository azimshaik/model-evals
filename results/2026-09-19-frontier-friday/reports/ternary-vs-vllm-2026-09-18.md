# Ternary 27B vs vLLM 27B on the 4× 2080 Ti rig — measured, 2026-09-18 night

Question: can a smaller-bytes model (ternary 27B, 5.95 GB) beat the current dense 27B
(NVFP4, 22 GB, TP4) on speed and cost? **Answer: no on speed, yes on VRAM and power.**
Raw data: `/tmp/benchres-*.json`, `/tmp/benchpar-*.json`, logs `/tmp/ternary*.log`.

## Side-by-side (same 1000-token decode test unless noted)

| | vLLM dense 27B NVFP4 | Ternary Bonsai 2 27B PTQ1_0 |
|---|---|---|
| Engine | vLLM 0.1.17 sm75 fork, TP4 | llama.cpp-prism fork (commit 9a9394a), 1 GPU |
| Context served | 262,144 (native) | 8,192 / 32,768 tested (native 262,144) |
| Decode, single stream | **48.40 tok/s** (175 W cap) · 49.13 (250 W) | **30.4 tok/s** (steady 30.4–30.5 over 1000 tok) |
| 4 parallel requests, 400 tok each | aggregate **49.09 tok/s**, reqs serialized (8.2/16.3/24.4/32.6 s) | aggregate **34.3 tok/s** (2 slots ~17 each; 4 slots configured) |
| VRAM used | 4 × ~21.0 GB = **84 GB** | **6.4 GB** (8K) / 8.4 GB (32K, 4 slots) |
| Rig GPU power | 672 W @175 cap · 849 W @250 | **185 W** (GPU0 168 W; other 3 cards 3–20 W, asleep) |
| Hottest GPU | GPU2 74 °C @175 cap · 83 °C @250, fans 100 % | GPU0 63–65 °C, fans ~68 % |
| Output correctness | verified earlier | verified: "17 times 4" -> 68 |

## What did NOT work (the two tricks that were supposed to close the gap)

1. **Speculative decoding with the DFlash2 draft** — `-md Bonsai-2-27B-DFlash2-Q8_0.gguf`:
   `error loading model: done_getting_tensors: wrong number of tensors; expected 81, got 58`.
   The GGUF itself parses end-to-end (81/81 tensor headers, 2.06 GB, complete) and the fork
   recognises it (`auto-detected speculative type 'draft-dflash'`), so this is a fork/file
   version skew, not a corrupt download. Fix = rebuild the PrismML fork from current source or
   use their pinned binary that matches the file revision. Potential: 1.5–2.5× on top of 30 tok/s.
2. **Multi-GPU row split** (`-sm row -ts 1,1,1,1`): `device CUDA0 does not support split buffers`
   — the packed ternary kernel cannot be row-split, so tensor-parallel across 4 cards is not
   available for this quant. Layer split (`-sm layer`, the default) works but does not speed up
   a single stream (each token still traverses every layer).

## Why the ternary card is NOT bandwidth-limited as expected

Bandwidth math predicted ~100 tok/s (5.95 GB read per token ÷ 616 GB/s). Reality: 30 tok/s.
Reason: this model is a hybrid — 64 layers, 48 of them Gated DeltaNet linear attention. Those
layers' per-token work is **compute**, not weight reads, and FP16 tensor-core FLOPs do not shrink
when you quantize the weights. On one 2080 Ti the FLOPs become the limit at ~3 bits/weight, and
the compute cannot be spread over the other three cards because row split is unavailable. So the
"fewer bytes = proportionally faster" rule breaks for linear-attention hybrids on Turing.

## Operational traps hit during the test (worth knowing)

- Stopping `vllm27b.service` and starting it again later hit `start-limit-hit`
  (`StartLimitIntervalSec=1800`, `StartLimitBurst=3`). Fix: `systemctl --user reset-failed vllm27b.service` before starting.
- Something restarted `vllm27b.service` by itself ~13 min after a clean `stop` (journal shows
  "Starting vllm27b.service" with no user action; cron/timers ruled out). Cause not identified —
  Hermes ships a local-models supervisor (`hermes_cli/web_routers/local_models.py`), so the
  dashboard/gateway is the likely candidate. Consequence: a stopped engine may come back and take
  all four GPUs mid-experiment.
- Port 8080 is `~/inference/ui/serve_ui.py` (proxies `/v1` and `/health` to the engine) — use
  8090+ for a second engine.
- The `-pl` power caps survive a service restart (they are driver-level, reset only at reboot).

## Deployment implication (the useful part)

The ternary model is a poor replacement for the daily driver (0.63× the speed) but an excellent
**second** model: 6–8 GB on one card, 185 W. The 27B can be reduced to TP2 (measured 36.3 tok/s,
KV pool 503K tokens = still 256K per request) using two cards, leaving two cards free — which
makes "27B agent engine + a second small/ternary model alongside" possible on this rig without a
model switcher. That is the configuration to test next if multi-model serving is wanted.
