#!/usr/bin/env python3
"""Refresh stale README sections + one build.py comment. Docs only; build output unchanged.
Run once from the repo root: python3 fix_readme.py  (then delete this file)."""
import sys
MARK = "<!-- fix_readme applied -->"
WC0, WC1 = "## Working with Claude (token-saving)\n", "## Deploy (GitHub Pages)\n"
PROV = ("`src` + `assets.json` in this commit rebuild **demo_11_13** exactly:\n"
        "`sha256 = 9965f0747feda783fb6a3504b75d119b4fbaa94062dbe6337df5f367135e9ae2`\n")
NEW_WC = """## Working with Claude

Claude validates game logic on the stub build and never needs `assets.json` (~14 MB).
With this folder connected in the Claude desktop app, Claude reads the repo directly,
tests on a scratch copy, and hands back small `fix_*.py` scripts plus the exact
terminal commands to run. You review, run, commit and push (GitHub Desktop).
Your local `python3 build.py` remains the check on final asset integrity.

"""
NEW_PROV = ("`build.py` is deterministic: the same `src` + `assets.json` always give the same\n"
            "file. It prints the output's sha256 -- paste that line into the release commit\n"
            "message to record exactly what shipped.\n")

r, b = open("README.md", encoding="utf-8").read(), open("build.py", encoding="utf-8").read()
if MARK in r: sys.exit("already applied")
for name, s, a in (("README Working with Claude", r, WC0), ("README Deploy", r, WC1),
                   ("README Provenance", r, PROV), ("build.py comment", b, "the 4.7MB bundle")):
    if s.count(a) != 1: sys.exit(f"ABORT: anchor not found exactly once: {name}")
r = r[:r.index(WC0)] + NEW_WC + r[r.index(WC1):]
r = r.replace(PROV, NEW_PROV).rstrip("\n") + "\n\n" + MARK + "\n"
b = b.replace("the 4.7MB bundle", "the ~14 MB bundle")
for p, t in (("README.md", r), ("build.py", b)):
    open(p + ".bak", "w", encoding="utf-8").write(open(p, encoding="utf-8").read())
    open(p, "w", encoding="utf-8").write(t)
print("README.md and build.py updated (.bak copies written, git-ignored)")
