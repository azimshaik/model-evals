# Model Evals

A small, honest harness for comparing LLMs: the **same task** is run against multiple models through the **same API** (OpenRouter) with **identical parameters**, and every model's code output is **extracted and executed** against a test suite — scores come from real execution, not eyeballing.

## First run (2026-08-22): The Stealth Ox Bake-Off

`stealth/ox-alpha` — a free, anonymous model with a 1M-token context — vs. three references:

| Model | Tests | Latency | Cost | Format ✓ |
|---|---|---|---|---|
| **stealth/ox-alpha** | **9/9** | 30.1s | **$0.00** | ✅ |
| **anthropic/claude-opus-4.8** | 8/9 | **8.6s** | $0.016 | ✅ |
| **deepseek/deepseek-v4-flash** | 8/9 | 14.4s | $0.0001 | ✅ |
| **z-ai/glm-5.3** | 8/9 | 23.0s | $0.005 | ❌ |

Task: ISBN-10 validator (code + checksum explanation + edge case). 9-case test suite executed against each model's actual code. Total experiment cost: **$0.022**.

📄 Full write-up: [`articles/ox-alpha-bakeoff-article.md`](articles/ox-alpha-bakeoff-article.md)
📊 Raw outputs: [`results/2026-08-22-ox-alpha-bakeoff/`](results/2026-08-22-ox-alpha-bakeoff/)

## Second run (2026-09-19): Frontier Friday, local rig edition

The same task discipline moved onto one workstation: **five local models, one at a time, no cloud
API anywhere in the loop** (nothing cloud-generated, nothing cloud-judged). Task: build a
single-file home inventory web app. Every app was then opened in a real browser and driven —
demo data, add an item with real input events, search, reload — because static checks passed on all
five, including the one that doesn't actually save.

| Model | served on | decode tok/s | rig W | tok/s per W | app | works? |
|---|---|---|---|---|---|---|
| **Qwen3.5-35B-A3B** (MoE, ~3B active) | llama.cpp, 1 card | **90.7** | 187 | **0.485** | 24.5 KiB | ✅ |
| Qwen3-8B Q4_K_M | llama.cpp, 1 card | 81.8 | 185 | 0.442 | 14.5 KiB | ✅ |
| Qwen3.5-9B UD-Q4_K_XL | llama.cpp, 1 card | 73.1 | 187 | 0.391 | 21.3 KiB | ✅ |
| Qwen3.8-27B-NVFP4 (daily engine) | vLLM TP4, **4 cards** | 39.2 | 690 | 0.057 | 39.0 KiB | ✅ (richest UI) |
| Ternary Bonsai 2 27B PTQ1_0 | llama.cpp-prism, 1 card | 29.3 | 191 | 0.153 | 33.0 KiB | ❌ add-item broken |

A 35B MoE on **one** card built its app with 13× less energy than the 4-card dense 27B, at 1.8× the
decode speed. And with thinking enabled, the dense 27B spent two full budgets reasoning and emitted
**zero code** — reasoning transcripts for every attempt are in the run directory.

📄 Full write-up: [`articles/2026-09-19-frontier-friday-local.md`](articles/2026-09-19-frontier-friday-local.md)
📊 Raw outputs, apps, reasoning transcripts: [`results/2026-09-19-frontier-friday/`](results/2026-09-19-frontier-friday/)
🔧 Local harness (any OpenAI-compatible endpoint): [`harness/local/`](harness/local/)

## Repo layout

```
tasks/     — task prompts (one file per benchmark task)
harness/   — eval runner + verification scripts
harness/local/ — local-endpoint variant (vLLM / llama.cpp) + app checks + rig telemetry
results/   — dated runs: raw model outputs, manifest, summary
articles/  — write-ups of each run
```

## How to run

```bash
# 1. Set your OpenRouter key (models may cost money — check pricing first)
export OPENROUTER_API_KEY=sk-or-...

# 2. Run the harness (edit MODELS / TASK inside eval_models.py)
python3 harness/eval_models.py

# 3. Verify model-written code by executing it
python3 harness/verify_codes.py
```

Requires Python 3.10+ (stdlib only — no dependencies).

## Principles

1. **Same task, same API, same params** — the only variable is the model.
2. **Execute, don't admire** — model-written code gets run against real tests.
3. **Report cost + latency** — they're part of the result.
4. **No secrets in the repo** — keys come from the environment.
