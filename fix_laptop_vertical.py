#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_laptop_vertical.py
Academic Battle Cards -- 2026-09-08

REPORTED: on a 13" MacBook Air the board text is compressed to the point of
being hard to read.

CAUSE: every --card-h override is gated on pointer:coarse or on WIDTH --

    coarse + 761..1400px    -> 132px
    <=760px, or coarse      ->  74px
    coarse landscape, tall  -> 150px
    coarse landscape, short ->  84px

A 13" laptop is pointer:FINE at 1440x900, so none of them match and it falls
through to the BASE 150px, a value sized for a full desktop monitor. The hand
then takes roughly a quarter of the viewport:

    chrome + header      ~105px
    hand at 150px cards  ~232px
    phase bar + controls  ~96px
    board                ~467px   -> ~230px a side

fitBoard scales the board down to fit that, so the text is not merely small --
it is being shrunk by a transform, which is why it reads as compressed rather
than as small type.

This is the same fault as the landscape iPhone bug: a rule gated on width or
pointer when the real constraint is HEIGHT.

FIX: on fine pointers the card height follows the viewport --

    --card-h: clamp(86px, 13.5vh, 150px)

    1080p -> 146px   (unchanged in practice)
     900p -> 121px
     800p -> 108px
     700p ->  95px

No breakpoints to fall between, and a large monitor keeps today's sizing. The
hand's own padding and the side padding also tighten below 900px, which returns
roughly another 30px to the board. Together that is enough for fitBoard to stop
scaling on a 13" screen, so the text renders at its true size.

Run from the repo root:

    python3 fix_laptop_vertical.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

CSS = r"""
/* ===== laptop vertical budget (fix_laptop_vertical.py) =====
   Every --card-h rule was gated on pointer:coarse or on width, so a fine-pointer
   laptop fell through to the desktop-monitor base of 150px and the hand ate a
   quarter of a 900px viewport. The constraint is height, so the rule is too. */
@media (pointer:fine){
  body[data-screen="play"] .hand{
    --card-h:clamp(86px, 13.5vh, 150px);
    --fan-lift:clamp(12px, 2.4vh, 26px);
  }
}
/* below a full-height screen, give the board back the padding as well */
@media (pointer:fine) and (max-height:900px){
  body[data-screen="play"] .hand-wrap{padding:3px 10px 5px}
  body[data-screen="play"] .board .side{padding:5px}
  body[data-screen="play"] .side-meta{font-size:10px;padding:1px 4px}
}
@media (pointer:fine) and (max-height:780px){
  body[data-screen="play"] .hand-wrap{padding:2px 8px 4px}
  body[data-screen="play"] .board .side{padding:4px}
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
    if "fix_laptop_vertical.py" in src or "laptop vertical budget" in src:
        die("already applied. Ship a named fix_*.py to revise.")
    if "--card-h:150px" not in src:
        die("could not find the base card height -- has fix_hand_fan.py been applied?")

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before, st_before = src.count("<script"), src.count("<style")

    tail = src.rindex("</style>")
    out = src[:tail] + CSS + src[tail:]

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before or out.count("<style") != st_before:
        die("block counts changed")

    # the touch breakpoints are tuned; this patch must not reach them
    # slice from the comment's OPENING so the strip can match it, and strip
    # before checking -- the prose legitimately names pointer:coarse. This is
    # the sixth guard in this project to trip on its own explanation.
    # bound at </style>: an unbounded slice runs into the rest of the document,
    # which legitimately contains pointer:coarse elsewhere
    blk = out[out.rindex("/* ===== laptop vertical budget"):out.rindex("</style>")]
    blk = re.sub(r"/\*[\s\S]*?\*/", "", blk)
    rules = "\n".join(l for l in blk.split("\n") if not l.strip().startswith("*"))
    if "pointer:coarse" in rules:
        die("this patch must only affect fine pointers.")
    if blk.count("clamp(86px, 13.5vh, 150px)") != 1:
        die("the responsive card height is missing.")
    # and it must land after the base rule it overrides
    if out.rindex("laptop vertical budget") < out.rindex("--card-h:150px;"):
        die("the fix would be overridden by the base rule.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  laptop vertical budget fixed")
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    card height   clamp(86px, 13.5vh, 150px) on fine pointers")
    print("                  1080p 146px | 900p 121px | 800p 108px | 700p 95px")
    print("    padding       tightened below 900px and again below 780px")
    print("    touch breakpoints untouched")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
