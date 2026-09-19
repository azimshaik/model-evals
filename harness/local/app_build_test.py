#!/usr/bin/env python3
"""Ask a locally served model to build the same single-file web app, capture the
generated code, the raw output, generation metrics and GPU telemetry.

No cloud APIs: talks only to the local OpenAI-compatible endpoint you point it at.

Usage:
  app_build_test.py --label <name> --base-url http://127.0.0.1:8000 --model <model-id> \
      [--max-tokens 8192] [--prompt-file PROMPT.txt] [--outdir DIR] [--timeout 1800]
"""
import argparse, csv, json, os, re, subprocess, sys, threading, time, urllib.error, urllib.request

OUT_ROOT = os.path.expanduser("~/models/sweep/app-build")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--label", required=True)
    p.add_argument("--base-url", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--max-tokens", type=int, default=8192)
    p.add_argument("--prompt-file", default=f"{OUT_ROOT}/PROMPT.txt")
    p.add_argument("--outdir", default=OUT_ROOT)
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--chat", action="store_true", help="use /v1/chat/completions instead of /v1/completions")
    p.add_argument("--no-think", action="store_true", help="send chat_template_kwargs enable_thinking=false")
    p.add_argument("--usage", action="store_true", help="request stream_options include_usage (vLLM)")
    return p.parse_args()


def sample_gpus(stop, rows):
    q = "index,temperature.gpu,power.draw,fan.speed,memory.used"
    while not stop.is_set():
        r = subprocess.run(["nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True)
        for line in r.stdout.strip().splitlines():
            rows.append([x.strip() for x in line.split(",")])
        stop.wait(2.0)


def extract_html(text):
    m = re.search(r"```(?:html)?\s*(.*?)```", text, re.S | re.I)
    body = m.group(1) if m else text
    i = body.lower().find("<!doctype")
    if i < 0:
        i = body.lower().find("<html")
    j = body.lower().rfind("</html>")
    if i >= 0 and j > i:
        return body[i:j + 7].strip()
    return body.strip()


def main():
    a = parse_args()
    d = os.path.join(a.outdir, a.label)
    os.makedirs(d, exist_ok=True)
    prompt = open(a.prompt_file).read()

    path = "/v1/chat/completions" if a.chat else "/v1/completions"
    if a.chat:
        body = {"model": a.model, "messages": [{"role": "user", "content": prompt}],
                "max_tokens": a.max_tokens, "temperature": a.temperature, "stream": True}
        if a.no_think:
            body["chat_template_kwargs"] = {"enable_thinking": False}
        if a.usage:
            body["stream_options"] = {"include_usage": True}
    else:
        body = {"model": a.model, "prompt": prompt, "max_tokens": a.max_tokens,
                "temperature": a.temperature, "stream": True}
        if a.no_think:
            body["chat_template_kwargs"] = {"enable_thinking": False}

    req = urllib.request.Request(a.base_url.rstrip("/") + path,
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    rows = []
    stop = threading.Event()
    th = threading.Thread(target=sample_gpus, args=(stop, rows), daemon=True)
    th.start()

    t0 = time.time()
    ttft = None
    pieces, think_pieces, usage, finish = [], [], {}, None
    try:
        with urllib.request.urlopen(req, timeout=a.timeout) as r:
            for raw in r:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    obj = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if obj.get("usage"):
                    usage = obj["usage"]
                ch = (obj.get("choices") or [{}])[0]
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
                delta = ch.get("delta") or ch.get("text") or ""
                reason = ""
                if isinstance(delta, dict):
                    reason = delta.get("reasoning_content") or delta.get("reasoning") or ""
                    delta = delta.get("content") or ""
                if reason:
                    if ttft is None:
                        ttft = time.time() - t0
                    think_pieces.append(reason)
                if delta:
                    if ttft is None:
                        ttft = time.time() - t0
                    pieces.append(delta)
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")[:500]
        print(f"[{a.label}] HTTP {e.code}: {err}")
        json.dump({"label": a.label, "error": f"HTTP {e.code}", "detail": err},
                  open(os.path.join(d, "metrics.json"), "w"), indent=1)
        stop.set(); th.join()
        return 2
    except Exception as e:
        print(f"[{a.label}] FAILED: {type(e).__name__} {e}")
        json.dump({"label": a.label, "error": f"{type(e).__name__}: {e}"},
                  open(os.path.join(d, "metrics.json"), "w"), indent=1)
        stop.set(); th.join()
        return 2

    wall = time.time() - t0
    stop.set(); th.join()
    text = "".join(pieces)
    thinking = "".join(think_pieces)
    open(os.path.join(d, "raw.txt"), "w").write(text)
    if thinking:
        open(os.path.join(d, "reasoning.txt"), "w").write(thinking)
    html = extract_html(text)
    open(os.path.join(d, "index.html"), "w").write(html)

    with open(os.path.join(d, "telem.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow("index,temperature.gpu,power.draw,fan.speed,memory.used".split(","))
        w.writerows(rows)

    ct = (usage or {}).get("completion_tokens") or 0
    pt = (usage or {}).get("prompt_tokens") or 0
    ct_estimated = False
    if not ct and text:
        ct = max(1, round(len(text) / 4))
        ct_estimated = True
    decode = (ct / (wall - ttft)) if (ct and ttft and wall > ttft) else (ct / wall if ct else 0)
    per = {}
    for r in rows:
        per.setdefault(r[0], []).append(r)
    gpu = {}
    for i, rs in per.items():
        T = [float(x[1]) for x in rs]; P = [float(x[2]) for x in rs]; F = [float(x[3]) for x in rs]
        gpu[i] = {"tmax": max(T), "tavg": round(sum(T) / len(T), 1),
                  "pmax": max(P), "pavg": round(sum(P) / len(P), 1), "fanmax": max(F)}
    metrics = {"label": a.label, "model": a.model, "endpoint": a.base_url, "path": path,
               "prompt_tokens": pt, "completion_tokens": ct, "tokens_estimated": ct_estimated,
               "reasoning_chars": len(thinking), "content_chars": len(text),
               "ttft_s": round(ttft, 2) if ttft else None,
               "wall_s": round(wall, 1), "decode_tok_s": round(decode, 2),
               "finish_reason": finish, "raw_chars": len(text), "html_chars": len(html),
               "html_bytes": os.path.getsize(os.path.join(d, "index.html")),
               "html_complete": bool(html.rstrip().lower().endswith("</html>")),
               "gpu_total_pavg_w": round(sum(g["pavg"] for g in gpu.values()), 0),
               "gpus": gpu, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
    json.dump(metrics, open(os.path.join(d, "metrics.json"), "w"), indent=1)
    with open(os.path.join(a.outdir, "RESULTS.jsonl"), "a") as fh:
        fh.write(json.dumps(metrics) + "\n")
    print(f"[{a.label}] {ct} tok in {wall:.0f}s | TTFT {metrics['ttft_s']}s | decode {metrics['decode_tok_s']} tok/s "
          f"| html {metrics['html_bytes']/1024:.1f} KiB complete={metrics['html_complete']} | "
          f"finish={finish} | GPU watts avg {metrics['gpu_total_pavg_w']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
