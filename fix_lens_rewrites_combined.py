#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_lens_rewrites_combined.py
Academic Battle Cards -- 2026-09-04

REPLACES fix_attach_refusal_render.py AND fix_lens_rewrites_1.py.
Run this one INSTEAD of those two. Do not run all three.

WHY THIS EXISTS
Those two patches were authored before fix_lens_affective_a2.py, and A2 rewrote
one of the exact lines they anchor on:

    was   attach('you',pend.handIdx,correct,pend.target);
          }
    now   const _afWant = correct && ... hasCrit('you','affective');
          attach('you',pend.handIdx,correct,pend.target);
          if(_afWant){ try{ afOffer('you'); }catch(e){} }
          }

So on a build with A2 already applied, the older patch could not find its anchor
and refused -- correctly, but unhelpfully. That was my error: I wrote anchors
that assumed my own patch order rather than tolerating any order.

This version anchors on the post-A2 text, and checks for A2 explicitly so it
cannot be run on a build where that assumption does not hold.

WHAT IT DOES  (identical outcome to running 17 then 18)

  * the trivia panel repaints when an attach is refused, so a refusal cannot
    leave the question stuck on screen
  * answerTrivia repaints after attach() returns, whatever path attach took
  * S1  Structuralism -- the ascending order becomes optional and rewarded
        rather than enforced; a charge that keeps the sequence counts double
  * AR1 Archetypal    -- +10 attack per distinct archetype among your living
        characters, replacing a passive that named First Strike, which the
        engine has never implemented
  * D3  Deconstruction -- blocks may pay for attacks and vice versa, priced by
        Exposed on your own Active

Run from the repo root:

    python3 fix_lens_rewrites_combined.py
    python3 fix_lens_card_text.py
    python3 build.py
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

# ---- S1: the ascent becomes optional, and pays -----------------------------
PATCHES.append((
    "s1-engine",
    """  if(correct && hasCrit(side,'structuralism')){
    const charged=act.atkCharge.concat(act.blkCharge).filter(c=>!c._wild);
    const lastPow=charged.length?Math.max(...charged.map(c=>c.power||0)):0;
    if((card.power||0)<lastPow){ if(side==='you') toast('Structuralism: charge in ascending Power order.'); return; }
  }""",
    """  /* Structuralism (S1): the ascent is OPTIONAL and rewarded. Nothing is ever
     refused -- a charge that continues the ascent simply counts twice. The
     bonus is a synthetic _wild entry, the same device Reader-Response and Mise
     En Scene use, and _wild entries are excluded from the test above, so a
     doubled charge cannot raise the bar against itself.
     The old branch refused the attach and returned WITHOUT repainting, which
     left the trivia question stranded on screen. */
  let _structDouble=false;
  if(correct && hasCrit(side,'structuralism')){
    const charged=act.atkCharge.concat(act.blkCharge).filter(c=>!c._wild);
    const lastPow=charged.length?Math.max(...charged.map(c=>c.power||0)):0;
    if((card.power||0)>=lastPow) _structDouble=true;
  }""",
))

PATCHES.append((
    "s1-award",
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

# ---- answerTrivia always repaints (post-A2 anchor) -------------------------
PATCHES.append((
    "answertrivia-repaint",
    """  attach('you',pend.handIdx,correct,pend.target);
  if(_afWant){ try{ afOffer('you'); }catch(e){} }
}""",
    """  attach('you',pend.handIdx,correct,pend.target);
  if(_afWant){ try{ afOffer('you'); }catch(e){} }
  /* attach() has several early returns and repaints on only some of them.
     S.pending is already null here, so a repaint is always correct and is the
     only thing that guarantees the trivia panel comes down -- whatever new
     refusal path is added to attach() later. */
  try{ render(); }catch(e){}
}""",
))

# ---- AR1: the monomyth -----------------------------------------------------
PATCHES.append((
    "ar1-damage",
    """  if(hasCrit(side,'marxist') && (ab.cost===1||ab.cost===2) && def.atk && (def.atk.cost===3||def.atk.cost===4)){ dmg+=10; pushLog('Marxist Lens: +10 class-struggle damage.'); }""",
    """  if(hasCrit(side,'marxist') && (ab.cost===1||ab.cost===2) && def.atk && (def.atk.cost===3||def.atk.cost===4)){ dmg+=10; pushLog('Marxist Lens: +10 class-struggle damage.'); }
  /* Archetypal (AR1): the monomyth. Every character carries an archetype and
     no lens has ever read one. Replaces a passive that named First Strike, a
     mechanic the engine does not have. */
  if(hasCrit(side,'archetypal')){
    const kinds={}; (A.team||[]).forEach(function(c){ if(c && c.hp>0 && c.archetype) kinds[c.archetype]=1; });
    const n=Object.keys(kinds).length;
    if(n>0){ dmg+=n*10; pushLog(`Archetypal Lens: +${n*10} \\u2014 ${n} archetype${n===1?'':'s'} in the story.`); }
  }""",
))

# ---- D3: cross-payment, priced in Exposed ---------------------------------
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
        /* the price of collapsing the binary. Margin Notes would NOT work here
           -- it is a POSITIVE status in this engine, so it would have been a
           gift rather than a cost. */
        att.status=att.status||{}; att.status.exposed=true;
        pushLog(`${att.name} pays a block into an attack \\u2014 the binary collapses, and ${att.name} is Exposed.`);
      }
    }
    spentAtk.push(...more); }""",
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
    if "function afOffer(" not in src:
        die("fix_lens_affective_a2.py must be applied first. If your build "
            "predates A2, use fix_attach_refusal_render.py + "
            "fix_lens_rewrites_1.py instead.")
    for mark in ("_structDouble", "Archetypal Lens: +"):
        if mark in src:
            die("already applied (found %r). Do not run this alongside "
                "fix_attach_refusal_render.py or fix_lens_rewrites_1.py." % mark)

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-22s found %d times, expected 1" % (label, n))
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
    if "Structuralism: charge in ascending Power order." in out:
        die("the old refusing Structuralism guard survived.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    repaint  the trivia panel can no longer be left stranded")
    print("    S1  Structuralism  ascent optional, doubles the charge")
    print("    AR1 Archetypal     +10 per distinct living archetype")
    print("    D3  Deconstruction cross-payment, priced with Exposed")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 fix_lens_card_text.py")
    print("       python3 build.py")


if __name__ == "__main__":
    main()
