# What each model was thinking — 2026-09-19

Same task, same prompt (build the Home Inventory web app), thinking enabled where the model has
a reasoning channel. Full text per model: `<model>-thinking-on/reasoning.txt` in
`~/models/sweep/app-build/`. Summary of the five:

| model | thinking text | code emitted | tokens | time | finished? | what happened |
|---|---|---|---|---|---|---|
| Daily 27B (Qwen3.8-27B, 4 cards) | 82,918 chars | **0** | 24,576 | 524 s | **no** (cut off) | built the whole app *inside* its reasoning and kept polishing; never wrote the answer |
| Ternary Bonsai 27B (1 card) | 54,646 chars | **0** | 16,384 | 568 s | **no** (cut off) | same pattern; drifted into CSS colour palettes at the end |
| Qwen3.5-35B-A3B (1 card) | 5,800 chars | 24,133 | 6,033 | 85 s | **yes** | numbered plan, then "Proceeding to generate the HTML string" |
| Qwen3.5-9B (1 card) | 4,563 chars | 21,330 | 6,666 | 92 s | **yes** | structured plan + a requirement-by-requirement review |
| Qwen3-8B (1 card) | 3,948 chars | 12,296 | 3,074 | 48 s | **yes** | plain prose plan, straight to code |

## The two that failed — and why

**Daily 27B.** It restated the spec, then designed the data model, then handled edge cases
(orphan room references), then wrote render functions, then moved on to typography and
accessibility polish — all in the reasoning channel. At the 60 % mark it is writing real
JavaScript inside its thinking ("`function renderAll() { rende…`"); at 95 % it is tuning CSS
("`.brand h1 { font-family: var(--font-display); font-size: clamp(1.4rem, 2.6vw, 1.9rem)…`").
Its final words before the budget ran out:

> "Also add `autocomplete="off"` on the search input. Number input: hide the spinners? Keep the
> default spinners — they're useful. Actually, the default number spinners are fine. Let me double…"

Self-corrections are constant ("Hmm," ×8, "Actually, let me…" ×1, "Wait:" ×1). It is not stuck —
it is **building the app in the wrong place** and never reaching the point where it stops
refining and emits the file. 24,576 tokens, zero bytes of deliverable.

**Ternary Bonsai 27B.** Identical failure shape (54,646 chars, "Hmm," ×13, "Actually, let me…" ×4).
It drafts HTML markup, CSS grid layouts and event-delegation JS in the thinking channel, then
spends its last stretch on styling detail:

> ".tag[data-cat="Food"] { background:#E7F1E5; color:#2F5D33; … } .tag[data-cat="Tools"] { … }"

**Diagnosis:** both models plan in prose, with no declared finish line and no size budget, so
the perfectionism loop never terminates. Giving them a bigger budget does not fix it — the daily
model still produced nothing when given 24,576 tokens.

## The three that finished — and how

**Qwen3.5-35B-A3B (MoE)** — 5,800 chars, 85 s, complete 23.6 KiB app. Its thinking is a short,
numbered engineering plan that mirrors the spec exactly: analyze → structure → CSS → JS →
self-corrections → final assembly, and it names its own exit:

> "10. **Final Code Assembly:** (This matches the provided good response)."
> "**Final Output:** (Proceeding to generate the HTML string). *Self-correction: Ensure the code
> block is strictly just the HTML.*"

**Qwen3.5-9B** — 4,563 chars, 92 s, complete 21.3 KiB app. Same house style, with an explicit
acceptance review at the end:

> "9. **Final Review against Requirements:** * Single file? Yes. * Offline? Yes. * Rooms CRUD? Yes.
> * Items CRUD? Yes. * Search/Filter? Yes. * Low stock? Yes. * Persistence? Yes. * Export/Import?
> Yes. * Responsive? Yes. * No console errors? (Will double-check variable names)."

**Qwen3-8B** — 3,948 chars, 48 s, smallest app (12.0 KiB). Plain prose, no numbering, no checklist,
the least "architectural" thinking of the set:

> "Okay, I need to create a single-file web app for a home organization and inventory manager.
> Let me start by breaking down the requirements. First, the app must work offline, so I'll use
> localStorage for persistence…"

## Practical takeaways

1. **Thinking mode is a liability for build tasks on the two big models** and a small benefit on
   the small ones. On your daily engine it was strictly harmful: thinking on = 0 code (even with
   24.5k tokens); thinking off = the best-looking app of the whole field, in 249 s.
2. **The models that finish are the ones whose reasoning is bounded and ends with an explicit
   "now write it" step.** The two that failed both plan in prose and keep refining forever. If you
   ever want them to deliver with thinking on, the fix is external: cap the phase ("plan in at
   most 300 words, then output the file"), or instruct "thinking is not allowed to contain code".
3. **Reasoning length is not a quality signal here.** The winner's thinking was the *second
   shortest*; the two longest were the two that produced nothing.
