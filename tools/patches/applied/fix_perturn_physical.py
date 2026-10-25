#!/usr/bin/env python3
"""
fix_perturn_physical.py — growing (perTurn) attacks and blocks start at their
printed number, matching physical play.

BEFORE  damage = base + step * max(1, turnsInPlay)
        -> a card printed 40+ dealt 50 the first time it could attack.
AFTER   damage = base + step * (own turns completed since it entered play)
        -> 40 the turn it enters (or the first turn of the game), 50 on your
           next turn, 60 the turn after.  Same rule for perTurn blocks
           (George's Tragic Avenger).

HOW: a per-character counter `_grow`, ticked at the END of each of its owner's
turns (the first player's opening turn has no turn-start, so a start-of-turn
tick would run a turn late).  Cards in play at the start of the game begin at 0.  Anything that enters mid-game — Drawn-mode placement/play, an
evolution, or a revive (Deus Ex Machina, Adaptation, Defibrillator) — resets
to 0 on entry, like a fresh counter in physical play.  A knocked-out card
loses its count.  turnsInPlay itself is untouched (evolution timing still
uses it).

USAGE (repo root):  python3 fix_perturn_physical.py   then   python3 build.py
Writes src/game.src.html.bak.  Refuses to run twice.
"""
import os, shutil, sys
SRC = os.path.join('src', 'game.src.html')
EDITS = [  # (label, anchor, replacement, expected count)
 ('calcDamage perTurn',
  "if(ab.dmgType==='perTurn') d=(ab.base||0)+(ab.step||10)*Math.max(1,ch.turnsInPlay);",
  "if(ab.dmgType==='perTurn') d=(ab.base||0)+(ab.step||10)*(ch._grow||0);   /* starts at the printed number */", 1),
 ('calcBlock perTurn',
  "if(ab.blockType==='perTurn') return {amt:(ab.base||0)+(ab.step||10)*Math.max(1,ch.turnsInPlay)};",
  "if(ab.blockType==='perTurn') return {amt:(ab.base||0)+(ab.step||10)*(ch._grow||0)};", 1),
 ('endTurn tick (end of each of the owner\'s turns)',
  "    _E.flags.extracredit=false;",
  "    _E.team.forEach(c=>{ if(c.hp>0) c._grow=(c._grow||0)+1; else delete c._grow; });   /* perTurn: +1 step per completed turn in play */\n    _E.flags.extracredit=false;", 1),
 ('Drawn place/play — fresh counter',
  "p.hand.splice(idx,1); p.team.push(ch);",
  "p.hand.splice(idx,1); p.team.push(ch); ch._grow=0;", 2),
 ('revives (Deus Ex / Adaptation) — fresh counter',
  "t.atkCharge=[]; t.blkCharge=[]; t.status={};",
  "t.atkCharge=[]; t.blkCharge=[]; t.status={}; t._grow=0;", 2),
 ('Defibrillator — fresh counter',
  "g.atkCharge=[];g.blkCharge=[];g.status={};",
  "g.atkCharge=[];g.blkCharge=[];g.status={}; g._grow=0;", 1),
 ('actEvolve — fresh counter',
  "c.turnsInPlay=0; c._tookHit=false; c._evoFx=true;",
  "c.turnsInPlay=0; c._grow=0; c._tookHit=false; c._evoFx=true;", 1),
 ('DATA doc comment',
  "(perTurn = base + step*turnsInPlay)",
  "(perTurn = base, +step each of your turns after it entered play)", 1),
]
def main():
    if not os.path.exists(SRC): sys.exit('Run from the repo root: %s not found.' % SRC)
    s = open(SRC, encoding='utf-8').read()
    if 'romeojuliet' not in s: sys.exit('This is not the live src/game.src.html.')
    if 'c._grow' in s: sys.exit('Already applied (_grow found). Nothing changed.')
    for label, a, _, n in EDITS:
        if s.count(a) != n: sys.exit('Anchor "%s" found %d times (need %d). Nothing changed.' % (label, s.count(a), n))
    for _, a, b, _ in EDITS: s = s.replace(a, b)
    shutil.copy2(SRC, SRC + '.bak')
    open(SRC, 'w', encoding='utf-8').write(s)
    print('fix_perturn_physical: growing moves now start at their printed number. Backup: %s.bak' % SRC)
if __name__ == '__main__': main()
