# Decisions, not text: what a typed-decision model actually buys you

*Frontier Friday · 2026-09-30 · all numbers in this post were produced by the harness in this repo*

A lot of production AI work is not "write me something". It is **decide something**: is this output
correct, is this request an attack, which queue does this belong in, how severe is this. Today we
mostly do that by prompting a chat model and parsing its text back into a boolean.

A **typed-decision model** skips the text. You hand it a state and a typed question and it returns
typed values with probabilities in one forward pass. The commercial one is **Jev** (TypeSafe AI's
"System One"); the open-weight equivalent we used earlier is a **322M** model that runs locally.

So we put the same two judgment tasks through three ways of deciding:

| Pass | What it is |
|---|---|
| **Jev** | hosted API, `POST /v1/systemone`, `noul` (yes/no) and 2-option `choice` questions |
| **322M local** | open-weight decision model, MLX on Apple silicon, ~zero marginal cost |
| **LLM judge** | chat model, temperature 0, forced to answer PASS/FAIL, verdict parsed from text |

## Why the labels are trustable

The usual failure of a judge benchmark is that the "correct" answers are somebody's opinion. Here,
**ground truth is executed**: every code candidate is *run* against a 9-case test suite and the
verifier's verdict is the label. That is not academic. Our first hand-written label claimed a
reversed-weight checksum implementation was broken; executing it showed it passes 9/9, because the
reversed weighted sum is mathematically equivalent. Only execution catches that.

Second rule: **no tuning on the test items.** The question phrasing was written for the local model
months earlier, so if anything it disadvantages Jev. Third: report **precision and recall**, not
just accuracy, because decision models fail asymmetrically.

## Results

**Task 1 — "does this output correctly implement the task?"** (20 items: 7 correct, 13 wrong, refusals, non-answers)

| Pass | Accuracy | Precision / Recall | Median latency | Cost per decision |
|---|---|---|---|---|
| **Jev** | **20/20** | 1.00 / 1.00 | 239 ms | $0.000019 |
| 322M local | 10/20 | 0.41 / 1.00 | **25 ms** | $0 |
| LLM judge | 16/20 | — | 1,632 ms | $0.001024 |

**Task 2 — "is this an attempt to override or inject instructions?"** (16 items: 8 probes, 8 benign)

| Pass | Accuracy | Precision / Recall | Median latency | Cost per decision |
|---|---|---|---|---|
| **Jev** | **15/16** | 1.00 / 0.875 | 233 ms | $0.000014 |
| 322M local | 12/16 | 1.00 / 0.50 | **19 ms** | $0 |
| LLM judge | **16/16** | — | 1,097 ms | $0.000224 |

The whole experiment cost **$0.0013**.

## Five things that surprised us

**1. The decision model beat the LLM judge, not just the local model.** On code correctness Jev was
20/20 against the chat model's 16/20, at 1/54th the cost and 1/7th the latency. All four of the
LLM's misses were *correct* implementations it rejected, which is the expensive direction to be
wrong in if you are filtering candidates.

**2. Confidence tracked error for one model and not the other.** The whole pitch of this class is
"decide locally when confident, escalate when not". That only works if confidence actually tracks
error. Jev's single guard miss sat at the bottom of its range (probability 0.19). Our earlier local
run missed 4 of 8 probes with confidence staying high, so **0 of 16 items escalated** and the
safety net never fired. Same architecture label, completely different behaviour. Calibration is
per-model and per-task: measure it, do not assume it.

**3. Escalating can make things worse.** With a 0.70 gate, deferring to the LLM dropped task 1 from
1.00 to 0.95, at roughly 7× the cost. A gate is only worth building where the fallback is actually
better at *that* task.

**4. A yes/no question has no confidence.** Confidence is derived from a probability
*distribution* (`(count × peak − 1)/(count − 1)`), which a binary question does not have. You can
derive a margin yourself (`2·|p − 0.5|`) or ask a 2-option `choice` instead. Both routes agreed on
**all 36 verdicts**, so the phrasing changed nothing about the decision, only whether a
vendor-supplied confidence was available.

**5. "Zero output tokens" is not quite what the API reports.** The responses carry
`usage.output_tokens` of about 20 per question. Output is priced at $0, so the cost claim holds, but
if you are budgeting on the idea that no tokens are generated at all, look at the payload.

## How to decide for your own task

1. **Write down what a wrong decision costs** in each direction. A filter that rejects good work
   and a filter that lets bad work through are different products.
2. **Build 30-ish labelled items and get the labels by execution**, not by asking a model or your
   own memory.
3. **Run all three passes** (local decision model, hosted decision model, LLM) with identical
   question text.
4. **Plot escalate-rate against error-rate** before shipping a confidence gate. If errors do not sit
   below your threshold, the gate is decoration.
5. **Quote effective numbers**: accuracy *and* cost after escalation, not the raw local score.
6. **Check the privacy axis.** A hosted decision model means the decision leaves your machine; the
   local 322M model is the only private option in this comparison.

## Reproduce

```bash
export JEV_API_KEY=***          # your own key; the harness reads it from the environment
python3 harness/jev_bench_2026_09_30.py
```

Per-item audit trail, the exact datasets, and the unedited run log are in
[`results/2026-09-30-frontier-friday/`](../results/2026-09-30-frontier-friday/).

## What we are not claiming

n = 20 and n = 16, so one item moves the score 5 to 6 points: treat this as direction, not a
leaderboard. Task 1 is one task family. The LLM baseline verdicts are reused from the recorded
earlier run rather than re-called. Jev's latency includes network, while the local number is
compute-only. And the price used ($0.042 per 1M input tokens, output free) is an early-access rate
card that can change.
