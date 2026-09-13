#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_ios_arena_mask.py
Academic Battle Cards -- 2026-09-08

REPORTED: on iPhone, after the board-spread update, the player's arena does not
appear at all -- the lower half is a flat wash of colour. The opponent's half
renders correctly.

CAUSE, and it is a regression I introduced. fix_board_spread.py masks each arena
layer so the two cross-fade:

    -webkit-mask-image:linear-gradient(0deg,#000 0%,#000 58%,rgba(0,0,0,0) 100%);

It sets mask-IMAGE but never mask-SIZE or mask-REPEAT. On desktop those default
harmlessly. WebKit on iOS does not: with no explicit size the gradient is laid
out at its intrinsic size and tiled, which on the bottom layer resolves to a
mask that is transparent across almost the whole element -- so the art is there
and masked away to nothing, leaving only the ownership tint. That is exactly
"only a faded colour".

The top layer survives because its gradient runs the other way, so the tiled
result happens to stay opaque over most of its area.

FIX: state the mask's size, repeat, position and origin explicitly, prefixed and
unprefixed. And add an @supports fallback: where masking is unavailable, each
layer simply keeps its art with a soft gradient edge instead of vanishing --
a missing cross-fade is a much smaller failure than a missing background.

Run from the repo root:

    python3 fix_ios_arena_mask.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

CSS = r"""
/* ===== iOS arena mask (fix_ios_arena_mask.py) =====
   The spread set mask-image but not mask-size or mask-repeat. WebKit on iOS
   then lays the gradient out at its intrinsic size and tiles it, which masked
   the player's arena away to nothing and left only the ownership tint. Desktop
   defaults hid the omission. State all of it. */
body[data-screen="play"] .board::before,
body[data-screen="play"] .board::after{
  -webkit-mask-size:100% 100%;  mask-size:100% 100%;
  -webkit-mask-repeat:no-repeat; mask-repeat:no-repeat;
  -webkit-mask-position:center;  mask-position:center;
  -webkit-mask-origin:border-box; mask-origin:border-box;
}
/* Where masking is not available at all, keep the art and lose only the
   cross-fade. A missing blend is a far smaller failure than a missing
   background. */
@supports not ((-webkit-mask-image: linear-gradient(#000,#000)) or (mask-image: linear-gradient(#000,#000))){
  body[data-screen="play"] .board::before{
    height:52%;
    -webkit-mask-image:none; mask-image:none;
    box-shadow:inset 0 -34px 30px -18px rgba(22,15,8,.92);
  }
  body[data-screen="play"] .board::after{
    height:52%;
    -webkit-mask-image:none; mask-image:none;
    box-shadow:inset 0 34px 30px -18px rgba(22,15,8,.92);
  }
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
    if "fix_ios_arena_mask.py" in src or "iOS arena mask" in src:
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

    blk = out[out.rindex("/* ===== iOS arena mask"):out.rindex("</style>")]
    rules = re.sub(r"/\*[\s\S]*?\*/", "", blk)
    for need in ("-webkit-mask-size:100% 100%", "mask-repeat:no-repeat",
                 "@supports not"):
        if need not in rules:
            die("missing rule: %s" % need)
    # it must land after the rules it completes
    if out.rindex("iOS arena mask") < out.rindex("-webkit-mask-image:linear-gradient(0deg"):
        die("the fix would be overridden by the spread's own mask rules.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  iOS arena mask fixed")
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    mask-size / repeat / position / origin now stated, both prefixes")
    print("    @supports fallback keeps the art where masking is unavailable")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
