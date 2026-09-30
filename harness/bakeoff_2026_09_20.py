#!/usr/bin/env python3
"""2026-09-20 bake-off: DeepSeek vs Meta (Llama 4 Scout / Muse Spark 1.3 Contributor).

Same task, identical params, outputs verified by EXECUTION against 9 known cases.
Usage: python3 bakeoff_2026_09_20.py [model_id ...]
"""
import json, os, re, sys, time, urllib.error, urllib.request

RUN = "2026-09-20-meta-vs-deepseek"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(ROOT, "results", RUN)
KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
if not KEY:
    sys.exit("OPENROUTER_API_KEY is not set — export it before running this harness.")
URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = ["deepseek/deepseek-v4-flash",
          "meta-llama/llama-4-scout",
          "meta/muse-spark-1.3-contributor"]

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

TESTS = [("0-306-40615-2", True), ("0306406152", True), ("0-8044-2957-X", True),
         ("0-306-40615-3", False), ("X123456789", False), ("12345678X9", False),
         ("0-306-4061", False), ("0-306-40615-2x", False), ("0-306-40615-2 ", True)]


def live_prices():
    req = urllib.request.Request("https://openrouter.ai/api/v1/models",
                                 headers={"Authorization": f"Bearer {KEY}"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    out = {}
    for m in d["data"]:
        p = m.get("pricing", {})
        try:
            out[m["id"]] = (float(p.get("prompt") or 0), float(p.get("completion") or 0))
        except (TypeError, ValueError):
            pass
    return out


def ask(model):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": TASK}],
                       "temperature": 0.3, "max_tokens": 4000}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    t0 = time.time()
    try:
        d = json.load(urllib.request.urlopen(req, timeout=600))
        msg = d["choices"][0]["message"]
        content = msg.get("content") or msg.get("reasoning") or ""
        return {"model": model, "ok": bool(content), "elapsed_s": round(time.time() - t0, 1),
                "content": content, "usage": d.get("usage", {})}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300]
        return {"model": model, "ok": False, "elapsed_s": round(time.time() - t0, 1),
                "error": f"HTTP {e.code}: {detail}"}
    except Exception as e:
        return {"model": model, "ok": False, "elapsed_s": round(time.time() - t0, 1),
                "error": f"{type(e).__name__}: {str(e)[:200]}"}


def verify(content):
    m = re.search(r"```python\n(.*?)```", content, re.S)
    if not m:
        return "NO CODE BLOCK"
    try:
        ns = {}
        exec(m.group(1), ns)
        fn = ns["is_valid_isbn10"]
        passed = sum(1 for inp, exp in TESTS if fn(inp) == exp)
        fails = [(i, exp) for i, exp in TESTS if fn(i) != exp]
        return f"{passed}/{len(TESTS)}" + (f" | fails: {fails[:3]}" if fails else " | ALL PASS")
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {str(e)[:80]}"


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    prices = live_prices()
    models = sys.argv[1:] or MODELS
    rows = []
    for m in models:
        print(f"▶ {m} ...", flush=True)
        r = ask(m)
        row = {"model": m, "elapsed_s": r["elapsed_s"]}
        if r["ok"]:
            p = os.path.join(OUTDIR, m.replace("/", "__") + ".txt")
            open(p, "w").write(r["content"])
            u = r["usage"] or {}
            pin, pout = prices.get(m, (0, 0))
            cost = (u.get("prompt_tokens", 0) or 0) * pin + (u.get("completion_tokens", 0) or 0) * pout
            row.update({"verified": verify(r["content"]), "in_tok": u.get("prompt_tokens"),
                        "out_tok": u.get("completion_tokens"),
                        "cost_usd": round(cost, 6), "file": p})
            print(f"  ✓ {row['elapsed_s']}s | {row['verified']} | {row['in_tok']}in/{row['out_tok']}out | ${row['cost_usd']}", flush=True)
        else:
            row.update({"verified": "BLOCKED", "note": r.get("error", "")[:160]})
            print(f"  ✗ {row['note'][:130]}", flush=True)
        rows.append(row)

    json.dump(rows, open(os.path.join(OUTDIR, "results.json"), "w"), indent=1)
    with open(os.path.join(OUTDIR, "results.md"), "w") as f:
        f.write(f"# Bake-off — Meta vs DeepSeek ({RUN})\n\n")
        f.write("Identical prompt, temperature 0.3, max_tokens 1200. Correctness verified by "
                "executing each output against 9 known cases (not judged by a model).\n\n")
        f.write("| Model | Verified | Latency | Tokens in/out | Cost |\n|---|---|---|---|---|\n")
        for r in rows:
            tok = f"{r.get('in_tok')}/{r.get('out_tok')}" if r.get("in_tok") else "—"
            cost = f"${r['cost_usd']:.6f}" if r.get("cost_usd") is not None else "—"
            f.write(f"| `{r['model']}` | {r['verified']} | {r['elapsed_s']}s | {tok} | {cost} |\n")
    print("\nresults ->", OUTDIR)


if __name__ == "__main__":
    main()
