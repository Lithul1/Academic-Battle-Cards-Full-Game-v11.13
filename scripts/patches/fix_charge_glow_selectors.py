#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_charge_glow_selectors.py
Academic Battle Cards -- 2026-08-27

fix_attach_charge_cues.py shipped the audio working and the VISUAL silently
dead. fxChargeGlow() looked for markup that does not exist:

    written              actual
    .side.you            .side.you-side
    .char[data-uid=..]   .char has no data-uid attribute
    .char.active         no .active class; the active character IS the only
                         .char rendered per side, tagged .char.you / .char.opp

Every lookup fell through to `document.querySelector('.char')`, which is the
OPPONENT's card (it renders first), and the row lookup found nothing at all. So
the chime played and nothing lit up.

I wrote those selectors from memory instead of reading the rendered board. The
audition page hid it, because that page has its own hand-built markup that
matched what I had assumed rather than what the game emits.

Also fixed: the glow is applied to a live node, but render() replaces the board
wholesale and fires several times around an attach, wiping the class mid
animation. The glow is now re-applied on a short interval for its own duration,
so it survives any number of intervening re-renders and stops on its own.

Run from the repo root:

    python3 fix_charge_glow_selectors.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

OLD = """function fxChargeGlow(side, ch, which){
  try{
    setTimeout(function(){
      const root=document.querySelector('.side.'+(side==='you'?'you':'opp'))||document;
      const card=root.querySelector('.char[data-uid="'+ch.uid+'"]')
              || root.querySelector('.char.active') || root.querySelector('.char');
      if(!card) return;
      card.classList.remove('chg-pulse'); void card.offsetWidth;
      card.classList.add('chg-pulse', which==='blk'?'chg-blk':'chg-atk');
      const row=card.querySelector('.pc-move.'+(which==='blk'?'blk':'atk'));
      if(row){ row.classList.remove('chg-lit'); void row.offsetWidth; row.classList.add('chg-lit'); }
      setTimeout(function(){
        card.classList.remove('chg-pulse','chg-atk','chg-blk');
        if(row) row.classList.remove('chg-lit');
      }, 900);
    }, 30);
  }catch(e){}
}"""

NEW = """function fxChargeGlow(side, ch, which){
  /* The board is `.side.you-side` / `.side.opp-side`, and the active character
     is the only `.char` on a side, tagged `.char.you` / `.char.opp`. There is
     no data-uid and no .active class -- an earlier version guessed at all
     three and silently lit nothing. */
  const sel = side==='you' ? '.char.you' : '.char.opp';
  const cls = which==='blk' ? 'chg-blk' : 'chg-atk';
  const rowSel = which==='blk' ? '.pc-move.blk' : '.pc-move.atk';
  const DUR = 900;
  try{
    /* One glow at a time. Two moves can come online on the same attach, and a
       previous glow's cleanup tick would otherwise strip the new one's classes
       partway through -- the old glow tidying up after the new one. */
    if(window._chgFxStop){ try{ window._chgFxStop(); }catch(e){} }
    /* wipe any leftover glow from either card, so a new colour never stacks on
       an old one */
    ['.char.you','.char.opp'].forEach(function(q){
      const n=document.querySelector(q); if(!n) return;
      n.classList.remove('chg-pulse','chg-atk','chg-blk');
      n.querySelectorAll('.pc-move.chg-lit').forEach(function(r){ r.classList.remove('chg-lit'); });
    });
    const paint = function(){
      const card=document.querySelector(sel);
      if(!card) return false;
      if(!card.classList.contains('chg-pulse')){
        card.classList.add('chg-pulse', cls);
      }
      const row=card.querySelector(rowSel);
      if(row && !row.classList.contains('chg-lit')) row.classList.add('chg-lit');
      return true;
    };
    /* render() replaces the board wholesale and runs more than once around an
       attach, so a class set on a live node is wiped mid animation. Re-apply
       for the animation's own length, then stop. */
    const t0=Date.now();
    let tick=null;
    const stop=function(){
      if(tick){ clearInterval(tick); tick=null; }
      /* If a newer glow has taken over, this one stops its timer and touches
         nothing: a superseded glow tidying up would strip the new one's
         classes mid-animation. */
      if(window._chgFxStop!==stop) return;
      window._chgFxStop=null;
      const card=document.querySelector(sel);
      if(card){
        card.classList.remove('chg-pulse','chg-atk','chg-blk');
        const row=card.querySelector(rowSel);
        if(row) row.classList.remove('chg-lit');
      }
    };
    window._chgFxStop=stop;
    tick=setInterval(function(){
      if(Date.now()-t0>DUR){ stop(); return; }
      paint();
    }, 90);
    setTimeout(paint, 20);
  }catch(e){}
}"""


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    if "function fxChargeGlow(" not in src:
        die("fix_attach_charge_cues.py must be applied first.")
    if "fix_charge_glow_selectors.py" in src or "no data-uid and no .active class" in src:
        die("already applied. Ship a named fix_*.py to revise.")

    if src.count(OLD) != 1:
        die("could not find the original fxChargeGlow exactly once.")

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    out = src.replace(OLD, NEW, 1)

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != src.count("<script"):
        die("script block count changed")
    # the wrong selectors must be gone. Strip comments first: the replacement
    # explains what was wrong, so the prose legitimately names them.
    span = out[out.index("function fxChargeGlow"):out.index("function fxAttack")]
    span = re.sub(r"/\*[\s\S]*?\*/", "", span)
    for bad in ("data-uid", ".char.active", "'.side.'+"):
        if bad in span:
            die("a stale selector survived in code: %r" % bad)
    for good in (".char.you", ".char.opp"):
        if good not in span:
            die("replacement is missing %r" % good)

    # expose the glow so it can be verified against the real board in tests --
    # the original shipped broken precisely because nothing exercised it
    exp = "  makeBuilderState, builderFocus, handleBuilder, edModCount, clone,"
    if out.count(exp) != 1:
        die("could not find the debug export anchor.")
    out = out.replace(exp, exp + "\n  fxChargeGlow, moveFull, chargeSnap, chargeReport, SFX,", 1)

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  fxChargeGlow repointed at the real markup")
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    selectors    .char.you / .char.opp  (was .side.you + data-uid)")
    print("    survives     re-renders, by re-applying for the animation's length")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
