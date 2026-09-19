#!/usr/bin/env python3
"""N parallel chat/completion requests against an OpenAI-compatible endpoint.
Reports aggregate throughput and per-request latency, sampling GPU telemetry.
Usage: bench_parallel.py <base_url> <label> [n_parallel] [max_tokens]"""
import collections, json, subprocess, sys, threading, time, urllib.error, urllib.request

BASE = sys.argv[1].rstrip("/")
LABEL = sys.argv[2]
NP = int(sys.argv[3]) if len(sys.argv) > 3 else 4
MAXTOK = int(sys.argv[4]) if len(sys.argv) > 4 else 400
Q = "index,temperature.gpu,power.draw,utilization.gpu,memory.used"

with urllib.request.urlopen(BASE + "/v1/models", timeout=10) as r:
    model = json.load(r)["data"][0]["id"]

PROMPT = ("Write a detailed technical explanation of PCIe link training, equalization and "
          "ASPM power states, with the trade-offs in a multi-GPU workstation.")

stop = threading.Event()
samples = []


def sampler():
    while not stop.is_set():
        r = subprocess.run(["nvidia-smi", f"--query-gpu={Q}", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True)
        for line in r.stdout.strip().splitlines():
            samples.append([x.strip() for x in line.split(",")])
        stop.wait(1.0)


def one(i, out):
    body = json.dumps({"model": model, "prompt": PROMPT, "max_tokens": MAXTOK}).encode()
    req = urllib.request.Request(BASE + "/v1/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            o = json.load(r)
        out[i] = (r.status, o.get("usage", {}).get("completion_tokens", 0), time.time() - t)
    except Exception as e:
        out[i] = ("ERR " + type(e).__name__, 0, time.time() - t)


th_s = threading.Thread(target=sampler); th_s.start()
t0 = time.time()
res = [None] * NP
threads = [threading.Thread(target=one, args=(i, res)) for i in range(NP)]
for t in threads:
    t.start()
for t in threads:
    t.join()
wall = time.time() - t0
stop.set(); th_s.join()

tot = sum(r[1] for r in res if r and isinstance(r[1], int))
print(f"[{LABEL}] {NP} parallel × {MAXTOK} tok | wall {wall:.1f}s | aggregate {tot/wall:.2f} tok/s "
      f"| {tot} tokens total")
for i, r in enumerate(res):
    if r:
        print(f"   req{i}: status {r[0]}, {r[1]} tok, {r[2]:.1f}s -> {r[1]/r[2]:.2f} tok/s")
per = collections.defaultdict(list)
for r in samples:
    per[r[0]].append(r)
tot_p = 0.0
for i in sorted(per):
    rs = per[i]
    P = [float(x[2]) for x in rs]; U = [float(x[3]) for x in rs]
    T = [float(x[1]) for x in rs]; M = [float(x[4]) for x in rs]
    tot_p += sum(P) / len(P)
    print(f"   GPU{i} Tmax {max(T):>3.0f}C Pavg {sum(P)/len(P):>6.1f}W utilavg "
          f"{sum(U)/len(U):>5.1f}% VRAM {max(M):>6.0f}MiB")
print(f"   TOTAL GPU Pavg {tot_p:.0f} W")
json.dump({"label": LABEL, "aggregate_tps": tot / wall, "wall_s": wall, "n_parallel": NP,
           "gpu_total_pavg_w": tot_p}, open(f"/tmp/benchpar-{LABEL}.json", "w"), indent=1)
