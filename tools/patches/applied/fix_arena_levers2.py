#!/usr/bin/env python3
"""
fix_arena_levers2.py — three more PreCon Arena levers (all off by default).

  Attacks spend only 1 ABC   an attack discards one charged ABC; the rest stay
                             attached (Dog-Eared Strategy still keeps all)
                                                       ARENA_RULES.keepCharges
  Commanders return once     a commander's first KO returns it to hand (1 attach
                             to replay); the second KO is permanent and counts.
                             KO target stays 3.        ARENA_RULES.cmdReturns
  Revise once per turn       put a card from hand on the bottom of the deck and
                             draw 1. Player: "Revise" in the hand view. AI: an
                             Act card with no host, a character it can't field,
                             or a second Lens.          ARENA_RULES.revise

The games CSV gains revises_a / revises_b; the rules column tags keep1 / ret1 /
revise. Nothing outside the Arena changes.

USAGE (repo root, after fix_arena_levers.py):
  python3 fix_arena_levers2.py      then   python3 build.py
Writes src/game.src.html.bak.  Refuses to run twice.
"""
import os, shutil, sys
SRC = os.path.join('src', 'game.src.html')
EDITS = [
 [
  "lever list",
  "  { key:'bmBoost',   label:'AI plays Bookmarks +25%',     tag:'bm+25' } ];",
  "  { key:'bmBoost',   label:'AI plays Bookmarks +25%',     tag:'bm+25' },\n  { key:'keep1',     label:'Attacks spend only 1 ABC',    tag:'keep1' },\n  { key:'ret1',      label:'Commanders return once',      tag:'ret1' },\n  { key:'revise',    label:'Revise once per turn',        tag:'revise' } ];"
 ],
 [
  "rule fields",
  "const ARENA_RULES = { handMin:0, firstAttachFree:false, perTurnCap:null, aiBmBoost:0, handSize:7,",
  "const ARENA_RULES = { handMin:0, firstAttachFree:false, perTurnCap:null, aiBmBoost:0, keepCharges:false, cmdReturns:null, revise:false, handSize:7,"
 ],
 [
  "levers applied",
  "    ARENA_RULES.aiBmBoost=on('bmBoost')?ARENA_LEVER_VAL.bmBoost.on:0;\n",
  "    ARENA_RULES.aiBmBoost=on('bmBoost')?ARENA_LEVER_VAL.bmBoost.on:0;\n    ARENA_RULES.keepCharges=on('keep1'); ARENA_RULES.cmdReturns=on('ret1')?1:null; ARENA_RULES.revise=on('revise');   /* fix_arena_levers2 */\n"
 ],
 [
  "attack spends 1 ABC",
  "  else A.discard.push(...spentAtk.filter(c=>!c._wild));\n  if(side==='you') A.flags.attacked=true;",
  "  else if(S.arena && ARENA_RULES.keepCharges && spentAtk.filter(c=>!c._wild).length>1){   /* lever: one ABC is spent, the rest stay attached */\n    const _k=spentAtk.filter(c=>!c._wild), _d=_k.shift(); A.discard.push(_d);\n    _k.reverse().forEach(function(c){ (c.type==='BLOCK'?att.blkCharge:att.atkCharge).unshift(c); });\n    pushLog(`${att.name} spends 1 ABC \\u2014 ${_k.length} stay attached.`); }\n  else A.discard.push(...spentAtk.filter(c=>!c._wild));\n  if(side==='you') A.flags.attacked=true;"
 ],
 [
  "commander returns",
  "  return n>=PM.maxReturns ? null : PM.returnCost[n];",
  "  const _mx=(S&&S.arena&&ARENA_RULES.cmdReturns!=null)?ARENA_RULES.cmdReturns:PM.maxReturns;   /* lever: one free return */\n  return n>=_mx ? null : PM.returnCost[n];"
 ],
 [
  "revise button",
  "      ${(S.drawn&&S.phase==='place')?'':`<button class=\"hv-disc${(S.you.discardsLeft||0)>0?'':' off'}\" data-do=\"dischand\" title=\"Shed this card into your discard pile\">\\uD83D\\uDDD1 Discard</button>`}\n",
  "      ${(S.drawn&&S.phase==='place')?'':`<button class=\"hv-disc${(S.you.discardsLeft||0)>0?'':' off'}\" data-do=\"dischand\" title=\"Shed this card into your discard pile\">\\uD83D\\uDDD1 Discard</button>`}\n      ${(S.arena&&ARENA_RULES.revise&&S.turn==='you'&&S.phase==='strategize'&&!S._sim)?`<button class=\"hv-disc${arenaCanRevise(S.you)?'':' off'}\" data-do=\"revisehand\" title=\"Put this card on the bottom of your deck and draw 1 (once per turn)\">\\u21bb Revise</button>`:''}\n"
 ],
 [
  "revise click",
  "    else if(d==='dischand'){ if(S && S._handView!=null) tryDiscardHandCard(S._handView,false); }",
  "    else if(d==='dischand'){ if(S && S._handView!=null) tryDiscardHandCard(S._handView,false); }\n    else if(d==='revisehand'){ if(S && S._handView!=null){ const _i=S._handView; if(!arenaCanRevise(S.you)){ toast('You have already revised this turn.'); return; } S._handView=null; arenaRevise('you',_i); } }"
 ],
 [
  "AI revises dead cards",
  "    if(S.arena){ arenaAiField(p); if(!drawnHasActive(p)){ pushLog('The AI has no one to field this turn.'); endAiTurn(); return; } }",
  "    if(S.arena){ arenaAiField(p); if(!drawnHasActive(p)){ pushLog('The AI has no one to field this turn.'); endAiTurn(); return; } }\n    if(S.arena) arenaAiRevise(p);"
 ],
 [
  "revise telemetry",
  "bonus_draws_a:T.bonus.A, bonus_draws_b:T.bonus.B,",
  "bonus_draws_a:T.bonus.A, bonus_draws_b:T.bonus.B, revises_a:(T.revise||{}).A||0, revises_b:(T.revise||{}).B||0,"
 ],
 [
  "revise module",
  "\nwindow.ABC_DEBUG = {",
  "\n/* ---- Revise (fix_arena_levers2): once per turn, a card from hand goes to the bottom of the deck and you draw 1 ---- */\nfunction arenaCanRevise(p){ return !!(S&&S.arena&&ARENA_RULES.revise&&p&&p.flags._reviseTurn!==(S._turnNo||0)); }\nfunction arenaRevise(side,idx){ const p=S&&S[side]; if(!arenaCanRevise(p)) return false;\n  const card=p.hand[idx]; if(!card) return false;\n  p.hand.splice(idx,1); p.deck.push(card); dealOne(side); p.flags._reviseTurn=(S._turnNo||0);\n  if(S._tel){ S._tel.revise=S._tel.revise||{A:0,B:0}; S._tel.revise[p._arenaSide]=(S._tel.revise[p._arenaSide]||0)+1; }\n  pushLog(`${who(p)} revises \\u2014 ${p===S.you&&!S._sim?card.name||'a card':'a card'} goes to the bottom of the deck; draw 1.`); render(); return true; }\n/* AI: revise the deadest card in hand — an Act card with no host anywhere, a character it can't field, a second Lens */\nfunction arenaAiRevise(p){ if(!arenaCanRevise(p)) return;\n  const hostFor=function(a){ return p.team.some(function(t){ return t.hp>0 && actStageId(t)===a.from; }) ||\n    p.hand.some(function(h){ return h.cat==='char' && (h.fe?((h._cdef&&h._cdef.base)||[])[1]:h.charId)===a.from; }) ||\n    p.hand.some(function(h){ return h.cat==='act' && h.actId===a.from; }); };\n  let i=p.hand.findIndex(function(c){ if(c.cat!=='act') return false; const a=actById(c.actId); return a && !hostFor(a); });\n  if(i<0) i=p.hand.findIndex(function(c){ return c.cat==='char' && (!arenaCanField(p,c) || (drawnHasActive(p) && drawnBench(p)>=ARENA_RULES.benchMax)); });\n  if(i<0 && p.crit) i=p.hand.findIndex(function(c){ return c.cat==='crit'; });\n  if(i>=0) arenaRevise(S.you===p?'you':'opp', i); }\n\nwindow.ABC_DEBUG = {"
 ]
]
def main():
    if not os.path.exists(SRC): sys.exit('Run from the repo root: %s not found.' % SRC)
    s = open(SRC, encoding='utf-8').read()
    if 'romeojuliet' not in s: sys.exit('This is not the live src/game.src.html.')
    if 'fix_arena_levers2' in s: sys.exit('Already applied. Nothing changed.')
    if 'fix_arena_levers' not in s: sys.exit('Run fix_arena_levers.py first. Nothing changed.')
    for label, a, _ in EDITS:
        if s.count(a) != 1: sys.exit('Anchor "%s" found %d times (need 1). Nothing changed.' % (label, s.count(a)))
    for _, a, b in EDITS: s = s.replace(a, b, 1)
    shutil.copy2(SRC, SRC + '.bak')
    open(SRC, 'w', encoding='utf-8').write(s)
    print('fix_arena_levers2: 3 more rule levers added. Backup: %s.bak' % SRC)
if __name__ == '__main__': main()
