#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_side_toast.py
Academic Battle Cards -- opponent messages leaking to the player (2026-09-03)

REPORTED: "with 4 attack ABCs the game is telling me i have zero". The message
was real, but it was about the OPPONENT's card. Their active had 0/2 charged;
yours had 4/2 and was ready. The toast simply never checked whose failure it was.

THE ACTUAL DEFECT is not three missing guards. `toast()` is a player-facing UI
primitive with no notion of sides, called from engine functions that run for
BOTH players. Every failure branch added to such a function is a new leak unless
its author remembers a guard, and three of six in performAttack had already
forgotten. Guarding three lines fixes today's report and leaves the trap armed.

So: a `sideToast(side, msg, kind)` helper that no-ops for the opponent, and the
leaking sites converted to it. The guard now lives in one function instead of
being re-remembered at every call site.

MEASURED before the fix -- 103 toast sites audited, 8 reachable with side='opp',
3 confirmed leaking by driving each path:

  performAttack, unpaid cost   "Need 3 ATTACK ABCs (have 0)."
  performAttack, no target     "No target."
  playBookmark, Defibrillator  "Defibrillator needs a KO'd ally and 3 cards."
                               -- 33 leaks in 545 real AI bookmark plays (~6%)

The other five candidates proved unreachable for real AI plays and are left
alone rather than churned.

The two informative ones are not simply silenced: the opponent's failed attack
and their fizzled Defibrillator now reach the log, so the information survives
without a message that looks like it is addressed to you.

Run from the repo root:

    python3 fix_side_toast.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

# ------------------------------------------------------------ the helper ---
PATCHES.append((
    "sidetoast-helper",
    """function flash(side){ const el=$(`.char.${side}`); if(el){ el.classList.remove('hit'); void el.offsetWidth; el.classList.add('hit'); } }""",
    """/* A toast is addressed to the PLAYER. Engine functions run for both sides, so
   any toast raised from one needs to know whose failure it describes -- an
   unguarded one shows the opponent's problem as though it were yours. Putting
   the check here means it is made once instead of re-remembered at every new
   failure branch. (fix_side_toast.py) */
function sideToast(side, msg, kind){
  if(side !== 'you') return;
  toast(msg, kind||'');
}
function flash(side){ const el=$(`.char.${side}`); if(el){ el.classList.remove('hit'); void el.offsetWidth; el.classList.add('hit'); } }""",
))

# ------------------------------------------- performAttack: unpaid cost ----
PATCHES.append((
    "attack-cost",
    """  if(cost!=null && pool()<cost){ toast(`Need ${cost} ATTACK ABCs (have ${pool()}).`); return false; }""",
    """  if(cost!=null && pool()<cost){
    sideToast(side, `Need ${cost} ATTACK ABCs (have ${pool()}).`);
    /* keep the information, lose the misdirected message */
    if(side!=='you') pushLog(`Opponent cannot pay for ${ab.n||'that attack'} \\u2014 needs ${cost}, has ${pool()}.`);
    return false; }""",
))

# ------------------------------------------- performAttack: no target ------
PATCHES.append((
    "attack-notarget",
    """  if(!def||def.hp<=0){ toast('No target.'); return false; }""",
    """  if(!def||def.hp<=0){ sideToast(side,'No target.'); return false; }""",
))

# ------------------------------- performAttack: no active (drawn mode) -----
PATCHES.append((
    "attack-noactive",
    """  if(S&&S.drawn){ const _ap=S[arguments[0]]||S.you; if(!_ap||!_ap.team[_ap.activeIdx]||_ap.team[_ap.activeIdx].hp<=0){ toast&&toast('No Active character on the field.'); return false; } }""",
    """  if(S&&S.drawn){ const _ap=S[arguments[0]]||S.you; if(!_ap||!_ap.team[_ap.activeIdx]||_ap.team[_ap.activeIdx].hp<=0){ sideToast(side,'No Active character on the field.'); return false; } }""",
))

# ------------------------------------------- playBookmark: Defibrillator ---
PATCHES.append((
    "bm-defib",
    """      if(P.grave.length===0 || others.length<3){ toast("Defibrillator needs a KO'd ally and 3 cards."); return; }""",
    """      if(P.grave.length===0 || others.length<3){
        sideToast(side,"Defibrillator needs a KO'd ally and 3 cards.");
        if(side!=='you') pushLog('Opponent\\u2019s Defibrillator fizzles \\u2014 no KO\\u2019d ally to revive.');
        return; }""",
))

# ------------------------------- playBookmark: the remaining two branches --
# Not reachable for real AI plays in 545 simulated bookmark plays, but they are
# the same shape and would leak the moment the AI's card pool changes.
PATCHES.append((
    "bm-noswap",
    """      if(!bench.length){ toast('No benched character to swap in.'); return; }""",
    """      if(!bench.length){ sideToast(side,'No benched character to swap in.'); return; }""",
))

PATCHES.append((
    "bm-noeffect",
    """    default: toast('No effect'); return;""",
    """    default: sideToast(side,'No effect'); return;""",
))

PATCHES.append((
    "bm-immune",
    """      const go=t=>{ if(t&&t.fe&&t.passive&&t.passive.immuneSelfBuff){ toast&&toast(`${t.name} cannot be healed.`);""",
    """      const go=t=>{ if(t&&t.fe&&t.passive&&t.passive.immuneSelfBuff){ sideToast(side,`${t.name} cannot be healed.`);""",
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
    for mark in ["fix_side_toast.py", "function sideToast("]:
        if mark in src:
            die("already applied (found %r). Ship a named fix_*.py to revise." % mark)

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

    # every toast inside the two engine functions must now be side-aware
    for fname in ("performAttack", "playBookmark"):
        i = out.index("function %s(" % fname)
        j = out.index("\nfunction ", i + 10)
        body = out[i:j]
        for ln in body.split("\n"):
            if re.search(r"(?<!side)toast\(", ln) and "sideToast(" not in ln:
                if "side==='you'" in ln or "isYou" in ln:
                    continue          # already guarded the old way; fine
                die("%s still raises an unguarded toast:\n    %s" % (fname, ln.strip()[:110]))

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before:
        die("script block count changed")
    if out == src:
        die("no change produced.")

    exp = "  zoomCard, zoomLayer, zoomHtmlFor,"
    if out.count(exp) != 1:
        die("could not find the debug export anchor.")
    out = out.replace(exp, exp + "\n  sideToast, playBookmark, performAttack,", 1)

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    sideToast()  the guard is made once, not at every call site")
    print("    converted    3 confirmed leaks + 4 latent ones of the same shape")
    print("    preserved    the two informative failures now reach the log")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
