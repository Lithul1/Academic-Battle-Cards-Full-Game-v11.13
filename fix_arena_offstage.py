#!/usr/bin/env python3
"""
fix_arena_offstage.py — removes the Revise lever and adds the Offstage lever.

REMOVED  Revise (button, AI policy, revises_a/b CSV columns).
ADDED    Offstage once per turn (Arena lever, off by default; rules tag "offstage")
  * During your Strategize phase, one Backstage character (never the Active) may
    go offstage: discard 1 ABC from that character or from your hand.
  * It returns to hand together with its other attached ABCs.
  * Heal limit: it re-enters later with the damage it left with (minimum 10 HP),
    and it can't be replayed the same turn.
  * Evolved: returns as its base card; its Act cards go to the discard.
  * Commanders may go offstage; it counts as one of their returns (replay cost
    rises). With no returns left, a commander can't go offstage.
  * Player: "\u21e0 Offstage" button in the Strategize action bar, then pick the
    character (and where the ABC comes from, if both are possible).
  * AI: when Backstage is full and a host for an Act card in its hand is waiting
    in hand, it clears the weakest Backstage character that isn't a host
    (commanders kept).
  * Games CSV: offstage_a / offstage_b.

USAGE (repo root, after fix_arena_levers2.py):
  python3 fix_arena_offstage.py      then   python3 build.py
Writes src/game.src.html.bak.  Refuses to run twice.
"""
import os, shutil, sys
SRC = os.path.join('src', 'game.src.html')
EDITS = [
 [
  "remove Revise lever / add Offstage lever",
  "  { key:'revise',    label:'Revise once per turn',        tag:'revise' } ];",
  "  { key:'offstage',  label:'Offstage once per turn',      tag:'offstage' } ];",
  1
 ],
 [
  "rule field",
  "keepCharges:false, cmdReturns:null, revise:false,",
  "keepCharges:false, cmdReturns:null, offstage:false,",
  1
 ],
 [
  "lever applied",
  "ARENA_RULES.revise=on('revise');   /* fix_arena_levers2 */",
  "ARENA_RULES.offstage=on('offstage');   /* fix_arena_levers2; Offstage: fix_arena_offstage */",
  1
 ],
 [
  "remove Revise button",
  "      ${(S.arena&&ARENA_RULES.revise&&S.turn==='you'&&S.phase==='strategize'&&!S._sim)?`<button class=\"hv-disc${arenaCanRevise(S.you)?'':' off'}\" data-do=\"revisehand\" title=\"Put this card on the bottom of your deck and draw 1 (once per turn)\">\\u21bb Revise</button>`:''}\n",
  "",
  1
 ],
 [
  "remove Revise click / add Offstage click",
  "\n    else if(d==='revisehand'){ if(S && S._handView!=null){ const _i=S._handView; if(!arenaCanRevise(S.you)){ toast('You have already revised this turn.'); return; } S._handView=null; arenaRevise('you',_i); } }",
  "\n    else if(d==='offstage-start'){ if(S&&S.arena&&S.turn==='you'){ const p=S.you, el=p.team.filter(function(c){ return arenaOffOk(p,c); });\n      if(!el.length){ toast('No Backstage character can go offstage right now.'); return; }\n      askPick('Offstage \\u2014 which Backstage character?', el.map(function(c){ return {label:`${c.name} (${c.hp}/${c.maxHp} HP, ${c.atkCharge.length+c.blkCharge.length} ABC)`, val:c.uid}; }), function(uid){\n        const c=p.team.find(function(t){ return t.uid===uid; }); if(!c) return; const own=(c.atkCharge.length+c.blkCharge.length)>0, hand=p.hand.some(function(h){ return h.cat==='abc'; });\n        if(own&&hand) askPick('Pay 1 ABC from\\u2026',[{label:`${c.name}'s ABC`,val:'char'},{label:'Your hand',val:'hand'}],function(v){ arenaOffstage('you',uid,v); });\n        else arenaOffstage('you',uid,own?'char':'hand'); }); } }",
  1
 ],
 [
  "AI: Offstage instead of Revise",
  "    if(S.arena) arenaAiRevise(p);",
  "    if(S.arena){ arenaAiOffstage(p); arenaAiField(p); }",
  1
 ],
 [
  "telemetry columns",
  "revises_a:(T.revise||{}).A||0, revises_b:(T.revise||{}).B||0,",
  "offstage_a:(T.offstage||{}).A||0, offstage_b:(T.offstage||{}).B||0,",
  1
 ],
 [
  "remove Revise module / add Offstage module",
  "/* ---- Revise (fix_arena_levers2): once per turn, a card from hand goes to the bottom of the deck and you draw 1 ---- */\nfunction arenaCanRevise(p){ return !!(S&&S.arena&&ARENA_RULES.revise&&p&&p.flags._reviseTurn!==(S._turnNo||0)); }\nfunction arenaRevise(side,idx){ const p=S&&S[side]; if(!arenaCanRevise(p)) return false;\n  const card=p.hand[idx]; if(!card) return false;\n  p.hand.splice(idx,1); p.deck.push(card); dealOne(side); p.flags._reviseTurn=(S._turnNo||0);\n  if(S._tel){ S._tel.revise=S._tel.revise||{A:0,B:0}; S._tel.revise[p._arenaSide]=(S._tel.revise[p._arenaSide]||0)+1; }\n  pushLog(`${who(p)} revises \\u2014 ${p===S.you&&!S._sim?card.name||'a card':'a card'} goes to the bottom of the deck; draw 1.`); render(); return true; }\n/* AI: revise the deadest card in hand — an Act card with no host anywhere, a character it can't field, a second Lens */\nfunction arenaAiRevise(p){ if(!arenaCanRevise(p)) return;\n  const hostFor=function(a){ return p.team.some(function(t){ return t.hp>0 && actStageId(t)===a.from; }) ||\n    p.hand.some(function(h){ return h.cat==='char' && (h.fe?((h._cdef&&h._cdef.base)||[])[1]:h.charId)===a.from; }) ||\n    p.hand.some(function(h){ return h.cat==='act' && h.actId===a.from; }); };\n  let i=p.hand.findIndex(function(c){ if(c.cat!=='act') return false; const a=actById(c.actId); return a && !hostFor(a); });\n  if(i<0) i=p.hand.findIndex(function(c){ return c.cat==='char' && (!arenaCanField(p,c) || (drawnHasActive(p) && drawnBench(p)>=ARENA_RULES.benchMax)); });\n  if(i<0 && p.crit) i=p.hand.findIndex(function(c){ return c.cat==='crit'; });\n  if(i>=0) arenaRevise(S.you===p?'you':'opp', i); }\n",
  "/* ---- Offstage (fix_arena_offstage): once per turn, a Backstage character leaves play ----\n   Cost: discard 1 ABC from that character or from your hand. The character goes back to hand with its\n   other ABCs. It re-enters later with the damage it left with (min 10 HP) and can't be replayed the same\n   turn. An evolved character returns as its base card (Act cards to the discard). A commander's Offstage\n   counts as one of its returns; with none left it can't go offstage. */\nfunction arenaOffOk(p,c){ if(!(S&&S.arena&&ARENA_RULES.offstage&&p&&c)) return false;\n  if(p.flags._offTurn===(S._turnNo||0)) return false;\n  const i=p.team.indexOf(c); if(i<0||i===p.activeIdx||c.hp<=0) return false;\n  if(c._pmCmd && pmReturnCost(c)===null) return false;\n  return (c.atkCharge.length+c.blkCharge.length)>0 || p.hand.some(function(h){ return h.cat==='abc'; }); }\nfunction arenaOffstage(side,uid,pay){ const p=S&&S[side], c=p&&p.team.find(function(t){ return t.uid===uid; });\n  if(!arenaOffOk(p,c)) return false;\n  let paid=null;\n  if(pay!=='hand' && (c.blkCharge.length||c.atkCharge.length)) paid=(c.blkCharge.length?c.blkCharge:c.atkCharge).pop();\n  else { let k=p.hand.findIndex(function(h){ return h.cat==='abc'&&h.type==='BLOCK'; }); if(k<0) k=p.hand.findIndex(function(h){ return h.cat==='abc'; }); if(k>=0) paid=p.hand.splice(k,1)[0]; }\n  if(!paid) return false; p.discard.push(paid);\n  const dmg=Math.max(0,c.maxHp-c.hp), cost=c._pmCmd?pmReturnCost(c):0;\n  if(c._actBase){ c._offstaging=true; actOnKO(p,c); delete c._offstaging; }\n  const back=c.atkCharge.splice(0).concat(c.blkCharge.splice(0)); back.forEach(function(x){ x._new=true; p.hand.push(x); });\n  const def=c.fe?firstedById(c.id):((DATA.characters[p.setKey]||[]).find(function(x){ return x.id===c.id; })||c);\n  const card={ cat:'char', charId:c.id, name:def.name, accent:def.accent||'#444', hp:def.hp, fe:!!c.fe, _cdef:def,\n    cid:'os'+c.id+'_'+Math.random().toString(36).slice(2,6), _offDmg:dmg, _offTurn:(S._turnNo||0), _new:true };\n  if(c._pmCmd){ card._pmCmd=true; card._pmReturns=(c._pmReturns||0)+1; card._pmCost=cost; }\n  const i=p.team.indexOf(c); p.team.splice(i,1); if(i<p.activeIdx) p.activeIdx--;\n  p.hand.push(card); p.flags._offTurn=(S._turnNo||0);\n  if(S._tel){ S._tel.offstage=S._tel.offstage||{A:0,B:0}; S._tel.offstage[p._arenaSide]=(S._tel.offstage[p._arenaSide]||0)+1; }\n  pushLog(`${card.name} steps offstage (1 ${paid.type==='BLOCK'?'Block':'Attack'} ABC discarded)`+(back.length?` \\u2014 ${back.length} ABC back to hand`:'')+(dmg?` \\u2014 carries ${dmg} damage`:'')+'.');\n  render(); return true; }\n/* AI: when Backstage is full and a host for an Act card in hand is waiting in hand,\n   clear the weakest Backstage character that isn't itself a host (commanders kept). */\nfunction arenaAiOffstage(p){ if(!(S.arena&&ARENA_RULES.offstage)||p.flags._offTurn===(S._turnNo||0)) return;\n  if(drawnBench(p)<ARENA_RULES.benchMax) return;\n  const from=p.hand.filter(function(h){ return h.cat==='act'; }).map(function(h){ const a=actById(h.actId); return a&&a.from; }).filter(Boolean);\n  if(!from.length) return;\n  if(!p.hand.some(function(h){ return h.cat==='char' && from.indexOf(h.charId)>=0 && h._offTurn==null; })) return;\n  const bench=p.team.filter(function(c){ return !c._pmCmd && from.indexOf(actStageId(c))<0 && arenaOffOk(p,c); });\n  if(!bench.length) return;\n  const pick=bench.sort(function(x,y){ return x.hp-y.hp; })[0];\n  arenaOffstage(S.you===p?'you':'opp', pick.uid, (pick.atkCharge.length+pick.blkCharge.length)>0?'char':'hand'); }\n",
  1
 ],
 [
  "Offstage button",
  "    else if(S.phase==='strategize') actionBtn=`<button class=\"bigbtn\" data-do=\"engage\">Done — go to Engage ›</button><span class=\"hint\">Attaches left: ${you.attachesLeft} · Bookmarks: ${2-(you.flags.bmCount||0)} left</span>`;",
  "    else if(S.phase==='strategize') actionBtn=`<button class=\"bigbtn\" data-do=\"engage\">Done — go to Engage ›</button>${(S.arena&&ARENA_RULES.offstage&&!S._sim)?`<button class=\"toolbtn\" data-do=\"offstage-start\"${you.team.some(function(c){ return arenaOffOk(you,c); })?'':' style=\"opacity:.45\"'}>\\u21e0 Offstage</button>`:''}<span class=\"hint\">Attaches left: ${you.attachesLeft} · Bookmarks: ${2-(you.flags.bmCount||0)} left</span>`;",
  1
 ],
 [
  "not replayable the same turn (player)",
  "  if(!card||card.cat!=='char') return;\n  { const _k=",
  "  if(!card||card.cat!=='char') return;\n  if(card._offTurn!=null && card._offTurn===(S._turnNo||0)){ toast(`${card.name} went offstage this turn \\u2014 it can come back next turn.`); return; }\n  { const _k=",
  1
 ],
 [
  "not replayable the same turn (AI)",
  "function arenaCanField(p,card){ if(!card||card.cat!=='char') return false;",
  "function arenaCanField(p,card){ if(!card||card.cat!=='char') return false; if(card._offTurn!=null && card._offTurn===(S._turnNo||0)) return false;",
  1
 ],
 [
  "quiet Act-card exit (no KO caveat)",
  "  if(c.passive&&c.passive.koDiscardRandom&&p.hand.length){",
  "  if(!c._offstaging&&c.passive&&c.passive.koDiscardRandom&&p.hand.length){",
  1
 ],
 [
  "Offstage log line",
  "  pushLog(`${top}\\u2019s Act cards go to the discard; ${c.name} rests with the fallen.`);",
  "  pushLog(c._offstaging?`${top}\\u2019s Act cards go to the discard; ${c.name} steps offstage.`:`${top}\\u2019s Act cards go to the discard; ${c.name} rests with the fallen.`);",
  1
 ],
 [
  "re-enters with the damage it left with (3 sites)",
  "makeChar(card._cdef, p._hpScale||1.0);",
  "makeChar(card._cdef, p._hpScale||1.0); if(card._offDmg) ch.hp=Math.max(10,ch.maxHp-card._offDmg);",
  3
 ]
]
def main():
    if not os.path.exists(SRC): sys.exit('Run from the repo root: %s not found.' % SRC)
    s = open(SRC, encoding='utf-8').read()
    if 'romeojuliet' not in s: sys.exit('This is not the live src/game.src.html.')
    if 'fix_arena_offstage' in s: sys.exit('Already applied. Nothing changed.')
    if 'fix_arena_levers2' not in s: sys.exit('Run fix_arena_levers2.py first. Nothing changed.')
    for label, a, _, n in EDITS:
        if s.count(a) != n: sys.exit('Anchor "%s" found %d times (need %d). Nothing changed.' % (label, s.count(a), n))
    for _, a, b, _ in EDITS: s = s.replace(a, b)
    shutil.copy2(SRC, SRC + '.bak')
    open(SRC, 'w', encoding='utf-8').write(s)
    print('fix_arena_offstage: Revise removed, Offstage lever added. Backup: %s.bak' % SRC)
if __name__ == '__main__': main()
