#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_board_dashed_borders.py
Academic Battle Cards -- 2026-09-07

REPORTED: dashed lines around the two halves of the board, distracting and
serving no purpose.

CAUSE: .opp-side and .you-side each carry `border:1px dashed` from before the
arena art existed, when the two halves needed some edge to tell them apart:

    .opp-side{background:linear-gradient(...);border:1px dashed #b53a2c88}
    .you-side{background:linear-gradient(...);border:1px dashed #1f6a6a99}

fix_board_spread.py replaced their BACKGROUNDS with the continuous spread but
left the borders behind, so the dashes stayed -- drawing exactly the division
the spread was built to remove, including one straight across the middle where
the two worlds are supposed to meet.

The tinted gradients underneath go too. They were the old ownership cue; the
spread's own tint replaced them, and two washes stacked is one too many.

Ownership is now carried by the 3px hairline on each player's OUTER edge, which
fix_board_spread.py already sets and which this patch leaves alone.

Run from the repo root:

    python3 fix_board_dashed_borders.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

CSS = r"""
/* ===== no dashed division (fix_board_dashed_borders.py) =====
   .opp-side / .you-side kept `border:1px dashed` from before the arena art,
   plus a tinted gradient that the spread's own ownership wash replaced. Both
   drew a line where the two worlds are meant to meet. */
body[data-screen="play"] .board .side.opp-side,
body[data-screen="play"] .board .side.you-side{
  border:0 !important;
  background-image:none !important;
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
    if "fix_board_dashed_borders.py" in src or "no dashed division" in src:
        die("already applied. Ship a named fix_*.py to revise.")
    if "--opp-art" not in src:
        die("fix_board_spread.py must be applied first.")

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before, st_before = src.count("<script"), src.count("<style")

    tail = src.rindex("</style>")
    out = src[:tail] + CSS + src[tail:]

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before or out.count("<style") != st_before:
        die("block counts changed")

    # this must land after every dashed rule it cancels, or it does nothing
    mine = out.rindex("/* ===== no dashed division")
    for m in re.finditer(r"\.(opp|you)-side\{[^}]*dashed[^}]*\}", out):
        if m.start() > mine:
            die("a dashed border rule sits after the fix and would win.")

    # the ownership hairlines from the spread must survive
    for need in ("inset 0 3px 0 color-mix", "inset 0 -3px 0 color-mix"):
        if need not in out:
            die("the spread's ownership hairline is missing: %s" % need)

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  dashed side borders removed")
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    also dropped the old tinted gradients the spread replaced")
    print("    ownership hairlines on the outer edges are untouched")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
