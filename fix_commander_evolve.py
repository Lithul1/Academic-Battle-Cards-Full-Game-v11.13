#!/usr/bin/env python3
"""
fix_commander_evolve.py — commanders (1st Editions) can evolve with their own
Act cards, as decided for the physical precons.

1. ACT_ALLOW_1E = true, and Pagemaster commanders are no longer excluded.
2. actStageId(): an un-evolved 1st Edition counts as its base character
   (Gatsby 1E is a "gatsby" host for The Host of West Egg).
3. Evolving REPLACES the 1E passive with the Act card's passive (existing
   evolve behaviour) — and clears the 1E's locked caveat statuses, since
   evolution already clears all statuses.
4. KO of an evolved Pagemaster commander: its Act cards go to the discard and
   it returns to hand as the 1st Edition (was: returned under its Act name).
5. Drawn play: only one copy of a character on the field — a commander and its
   own base card can't both be in play (placement and mid-game play).

USAGE (repo root):  python3 fix_commander_evolve.py   then   python3 build.py
Writes src/game.src.html.bak.  Refuses to run twice.
"""
import os, shutil, sys
SRC = os.path.join('src', 'game.src.html')
DUP = ("  { const _k=(card.fe?((card._cdef&&card._cdef.base)||[])[1]:card.charId);   /* one copy in play (fix_commander_evolve) */\n"
       "    const _on=p.team.find(function(c){ return c.hp>0 && (c.fe&&c.base?c.base[1]:c.id)===_k; });\n"
       "    if(_k && _on){ toast(`${_on.name} is already on the field \\u2014 only one copy of a character can be in play.`); return; } }\n")
EDITS = [
 ('allow 1E evolution', "const ACT_ALLOW_1E=false;", "const ACT_ALLOW_1E=true;", 1),
 ('Pagemaster commanders may evolve',
  "function actBaseOk(c){ return !!c && !c.cid && !c._boss && !c._pmCmd && (ACT_ALLOW_1E || !c.fe); }",
  "function actBaseOk(c){ return !!c && !c.cid && !c._boss && (ACT_ALLOW_1E || (!c.fe && !c._pmCmd)); }", 1),
 ('1E counts as its base character',
  "function actStageId(c){ return c ? (c._actId||c.id) : null; }",
  "function actStageId(c){ return c ? (c._actId||(c.fe&&c.base?c.base[1]:c.id)) : null; }", 1),
 ('evolved commander KO: restore 1E before returning to hand',
  "    if(p._pm && a._pmCmd && pmReturnCost(a)!==null){\n",
  "    if(p._pm && a._pmCmd && pmReturnCost(a)!==null){\n      if(a._actBase) actOnKO(p,a);   /* Act cards to the discard; it returns as the 1st Edition */\n", 1),
 ('one copy in play — placement',
  "  if(!card||card.cat!=='char'){ toast('Only characters can be placed.'); return; }\n",
  "  if(!card||card.cat!=='char'){ toast('Only characters can be placed.'); return; }\n" + DUP, 1),
 ('one copy in play — mid-game play',
  "  if(!card||card.cat!=='char') return;\n  /* a returned Pagemaster commander is not free to replay */\n",
  "  if(!card||card.cat!=='char') return;\n" + DUP + "  /* a returned Pagemaster commander is not free to replay */\n", 1),
]
def main():
    if not os.path.exists(SRC): sys.exit('Run from the repo root: %s not found.' % SRC)
    s = open(SRC, encoding='utf-8').read()
    if 'romeojuliet' not in s: sys.exit('This is not the live src/game.src.html.')
    if 'fix_commander_evolve' in s: sys.exit('Already applied. Nothing changed.')
    for label, a, _, n in EDITS:
        if s.count(a) != n: sys.exit('Anchor "%s" found %d times (need %d). Nothing changed.' % (label, s.count(a), n))
    for _, a, b, _ in EDITS: s = s.replace(a, b)
    shutil.copy2(SRC, SRC + '.bak')
    open(SRC, 'w', encoding='utf-8').write(s)
    print('fix_commander_evolve: commanders can evolve; one copy per character in play. Backup: %s.bak' % SRC)
if __name__ == '__main__': main()
