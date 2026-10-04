#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_attach_refusal_render.py
Academic Battle Cards -- 2026-09-03

REPORTED: with the Structuralism lens, charging out of Power order leaves the
trivia question stuck on screen.

DIAGNOSED: the game state is fine. answerTrivia() clears S.pending and busy,
then hands off to attach() -- and has no render() of its own, relying on attach
to repaint. Structuralism's ascending-order guard returns early:

    if((card.power||0)<lastPow){ if(side==='you') toast(...); return; }

so nothing repaints and the modal from the previous render stays on screen. It
clears the moment anything else triggers a render, which is why it looks like a
message that "sticks" rather than a hang.

Reproduced: S.pending false, busy false, toast raised, trivia modal still in the
DOM; a manual render() removes it.

THE GENERAL FAULT, not the specific one: attach() has SEVEN early returns and
answerTrivia() renders after none of them. Structuralism is simply the one whose
guard players hit most. Every refusal path has the same defect, and any new one
will inherit it.

Fixed by rendering at the point of refusal rather than at each return: the
Structuralism guard repaints, and answerTrivia repaints unconditionally after
attach() hands back, so no future early return can strand the modal again.

Run from the repo root:

    python3 fix_attach_refusal_render.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

PATCHES.append((
    "structuralism-repaint",
    """    if((card.power||0)<lastPow){ if(side==='you') toast('Structuralism: charge in ascending Power order.'); return; }""",
    """    if((card.power||0)<lastPow){
      if(side==='you') toast('Structuralism: charge in ascending Power order.');
      /* the trivia panel is still on screen from the last paint; answerTrivia
         cleared S.pending and handed off to us, so if we return without
         repainting the question stays up. */
      try{ render(); }catch(e){}
      return; }""",
))

PATCHES.append((
    "answertrivia-repaint",
    """  attach('you',pend.handIdx,correct,pend.target);
}""",
    """  attach('you',pend.handIdx,correct,pend.target);
  /* attach() has several early returns and repaints on only some of them.
     S.pending is already null here, so a repaint is always correct and is the
     only thing that guarantees the trivia panel comes down -- whatever new
     refusal path someone adds to attach() later. */
  try{ render(); }catch(e){}
}""",
))


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    if "fix_attach_refusal_render.py" in src or "whatever new\n     refusal path" in src:
        die("already applied. Ship a named fix_*.py to revise.")

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-24s found %d times, expected 1" % (label, n))
    if problems:
        die("anchor check failed -- nothing written:\n" + "\n".join(problems))

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before = src.count("<script")

    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before:
        die("script block count changed")
    if out == src:
        die("no change produced.")

    # answerTrivia must repaint after handing off
    i = out.index("function answerTrivia")
    j = out.index("\n/* ================= RENDERING", i)
    if "attach('you',pend.handIdx,correct,pend.target);" not in out[i:j]:
        die("answerTrivia no longer hands off to attach as expected.")
    if out[i:j].rindex("render()") < out[i:j].rindex("attach('you'"):
        die("answerTrivia does not repaint after attach().")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    structuralism refusal now repaints")
    print("    answerTrivia repaints unconditionally after attach()")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
