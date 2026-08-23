#!/usr/bin/env python3
"""Execute each model's isbn10 implementation against a test suite."""
import re, sys, os

TESTS = [
    ("0-306-40615-2", True),    # classic valid
    ("0306406152", True),       # no hyphens
    ("0-8044-2957-X", True),    # X check digit
    ("0-306-40615-3", False),   # wrong check digit
    ("X123456789", False),      # misplaced X
    ("12345678X9", False),      # X not last
    ("0-306-4061", False),      # wrong length
    ("0-306-40615-2x", False),  # lowercase x extra
    ("0-306-40615-2 ", True),   # trailing space (after strip)
]

def extract_code(txt):
    m = re.search(r"```python\n(.*?)```", txt, re.S)
    return m.group(1) if m else None

def build(code):
    ns = {}
    exec(code, ns)
    return ns["is_valid_isbn10"]

results = {}
run_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "2026-08-22-ox-alpha-bakeoff")
for model in ["deepseek__deepseek-v4-flash", "anthropic__claude-opus-4.8",
              "stealth__ox-alpha", "z-ai__glm-5.3"]:
    path = os.path.join(run_dir, f"{model}.txt")
    txt = open(path).read()
    code = extract_code(txt)
    if not code:
        results[model] = "NO CODE FOUND"
        continue
    try:
        fn = build(code)
        passed = sum(1 for inp, exp in TESTS if fn(inp) == exp)
        fails = [(i, exp, fn(i)) for i, exp in TESTS if fn(i) != exp]
        results[model] = f"{passed}/{len(TESTS)} passed" + (f" | FAILS: {fails}" if fails else "")
    except Exception as e:
        results[model] = f"ERROR: {e}"

for m, r in results.items():
    print(f"{m:38} {r}")
