#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_d3_ui_gate.py
Academic Battle Cards -- 2026-09-04

REPORTED: with Deconstruction active and 2 attack + 1 block charged against a
cost-3 attack, the attack cannot be used.

CAUSE, and it is mine. D3 let blocks pay for attacks by widening the pool in
performAttack:

    engine  const pool=()=> (hasCrit(side,'queer')||hasCrit(side,'deconstruct'))
                              ? (att.atkCharge.length+att.blkCharge.length)
                              : att.atkCharge.length;

but the readiness gate that decides whether the attack BUTTON is enabled was
left alone:

    ui      const effPool = hasCrit(side,'queer')
                              ? (ch.atkCharge.length+ch.blkCharge.length)
                              : ch.atkCharge.length;

So the engine would happily resolve the attack, and the button the player has to
press stayed disabled. Reproduced against the reported state: pool 3, cost 3,
`ready` false, `disabled` true -- while performAttack, called directly, spent a
block charge and applied Exposed correctly.

This is the same fault as the Formalism work: a rule changed in one of two
places that must agree. There I traced all eight call sites by hand; here I
changed the engine and forgot the mirror in the renderer.

The two expressions now derive from one helper, so they cannot drift again.

Run from the repo root:

    python3 fix_d3_ui_gate.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

PATCHES.append((
    "shared-helper",
    """function deckIsPm(def){ return !!(def && def.pm); }""",
    """function deckIsPm(def){ return !!(def && def.pm); }
/* Which charges may pay for an attack. Queer Theory collapses the colour
   binary and Deconstruction collapses the attack/block one, so both may spend
   the other pile. The engine and the button gate MUST agree -- they were
   written separately and drifted, leaving an attack the engine allowed behind a
   button that stayed disabled. One expression now, used by both. */
function atkPoolOf(side, ch){
  if(!ch) return 0;
  const wide = hasCrit(side,'queer') || hasCrit(side,'deconstruct');
  return wide ? ((ch.atkCharge||[]).length + (ch.blkCharge||[]).length)
              : (ch.atkCharge||[]).length;
}""",
))

PATCHES.append((
    "ui-gate",
    """  const effPool = hasCrit(side,'queer') ? (ch.atkCharge.length+ch.blkCharge.length) : ch.atkCharge.length;""",
    """  const effPool = atkPoolOf(side, ch);""",
))

PATCHES.append((
    "engine-pool",
    """  const pool=()=> (hasCrit(side,'queer')||hasCrit(side,'deconstruct')) ? (att.atkCharge.length+att.blkCharge.length) : att.atkCharge.length;""",
    """  const pool=()=> atkPoolOf(side, att);""",
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
    if "fix_d3_ui_gate.py" in src or "function atkPoolOf(" in src:
        die("already applied. Ship a named fix_*.py to revise.")
    if "hasCrit(side,'deconstruct')" not in src:
        die("the Deconstruction rewrite must be applied first "
            "(fix_lens_rewrites_combined.py or fix_lens_rewrites_1.py).")

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-16s found %d times, expected 1" % (label, n))
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

    # neither side may compute the pool independently any more
    body = re.sub(r"/\*[\s\S]*?\*/", "", out)
    # only the two ATTACK-AFFORDABILITY expressions must agree. Other code
    # legitimately sums both piles for different purposes (loststacks counts a
    # bench character's total charges, for instance).
    stray = [ln.strip()[:100] for ln in body.split("\n")
             if ("const effPool" in ln or "const pool=()=>" in ln)
             and "atkPoolOf" not in ln]
    if stray:
        for s2 in stray:
            sys.stderr.write("  pool still computed inline: %s\n" % s2)
        die("the gate and the engine can still drift.")

    exp = "  afOffer, afAccept, afDecline, afAnswer, afModal,"
    if out.count(exp) == 1:
        out = out.replace(exp, exp + "\n  atkPoolOf,", 1)

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    the button gate and the engine now share one expression")
    print("    Deconstruction attacks are clickable when the engine allows them")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
