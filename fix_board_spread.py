#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_board_spread.py
Academic Battle Cards -- board background (2026-09-07)

The two arenas become one continuous spread instead of two boxed panels.

  was: each .side carried its own arena, rounded and inset, with a gap between
       them -- the halves read as separate photographs
  now: each arena is a layer on .board, 62% tall so the two overlap through the
       middle 24%, each masked to fade as it approaches the centre. They
       cross-fade into one another: the worlds meet rather than abut.

No dividing line, no crease, no boxing.

--------------------------------------------------------------- WHY LAYERS ---
An earlier attempt put both images in .board's own background at
`background-size:100% 50%` and passed each deck's focal point as the POSITION.
A focal point is not a placement: at half height the position decides which half
the image occupies, so the two overlapped and only one survived -- and 100% 50%
stretched the art besides. Absolutely-positioned layers with
`background-size:cover` keep every deck's existing crop (center 55%, center 62%,
center 66%) and place cleanly.

------------------------------------------------------------ OWNERSHIP TINT ---
With the art continuous, "whose half is this" needs restating. Each deck gets a
wash in its own signature colour, sampled from that deck's arena art -- hue
bucketed and weighted by saturation x value, so it is the colour the picture
reads as rather than its shadows, which average to grey. The wash is strongest
at the player's outer edge and gone by 82% of their half, so it never draws a
line where the worlds meet. A 3px hairline sits on each player's OUTER edge only.

Six decks share three arenas, so macbeth/othello and tewwg/romeojuliet/odyssey
share a tint. Twelve hand-picked deck accents would separate them; that is a
palette decision and is not part of this patch.

--------------------------------------------------------------- LAYER ORDER ---
Everything the spread adds sits at z-index 0 and the cards are raised to 1. An
earlier version put the fold at z-index 4 and painted it over every play asset.
The guard below refuses to write if anything in the block sits above the cards.

Run from the repo root:

    python3 fix_board_spread.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

# deck -> tint, sampled from that deck's own arena art
TINT = {
    "gatsby": "#4d7a8c", "hamlet": "#4d4f8c", "frankenstein": "#4d7c8c",
    "sherlock": "#8d874d", "wonderland": "#4d798c", "oz": "#5c4e8f",
    "macbeth": "#8c4d64", "othello": "#8c4d64", "crucible": "#4d8c64",
    "tewwg": "#8c2b21", "romeojuliet": "#8c2b21", "odyssey": "#8c2b21",
}

OLD_MARKUP = """   <div class="board"><div class="board-inner">"""
NEW_MARKUP = """   <div class="board" data-opp="${opp.setKey}" data-you="${you.setKey}"><div class="board-inner">"""

CSS_HEAD = r"""
/* ===== the board as one spread (fix_board_spread.py) =====
   Each arena is a layer 62% tall, masked to fade toward the centre, so the two
   overlap through the middle 24% and cross-fade. Layers with background-size:
   cover, NOT background-size:100% 50% -- that stretches the art and cannot
   honour a focal point. Everything here is z-index 0; the cards are raised. */
body[data-screen="play"] .board{
  position:relative; gap:0; padding:0; border-radius:14px;
  overflow:hidden; isolation:isolate; background:#160f08;
  box-shadow:inset 0 0 70px rgba(30,20,8,.38), 0 18px 32px rgba(0,0,0,.42);
}
body[data-screen="play"] .board-inner{gap:0!important; position:relative; z-index:1}
body[data-screen="play"] .board::before,
body[data-screen="play"] .board::after{
  content:''; position:absolute; left:0; right:0; height:62%;
  z-index:0; pointer-events:none;
  background-repeat:repeat, no-repeat;
  background-size:auto, cover;
}
body[data-screen="play"] .board::before{
  top:0;
  background-image:
    repeating-linear-gradient(0deg,rgba(150,120,70,.045) 0 3px,rgba(0,0,0,0) 3px 7px),
    var(--opp-art,none);
  background-position:center, var(--opp-pos,center);
  -webkit-mask-image:linear-gradient(180deg,#000 0%,#000 58%,rgba(0,0,0,0) 100%);
          mask-image:linear-gradient(180deg,#000 0%,#000 58%,rgba(0,0,0,0) 100%);
}
body[data-screen="play"] .board::after{
  bottom:0;
  background-image:
    repeating-linear-gradient(0deg,rgba(150,120,70,.045) 0 3px,rgba(0,0,0,0) 3px 7px),
    var(--you-art,none);
  background-position:center, var(--you-pos,center bottom);
  -webkit-mask-image:linear-gradient(0deg,#000 0%,#000 58%,rgba(0,0,0,0) 100%);
          mask-image:linear-gradient(0deg,#000 0%,#000 58%,rgba(0,0,0,0) 100%);
}
/* the sides are layout only now -- the spread shows through them */
body[data-screen="play"] .board .side{
  position:relative; z-index:1; border-radius:0; margin:0;
  background-image:none!important; background:none;
}
/* ownership tint: strongest at the outer edge, gone before the middle, so it
   never draws a line where the worlds meet */
body[data-screen="play"] .board .side::before{
  content:''; position:absolute; inset:0; pointer-events:none; z-index:0;
  mix-blend-mode:soft-light; opacity:.5;
}
body[data-screen="play"] .board .side.opp-side::before{
  background:linear-gradient(180deg, var(--opp-tint,#6b6257) 0%,
    color-mix(in srgb, var(--opp-tint,#6b6257) 32%, transparent) 52%, transparent 82%);
}
body[data-screen="play"] .board .side.you-side::before{
  background:linear-gradient(0deg, var(--you-tint,#6b6257) 0%,
    color-mix(in srgb, var(--you-tint,#6b6257) 32%, transparent) 52%, transparent 82%);
}
body[data-screen="play"] .board .side.opp-side{
  box-shadow:inset 0 3px 0 color-mix(in srgb, var(--opp-tint,#6b6257) 60%, transparent)}
body[data-screen="play"] .board .side.you-side{
  box-shadow:inset 0 -3px 0 color-mix(in srgb, var(--you-tint,#6b6257) 60%, transparent)}
/* every card above the art and the tint */
body[data-screen="play"] .board .side > *{position:relative; z-index:1}
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
    if "fix_board_spread.py" in src or "--opp-art" in src:
        die("already applied. Ship a named fix_*.py to revise.")
    if src.count(OLD_MARKUP) != 1:
        die("could not find the board markup exactly once.")

    # build the per-deck rules from the arena mapping already in the stylesheet,
    # so a deck's arena and focal point are never restated by hand
    pairs = []
    for m in re.finditer(r'\.side\[data-arena="([a-z]+)"\]\{--arena:var\(--arena-([a-z]+)\);'
                         r'--arena-pos:([^}]+)\}', src):
        if m.group(1) not in [p[0] for p in pairs]:
            pairs.append((m.group(1), m.group(2), m.group(3).strip()))
    if len(pairs) < 10:
        die("found only %d deck arena rules -- expected all twelve." % len(pairs))

    rules = []
    for deck, art, pos in pairs:
        tint = TINT.get(deck, "#6b6257")
        rules.append(
            'body[data-screen="play"] .board[data-opp="%s"]'
            '{--opp-art:var(--arena-%s);--opp-pos:%s;--opp-tint:%s}' % (deck, art, pos, tint))
        rules.append(
            'body[data-screen="play"] .board[data-you="%s"]'
            '{--you-art:var(--arena-%s);--you-pos:%s;--you-tint:%s}' % (deck, art, pos, tint))

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before, st_before = src.count("<script"), src.count("<style")

    out = src.replace(OLD_MARKUP, NEW_MARKUP, 1)
    tail = out.rindex("</style>")
    block = CSS_HEAD + "\n" + "\n".join(rules) + "\n"
    out = out[:tail] + block + out[tail:]

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before or out.count("<style") != st_before:
        die("block counts changed")

    # nothing the spread adds may sit above the cards
    scope = re.sub(r"/\*[\s\S]*?\*/", "", block)
    if re.search(r"z-index:[2-9]", scope):
        die("a layer in the spread sits above the cards.")
    if "100% 50%" in scope:
        die("a stretching background-size survived.")
    if scope.count("background-size:auto, cover") != 1:
        die("the arena layers must use cover, once, for both pages.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  board spread wired")
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    decks wired  %d, focal points read from the existing rules" % len(pairs))
    print("    layers       62%% tall each, 24%% cross-fade, all at z-index 0")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
