#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_crit_chip_layout.py
Academic Battle Cards -- 2026-09-04

REPORTED: in the Crit-Cards grid the magnifier (inspect) button is shoved to the
right, sometimes covered by neighbouring text or pushed out of the tile
entirely, so it cannot be clicked.

CAUSE: .bd-chip is `display:flex`, and its name element

    .bd-nm{font-family:var(--cond);letter-spacing:.5px;font-size:14px;font-weight:600}

has no `min-width`. A flex item's default `min-width:auto` means it refuses to
shrink below its content, so a long lens name -- "Postcolonial Lens",
"Psychoanalytic Lens", "Biographical Criticism", "Archetypal Lens" -- forces the
row wider than the tile. Everything after it in the flex line, which is exactly
the magnifier and the tick, gets pushed past the border.

The character chips already solve this: `.bd-chip.ch .bd-nm` sets
`white-space:normal; overflow-wrap:anywhere` and pins .bd-pv and .bd-mk
absolutely. The crit chips never got the same treatment, and the step-4 builder
made it visible by putting them in a four-column grid where the tiles are
narrower than the old single-column list.

FIX: give crit chips the same treatment the character chips already have --
a name that may wrap and shrink, and an inspect button pinned inside the tile
with room reserved for it.

Run from the repo root:

    python3 fix_crit_chip_layout.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

CSS = r"""
/* ===== crit chip layout (fix_crit_chip_layout.py) =====
   .bd-nm had no min-width, so in a flex row a long lens name refused to shrink
   and pushed the magnifier and the tick outside the tile. The character chips
   already handled this; the crit chips never did, and the four-column grid made
   it visible. */
.bd-chip.crt{padding-right:30px;align-items:flex-start}
.bd-chip.crt .bd-nm{
  min-width:0;flex:1 1 auto;
  white-space:normal;overflow-wrap:anywhere;
  font-size:12.5px;line-height:1.15;
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.bd-chip.crt .bd-cav{flex:0 0 auto}
/* pin the controls inside the tile, as the character chips do */
.bd-chip.crt .bd-pv{
  position:absolute;right:6px;bottom:5px;top:auto;
  font-size:13px;line-height:1;padding:2px;opacity:.65;
  width:20px;height:20px;display:grid;place-items:center;border-radius:5px}
.bd-chip.crt .bd-pv:hover{opacity:1;background:rgba(0,0,0,.08)}
.bd-chip.crt .bd-mk{position:absolute;top:5px;right:7px;font-size:14px;line-height:1}
/* the locked tiles carry a second line, so they need the room too */
.bd-chip.crt.lockcard .bd-nm{-webkit-line-clamp:4}
.bd-chip.crt .lk-hint{white-space:normal;overflow-wrap:anywhere}
@media (max-width:760px){
  .bd-chip.crt .bd-nm{font-size:11.5px;-webkit-line-clamp:2}
  .bd-chip.crt .bd-cav{width:26px;height:26px}
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
    if "fix_crit_chip_layout.py" in src or ".bd-chip.crt .bd-nm{" in src:
        die("already applied. Ship a named fix_*.py to revise.")
    if "bdk-wrap" not in src:
        die("fix_builder_ui.py must be applied first.")

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before, st_before = src.count("<script"), src.count("<style")

    tail = src.rindex("</style>")
    out = src[:tail] + CSS + src[tail:]

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before or out.count("<style") != st_before:
        die("block counts changed")
    if out == src:
        die("no change produced.")

    # the rules must land AFTER the generic .bd-nm they override
    blk = out.rindex("/* ===== crit chip layout")
    generic = out.rindex(".bd-nm{font-family:var(--cond)")
    if blk < generic:
        die("the fix would be overridden by the generic .bd-nm rule.")
    for need in (".bd-chip.crt .bd-nm{", "min-width:0", "position:absolute;right:6px;bottom:5px"):
        if need not in out[blk:]:
            die("missing rule: %s" % need)

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  crit chip layout fixed")
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    the lens name may now shrink and wrap (min-width:0)")
    print("    the inspect button is pinned inside the tile")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
