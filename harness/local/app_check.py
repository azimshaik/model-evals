#!/usr/bin/env python3
"""Objective checks on a generated single-file app. No LLM judgement involved.

Usage: app_check.py <dir-with-index.html> [more dirs...]
Writes check.json into each dir and prints a one-line summary.
"""
import json, os, re, subprocess, sys

CHECKS = {
    "doctype":            r"<!doctype html",
    "closes_html":        r"</html>\s*$",
    "localStorage":       r"localStorage",
    "add_item":           r"(add|create).{0,20}(item|new)|form\.submit|addEventListener\(\s*['\"]submit",
    "edit":               r"edit",
    "delete":             r"delete|remove",
    "search":             r"search|filter",
    "category_filter":    r"category",
    "rooms":              r"room",
    "quantity":           r"quantity|qty",
    "low_stock":          r"low.?stock|<=?\s*2|quantity\s*<\s*3",
    "export_json":        r"export|download|blob",
    "import_json":        r"import|fileReader|input type=[\"']file",
    "demo_data":          r"demo|sample data|seed",
    "responsive":         r"@media|viewport",
    "no_external_cdn":    r"^(?!.*(cdn\.|unpkg|jsdelivr|https?://[^\"']*\.js)).*$",
}


def check_dir(d):
    p = os.path.join(d, "index.html")
    if not os.path.exists(p):
        return {"dir": d, "error": "no index.html"}
    html = open(p, encoding="utf-8", errors="replace").read()
    low = html.lower()
    res = {"dir": os.path.basename(d), "bytes": len(html.encode()),
           "html_complete": bool(re.search(r"</html>\s*$", low, re.I)),
           "n_script_blocks": low.count("<script"), "n_style_blocks": low.count("<style"),
           "n_inputs": low.count("<input"), "n_buttons": low.count("<button"),
           "n_functions": len(re.findall(r"\bfunction\s+\w+|\w+\s*=>\s*\{", html)),
           "n_lines": html.count("\n") + 1,
           "external_refs": re.findall(r"""(?:src|href)\s*=\s*["'](https?://[^"']+)["']""", html)}
    for name, pat in CHECKS.items():
        if name in ("doctype", "closes_html"):
            continue
        res[name] = bool(re.search(pat, html, re.I | re.S))
    res["doctype"] = bool(re.search(r"<!doctype html", low))
    # JS syntax check on every inline script block, with node if available
    node = os.path.expanduser("~/.local/bin/node")
    blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S | re.I)
    js = "\n;\n".join(b for b in blocks if b.strip())
    res["js_chars"] = len(js)
    res["js_syntax_ok"] = None
    if js.strip() and os.path.exists(node):
        tmp = "/tmp/_appcheck.js"
        # strip top-level DOM-guarded code? keep as-is; node --check only parses
        open(tmp, "w").write(js)
        r = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
        res["js_syntax_ok"] = (r.returncode == 0)
        if r.returncode != 0:
            res["js_syntax_error"] = (r.stderr or "").strip().splitlines()[:4]
    json.dump(res, open(os.path.join(d, "check.json"), "w"), indent=1)
    got = [k for k, v in res.items() if v is True]
    missing = [k for k, v in res.items() if v is False]
    print(f"{res['dir']:26s} {res['bytes']/1024:7.1f} KiB complete={res['html_complete']} "
          f"js_ok={res['js_syntax_ok']} scripts={res['n_script_blocks']} inputs={res['n_inputs']} "
          f"buttons={res['n_buttons']} feats={len(got)} missing={','.join(missing) or '-'}")
    return res


if __name__ == "__main__":
    roots = sys.argv[1:]
    for d in roots:
        if os.path.isdir(d):
            check_dir(d)
