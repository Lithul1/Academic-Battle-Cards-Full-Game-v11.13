#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_lens_rewrites_1.py
Academic Battle Cards -- lens redesign, part 1 of 2 (2026-09-03)

Ships three of the five agreed rewrites. F1 (Formalism) and A2 (Affective
Fallacy) are deliberately held for a second patch -- see the note at the end.

------------------------------------------------------------------ S1 --------
STRUCTURALISM: order rewarded, not enforced.

  was: "you may only charge ABC cards in ascending Power order (1->4)"
  now: "charging in ascending Power order is optional. Each charge that
        continues the ascent counts double."

The old passive was the only lens effect that made your own turn strictly worse,
with no upside attached, and it was the hardest rule in the game to police at a
table. It also produced the stuck-modal bug, because it was the refusal path
players hit most.

Nothing is ever refused now, so that class of bug cannot recur here. The double
charge is a synthetic `_wild` entry, the same device Reader-Response and Mise En
Scene already use for granted charges -- and `_wild` entries are excluded from
the ascent check, so a doubled charge cannot itself raise the bar.

------------------------------------------------------------------ AR1 -------
ARCHETYPAL: the monomyth.

  was: "Hero / Villain characters gain First Strike when fully charged"
       -- First Strike does not exist anywhere in the engine
  now: "Your Active gains +10 attack for each distinct archetype among your
        living characters."

Reads the `archetype` field, which all 163 characters carry (21 distinct, led by
Shadow 20 / Trickster 19 / Hero 18) and which no lens has ever read. No new data
and no new mechanic. Counted at a glance on a table.

------------------------------------------------------------------ D3 --------
DECONSTRUCTION: the margin overtakes the text.

  was: "Binary inversion -- Negate doubles incoming damage, Pierce can be
        blocked" (symmetrical, so it helped the opponent as often as you)
  now: "Your blocks may pay for attacks and your attacks may pay for blocks.
        Each mismatched payment leaves your own Active Exposed until your next
        turn."

Mismatched payment reuses the path Queer Theory already proves works. The cost
is Exposed on YOUR active -- a real negative status (next incoming attack deals
double). My original draft priced this with Margin Notes, which is a POSITIVE
status in this engine ("the next ABC attached here draws a card"): the cost was
a gift. Trevor caught that the pricing was wrong; the audit found why.

Run from the repo root:

    python3 fix_lens_rewrites_1.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

# ================================================================= S1 ========
PATCHES.append((
    "s1-structuralism-engine",
    """  if(correct && hasCrit(side,'structuralism')){
    const charged=act.atkCharge.concat(act.blkCharge).filter(c=>!c._wild);
    const lastPow=charged.length?Math.max(...charged.map(c=>c.power||0)):0;
    if((card.power||0)<lastPow){
      if(side==='you') toast('Structuralism: charge in ascending Power order.');
      /* the trivia panel is still on screen from the last paint; answerTrivia
         cleared S.pending and handed off to us, so if we return without
         repainting the question stays up. */
      try{ render(); }catch(e){}
      return; }""",
    """  /* Structuralism (S1): the ascent is now OPTIONAL and rewarded. Nothing is
     refused -- a charge that continues the ascent simply counts twice. The
     bonus is a synthetic _wild entry, the same device Reader-Response and Mise
     En Scene use, and _wild entries are excluded from the ascent test below so
     a doubled charge cannot raise the bar against itself. */
  let _structDouble=false;
  if(correct && hasCrit(side,'structuralism')){
    const charged=act.atkCharge.concat(act.blkCharge).filter(c=>!c._wild);
    const lastPow=charged.length?Math.max(...charged.map(c=>c.power||0)):0;
    if((card.power||0)>=lastPow) _structDouble=true;""",
))

PATCHES.append((
    "s1-structuralism-award",
    """  pile.push(card);
    if(side==='you'){ try{ SFX.attach(card.type==='ATTACK'?'atk':'blk'); }catch(e){}""",
    """  pile.push(card);
    if(_structDouble){
      pile.push({cat:'abc',type:card.type,power:0,_wild:true,_struct:true});
      if(side==='you') toast('Structuralism: the pattern holds \\u2014 that charge counts double.','good');
      pushLog(`${act.name} keeps the sequence \\u2014 the charge counts twice.`);
    }
    if(side==='you'){ try{ SFX.attach(card.type==='ATTACK'?'atk':'blk'); }catch(e){}""",
))

# ================================================================ AR1 ========
PATCHES.append((
    "ar1-archetypal-damage",
    """  if(hasCrit(side,'marxist') && (ab.cost===1||ab.cost===2) && def.atk && (def.atk.cost===3||def.atk.cost===4)){ dmg+=10; pushLog('Marxist Lens: +10 class-struggle damage.'); }""",
    """  if(hasCrit(side,'marxist') && (ab.cost===1||ab.cost===2) && def.atk && (def.atk.cost===3||def.atk.cost===4)){ dmg+=10; pushLog('Marxist Lens: +10 class-struggle damage.'); }
  /* Archetypal (AR1): the monomyth. Every character carries an archetype and
     no lens has ever read one. Replaces a passive that referenced First Strike,
     a mechanic the engine does not have. */
  if(hasCrit(side,'archetypal')){
    const kinds={}; (A.team||[]).forEach(function(c){ if(c && c.hp>0 && c.archetype) kinds[c.archetype]=1; });
    const n=Object.keys(kinds).length;
    if(n>0){ dmg+=n*10; pushLog(`Archetypal Lens: +${n*10} \\u2014 ${n} archetype${n===1?'':'s'} in the story.`); }
  }""",
))

# ================================================================= D3 ========
PATCHES.append((
    "d3-pool",
    """  const pool=()=> hasCrit(side,'queer') ? (att.atkCharge.length+att.blkCharge.length) : att.atkCharge.length;""",
    """  /* Deconstruction (D3) collapses the attack/block binary exactly as Queer
     Theory collapses the colour one, so it shares the pool. */
  const pool=()=> (hasCrit(side,'queer')||hasCrit(side,'deconstruct')) ? (att.atkCharge.length+att.blkCharge.length) : att.atkCharge.length;""",
))

PATCHES.append((
    "d3-payment",
    """  if(spentAtk.length<cost && hasCrit(side,'queer')){ const more=spend(att.blkCharge,cost-spentAtk.length); if(more.length) A.critTurn.queerMismatch=true; spentAtk.push(...more); }""",
    """  if(spentAtk.length<cost && (hasCrit(side,'queer')||hasCrit(side,'deconstruct'))){
    const more=spend(att.blkCharge,cost-spentAtk.length);
    if(more.length){
      if(hasCrit(side,'queer')) A.critTurn.queerMismatch=true;
      if(hasCrit(side,'deconstruct')){
        /* the price of collapsing the binary: your own Active is Exposed.
           Margin Notes would NOT work here -- it is a positive status in this
           engine and would have been a gift to whoever received it. */
        att.status=att.status||{}; att.status.exposed=true;
        pushLog(`${att.name} pays a block into an attack \\u2014 the binary collapses, and ${att.name} is Exposed.`);
      }
    }
    spentAtk.push(...more); }""",
))

ALREADY = ["fix_lens_rewrites_1.py", "_structDouble", "Archetypal Lens: +"]


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    if "try{ render(); }catch(e){}\n      return; }" not in src:
        die("fix_attach_refusal_render.py must be applied first.")
    for mark in ALREADY:
        if mark in src:
            die("already applied (found %r). Ship a named fix_*.py to revise." % mark)

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-24s found %d times, expected 1" % (label, n))
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

    # Structuralism must no longer refuse an attach
    if "Structuralism: charge in ascending Power order." in out:
        die("the old refusing Structuralism guard survived.")
    # D3's cost must be a NEGATIVE status
    d3 = out[out.index("d3 begins") if "d3 begins" in out else out.index("the binary collapses")-600:]
    if "marginNotes" in d3[:900]:
        die("D3 is pricing itself with a positive status again.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    S1  Structuralism  ascent optional, doubles the charge")
    print("    AR1 Archetypal     +10 per distinct living archetype")
    print("    D3  Deconstruction cross-payment, priced with Exposed")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Still to come: F1 (Formalism) and A2 (Affective Fallacy).")
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
