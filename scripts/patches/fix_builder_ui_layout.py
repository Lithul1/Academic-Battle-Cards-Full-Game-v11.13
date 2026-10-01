#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_builder_ui_layout.py
Academic Battle Cards -- builder redesign, step 4 layout repair (2026-08-25)

Requires fix_builder_ui.py. Shipped separately because that patch is already
applied and refuses a second run.

--------------------------------------------------------------- THE OVERLAP --
`.builder{max-width:860px}` was right when the builder was one stacked column.
With a 430px deck rail beside it the pool is left with

    860 - 28 padding - 430 rail - 14 gap  =  388px

Five Anton tabs need roughly 700px, so `.bdk-tabs` -- a nowrap flex row --
overflowed by ~310px and painted over the Pagemaster column. Raising the tab
font for legibility is what tipped it past the edge.

Fixed three ways so it cannot recur:
  * the builder widens when it is in two-column mode
  * the tab strip wraps instead of overflowing
  * the tabs are trimmed slightly (14px -> 13px, tighter padding) while staying
    on Anton, which was the point of the font change

------------------------------------------------------------ THE DENSITY -----
Same root cause. At 388px the grids collapsed to one or two columns:

    characters  minmax(150px)  ->  2 columns
    trivia      minmax(230px)  ->  1 column
    bookmarks   minmax(240px)  ->  1 column   <- the tall scroll in the report

With the pool restored to ~1090px those become 6 / 4 / 4, which is the
multi-row, multi-column shape the concepts called for. The chips are also
tightened vertically so more fits per screen without shrinking the type.

The deck rail widens from 430 to 470 (215 -> 235 per column), because deck
entries were truncating mid-word: "ATK - Who is rumored to have ...".

Run from the repo root:

    python3 fix_builder_ui_layout.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

CSS = r"""
/* ===== builder redesign, step 4 layout repair (fix_builder_ui_layout.py) =====
   The 860px cap belonged to the single-column builder. Two columns need room:
   below it the tab strip overflowed onto the deck rail and every grid collapsed
   to one or two columns. */
.builder.bdk{max-width:min(1560px,97vw)}
/* a tab strip must never be able to overflow onto its neighbour again */
.bdk-tabs{flex-wrap:wrap;row-gap:3px}
.bdk-tab{font-size:13px;padding:6px 12px;letter-spacing:.9px}
/* the rail: 235px a column, so entries stop truncating mid-word */
.bdk-cols{flex:0 0 470px}

/* ---- density: more per screen, same type size ---- */
.bdk .bd-grid.ch{grid-template-columns:repeat(auto-fill,minmax(178px,1fr));gap:6px}
.bdk .bd-grid.ab{grid-template-columns:repeat(auto-fill,minmax(226px,1fr));gap:6px}
.bdk .bd-bmgrid{grid-template-columns:repeat(auto-fill,minmax(238px,1fr));gap:6px}
.bdk .bd-chip{padding:5px 7px}
.bdk .bd-chip.ab{min-height:0}
.bdk .bd-bm{padding:6px 8px}
.bdk .bd-sec{margin-bottom:10px}
.bdk .bd-sec h3{margin:0 0 6px}
/* the pool scrolls inside itself rather than driving the whole page */
.bdk .bd-sec .bd-grid,.bdk .bd-sec .bd-bmgrid{max-height:62vh;overflow-y:auto;padding-right:4px}

/* ---- narrower desktops: shed the rail width before shedding columns ---- */
@media (max-width:1400px){
  .bdk-cols{flex:0 0 420px}
  .bdk .bd-grid.ch{grid-template-columns:repeat(auto-fill,minmax(164px,1fr))}
  .bdk .bd-grid.ab{grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}
  .bdk .bd-bmgrid{grid-template-columns:repeat(auto-fill,minmax(222px,1fr))}
}
/* ---- tablet and below: the rail drops under the pool (already in step 4),
        so the grids get the full width back ---- */
@media (max-width:1100px){
  .bdk-cols{flex:none;width:100%}
  .bdk .bd-sec .bd-grid,.bdk .bd-sec .bd-bmgrid{max-height:none;overflow:visible}
  .bdk-items{max-height:38vh}
}
@media (max-width:760px){
  .bdk-tab{font-size:12px;padding:5px 9px;letter-spacing:.6px}
  .bdk-cols{flex-direction:column}
  .bdk .bd-grid.ch{grid-template-columns:repeat(auto-fill,minmax(140px,1fr))}
  .bdk .bd-grid.ab{grid-template-columns:repeat(auto-fill,minmax(180px,1fr))}
  .bdk .bd-bmgrid{grid-template-columns:1fr}
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
    if "bdk-wrap" not in src:
        die("fix_builder_ui.py (step 4) must be applied first.")
    if "fix_builder_ui_layout.py" in src or ".builder.bdk{max-width" in src:
        die("already applied. Ship a named fix_*.py to revise.")

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before = src.count("<script")
    st_before = src.count("<style")

    tail = src.rindex("</style>")
    out = src[:tail] + CSS + src[tail:]

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before or out.count("<style") != st_before:
        die("block counts changed")
    if out == src:
        die("no change produced.")

    # the fix is inert unless it lands after the step-4 rules it overrides
    base = ".bdk-cols{flex:0 0 430px;display:flex;gap:10px}"
    if base not in out:
        die("could not find the step-4 rail rule to override.")
    if out.index(".builder.bdk{max-width") < out.rindex(base):
        die("the layout rules would be overridden by step 4 -- wrong order.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  layout repair applied")
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    builder      860px -> min(1560px, 97vw) in two-column mode")
    print("    tabs         wrap; 14px -> 13px, still Anton")
    print("    grids        ch 2->6 cols, ab 1->4, bookmarks 1->4 at 1560px")
    print("    rail         430 -> 470px (235 a column)")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
