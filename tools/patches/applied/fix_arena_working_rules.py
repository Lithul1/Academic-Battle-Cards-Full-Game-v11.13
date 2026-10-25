#!/usr/bin/env python3
"""
fix_arena_working_rules.py — makes the working playtest rule set the Arena default,
and lets the player choose which ABC they give up.

WORKING RULES (now pre-selected on the Arena screen)
  Spend 1 ABC per attack \u00b7 Commanders return once \u00b7 Offstage once per turn \u00b7 AI 100%
  Two new buttons: "Working playtest rules" and "Baseline (all off)". Every
  lever can still be toggled individually.

PLAYER CHOOSES WHAT TO SACRIFICE
  * Spend 1 ABC: after your attack resolves, a picker lists the ABCs that paid
    for it (type and power). The one you pick goes to the discard; the rest stay
    attached. One option = no picker. With "ABC power adds to damage" on, every
    charged ABC's power still counts for the attack; the choice is which one you
    keep for later.
  * Offstage: after choosing the character, a picker lists every ABC that could
    pay, on that character or in your hand (type and power). One option = no
    picker.
  * AI: spends its lowest-power ABC after an attack (was: the first one), and
    still pays Offstage with a Block ABC first.

USAGE (repo root, after fix_arena_offstage.py):
  python3 fix_arena_working_rules.py      then   python3 build.py
Writes src/game.src.html.bak.  Refuses to run twice.
"""
import os, shutil, sys
SRC = os.path.join('src', 'game.src.html')
EDITS = [
 [
  "working rules are the default",
  "APP.arena={ a:(L[0]||{}).id, b:(L[1]||L[0]||{}).id, ctrlA:'human', ctrlB:'ai', first:'random' };",
  "APP.arena={ a:(L[0]||{}).id, b:(L[1]||L[0]||{}).id, ctrlA:'human', ctrlB:'ai', first:'random', levers:arenaWorkingLevers() };",
  1
 ],
 [
  "preset buttons",
  "<h3 class=\"sub-h\" style=\"font-size:1.05em\">Rule levers <small style=\"font-weight:normal\">(all off = baseline)</small></h3>",
  "<h3 class=\"sub-h\" style=\"font-size:1.05em\">Rule levers <small style=\"font-weight:normal\">(working playtest rules: Spend 1 ABC \\u00b7 Commanders return once \\u00b7 Offstage \\u00b7 AI 100%)</small></h3><div class=\"sub-actions\"><button class=\"toolbtn\" data-do=\"arena-preset:working\">Working playtest rules</button> <button class=\"toolbtn\" data-do=\"arena-preset:baseline\">Baseline (all off)</button></div>",
  1
 ],
 [
  "preset clicks",
  "  else if(d.indexOf('arena-lever:')===0){ c.levers=c.levers||{}; c.levers[v]=!c.levers[v]; }",
  "  else if(d.indexOf('arena-lever:')===0){ c.levers=c.levers||{}; c.levers[v]=!c.levers[v]; }\n  else if(d.indexOf('arena-preset:')===0){ c.levers=(v==='working')?arenaWorkingLevers():{}; }",
  1
 ],
 [
  "spend 1 ABC: player chooses",
  "    const _k=spentAtk.filter(c=>!c._wild), _d=_k.shift(); A.discard.push(_d);\n    _k.reverse().forEach(function(c){ (c.type==='BLOCK'?att.blkCharge:att.atkCharge).unshift(c); });\n    pushLog(`${att.name} spends 1 ABC \\u2014 ${_k.length} stay attached.`); }",
  "    const _k=spentAtk.filter(c=>!c._wild);\n    if(side==='you' && !S._sim){   /* the player chooses which ABC is spent once the attack resolves (arenaSpendPrompt) */\n      _k.slice().reverse().forEach(function(c){ (c.type==='BLOCK'?att.blkCharge:att.atkCharge).unshift(c); });\n      S._spendPick={ uid:att.uid, cids:_k.map(function(c){ return c.cid; }) }; }\n    else { _k.sort(function(x,y){ return (x.power||0)-(y.power||0); }); const _d=_k.shift(); A.discard.push(_d);   /* AI spends its lowest-power ABC */\n      _k.reverse().forEach(function(c){ (c.type==='BLOCK'?att.blkCharge:att.atkCharge).unshift(c); });\n      pushLog(`${att.name} spends 1 ABC \\u2014 ${_k.length} stay attached.`); } }",
  1
 ],
 [
  "Offstage: pay with a named ABC",
  "  let paid=null;\n  if(pay!=='hand' && (c.blkCharge.length||c.atkCharge.length)) paid=(c.blkCharge.length?c.blkCharge:c.atkCharge).pop();\n  else {",
  "  let paid=null;\n  if(pay && pay!=='char' && pay!=='hand'){   /* the player named the exact ABC (its cid) */\n    const take=function(arr){ const k=arr.findIndex(function(a){ return a.cid===pay; }); return k>=0?arr.splice(k,1)[0]:null; };\n    paid=take(c.atkCharge)||take(c.blkCharge)||take(p.hand); if(!paid) return false; }\n  else if(pay!=='hand' && (c.blkCharge.length||c.atkCharge.length)) paid=(c.blkCharge.length?c.blkCharge:c.atkCharge).pop();\n  else {",
  1
 ],
 [
  "Offstage: player picks the exact ABC",
  "        const c=p.team.find(function(t){ return t.uid===uid; }); if(!c) return; const own=(c.atkCharge.length+c.blkCharge.length)>0, hand=p.hand.some(function(h){ return h.cat==='abc'; });\n        if(own&&hand) askPick('Pay 1 ABC from\\u2026',[{label:`${c.name}'s ABC`,val:'char'},{label:'Your hand',val:'hand'}],function(v){ arenaOffstage('you',uid,v); });\n        else arenaOffstage('you',uid,own?'char':'hand'); }); } }",
  "        const c=p.team.find(function(t){ return t.uid===uid; }); if(!c) return;\n        const lab=function(a,where){ return `${a.type==='BLOCK'?'Block':'Attack'} ABC \\u00b7 power ${a.power||1} \\u2014 ${where}`; };\n        const opts=c.atkCharge.concat(c.blkCharge).map(function(a){ return {label:lab(a,'on '+c.name), val:a.cid}; })\n          .concat(p.hand.filter(function(h){ return h.cat==='abc'; }).map(function(a){ return {label:lab(a,'from your hand'), val:a.cid}; }));\n        if(opts.length===1) arenaOffstage('you',uid,opts[0].val);\n        else askPick(`Which ABC does ${c.name} discard to go offstage?`, opts, function(cid){ arenaOffstage('you',uid,cid); }); }); } }",
  1
 ],
 [
  "render: open the spend prompt once the attack has resolved",
  "    const r=_render.apply(this,arguments);\n    try{ if(S&&S._tel){ arenaScan(); if(S.over&&!S._telDone) arenaTelEnd(); } }catch(e){} return r; };",
  "    const r=_render.apply(this,arguments);\n    try{ if(S&&S._tel){ arenaScan(); if(S.over&&!S._telDone) arenaTelEnd(); } }catch(e){}\n    try{ arenaSpendPrompt(); }catch(e){} return r; };",
  1
 ],
 [
  "working-rules module",
  "\nwindow.ABC_DEBUG = {",
  "\n/* ---- Working playtest rules (fix_arena_working_rules) ---- */\nfunction arenaWorkingLevers(){ return { keep1:true, ret1:true, offstage:true, ai100:true }; }\n/* Spend 1 ABC: after the player's attack resolves, they pick which spent ABC goes to the discard. */\nfunction arenaSpendPrompt(){ const P=S&&S._spendPick; if(!P||busy||S.picker||S.over) return;\n  S._spendPick=null; const p=S.you, att=p.team.find(function(c){ return c.uid===P.uid; });\n  const pool=att?att.atkCharge.concat(att.blkCharge).filter(function(c){ return P.cids.indexOf(c.cid)>=0; }):[];\n  if(!att||att.hp<=0||!pool.length) return;\n  const spend=function(cid){ const take=function(arr){ const k=arr.findIndex(function(a){ return a.cid===cid; }); return k>=0?arr.splice(k,1)[0]:null; };\n    const x=take(att.atkCharge)||take(att.blkCharge);\n    if(x){ p.discard.push(x); pushLog(`${att.name} spends 1 ${x.type==='BLOCK'?'Block':'Attack'} ABC (power ${x.power||1}) \\u2014 ${pool.length-1} stay attached.`); } };\n  if(pool.length===1){ spend(pool[0].cid); render(); return; }\n  askPick(`${att.name} attacked \\u2014 which ABC does it spend? The rest stay attached.`,\n    pool.map(function(c){ return {label:`${c.type==='BLOCK'?'Block':'Attack'} ABC \\u00b7 power ${c.power||1}`, val:c.cid}; }), function(cid){ spend(cid); });\n}\n\nwindow.ABC_DEBUG = {",
  1
 ]
]
def main():
    if not os.path.exists(SRC): sys.exit('Run from the repo root: %s not found.' % SRC)
    s = open(SRC, encoding='utf-8').read()
    if 'romeojuliet' not in s: sys.exit('This is not the live src/game.src.html.')
    if 'fix_arena_working_rules' in s: sys.exit('Already applied. Nothing changed.')
    if 'fix_arena_offstage' not in s: sys.exit('Run fix_arena_offstage.py first. Nothing changed.')
    for label, a, _, n in EDITS:
        if s.count(a) != n: sys.exit('Anchor "%s" found %d times (need %d). Nothing changed.' % (label, s.count(a), n))
    for _, a, b, _ in EDITS: s = s.replace(a, b)
    shutil.copy2(SRC, SRC + '.bak')
    open(SRC, 'w', encoding='utf-8').write(s)
    print('fix_arena_working_rules: working playtest rules are the Arena default; players choose their ABC. Backup: %s.bak' % SRC)
if __name__ == '__main__': main()
