#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_russian_formalism_cap.py
Academic Battle Cards -- balance (2026-09-06)

RUSSIAN FORMALISM: damage equal to HALF your current HP, not all of it.

  was: dmg = att.hp
  now: dmg = ceil(att.hp / 2)

The lens audit flagged this as the largest outlier in the pool. At full HP a
140 HP character struck for 140, in a game where every other attack lives in the
40-70 band, with no setup, no charge condition and no cap. Halving puts a
healthy Creature at 70 -- the top of the normal band rather than double it --
while a wounded character still hits for less, so the lens keeps its identity:
your best swing is your first one, and it decays as you take damage.

Rounded UP, so the effect never reads as 0 at 1 HP: a character on its last
point still lands 1. Damage elsewhere in the game moves in tens, so ceil also
keeps odd HP totals from silently losing a point.

The card text is updated in the same patch -- there is no window in which the
card promises full HP and the engine pays half.

Run from the repo root:

    python3 fix_russian_formalism_cap.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

PATCHES.append((
    "engine",
    """  if(hasCrit(side,'russian')){ dmg=att.hp; pushLog(`Russian Formalism: ${att.name}'s damage equals its HP (${dmg}).`); }""",
    """  if(hasCrit(side,'russian')){
    /* was dmg=att.hp, which put a healthy 140 HP character at 140 against a
       40-70 band with no setup and no cap. Half, rounded up so a character on
       1 HP still lands 1 rather than nothing. */
    dmg=Math.ceil(att.hp/2);
    pushLog(`Russian Formalism: ${att.name} strikes for half its HP (${dmg}).`);
  }""",
))

PATCHES.append((
    "card-text",
    r"""passive:'Defamiliarize \u2014 your Active\u2019s attack damage equals its current HP.',""",
    r"""passive:'Defamiliarize \u2014 your Active\u2019s attack damage equals half its current HP, rounded up.',"""),
)


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    if "fix_russian_formalism_cap.py" in src or "strikes for half its HP" in src:
        die("already applied. Ship a named fix_*.py to revise.")

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-12s found %d times, expected 1" % (label, n))
    if problems:
        die("anchor check failed -- nothing written:\n" + "\n".join(problems))

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != src.count("<script"):
        die("script block count changed")
    if out == src:
        die("no change produced.")

    # the engine and the card must not disagree about the fraction
    if "dmg=att.hp;" in out:
        die("the full-HP damage line survived.")
    if "attack damage equals its current HP" in out:
        die("the card still promises full HP.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    damage       att.hp -> ceil(att.hp / 2)")
    print("    card text    updated in the same patch, so the two cannot disagree")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
