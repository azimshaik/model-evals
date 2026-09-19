# Frontier Friday, local rig edition: the 35B MoE that beat a 4-GPU dense 27B

*Run date: 2026-09-19 · hardware: one workstation, 4× RTX 2080 Ti 22 GB (Turing) · no cloud API
used to generate or judge anything in this run.*

The previous Frontier Friday runs sent the same task to several models through one API. This one
moves the same discipline onto a single box: **one task, five local models, one model at a time**,
every artifact kept — the reply, the app, the metrics, and (a first for this repo) the model's
**full reasoning transcript**.

## The task

Build a complete single-file web app: a household **Home Organization & Inventory** manager —
rooms CRUD, items with quantity/category/room/notes, live search plus room and category filters,
low-stock highlighting, localStorage persistence, JSON import/export, demo data, responsive,
no frameworks, no CDNs, offline. Output contract: one fenced code block, nothing else
(`tasks/home-inventory-app.md`).

Scoring is mechanical, never by eye: the reply is parsed, the HTML extracted, every inline
`<script>` run through `node --check`, feature markers checked, and then the app is **opened in a
real browser and driven** — demo data, add an item with real input events, search, reload to prove
persistence.

## Results

| Model | served on | decode tok/s | rig W | tok/s per W | app | browser test |
|---|---|---|---|---|---|---|
| **Qwen3.5-35B-A3B** (MoE, ~3B active) IQ4_XS | llama.cpp, **1 card** | **90.7** | 187 | **0.485** | 24.5 KiB | ✅ |
| Qwen3-8B Q4_K_M | llama.cpp, 1 card | 81.8 | 185 | 0.442 | 14.5 KiB | ✅ |
| Qwen3.5-9B UD-Q4_K_XL | llama.cpp, 1 card | 73.1 | 187 | 0.391 | 21.3 KiB | ✅ |
| Qwen3.8-27B-NVFP4 — the box's daily engine | vLLM TP4, **4 cards** | 39.2 | **690** | 0.057 | **39.0 KiB** | ✅ (richest UI) |
| Ternary Bonsai 2 27B PTQ1_0 (5.95 GB) | llama.cpp-prism, 1 card | 29.3 | 191 | 0.153 | 33.0 KiB | ❌ add-item broken |

Energy to build one app: **0.0035 kWh** (35B MoE, one card) vs **0.0477 kWh** (dense 27B, four
cards). Same building, 13× the electricity.

## Finding 1 — sparsity beat card count

The 35B MoE has ~3B active parameters. It read 17.5 GB of weights from **one** card and produced
90.7 tok/s; the dense 27B read 22 GB spread over **four** cards and produced 39–49 tok/s while
pulling 690 W and living at 68–75 °C. Three of the four GPUs sat idle at 32–45 °C during the MoE
run. On a rig whose owner cares about heat, noise and card life, that is the whole story: **the
parameter count buys quality, the active-parameter count buys speed and watts.**

It also disagrees with a common assumption — that you need the whole card set working to get
useful agentic throughput. Here the opposite held: fewer cards, on a sparser model, was faster.

## Finding 2 — thinking mode is a liability for code tasks, and it fails loudly

This is the run's most reproducible result. The dense 27B, with its default thinking enabled,
consumed its **entire** output budget inside the reasoning channel and emitted **zero code**:

- attempt 1: 16,384-token cap → 16,384 tokens of reasoning, `finish_reason=length`, 0 bytes of HTML.
- attempt 2: 24,576-token cap → 24,576 tokens of reasoning (82,918 characters), 524 s, still 0 bytes.

With thinking disabled, the same model produced the best-looking app of the field in 249 s.

The transcript explains it: it is not stuck, it is **building the app in the wrong place**. It
designs the data model, writes real render functions, handles orphan-room edge cases, then drifts
into typography and accessibility polish — and its last words before the budget died were:

> "Also add `autocomplete="off"` on the search input. Number input: hide the spinners? Keep the
> default spinners — they're useful. Actually, the default number spinners are fine. Let me double…"

The ternary 27B failed the same way (54,646 characters of reasoning, no code, ended mid-CSS:
`.tag[data-cat="Food"] { background:#E7F1E5; … }`). Notably this is the *same failure mode* this
repo recorded for `qwen/qwen3.8-flash` on 2026-08-30 — reasoning leak, no final answer, truncated —
which suggests it is a property of the model families, not of one API.

## Finding 3 — the finishers declared their own exit

The three models that delivered all ended their planning with an explicit hand-off:

- 35B MoE: *"**Final Output:** (Proceeding to generate the HTML string). *Self-correction: Ensure
  the code block is strictly just the HTML.*"*
- 9B: *"**Final Review against Requirements:** Single file? Yes. Offline? Yes. Rooms CRUD? Yes. …
  No console errors? (Will double-check variable names)."*
- 8B: plain prose planning, no checklist, straight to code — and the fastest run of all (48 s).

Reasoning length was not a quality signal: the winner's thinking was the *second shortest*; the
two longest produced nothing at all.

## Finding 4 — static checks pass on broken apps

All five apps passed every static check: complete file, every inline script parses, all seventeen
feature markers present. Only the live browser test separated them: the ternary model's app renders
beautifully, loads demo data — and on "save item" it clears the form and stores nothing (verified
with real typed input and real clicks, dialogs dismissed first, so it is not an automation artifact;
the file contains no `alert()`).

**Execute, don't admire** applies to whole apps, not just functions.

## Method notes, honestly

- Watts are GPU-side from `nvidia-smi` (sampled every 1–2 s during generation), not wall power.
- llama.cpp numbers come from the server's own `eval time` counters; the vLLM run's token count is
  estimated from reply length (the engine streamed without usage reporting).
- Every prompt was byte-identical; every model got the same 175 W per-card cap, the same context,
  and thinking disabled for parity except where the run was explicitly a thinking experiment.
- The two apps that use `alert()`/`confirm()` blocked headless automation until dialogs were
  dismissed/stubbed — an automation problem, re-tested properly before judging.
- Reproduce with `harness/local/` (any OpenAI-compatible endpoint) plus `harness/local/PROMPT.txt`.

## What I'd do with this

1. **Promote the 35B MoE to the daily driver** for agentic work, and keep the dense 27B for
   artifact-heavy tasks where its extra polish shows. The MoE frees three cards — which is exactly
   the headroom a second model (or a longer-context service) needs on this box.
2. **Never enable thinking for code generation on these models** without an external phase cap.
   The cheap fix is a prompt constraint ("plan in at most 300 words, then output the file") or a
   server-side reasoning budget.
3. **Verify by execution, always.** Every static signal said the ternary app was fine.
