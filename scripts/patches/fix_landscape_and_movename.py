#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_landscape_and_movename.py
Academic Battle Cards -- 2026-08-29

Two fixes, both from phone screenshots.

--------------------------------------------------- 1. LANDSCAPE PHONE (mine)
fix_hand_fan.py added an iPad-landscape rule:

    @media (pointer:coarse) and (orientation:landscape) and (min-width:1000px){
      body[data-screen="play"] .hand{ --card-h:150px; ... }
    }

A landscape iPhone is also coarse, also landscape, and also wider than 1000px --
so it matched, and got 150px cards meant for a 10-inch iPad on a viewport barely
390px tall. The hand ate the screen, the board got the remainder, and fitBoard()
scaled what was left down to unreadable strips.

I gated on WIDTH when the constraint is HEIGHT. An iPad in landscape has ~800px
of height to spend; a phone has ~390. Same width, entirely different budget.

Now gated on `min-height:700px` as well, so tall landscape devices keep the big
cards and short ones fall back to phone sizing. A short-landscape branch is
added explicitly rather than left to inherit, because inheriting is what let the
iPad rule reach a phone in the first place.

------------------------------------------------ 2. MOVE NAMES TRUNCATE HARD
On the active card the move names ellipsed to nothing useful: "The T...",
"Norw...", "From ...", "Shield...". .pc-mn is `flex:1; min-width:0;
white-space:nowrap; text-overflow:ellipsis`, so the name gives up all its space
to the charge counter and the cost chip beside it, then clips.

The name may now wrap to two lines and the two chips beside it stop shrinking.
This is not device-specific -- it clips on desktop too, just less often.

Run from the repo root:

    python3 fix_landscape_and_movename.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

OLD_LS = """@media (pointer:coarse) and (orientation:landscape) and (min-width:1000px){
  body[data-screen="play"] .hand{
    --card-h:150px;--fan-step:4.5deg;--fan-arc:1.7px;
    --fan-lift:26px;--fan-scale:1.16;--tuck-frac:0.09;
  }"""

NEW_LS = """/* A landscape PHONE is coarse, landscape and >1000px wide, exactly like an
   iPad -- but it has roughly 390px of height instead of 800. Gating this on
   width alone sent iPad-sized cards to phones, where the hand ate the screen
   and the board was scaled down to strips. Height is the real constraint. */
@media (pointer:coarse) and (orientation:landscape) and (min-width:1000px) and (min-height:700px){
  body[data-screen="play"] .hand{
    --card-h:150px;--fan-step:4.5deg;--fan-arc:1.7px;
    --fan-lift:26px;--fan-scale:1.16;--tuck-frac:0.09;
  }"""

CSS = r"""
/* ===== landscape phone + move names (fix_landscape_and_movename.py) ===== */
/* Short landscape: phones held sideways. Declared rather than inherited --
   inheriting is how the iPad rule reached a phone to begin with. */
@media (pointer:coarse) and (orientation:landscape) and (max-height:699px){
  body[data-screen="play"] .hand{
    --card-h:84px;--fan-step:5deg;--fan-arc:1.6px;
    --fan-lift:16px;--fan-scale:1.5;--tuck-frac:0.14;
    padding:6px 4px 2px;
  }
  /* give the board back the height the hand was taking */
  body[data-screen="play"] .hand-wrap{padding:2px 8px 3px}
  body[data-screen="play"] .bench-mini{width:44px;height:32px}
  body[data-screen="play"] .pc-art{max-height:26vh}
}
/* The move name was flex:1 + min-width:0 + nowrap + ellipsis, so it surrendered
   all its width to the counter and the cost chip and then clipped to nothing:
   "The T...", "Norw...", "Shield...". Let it wrap; stop the chips shrinking. */
.pc-move .pc-mn{white-space:normal;overflow:visible;text-overflow:clip;
  line-height:1.08;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  overflow-wrap:anywhere}
.pc-move .pc-mc,.pc-move .pc-chip{flex:0 0 auto}
.pc-move{align-items:center;min-height:0}
@media (pointer:coarse) and (orientation:landscape) and (max-height:699px){
  .pc-move .pc-mn{-webkit-line-clamp:1;font-size:10.5px}
}
"""


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    if "fix_landscape_and_movename.py" in src or "(min-height:700px)" in src:
        die("already applied. Ship a named fix_*.py to revise.")
    if "--card-h:150px" not in src:
        die("fix_hand_fan.py must be applied first.")

    if src.count(OLD_LS) != 1:
        die("could not find the iPad landscape rule exactly once.")

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before, st_before = src.count("<script"), src.count("<style")

    out = src.replace(OLD_LS, NEW_LS, 1)
    tail = out.rindex("</style>")
    out = out[:tail] + CSS + out[tail:]

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before or out.count("<style") != st_before:
        die("block counts changed")
    if out == src:
        die("no change produced.")

    # the iPad rule must no longer be reachable by a short viewport
    m = re.search(r"@media \(pointer:coarse\) and \(orientation:landscape\) and "
                  r"\(min-width:1000px\)([^{]*)\{", out)
    if not m or "min-height" not in m.group(1):
        die("the iPad landscape rule is still gated on width alone.")
    if "(max-height:699px)" not in out:
        die("no short-landscape branch was added.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  landscape + move-name fixes applied")
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    landscape    iPad rule now needs min-height:700px")
    print("                 phones get an explicit short-landscape branch")
    print("    move names   wrap to two lines instead of clipping to 'The T...'")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
