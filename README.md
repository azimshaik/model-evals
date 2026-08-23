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

## Repo layout

```
tasks/     — task prompts (one file per benchmark task)
harness/   — eval runner + verification scripts
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
