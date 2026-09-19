#!/usr/bin/env python3
"""Benchmark any OpenAI-compatible endpoint with GPU telemetry sampled during the run.
Usage: bench_api.py <base_url> <label> [n_runs] [max_tokens] [prompt_tokens]"""
import collections, json, subprocess, sys, threading, time, urllib.error, urllib.request

BASE = sys.argv[1].rstrip("/")
LABEL = sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 3
MAXTOK = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
PTARGET = int(sys.argv[5]) if len(sys.argv) > 5 else 45   # ~45 tokens ≈ same prompt as the vLLM runs
Q = "index,temperature.gpu,power.draw,clocks.current.sm,utilization.gpu,memory.used"

def post(path, obj, timeout=900):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

MODELS = ("Write a long, detailed technical explanation of how PCIe link training, "
          "equalization, and ASPM power states work, including the trade-offs in a "
          "multi-GPU workstation. Be thorough and continue.")

st, m = post("/v1/models", {}) if False else (0, None)
try:
    with urllib.request.urlopen(BASE + "/v1/models", timeout=10) as r:
        mids = [x["id"] for x in json.load(r)["data"]]
except Exception as e:
    mids = []
model = mids[0] if mids else "local"
print(f"[{LABEL}] endpoint {BASE} model={model} runs={N} max_tokens={MAXTOK}")

# prompt sized to PTARGET tokens (repeat text; ~0.75 words/token)
words = ("The quick brown fox jumps over the lazy dog while PCIe equalization settles ".split())
prompt = " ".join(words * max(1, PTARGET // len(words) // 2))
prompt = prompt[: PTARGET * 4]

stop = threading.Event()
samples = []

def sampler():
    while not stop.is_set():
        r = subprocess.run(["nvidia-smi", f"--query-gpu={Q}", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True)
        for line in r.stdout.strip().splitlines():
            samples.append([x.strip() for x in line.split(",")])
        stop.wait(1.0)

th = threading.Thread(target=sampler)
th.start()
tps, ttfts, pre_speeds = [], [], []
for i in range(N):
    body = {"model": model, "prompt": prompt, "max_tokens": MAXTOK, "temperature": 0.7}
    t = time.time()
    st, out = post("/v1/completions", body)
    dt = time.time() - t
    if st != 200:
        print(f"  run{i+1}: HTTP {st} {out}")
        continue
    u = out.get("usage", {})
    ct = u.get("completion_tokens", 0)
    t_ = out.get("timings") or {}
    dec = t_.get("predicted_per_second") or (ct / dt if ct else 0)
    ttft = (t_.get("prompt_ms") or 0) / 1000 or (t_.get("ttft_ms") or 0) / 1000
    ptoks = u.get("prompt_tokens")
    if ttft and ptoks:
        pre_speeds.append(ptoks / ttft)
    tps.append(dec)
    ttfts.append(ttft)
    print(f"  run{i+1}: {ct} tok in {dt:.1f}s wall | decode {dec:.2f} tok/s | "
          f"prompt {ptoks} tok, prefill {'%.0f' % (ptoks/ttft) if ttft else '?'} tok/s, TTFT {ttft:.2f}s")
stop.set()
th.join()

per = collections.defaultdict(list)
for r in samples:
    per[r[0]].append(r)
print(f"=== {LABEL}: decode {'%.2f' % (sum(tps)/len(tps)) if tps else 'n/a'} tok/s "
      f"(n={len(tps)}) | TTFT {'%.2f' % (sum(ttfts)/len(ttfts)) if ttfts else '?'}s "
      f"| prefill {'%.0f' % (sum(pre_speeds)/len(pre_speeds)) if pre_speeds else '?'} tok/s")
tot = 0.0
for i in sorted(per):
    rs = per[i]
    T = [float(x[1]) for x in rs]; P = [float(x[2]) for x in rs]
    S = [float(x[3]) for x in rs]; M = [float(x[5]) for x in rs]
    tot += sum(P) / len(P)
    print(f"  GPU{i} Tmax {max(T):>3.0f}C Tavg {sum(T)/len(T):>5.1f}C Pmax {max(P):>6.1f}W "
          f"Pavg {sum(P)/len(P):>6.1f}W SMavg {sum(S)/len(S):>5.0f}MHz VRAMmax {max(M):>6.0f}MiB "
          f"samples {len(rs)}")
print(f"  TOTAL GPU Pavg {tot:.0f} W")
json.dump({"label": LABEL, "decode_tps": sum(tps)/len(tps) if tps else None,
           "ttft_s": sum(ttfts)/len(ttfts) if ttfts else None,
           "prefill_tps": sum(pre_speeds)/len(pre_speeds) if pre_speeds else None,
           "gpu_total_pavg_w": tot,
           "tmax": {i: max(float(x[1]) for x in per[i]) for i in per}},
          open(f"/tmp/benchres-{LABEL}.json", "w"), indent=1)
