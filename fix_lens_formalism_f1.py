#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_lens_formalism_f1.py
Academic Battle Cards -- lens redesign, F1 (2026-09-03)

FORMALISM: strip the context -- but theirs, not yours.

  was: "all special symbols are ignored"  -- both sides, so the lens disabled
       your own keywords too and played as a self-handicap
  now: "special symbols on ENEMY moves are ignored. Yours still function."

------------------------------------------------------------- WHY THIS IS FIDDLY
symbolsOff() took no argument and answered a global question:

    function symbolsOff(){ return critFx('you')==='formalism'||critFx('opp')==='formalism'; }

Making it one-sided means every caller must say WHOSE move is being resolved,
and the eight callers sit in the damage pipeline -- the most safety-critical
code in the game. Getting one backwards would silently invert keyword behaviour
for a whole category of moves, and neither node --check nor a markup assertion
would notice.

So each site was traced to its actor by hand before anything was written:

  site                                    move belongs to   actor passed
  calcBlock(ch,ab,incoming)               the blocker       sideOfChar(ch)
  performAttack: pierce=false             the attacker      side
  performAttack: ab.siphon                the attacker      side
  performAttack: riposte (def.blk.riposte) the DEFENDER     dKey
  doBlock: block effects (b.grant etc)    the defender      dKey
  finishAttack: feminist sacrifice cap    the attacker      side
  finishAttack: ab.sacrifice              the attacker      side
  finishAttack: attack effects (ab.*)     the attacker      side

Two of those are counter-intuitive and are the reason this got its own patch:
the riposte lives inside performAttack but belongs to the DEFENDER, and
calcBlock is called while resolving an attack but evaluates the DEFENDER's move.

symbolsOff() keeps working with no argument, returning the old global answer, so
any site not listed above is unaffected.

Run from the repo root:

    python3 fix_lens_formalism_f1.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

PATCHES.append((
    "symbolsoff-sided",
    """function symbolsOff(){ return critFx('you')==='formalism'||critFx('opp')==='formalism'; }""",
    """/* Formalism (F1) strips the ENEMY's symbols, not everyone's. `actor` is the
   side whose move is being resolved; its symbols are off when the OPPOSING side
   is running Formalism. Called with no argument it answers the old global
   question, so untouched callers keep their previous behaviour. */
function symbolsOff(actor){
  if(actor!=='you' && actor!=='opp') return critFx('you')==='formalism'||critFx('opp')==='formalism';
  return critFx(actor==='you'?'opp':'you')==='formalism';
}""",
))

# --- calcBlock: the move being evaluated is the BLOCKER's ------------------
PATCHES.append((
    "calcblock",
    """  if(typeof symbolsOff==='function' && symbolsOff()) return {amt:ab.block||0};""",
    """  /* ab is `ch`'s own block, so the actor is whoever holds it */
  if(typeof symbolsOff==='function' && symbolsOff(sideOfChar(ch))) return {amt:ab.block||0};""",
))

# --- performAttack: pierce and siphon belong to the ATTACKER ---------------
PATCHES.append((
    "pierce",
    """  if(symbolsOff()) pierce=false;""",
    """  if(symbolsOff(side)) pierce=false;""",
))

PATCHES.append((
    "atk-siphon",
    """  if(ab.siphon && !symbolsOff()) applySiphon(def,att,side,ab.siphon);""",
    """  if(ab.siphon && !symbolsOff(side)) applySiphon(def,att,side,ab.siphon);""",
))

# --- riposte lives in performAttack but belongs to the DEFENDER ------------
PATCHES.append((
    "riposte",
    """    if(armed && !symbolsOff() && att._ripostedTurn!==S._turnNo){""",
    """    /* def.blk.riposte -- the defender's symbol, not the attacker's */
    if(armed && !symbolsOff(dKey) && att._ripostedTurn!==S._turnNo){""",
))

# --- doBlock: the block's own effects belong to the DEFENDER ---------------
PATCHES.append((
    "block-effects",
    """  D.discard.push(...spentBlk.filter(c=>!c._wild));
  if(!symbolsOff()){""",
    """  D.discard.push(...spentBlk.filter(c=>!c._wild));
  if(!symbolsOff(dKey)){""",
))

# --- finishAttack: sacrifice and attack effects belong to the ATTACKER -----
PATCHES.append((
    "sacrifice-cap",
    """  if(ab.sacrifice && hasCrit(dKey,'feminist') && !symbolsOff() && net>30){ net=30; pushLog('Feminist Lens caps the Sacrifice attack at 30.'); }""",
    """  if(ab.sacrifice && hasCrit(dKey,'feminist') && !symbolsOff(side) && net>30){ net=30; pushLog('Feminist Lens caps the Sacrifice attack at 30.'); }""",
))

PATCHES.append((
    "sacrifice",
    """  if(ab.sacrifice && !symbolsOff()){ const _sac=applyDmg(att,ab.sacrifice); if(_sac>0) pushLog(`${att.name} sacrifices ${_sac} HP.`); }""",
    """  if(ab.sacrifice && !symbolsOff(side)){ const _sac=applyDmg(att,ab.sacrifice); if(_sac>0) pushLog(`${att.name} sacrifices ${_sac} HP.`); }""",
))

PATCHES.append((
    "attack-effects",
    """  if(!symbolsOff()){
    if(ab.inflictIfHas && def.hp>0){""",
    """  if(!symbolsOff(side)){
    if(ab.inflictIfHas && def.hp>0){""",
))

ALREADY = ["fix_lens_formalism_f1.py", "function symbolsOff(actor)"]


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    for mark in ALREADY:
        if mark in src:
            die("already applied (found %r). Ship a named fix_*.py to revise." % mark)

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-18s found %d times, expected 1" % (label, n))
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

    # every call site must now name its actor -- a bare symbolsOff() left in the
    # damage pipeline is the exact bug this patch exists to prevent
    bare = 0
    for fname in ("calcBlock", "performAttack", "doBlock", "finishAttack"):
        i = out.index("function %s(" % fname)
        j = out.index("\nfunction ", i + 10)
        for ln in out[i:j].split("\n"):
            if re.search(r"symbolsOff\(\s*\)", ln):
                bare += 1
                sys.stderr.write("  unsided call left in %s: %s\n" % (fname, ln.strip()[:100]))
    if bare:
        die("%d call site(s) in the damage pipeline still ask the global question." % bare)

    # expose for tests: the whole risk of this patch is a site picking the wrong
    # side, and that is only checkable by calling it
    exp = "  sideToast, playBookmark, performAttack,"
    if out.count(exp) != 1:
        die("could not find the debug export anchor.")
    out = out.replace(exp, exp + "\n  symbolsOff, calcBlock, doBlock, critFx, sideOfChar,", 1)

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    Formalism now strips ENEMY symbols only")
    print("    8 call sites traced to their actor; 0 bare calls left in the pipeline")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
