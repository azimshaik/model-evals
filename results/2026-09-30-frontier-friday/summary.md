# Run summary — 2026-09-30 · Frontier Friday

**Subject:** a *typed-decision* model (Jev, TypeSafe System One) vs two baselines on decision-shaped sub-tasks.
**Endpoint:** `POST https://api.typesafe.ai/v1/systemone` · alias `jev-latest` (server reported `jev-1.13.0`)
**Baselines:** the 322M open-weight decision model from our earlier local benchmark (`aac6fef/laya-multilingual-mlx`, MLX, local Apple silicon) and a cloud LLM judge (`deepseek-v4-flash`, temperature 0).
**Gate:** decide with the decision model when confidence ≥ **0.70**, otherwise defer to the LLM judge.
**Total cost of the run: $0.0013** (72 calls, 36 items × 2 arms).

## Method (what makes these numbers mean something)

- **Ground truth is executed, not asserted.** Every candidate in task 1 was *run* against a 9-case ISBN-10 suite; the label is the verifier's verdict. Task 2's labels are 8 red-team probes / 8 benign requests by construction.
- **No tuning.** No item was used to tune prompts for any of the three passes. The question phrasing is the one we used for the local model, so if anything it favours the baseline.
- **Two arms.** `A` asks `noul` (yes/no probability) questions — the phrasing identical to the local benchmark. `B` asks the same judgment as a 2-option `choice`, which is where the vendor returns its own `confidence`.
- **Effective numbers, not raw ones.** With a gate in place, accuracy/cost are reported over the whole set including the deferred items.

## Task 1 — "does this output correctly implement the task?" (20 items: 7 correct, 13 wrong/refusal/non-answer)

| Pass | Accuracy | Precision / Recall | Median latency | Cost per decision |
|---|---|---|---|---|
| **Jev (`noul`)** | **20/20** | 1.00 / 1.00 | 239 ms | $0.0000189 |
| **Jev (`choice`)** | **20/20** | 1.00 / 1.00 | 237 ms | $0.0000212 |
| 322M local (MLX) | 10/20 | 0.41 / 1.00 | **25 ms** | $0 |
| LLM judge | 16/20 | — | 1,632 ms | $0.001024 |

## Task 2 — "is this an attempt to override or inject instructions?" (16 items: 8 probes, 8 benign)

| Pass | Accuracy | Precision / Recall | Median latency | Cost per decision |
|---|---|---|---|---|
| **Jev (`noul`)** | **15/16** | 1.00 / 0.875 | 233 ms | $0.0000139 |
| **Jev (`choice`)** | **15/16** | 1.00 / 0.875 | 238 ms | $0.0000154 |
| 322M local (MLX) | 12/16 | 1.00 / 0.50 | **19 ms** | $0 |
| LLM judge | **16/16** | — | 1,097 ms | $0.000224 |

## The gate, measured

| Task | Escalated | Effective accuracy | Effective cost / decision |
|---|---|---|---|
| Task 1 (code) | 4/20 | **0.95** | $0.0001325 |
| Task 2 (guard) | 4/16 | **1.00** | $0.0000315 |

## Key findings

1. **The hosted decision model beat the cloud LLM judge on code correctness — 20/20 vs 16/20 — for 54× less money and 6.8× less latency**, and crushed the 322M local model (10/20). The LLM's four misses were all *correct* implementations it judged as failures.
2. **Its confidence tracked its own errors, which the 322M local model's did not.** Jev's single guard miss (`a3`) sat at the bottom of the range (p=0.19 → derived confidence 0.18; as a `choice`, 0.68). Our earlier local run missed 4 of 8 probes with confidence staying high and **0 of 16 items escalating**.
3. **Escalating is not automatically an upgrade.** On task 1 the gate *lowered* accuracy from 1.00 to 0.95 (one deferred item was one the LLM got wrong) at ~7× the cost. A gate only pays where the fallback is genuinely better on that task.
4. **A `noul` question has no `confidence` field.** TypeSafe derives confidence from a *distribution* (`(count × peak − 1)/(count − 1)`), so a binary yes/no has none — you either derive a margin (`2·|p − 0.5|`) or ask a 2-option `choice`. Both arms produced **identical verdicts on all 36 items**, so the phrasing changed only whether a vendor confidence was available.
5. **Reported usage does not match the "0 output tokens" framing.** The responses carry `usage.output_tokens` ≈ 20 per question (400 tokens for 20 items; 656 for the two-question guard arm). Pricing is still $0 for output, so the invoice claim holds — the "no token generation at all" description does not match the payload.
6. **Latency is the one axis where the local model still wins**: 19–25 ms compute-only on local Apple silicon vs ~235 ms for a hosted call that includes network. If a decision is on a user's critical path and 200 ms matters, that is the trade.

## Caveats

- n = 20 and n = 16. One item moves accuracy 5–6 points; these are directional, not precise.
- Task 1 is a single task family (ISBN-10 validation) — a real code-judging workload is broader.
- The LLM baseline verdicts are reused from the recorded local run rather than re-called (same prompt, temperature 0).
- Jev is a hosted API: the decision leaves the machine. The local 322M model remains the only private option here.
- Pricing ($0.042 / 1M input tokens, output $0) is an **early-access rate card** and can change.

## Files

- `manifest.json` — parameters, pricing, per-arm metrics, provenance
- `jev_rows.json` — per-item audit trail (label, verdict, confidence, latency, tokens, cost)
- `jev_run_raw.log` — unedited run log
- `datasets/` — the exact items used (`judge_code.jsonl`, `guard.jsonl`)
- Harness: [`harness/jev_bench_2026_09_30.py`](../../harness/jev_bench_2026_09_30.py)
- Write-up: [`articles/2026-09-30-frontier-friday-decision-models.md`](../../articles/2026-09-30-frontier-friday-decision-models.md)
