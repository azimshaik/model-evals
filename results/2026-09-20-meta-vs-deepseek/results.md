# Bake-off — Meta vs DeepSeek (2026-09-20-meta-vs-deepseek)

Identical prompt, temperature 0.3, max_tokens 1200. Correctness verified by executing each output against 9 known cases (not judged by a model).

| Model | Verified | Latency | Tokens in/out | Cost |
|---|---|---|---|---|
| `deepseek/deepseek-v4-flash` | 8/9 | fails: [('0-306-40615-2 ', True)] | 31.9s | 174/2157 | $0.000342 |
| `meta-llama/llama-4-scout` | 8/9 | fails: [('0-306-40615-2 ', True)] | 28.3s | 176/514 | $0.000172 |
