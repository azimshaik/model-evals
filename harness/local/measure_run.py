#!/usr/bin/env python3
"""Sustained decode load + telemetry: N x max_tokens generations, sampled during load.
Usage: measure_run.py <cap_label> [n_runs] [max_tokens]"""
import collections, csv, json, os, subprocess, sys, threading, time, urllib.request

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
URL = BASE + "/v1/completions"
MODEL = os.environ.get("MODEL_ID", "qwen27b-int4-fp16kv-256K-mtp3-text-only-cu128")
PROMPT = ("Write a long, detailed technical explanation of how PCIe link training, "
          "equalization, and ASPM power states work, including the trade-offs in a "
          "multi-GPU workstation. Be thorough.")
Q = "index,temperature.gpu,power.draw,clocks.current.sm,utilization.gpu,fan.speed,power.limit"

label = sys.argv[1] if len(sys.argv) > 1 else "run"
n_runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
max_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 1000


def gen(mt):
    body = json.dumps({"model": MODEL, "prompt": PROMPT, "max_tokens": mt}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        out = json.load(r)
    return time.time() - t, out["usage"]["completion_tokens"]


stop = threading.Event()
rows = []


def sampler():
    while not stop.is_set():
        r = subprocess.run(["nvidia-smi", f"--query-gpu={Q}", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True)
        for line in r.stdout.strip().splitlines():
            rows.append([x.strip() for x in line.split(",")])
        stop.wait(1.0)


gen(150)  # warmup
th = threading.Thread(target=sampler); th.start()
tps = []
for i in range(n_runs):
    dt, ct = gen(max_tokens)
    tps.append(ct / dt)
    print(f"  run{i+1}: {ct} tok / {dt:.1f}s = {ct/dt:.2f} tok/s")
stop.set(); th.join()

per = collections.defaultdict(list)
for r in rows:
    per[r[0]].append(r)
print(f"=== {label}: mean {sum(tps)/len(tps):.2f} tok/s over {n_runs} runs, "
      f"{len(rows)//4} samples/GPU")
tot = 0.0
for i in sorted(per):
    rs = per[i]
    T = [float(x[1]) for x in rs]; P = [float(x[2]) for x in rs]
    S = [float(x[3]) for x in rs]; F = [float(x[5]) for x in rs]; L = [float(x[6]) for x in rs]
    tot += sum(P) / len(P)
    print(f"  GPU{i} Tmax {max(T):>4.0f}C Tavg {sum(T)/len(T):>5.1f}C "
          f"s>=75C {sum(1 for x in T if x >= 75):>3} Pmax {max(P):>6.1f}W Pavg {sum(P)/len(P):>6.1f}W "
          f"SMavg {sum(S)/len(S):>5.0f}MHz Fanmax {max(F):>3.0f}% limit={set(L)}")
print(f"  TOTAL GPU Pavg {tot:.0f} W")
with open(f"/tmp/rigdiag-{label}.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(Q.split(",")); w.writerows(rows)
