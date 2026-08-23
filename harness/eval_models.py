#!/usr/bin/env python3
"""Model bake-off harness: run the SAME task on all models via OpenRouter."""
import json, os, time, urllib.request, sys

KEY = [l.split("=",1)[1].strip() for l in open(os.path.expanduser("~/.hermes/.env")) if l.startswith("OPENROUTER_API_KEY=")][0]
URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = [
    "deepseek/deepseek-v4-flash",
    "anthropic/claude-opus-4.8",
    "stealth/ox-alpha",
    "z-ai/glm-5.3",
]

TASK = """Complete this task. Return your answer EXACTLY in this format:

CODE:
```python
<your python code>
```
EXPLANATION:
<one paragraph>
EDGE_CASE:
<one sentence>

The task:
1. Write a Python function is_valid_isbn10(code: str) -> bool that validates an ISBN-10 string (allow hyphens), including the checksum: digits d1..d9 plus a check digit, weighted sum of d_i * (10-i) for i in 0..9 must be divisible by 11. The check digit may be 'X' (value 10) in the last position.
2. Explain in one paragraph how the checksum works and why it catches transposition errors.
3. List exactly one edge case most implementations get wrong and how your code handles it."""

def run(model):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": TASK}],
        "temperature": 0.3,
        "max_tokens": 1200,
    }).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    t0 = time.time()
    try:
        d = json.load(urllib.request.urlopen(req, timeout=300))
        elapsed = time.time() - t0
        msg = d["choices"][0]["message"]
        content = msg.get("content") or msg.get("reasoning") or ""
        usage = d.get("usage", {})
        return {"model": model, "ok": bool(content), "elapsed_s": round(elapsed, 1),
                "content": content, "usage": usage,
                "cost": usage.get("cost", 0)}
    except Exception as e:
        return {"model": model, "ok": False, "error": str(e), "elapsed_s": round(time.time() - t0, 1)}

def main():
    outdir = os.path.expanduser("~/ox-test/eval")
    os.makedirs(outdir, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    results = []
    for m in (MODELS if not only else [only]):
        print(f"▶ running {m} ...", flush=True)
        r = run(m)
        if r["ok"]:
            fn = os.path.join(outdir, m.replace("/", "__") + ".txt")
            with open(fn, "w") as f:
                f.write(r["content"])
            r["file"] = fn
            print(f"  ✓ {r['elapsed_s']}s | cost ${r['cost']:.6f} | tokens {r['usage'].get('total_tokens')}", flush=True)
        else:
            print(f"  ✗ {r['error'][:120]}", flush=True)
        results.append(r)
    with open(os.path.join(outdir, "manifest.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("\nDONE. outputs in", outdir)

if __name__ == "__main__":
    main()
