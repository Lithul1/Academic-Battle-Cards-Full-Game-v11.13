#!/usr/bin/env python3
"""
fix_arena_offstage_ui.py — a visible way to send a Backstage character offstage.

Before: the only entry point was a small "Offstage" button in the Strategize
action bar, easy to miss and silent about why it was dimmed.

Now:
  * Tap any of your Backstage characters: its card shows "\u21e0 Send offstage
    (costs 1 ABC)" — or, if it can't go, the reason (not your Strategize phase,
    already used this turn, it's your Active, no ABC to pay, commander has no
    returns left, or Offstage is off in this match's rules).
  * The action-bar "\u21e0 Offstage\u2026" button still works; it skips straight to
    the character when only one is eligible and explains itself when none is.
  * Either way you then pick the exact ABC that pays (unchanged).
Arena only; nothing else changes.

USAGE (repo root, after fix_arena_working_rules.py):
  python3 fix_arena_offstage_ui.py      then   python3 build.py
Writes src/game.src.html.bak.  Refuses to run twice.
"""
import os, shutil, sys
SRC = os.path.join('src', 'game.src.html')
EDITS = [
 [
  "dispatch: action bar + Backstage card",
  "    else if(d==='offstage-start'){ if(S&&S.arena&&S.turn==='you'){ const p=S.you, el=p.team.filter(function(c){ return arenaOffOk(p,c); });\n      if(!el.length){ toast('No Backstage character can go offstage right now.'); return; }\n      askPick('Offstage \\u2014 which Backstage character?', el.map(function(c){ return {label:`${c.name} (${c.hp}/${c.maxHp} HP, ${c.atkCharge.length+c.blkCharge.length} ABC)`, val:c.uid}; }), function(uid){\n        const c=p.team.find(function(t){ return t.uid===uid; }); if(!c) return;\n        const lab=function(a,where){ return `${a.type==='BLOCK'?'Block':'Attack'} ABC \\u00b7 power ${a.power||1} \\u2014 ${where}`; };\n        const opts=c.atkCharge.concat(c.blkCharge).map(function(a){ return {label:lab(a,'on '+c.name), val:a.cid}; })\n          .concat(p.hand.filter(function(h){ return h.cat==='abc'; }).map(function(a){ return {label:lab(a,'from your hand'), val:a.cid}; }));\n        if(opts.length===1) arenaOffstage('you',uid,opts[0].val);\n        else askPick(`Which ABC does ${c.name} discard to go offstage?`, opts, function(cid){ arenaOffstage('you',uid,cid); }); }); } }",
  "    else if(d==='offstage-start'){ arenaOffstageStart(null); }\n    else if(d.indexOf('offstage:')===0){ S._benchView=null; arenaOffstageStart(d.slice(9)); }",
  1
 ],
 [
  "Backstage card: Send offstage button",
  "    ${benchChargeList(ch)}\n    <button class=\"pcb-close\" data-do=\"benchclose\">Close &#10005;</button>",
  "    ${benchChargeList(ch)}\n    ${(v.side==='you'&&S.arena&&ARENA_RULES.offstage&&!S._sim&&p.team.indexOf(ch)!==p.activeIdx)?arenaOffBtn(p,ch):''}\n    <button class=\"pcb-close\" data-do=\"benchclose\">Close &#10005;</button>",
  1
 ],
 [
  "action-bar button tooltip",
  "${(S.arena&&ARENA_RULES.offstage&&!S._sim)?`<button class=\"toolbtn\" data-do=\"offstage-start\"${you.team.some(function(c){ return arenaOffOk(you,c); })?'':' style=\"opacity:.45\"'}>\\u21e0 Offstage</button>`:''}",
  "${(S.arena&&ARENA_RULES.offstage&&!S._sim)?`<button class=\"toolbtn\" data-do=\"offstage-start\" title=\"Send a Backstage character back to your hand (costs 1 ABC). You can also tap a Backstage character.\"${you.team.some(function(c){ return arenaOffOk(you,c); })?'':' style=\"opacity:.45\"'}>\\u21e0 Offstage\\u2026</button>`:''}",
  1
 ],
 [
  "Offstage UI module",
  "\nwindow.ABC_DEBUG = {",
  "\n/* ---- Offstage entry points (fix_arena_offstage_ui): tap a Backstage character, or the action-bar button ---- */\nfunction arenaOffWhy(p,c){ if(!(S&&S.arena&&ARENA_RULES.offstage)) return 'Offstage is off in this match\\u2019s rules.';\n  if(S.turn!=='you'||S.phase!=='strategize') return 'Offstage happens during your Strategize phase.';\n  if(p.flags._offTurn===(S._turnNo||0)) return 'You have already used Offstage this turn.';\n  if(c){ const i=p.team.indexOf(c); if(i===p.activeIdx) return 'Your Active can\\u2019t go offstage \\u2014 only Backstage characters.';\n    if(c._pmCmd && pmReturnCost(c)===null) return `${c.name} has no returns left.`;\n    if(!(c.atkCharge.length+c.blkCharge.length) && !p.hand.some(function(h){ return h.cat==='abc'; })) return 'You need 1 ABC to pay \\u2014 on this character or in your hand.'; }\n  return ''; }\nfunction arenaOffBtn(p,c){ const why=arenaOffOk(p,c)?'':arenaOffWhy(p,c);\n  return why?`<div class=\"bv-ph\" style=\"opacity:.75;margin:.4em 0\">\\u21e0 Offstage: ${why}</div>`\n            :`<button class=\"bigbtn\" data-do=\"offstage:${c.uid}\" style=\"margin:.4em 0\">\\u21e0 Send offstage (costs 1 ABC)</button>`; }\nfunction arenaOffstageStart(uid){ if(!S) return; const p=S.you;\n  const go=function(c){ const why=arenaOffOk(p,c)?'':arenaOffWhy(p,c); if(why){ toast(why); render(); return; }\n    const lab=function(a,where){ return `${a.type==='BLOCK'?'Block':'Attack'} ABC \\u00b7 power ${a.power||1} \\u2014 ${where}`; };\n    const opts=c.atkCharge.concat(c.blkCharge).map(function(a){ return {label:lab(a,'on '+c.name), val:a.cid}; })\n      .concat(p.hand.filter(function(h){ return h.cat==='abc'; }).map(function(a){ return {label:lab(a,'from your hand'), val:a.cid}; }));\n    if(opts.length===1) arenaOffstage('you',c.uid,opts[0].val);\n    else askPick(`Which ABC does ${c.name} discard to go offstage?`, opts, function(cid){ arenaOffstage('you',c.uid,cid); }); };\n  if(uid){ const c=p.team.find(function(t){ return t.uid===uid; }); if(c) go(c); return; }\n  const gen=arenaOffWhy(p,null); if(gen){ toast(gen); return; }\n  const el=p.team.filter(function(c){ return arenaOffOk(p,c); });\n  if(!el.length){ toast('No Backstage character can go offstage \\u2014 each needs 1 ABC to pay, on it or in your hand.'); return; }\n  if(el.length===1){ go(el[0]); return; }\n  askPick('Offstage \\u2014 which Backstage character?', el.map(function(c){ return {label:`${c.name} (${c.hp}/${c.maxHp} HP, ${c.atkCharge.length+c.blkCharge.length} ABC)`, val:c.uid}; }),\n    function(id){ const c=p.team.find(function(t){ return t.uid===id; }); if(c) go(c); }); }\n\nwindow.ABC_DEBUG = {",
  1
 ]
]
def main():
    if not os.path.exists(SRC): sys.exit('Run from the repo root: %s not found.' % SRC)
    s = open(SRC, encoding='utf-8').read()
    if 'romeojuliet' not in s: sys.exit('This is not the live src/game.src.html.')
    if 'fix_arena_offstage_ui' in s: sys.exit('Already applied. Nothing changed.')
    if 'fix_arena_working_rules' not in s: sys.exit('Run fix_arena_working_rules.py first. Nothing changed.')
    for label, a, _, n in EDITS:
        if s.count(a) != n: sys.exit('Anchor "%s" found %d times (need %d). Nothing changed.' % (label, s.count(a), n))
    for _, a, b, _ in EDITS: s = s.replace(a, b)
    shutil.copy2(SRC, SRC + '.bak')
    open(SRC, 'w', encoding='utf-8').write(s)
    print('fix_arena_offstage_ui: Backstage cards now offer "Send offstage". Backup: %s.bak' % SRC)
if __name__ == '__main__': main()
