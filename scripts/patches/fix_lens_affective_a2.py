#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_lens_affective_a2.py
Academic Battle Cards -- lens redesign, A2 (2026-09-04)

AFFECTIVE FALLACY: emotional reading, paid for.

  was: "any wrong trivia answer deals 10 damage to that player's Active"
       -- symmetrical, and you answer far more trivia than the AI does, so the
       lens damaged its own holder more than the opponent
  now: "after a correct answer you may read further. Answer a second question:
        correct heals your Active 20 and draws a card, wrong costs your Active
        10."

The second question is a RANDOM ABC from your book's pool, not the card you just
answered and not one you chose -- so it is a real knowledge test, and it mirrors
the tabletop rule (the opponent picks a question from the trivia tome). You
cannot see it before deciding whether to read further.

This is the only lens that makes a player CHOOSE to answer more questions, which
is the point of it in a classroom.

WHY IT IS OPT-IN: the old passive fired automatically on every wrong answer.
This one asks. Declining costs nothing, so the lens is never a tax -- the fault
shared by the four lenses in this redesign pass.

RENDER-SAFE: the prompt and the question live in state (S._af), not in the DOM,
and the panel is drawn from that state beside the existing trivia modal. A
re-render repaints it rather than losing it. Declining or answering clears the
state and repaints -- the stuck-modal failure mode that Structuralism's refusal
path produced cannot happen here, because there is no early return that skips a
paint.

Run from the repo root:

    python3 fix_lens_affective_a2.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

# --------------------------------------------------------------- engine ----
PATCHES.append((
    "a2-engine",
    """function triviaModal(){""",
    """/* ---- Affective Fallacy (A2): read further, at a risk ----
   Offered after a correct answer. The question is drawn at random from the
   player's own book pool, so it cannot be the card just answered and cannot be
   chosen -- the digital equivalent of the opponent picking from the tome. */
function afOffer(side){
  if(side!=='you') return false;               /* the AI does not gamble */
  if(!hasCrit('you','affective')) return false;
  if(S._af || S.pending) return false;         /* never stack on another prompt */
  const act=active(S.you);
  if(!act || act.hp<=0) return false;
  const k=S.you.setKey || (S.you.def&&S.you.def.d);
  const pool=(DATA.abcs[k]||[]).filter(a=>a && a.q && a.opts && a.opts.length);
  if(!pool.length) return false;
  const q=pool[rnd(pool.length)];
  S._af={ q:q.q, opts:q.opts.slice(), ans:q.ans, stage:'offer' };
  return true;
}
function afDecline(){
  if(!S||!S._af) return;
  S._af=null;
  pushLog('You set the book down \\u2014 no further reading.');
  try{ render(); }catch(e){}
}
function afAccept(){
  if(!S||!S._af) return;
  S._af.stage='ask';
  try{ render(); }catch(e){}
}
function afAnswer(choice){
  if(!S||!S._af||S._af.stage!=='ask') return;
  const correct = choice===S._af.ans;
  const act=active(S.you);
  S._af=null;
  try{ triviaStamp(correct); }catch(e){}
  if(correct){
    if(act){
      const before=act.hp;
      act.hp=Math.min(act.maxHp, act.hp+20);
      const healed=act.hp-before;
      if(!S.you.deck.length && S.you.discard.length) S.you.deck=shuffle(S.you.discard.splice(0));
      if(S.you.deck.length) S.you.hand.push(S.you.deck.shift());
      pushLog(`Affective Fallacy: the reading moves you \\u2014 ${act.name} recovers ${healed} HP and you draw a card.`);
    }
    toast('Read further \\u2014 correct! +20 HP and a card.','good');
    try{ SFX.heal(); }catch(e){}
  } else {
    if(act){
      const hurt=applyDmg(act,10);
      if(hurt>0) pushLog(`Affective Fallacy: the reading unsettles you \\u2014 ${act.name} takes ${hurt}.`);
      checkKO(S.you,'you');
    }
    toast('Read further \\u2014 wrong. Your Active takes 10.','bad');
    try{ SFX.status('burn'); }catch(e){}
  }
  try{ render(); }catch(e){}
}
function afModal(){
  if(!S||!S._af) return '';
  if(S._af.stage==='offer'){
    return `<div class="modal-bg"><div class="trivia af-offer">
      <div class="tri-head">\\u2726 AFFECTIVE FALLACY</div>
      <div class="tri-sub">Read further? A second question, drawn at random from your book.</div>
      <div class="tri-q">Correct: your Active recovers <b>20 HP</b> and you draw a card.<br>Wrong: your Active takes <b>10</b>.</div>
      <div class="tri-opts">
        <button class="tri-opt" data-af="yes"><b>A</b> Read further</button>
        <button class="tri-opt" data-af="no"><b>B</b> Set it down</button>
      </div></div></div>`;
  }
  return `<div class="modal-bg"><div class="trivia af-ask">
    <div class="tri-head">\\u2726 AFFECTIVE FALLACY \\u00b7 second reading</div>
    <div class="tri-sub tri-retry">No retry. Correct heals 20 and draws; wrong costs 10.</div>
    <div class="tri-q">${scrimTriviaText(S._af.q)}</div>
    <div class="tri-opts">${S._af.opts.map((o,i)=>
      `<button class="tri-opt" data-afans="${i}"><b>${'ABCD'[i]}</b> ${o}</button>`).join('')}</div>
    </div></div>`;
}
function triviaModal(){""",
))

# ------------------------------------------------------------- rendering ---
PATCHES.append((
    "a2-render",
    """${S.pending?triviaModal():''}${S._ip?ipModal():''}""",
    """${S.pending?triviaModal():''}${S._af?afModal():''}${S._ip?ipModal():''}""",
))

# ------------------------------------------------------------- routing ----
PATCHES.append((
    "a2-clicks",
    """  if(t.dataset.ans!=null){ if(S&&S._mg) mgAnswer(+t.dataset.ans); else answerTrivia(+t.dataset.ans); return; }""",
    """  if(t.dataset.af!=null){ if(t.dataset.af==='yes') afAccept(); else afDecline(); return; }
  if(t.dataset.afans!=null){ afAnswer(+t.dataset.afans); return; }
  if(t.dataset.ans!=null){ if(S&&S._mg) mgAnswer(+t.dataset.ans); else answerTrivia(+t.dataset.ans); return; }""",
))

# ---------------------------------------------- the trigger, and the old rule
PATCHES.append((
    "a2-trigger",
    """  attach('you',pend.handIdx,correct,pend.target);""",
    """  /* Affective Fallacy (A2): the offer comes after a CORRECT answer, once the
     attach has resolved, so the second question never competes with the first. */
  const _afWant = correct && typeof hasCrit==='function' && hasCrit('you','affective');
  attach('you',pend.handIdx,correct,pend.target);
  if(_afWant){ try{ afOffer('you'); }catch(e){} }""",
))

PATCHES.append((
    "a2-retire-old",
    """  if(affectiveOn() && act && act.hp>0){ const _af=applyDmg(act,10); if(_af>0) pushLog(`Critical anxiety: ${act.name} takes ${_af} damage.`); checkKO(p,side); }""",
    """  /* A2 replaced the automatic wrong-answer damage. It was symmetrical, and the
     player answers far more trivia than the AI, so the lens punished its own
     holder. The risk now lives in the optional second question instead. */""",
))

CSS = r"""
/* ===== Affective Fallacy, second reading (fix_lens_affective_a2.py) ===== */
.trivia.af-offer .tri-head,.trivia.af-ask .tri-head{background:#8E4B8B}
.trivia.af-offer .tri-q,.trivia.af-ask .tri-q{line-height:1.45}
.trivia.af-offer .tri-opt b,.trivia.af-ask .tri-opt b{color:#8E4B8B}
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
    for mark in ["fix_lens_affective_a2.py", "function afOffer(", "S._af"]:
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
    sc_before, st_before = src.count("<script"), src.count("<style")

    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)
    tail = out.rindex("</style>")
    out = out[:tail] + CSS + out[tail:]

    exp = "  symbolsOff, calcBlock, doBlock, critFx, sideOfChar,"
    if out.count(exp) != 1:
        die("could not find the debug export anchor.")
    out = out.replace(exp, exp + "\n  afOffer, afAccept, afDecline, afAnswer, afModal,", 1)

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before or out.count("<style") != st_before:
        die("block counts changed")
    if out == src:
        die("no change produced.")
    # the automatic symmetrical damage must be gone
    if "Critical anxiety:" in out:
        die("the old automatic wrong-answer damage survived.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    A2  optional second question, random from your book pool")
    print("        correct: +20 HP and a card | wrong: 10 to your Active")
    print("        the old symmetrical wrong-answer damage is retired")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
