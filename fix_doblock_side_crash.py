#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_doblock_side_crash.py
Academic Battle Cards -- regression fix (2026-09-03)

fix_floating_log.py added a flashLog call inside doBlock() using a variable that
does not exist there:

    flashLog(side==='you'?'opp':'you','blk', ...)

doBlock() destructures `const {A,att,def,D,dmg,dKey}=atkCtx` -- there is no
`side`. So every successful block threw

    ReferenceError: side is not defined
        at doBlock

which aborts the block mid-resolution: the damage is never applied, the log line
is never written, and the turn stalls.

`dKey` is the DEFENDER's side, i.e. exactly the side doing the blocking, so the
whole conditional was unnecessary -- flashLog already ignores anything that is
not the opponent.

WHY THE TESTS MISSED IT
The floating-log suite drove flashLog() directly and drove performAttack(), but
never resolved a BLOCK, so doBlock() was never entered. Asserting that a
function raises the right log line is not the same as asserting the function
runs. The suite now resolves a real block.

Found while verifying an unrelated patch, because that verification happened to
drive an attack into a charged blocker.

Run from the repo root:

    python3 fix_doblock_side_crash.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

OLD = """  flashLog(side==='you'?'opp':'you','blk',`${def.name} blocks with ${b.n} \\u2014 ${neg?'all damage negated':'-'+amt}.`);"""
NEW = """  /* dKey IS the blocking side -- doBlock has no `side` in scope, and reading one
     threw on every successful block. flashLog already filters to the opponent. */
  flashLog(dKey,'blk',`${def.name} blocks with ${b.n} \\u2014 ${neg?'all damage negated':'-'+amt}.`);"""


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    if "fix_doblock_side_crash.py" in src or "dKey IS the blocking side" in src:
        die("already applied. Ship a named fix_*.py to revise.")
    if "function flashLog(" not in src:
        die("fix_floating_log.py must be applied first.")

    if src.count(OLD) != 1:
        die("could not find the broken flashLog call exactly once.")

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    out = src.replace(OLD, NEW, 1)

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != src.count("<script"):
        die("script block count changed")

    # nothing in doBlock may reference a bare `side`
    i = out.index("function doBlock(")
    j = out.index("\nfunction ", i + 10)
    # strip comments first: the prose legitimately says "side" (this is the
    # third guard in this project to trip on its own explanation)
    body = re.sub(r"/\*[\s\S]*?\*/", "", out[i:j])
    body = re.sub(r"//[^\n]*", "", body)
    if re.search(r"(?<![.\w])side(?![\w:])", body):
        for ln in body.split("\n"):
            if re.search(r"(?<![.\w])side(?![\w:])", ln):
                sys.stderr.write("  still references `side`: %s\n" % ln.strip()[:110])
        die("doBlock still reads a variable it does not have.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  doBlock no longer throws on a successful block")
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
