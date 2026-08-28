#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_attach_charge_cues.py
Academic Battle Cards -- attach + charge-complete feedback (2026-08-27)

Adds the audio and visual cues Trevor asked for:

  * attaching an ATTACK ABC   -> a bright rising click
  * attaching a BLOCK ABC     -> a lower, rounder click (two cues, so the sound
                                 reinforces the red/blue language already on the
                                 cards)
  * attaching a BOOKMARK      -> its own distinct cue
  * a move reaching FULL      -> one shared chime for attack and block, plus the
                                 move row lighting red or blue and a brief pulse
                                 on the card edge

The opponent's charge-complete fires too, at lower volume and pitch, so a
Pagemaster or AI turn telegraphs "they can swing next turn" without you having
to read the board. Attach cues stay player-only: the AI attaches several times a
turn and it would become noise.

--------------------------------------------------------------- HOW "FULL" ----
The cue uses the SAME definition the game already uses to enable the move
button and to gate performAttack:

    act.atkCharge.length >= act.atk.cost

NOT attackCostFor(). Those two disagree -- attackCostFor() applies the Pagemaster
bench surcharge, escCost() escalation and the Biographical lens discount, while
the readiness check, the move button and the "2/3" counter all read the raw
ab.cost. Hanging the cue off the computed cost would make it fire at a moment
the UI does not agree with. That divergence is a real issue, but it is a
gameplay change and not this patch's business; see the note to Trevor.

Everything is generated with the existing beep/noise/env helpers, so no audio
assets are added and the placeholder count is untouched. Dropping
`sfx_attach_atk` etc. into window.ABC_SND later will take precedence
automatically -- SFX.card() already prefers a file when one exists.

Run from the repo root:

    python3 fix_attach_charge_cues.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

# ------------------------------------------------------------- the cues -----
PATCHES.append((
    "sfx-cues",
    """  function ko(){ if(!sfxOn||!ctx) return; const t=now(); beep(220,t,0.5,'sawtooth',0.3,60); noise(t,0.3,0.18,600); beep(110,t+0.05,0.6,'sine',0.25,45); }""",
    """  function ko(){ if(!sfxOn||!ctx) return; const t=now(); beep(220,t,0.5,'sawtooth',0.3,60); noise(t,0.3,0.18,600); beep(110,t+0.05,0.6,'sine',0.25,45); }
  /* ---- attach + charge feedback ----
     A recorded sample wins automatically if one is ever added: SFX.card()
     checks window.ABC_SND first, and these names match the sfx_ convention. */
  function attach(kind){
    if(!sfxOn||!ctx) return;
    if(FILEAUD['sfx_attach_'+kind]){ playSfxFile('attach_'+kind,0.6); return; }
    const t=now();
    if(kind==='blk'){                   /* lower, rounder -- the blue language */
      beep(300,t,0.09,'triangle',0.20,380); noise(t,0.035,0.07,900);
    } else if(kind==='bm'){             /* bookmarks get their own voice */
      beep(660,t,0.07,'sine',0.16,880); beep(990,t+0.05,0.10,'sine',0.13,1180);
    } else {                            /* attack -- brighter, rising */
      beep(520,t,0.08,'square',0.18,700); noise(t,0.03,0.08,2200);
    }
  }
  /* One chime for attack and block alike. The foe's is quieter and a fifth
     lower, so you can tell whose move came online without looking. */
  function chargeFull(foe){
    if(!sfxOn||!ctx) return;
    if(FILEAUD['sfx_charge_full']&&!foe){ playSfxFile('charge_full',0.7); return; }
    const t=now(), k=foe?0.66:1, v=foe?0.13:0.22;
    [784,1047,1319].forEach((f,i)=>beep(f*k,t+i*0.055,0.30,'sine',v));
  }""",
))

PATCHES.append((
    "sfx-export",
    """  return { unlock, attack, block, heal, status, ko, toggleMusic, toggleSfx, isMusicOn:()=>musicOn, isSfxOn:()=>sfxOn,""",
    """  return { unlock, attack, block, heal, status, ko, attach, chargeFull, toggleMusic, toggleSfx, isMusicOn:()=>musicOn, isSfxOn:()=>sfxOn,""",
))

# ------------------------------------- the helper that decides "just filled" --
PATCHES.append((
    "charge-helpers",
    """function fxAttack(side,dmg){""",
    """/* ---- attach + charge-complete feedback (fix_attach_charge_cues.py) ----
   "Full" here is deliberately the RAW ab.cost, matching the move button, the
   readiness gate and the n/cost counter on the card. attackCostFor() computes a
   different number in some situations; until those are reconciled the cue
   follows what the player can actually see and click. */
function moveFull(ch, which){
  if(!ch) return false;
  const ab = which==='blk' ? ch.blk : ch.atk;
  if(!ab || ab.cost==null) return false;
  const n = (which==='blk' ? ch.blkCharge : ch.atkCharge) || [];
  return n.length >= ab.cost;
}
/* Snapshot before an attach so we can tell a move that JUST came online from
   one that was already there -- otherwise the chime repeats on every attach. */
function chargeSnap(ch){
  return ch ? { atk:moveFull(ch,'atk'), blk:moveFull(ch,'blk') } : null;
}
function chargeReport(side, ch, before){
  if(!ch||!before) return;
  ['atk','blk'].forEach(function(w){
    if(!before[w] && moveFull(ch,w)){
      try{ SFX.chargeFull(side!=='you'); }catch(e){}
      fxChargeGlow(side, ch, w);
    }
  });
}
/* The move row lights in its own colour and the card edge pulses once. Both are
   pure CSS animations added to the live node, so a re-render simply clears
   them -- nothing to unwind. */
function fxChargeGlow(side, ch, which){
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
}
function fxAttack(side,dmg){""",
))

# ---------------------------------------------- attach site 1: trivia resolve --
PATCHES.append((
    "attach-trivia",
    """    pile.push(card);
    if(hasCrit(side,'reader') && p.crit && p.crit.declared===card.type){""",
    """    const _snap=chargeSnap(act);
    pile.push(card);
    if(side==='you'){ try{ SFX.attach(card.type==='ATTACK'?'atk':'blk'); }catch(e){} }
    chargeReport(side, act, _snap);
    if(hasCrit(side,'reader') && p.crit && p.crit.declared===card.type){""",
))

# ----------------------------------------- attach site 2: drag onto a bencher --
PATCHES.append((
    "attach-drag",
    """  (String(st.card.type).toUpperCase()==='ATTACK'?act.atkCharge:act.blkCharge).push(st.card);""",
    """  const _snap2=chargeSnap(act);
  (String(st.card.type).toUpperCase()==='ATTACK'?act.atkCharge:act.blkCharge).push(st.card);
  try{ SFX.attach(String(st.card.type).toUpperCase()==='ATTACK'?'atk':'blk'); }catch(e){}
  chargeReport('you', act, _snap2);""",
))

CSS = r"""
/* ===== attach + charge-complete feedback (fix_attach_charge_cues.py) ===== */
@keyframes chgPulse{
  0%{box-shadow:0 0 0 0 var(--chg,rgba(230,184,92,.85)),0 0 0 0 rgba(0,0,0,0)}
  35%{box-shadow:0 0 0 4px var(--chg,rgba(230,184,92,.85)),0 0 18px 6px var(--chg,rgba(230,184,92,.5))}
  100%{box-shadow:0 0 0 0 rgba(0,0,0,0),0 0 0 0 rgba(0,0,0,0)}
}
.char.chg-pulse{animation:chgPulse .85s ease-out 1}
.char.chg-atk{--chg:rgba(200,68,60,.9)}
.char.chg-blk{--chg:rgba(74,144,194,.9)}
@keyframes chgLit{
  0%{filter:brightness(1)}
  30%{filter:brightness(1.55) saturate(1.3)}
  100%{filter:brightness(1)}
}
.pc-move.chg-lit{animation:chgLit .85s ease-out 1;position:relative}
.pc-move.chg-lit::after{
  content:'';position:absolute;inset:0;border-radius:inherit;pointer-events:none;
  animation:chgLit .85s ease-out 1;
  box-shadow:inset 0 0 0 2px currentColor}
@media (prefers-reduced-motion: reduce){
  .char.chg-pulse,.pc-move.chg-lit,.pc-move.chg-lit::after{animation:none}
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
    for mark in ["fix_attach_charge_cues.py", "function chargeFull(", "function moveFull("]:
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
    st_before = src.count("<style")

    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)
    tail = out.rindex("</style>")
    out = out[:tail] + CSS + out[tail:]

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed -- no audio assets should have been added.")
    if out.count("<script") != sc_before or out.count("<style") != st_before:
        die("block counts changed")
    if out == src:
        die("no change produced.")
    # the cue must follow the visible definition, not the computed one
    if "moveFull" in out and "attackCostFor" in out[out.index("function moveFull"):out.index("function chargeSnap")]:
        die("moveFull must use the raw ab.cost, matching the move button.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged -- cues are synthesised, not sampled)" % ph_before)
    print("    attach       atk / blk / bookmark, player side only")
    print("    charge full  shared chime + move-row light + card-edge pulse")
    print("    opponent     charge-complete only, quieter and a fifth lower")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
