#!/usr/bin/env python3
"""
fix_arena_levers.py — five rule levers on the PreCon Arena screen, so each rule
change can be measured against the baseline with a batch.

  Refill hand to 4          start-of-turn draw tops the hand up to 4 (a normal
                            turn still draws 1)          ARENA_RULES.handMin
  First ABC attach is free  each player's first ABC attach of the game skips
                            the question and doesn't use an attach
                                                         ARENA_RULES.firstAttachFree
  Growing attacks cap +50   perTurn attacks and blocks grow at most +50
                                                         ARENA_RULES.perTurnCap
  AI answers 100%           AI trivia accuracy 1.0 (baseline 0.8)
  AI plays Bookmarks +25%   once per AI turn, if the AI's Bookmark brain passes,
                            a playable Bookmark is played with probability
                            ARENA_RULES.aiBmBoost (0.01, calibrated so plays per
                            game rise ~25% against the baseline: 2.04 -> 2.57 per game over 250 games)

All levers are off by default (= the rules you have today). The games CSV gains
a "rules" column (e.g. refill4+cap50) so batches can be compared in one sheet.
Draws per turn are unchanged. Nothing outside the Arena is affected.

USAGE (repo root, after fix_arena_sim.py):
  python3 fix_arena_levers.py      then   python3 build.py
Writes src/game.src.html.bak.  Refuses to run twice.
"""
import os, shutil, sys
SRC = os.path.join('src', 'game.src.html')
EDITS = [
 [
  "lever settings in ARENA_RULES",
  "const ARENA_RULES = { handSize:7,",
  "function arenaGrow(ch,ab){ const g=(ab.step||10)*(ch._grow||0); return (S&&S.arena&&ARENA_RULES.perTurnCap!=null)?Math.min(g,ARENA_RULES.perTurnCap):g; }\n/* Rule levers (fix_arena_levers): set per match from the Arena screen; all off = the baseline rules. */\nconst ARENA_LEVERS = [\n  { key:'refill4',   label:'Refill hand to 4',            tag:'refill4' },\n  { key:'firstFree', label:'First ABC attach is free',    tag:'firstFree' },\n  { key:'growCap',   label:'Growing attacks cap at +50',  tag:'cap50' },\n  { key:'ai100',     label:'AI answers 100%',             tag:'ai100' },\n  { key:'bmBoost',   label:'AI plays Bookmarks +25%',     tag:'bm+25' } ];\nconst ARENA_LEVER_VAL = { refill4:{ on:4, off:0 }, growCap:{ on:50, off:null }, ai100:{ on:1.0, off:0.8 }, bmBoost:{ on:0.01, off:0 } };\nconst ARENA_RULES = { handMin:0, firstAttachFree:false, perTurnCap:null, aiBmBoost:0, handSize:7,"
 ],
 [
  "levers applied at match start",
  "  if(opt.sim){ st.autoBlock=true; st.turnTimer=0; }",
  "  if(opt.sim){ st.autoBlock=true; st.turnTimer=0; }\n  { const lv=c.levers||{}, on=function(k){ return !!lv[k]; };   /* fix_arena_levers */\n    ARENA_RULES.handMin=on('refill4')?ARENA_LEVER_VAL.refill4.on:0; ARENA_RULES.firstAttachFree=on('firstFree');\n    ARENA_RULES.perTurnCap=on('growCap')?ARENA_LEVER_VAL.growCap.on:null; ARENA_RULES.aiAccuracy=on('ai100')?1.0:0.8;\n    ARENA_RULES.aiBmBoost=on('bmBoost')?ARENA_LEVER_VAL.bmBoost.on:0;\n    st.handMin=ARENA_RULES.handMin; st.aiAccuracy=ARENA_RULES.aiAccuracy; }"
 ],
 [
  "per-match flags + rules tag",
  "  if(opt.seed){ S._tel.seed=opt.seed; S._tel.id=opt.seed; }",
  "  if(opt.seed){ S._tel.seed=opt.seed; S._tel.id=opt.seed; }\n  S.you._arenaFirstFree=S.opp._arenaFirstFree=ARENA_RULES.firstAttachFree;\n  S._tel.rules=ARENA_LEVERS.filter(function(L){ return (c.levers||{})[L.key]; }).map(function(L){ return L.tag; }).join('+')||'baseline';"
 ],
 [
  "rules column",
  "first_player:T.first,",
  "first_player:T.first, rules:T.rules||'baseline',"
 ],
 [
  "CSV: union of columns",
  "function arenaCsv(rows){ if(!rows.length) return ''; const cols=Object.keys(rows[0]);",
  "function arenaCsv(rows){ if(!rows.length) return ''; const cols=[]; rows.forEach(function(r){ Object.keys(r).forEach(function(k){ if(cols.indexOf(k)<0) cols.push(k); }); });"
 ],
 [
  "growth cap — attacks",
  "if(ab.dmgType==='perTurn') d=(ab.base||0)+(ab.step||10)*(ch._grow||0);   /* starts at the printed number */",
  "if(ab.dmgType==='perTurn') d=(ab.base||0)+arenaGrow(ch,ab);   /* starts at the printed number */"
 ],
 [
  "growth cap — blocks",
  "if(ab.blockType==='perTurn') return {amt:(ab.base||0)+(ab.step||10)*(ch._grow||0)};",
  "if(ab.blockType==='perTurn') return {amt:(ab.base||0)+arenaGrow(ch,ab)};"
 ],
 [
  "first free attach — AI",
  "        const useFree=(p.flags.feFree||0)>0 && p.hand[pick] && p.hand[pick].cat==='abc'; const _ft=useFree?(p.flags.feFreeTo||null):null; if(useFree){ p.flags.feFree--; if(_ft){ p.flags.feFreeTo=null; p.attachesLeft++; } }",
  "        const _af=!!(S.arena && ARENA_RULES.firstAttachFree && p._arenaFirstFree && p.hand[pick] && p.hand[pick].cat==='abc');\n        if(_af){ p._arenaFirstFree=false; p.attachesLeft++; pushLog(`${who(p)}'s first attach of the game is free.`); }\n        const useFree=_af || ((p.flags.feFree||0)>0 && p.hand[pick] && p.hand[pick].cat==='abc'); const _ft=(useFree&&!_af)?(p.flags.feFreeTo||null):null; if(useFree&&!_af){ p.flags.feFree--; if(_ft){ p.flags.feFreeTo=null; p.attachesLeft++; } }"
 ],
 [
  "first free attach — player",
  "  if((p.flags.feFree||0)>0 && card.cat==='abc' && p.flags.feFreeTo && tgt.uid===p.flags.feFreeTo){",
  "  if(S.arena && ARENA_RULES.firstAttachFree && p._arenaFirstFree && card.cat==='abc'){ p._arenaFirstFree=false; p.attachesLeft++; p.flags._freeNow=true; pushLog('Your first attach of the game is free \\u2014 no question.'); attach('you',idx,true,tgt.uid); p.flags._freeNow=false; return; }\n  if((p.flags.feFree||0)>0 && card.cat==='abc' && p.flags.feFreeTo && tgt.uid===p.flags.feFreeTo){"
 ],
 [
  "AI Bookmark boost",
  "      const bi=aiPickBookmark(p, prof);",
  "      let bi=aiPickBookmark(p, prof);\n      if(bi<0 && S.arena && ARENA_RULES.aiBmBoost>0 && p.flags._bmBoostTurn!==(S._turnNo||0)){ p.flags._bmBoostTurn=(S._turnNo||0);   /* lever: plays a Bookmark the AI brain passed on */\n        if(Math.random()<ARENA_RULES.aiBmBoost) bi=p.hand.findIndex(function(c){ return c.cat==='bookmark' && bmRole(c) && bmPlayable(p,c); }); }"
 ],
 [
  "lever buttons",
  "    <h3 class=\"sub-h\" style=\"font-size:1.05em\">Who goes first</h3>",
  "    <h3 class=\"sub-h\" style=\"font-size:1.05em\">Rule levers <small style=\"font-weight:normal\">(all off = baseline)</small></h3><div class=\"sub-actions\">${ARENA_LEVERS.map(function(L){ const on=!!(c.levers||{})[L.key]; return `<button class=\"toolbtn${on?' on':''}\" data-do=\"arena-lever:${L.key}\"${on?' style=\"outline:2px solid currentColor\"':''}>${on?'\\u2713 ':''}${L.label}</button>`; }).join(' ')}</div>\n    <h3 class=\"sub-h\" style=\"font-size:1.05em\">Who goes first</h3>"
 ],
 [
  "lever clicks",
  "  else if(d.indexOf('arena-n:')===0) c.n=+v||1;",
  "  else if(d.indexOf('arena-n:')===0) c.n=+v||1;\n  else if(d.indexOf('arena-lever:')===0){ c.levers=c.levers||{}; c.levers[v]=!c.levers[v]; }"
 ]
]
def main():
    if not os.path.exists(SRC): sys.exit('Run from the repo root: %s not found.' % SRC)
    s = open(SRC, encoding='utf-8').read()
    if 'romeojuliet' not in s: sys.exit('This is not the live src/game.src.html.')
    if 'fix_arena_levers' in s: sys.exit('Already applied. Nothing changed.')
    if 'AI vs AI batch (fix_arena_sim)' not in s: sys.exit('Run fix_arena_sim.py first. Nothing changed.')
    for label, a, _ in EDITS:
        if s.count(a) != 1: sys.exit('Anchor "%s" found %d times (need 1). Nothing changed.' % (label, s.count(a)))
    for _, a, b in EDITS: s = s.replace(a, b, 1)
    shutil.copy2(SRC, SRC + '.bak')
    open(SRC, 'w', encoding='utf-8').write(s)
    print('fix_arena_levers: 5 rule levers added to the PreCon Arena. Backup: %s.bak' % SRC)
if __name__ == '__main__': main()
