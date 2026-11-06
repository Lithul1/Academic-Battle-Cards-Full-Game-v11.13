#!/usr/bin/env python3
"""fix_scrim_d20.py -- Literary Scrimmage: d20 skill checks in events (with a trivia bonus) and illuminated boss reveals.

Run from the repo root:   python3 fix_scrim_d20.py
                          python3 build.py
Undo:                     restore src/game.src.html from the .bak this writes.
Needs:                    fix_scrim_tome.py.

WHAT IT DOES
  * Every Scrimmage event gains one skill check (Wits, Cunning, Resolve or Charm, DC 11-14). Before the roll you may
    answer a trivia question from your kit's book: a correct answer adds +5. Each party member whose archetype suits the
    skill adds +2 (up to +4). A natural 20 always succeeds (+15 IP); a natural 1 always fails.
  * Most events keep their existing choices beside the check. Three gambles force the roll (no walking away): the
    Vending Machine, Lost & Found and Cafeteria Mystery Meat. Keeping the Mystery Meat down gives +10 base attack
    for the rest of the run (stacks; saved with the run; shown in the battle log).
  * Before each Algorithm boss, an illuminated bestiary page: portrait, HP, its archive lore, its curse(s) and moves,
    then "Draw steel".
"""
import os, sys, shutil, datetime
JS = r'''/* fix_scrim_d20 */
/* fix_scrim_d20: d20 skill checks in Scrimmage events, a trivia question that adds +5 to the roll, and an illuminated
   bestiary page before each Algorithm boss. Every existing event choice stays exactly as it was; each event gains one
   check. Failure on some checks falls back to that event's own existing outcome. */
const QD_SKILLS={
  Wits:['Mentor','Elder','Inquisitor','Sentinel'],
  Cunning:['Trickster','Shadow','Outlaw','Corrupter','Scourge','Urchin','Fallen'],
  Resolve:['Steadfast','Martyr','Monument','Gatekeeper','Warden','Zealot','Force of Nature'],
  Charm:['Hero','Paragon','Innocent']
};
/* force:1 = a gamble you cannot walk away from: the check replaces the event's choices.
   one check per event: ok = what success gives; no = what failure costs ('base:i' replays that event's own choice i) */
const QD_CHECKS={
  vending:{ force:1, label:'Give the machine a sharp knock', skill:'Cunning', dc:12, ok:['art'], no:['hp',8], okT:'It shudders and drops something for free', noT:'It bites back' },
  extracredit:{ label:'Argue the grading rubric', skill:'Wits', dc:13, ok:['ip',30], no:['lf',2], okT:'The professor concedes the point', noT:'A late penalty is applied' },
  professor:{ label:'Debate the professor for something rarer', skill:'Wits', dc:14, ok:['rareart'], no:['hp',10], okT:'Impressed, she opens the locked cabinet', noT:'She is unmoved, and the debate exhausts you' },
  overdue:{ label:'Talk your way out of the fines', skill:'Charm', dc:12, ok:['lf',3], no:['base',1], okT:'The librarian waives it — and finds a refund', noT:'She is not charmed; the distraction follows you' },
  substitute:{ label:'Interview the guest lecturer', skill:'Charm', dc:13, ok:['ip',25], no:['hp',6], okT:'A rousing exchange of ideas', noT:'An awkward silence' },
  lostfound:{ force:1, label:'Rummage through both piles', skill:'Cunning', dc:14, ok:['art+lf',5], no:['hp',10], okT:'You come away with a trinket and loose change', noT:'A mousetrap snaps shut' },
  studygroup:{ label:'Lead the study session', skill:'Wits', dc:12, ok:['heal'], no:['base',0], okT:'You keep everyone focused — healed, and still sharp', noT:'It drags on; rested but exhausted' },
  mysterymeat:{ force:1, label:'Eat it — and keep it down', skill:'Resolve', dc:11, ok:['atk',10], no:['base',0], okT:'Protein. Your whole party feels stronger', noT:'Your stomach has other ideas' },
  careerfair:{ label:'Negotiate a better rate', skill:'Charm', dc:13, ok:['career',4], no:['career',2], okT:'A recruiter pays a premium', noT:'They lowball you' }
};
const ABC_QD={};
/* +base attack from events lives on SCRIM.qdAtk, saved beside the run */
const qdStartKitBase=scrimStartKit;
scrimStartKit=function(){ SCRIM.qdAtk=0; return qdStartKitBase.apply(this,arguments); };
const qdSaveBase=scrimSave;
scrimSave=function(){ const r=qdSaveBase.apply(this,arguments); try{ if(SCRIM.active) localStorage.setItem('abc_scrim_d20',JSON.stringify({atk:SCRIM.qdAtk||0})); }catch(e){} return r; };
const qdLoadBase=scrimLoadSave;
scrimLoadSave=function(){ const ok=qdLoadBase.apply(this,arguments); try{ if(ok){ const j=JSON.parse(localStorage.getItem('abc_scrim_d20')||'{}'); SCRIM.qdAtk=+j.atk||0; } }catch(e){ SCRIM.qdAtk=0; } return ok; };
const qdClearBase=scrimClearSave;
scrimClearSave=function(){ try{ localStorage.removeItem('abc_scrim_d20'); }catch(e){} return qdClearBase.apply(this,arguments); };
function qdArch(rec){ const d=rec.fe?firstedById(rec.id):(DATA.characters[rec.deck]||[]).find(function(c){ return c.id===rec.id; }); return d?(d.archetype||''):''; }
function qdBonus(skill){
  const L=QD_SKILLS[skill]||[], who=[];
  (SCRIM.team||[]).forEach(function(rec){ if(rec.curHp>0 && L.indexOf(qdArch(rec))>=0) who.push(rec); });
  return { n:Math.min(4,2*who.length), who:who.map(function(r){ const d=r.fe?firstedById(r.id):(DATA.characters[r.deck]||[]).find(function(c){ return c.id===r.id; }); return d?d.name.split(' ')[0]:''; }).filter(Boolean) };
}
function qdQuestion(){
  const kit=(typeof SCRIM_KITS!=='undefined')&&SCRIM_KITS[SCRIM.kit], deck=(kit&&DATA.abcs[kit.deck])?kit.deck:Object.keys(DATA.abcs)[0];
  const pool=(DATA.abcs[deck]||[]).filter(function(a){ return a && a.q && a.opts && a.opts.length>1 && a.ans!=null; });
  return pool.length?pool[rnd(pool.length)]:null;
}
function qdApply(fx,good){
  const k=fx[0], n=fx[1]; let msg='';
  const art=function(t){ const id=scrimGrantArtifact(t); return id&&SCRIM_ART[id]?(SCRIM_ART[id].ic+' '+SCRIM_ART[id].name):null; };
  if(k==='art'){ const a=art(['common','uncommon']); if(a) msg='<b>'+a+'</b>'; else { META.ip=(META.ip||0)+15; metaSave(); msg='<b>+15 Intellect Points</b>'; } }
  else if(k==='rareart'){ const a=art(['uncommon','rare'])||art(['common','uncommon']); if(a) msg='<b>'+a+'</b>'; else { META.ip=(META.ip||0)+25; metaSave(); msg='<b>+25 Intellect Points</b>'; } }
  else if(k==='art+lf'){ const a=art(['common','uncommon']); SCRIM.lf=(SCRIM.lf||0)+n; msg=(a?'<b>'+a+'</b> and ':'')+'<b>+'+n+' Late Fees</b>'; }
  else if(k==='ip'){ META.ip=(META.ip||0)+n; metaSave(); msg='<b>+'+n+' Intellect Points</b>'; }
  else if(k==='lf'){ if(good){ SCRIM.lf=(SCRIM.lf||0)+n; msg='<b>+'+n+' Late Fees</b>'; } else { const l=Math.min(n,SCRIM.lf||0); SCRIM.lf=(SCRIM.lf||0)-l; msg=l?('<b>−'+l+' Late Fees</b>'):'nothing to lose'; } }
  else if(k==='hp'){ SCRIM.team.forEach(function(t){ if(t.curHp>0) t.curHp=Math.max(1,t.curHp-n); }); msg='<b>−'+n+' HP</b> to each of your characters'; }
  else if(k==='heal'){ SCRIM.team.forEach(function(t){ if(t.curHp>0) t.curHp=n?Math.min(t.maxHp,t.curHp+n):t.maxHp; }); msg=n?('<b>+'+n+' HP</b> to each of your characters'):'<b>team healed to full</b>'; }
  else if(k==='atk'){ SCRIM.qdAtk=(SCRIM.qdAtk||0)+n; msg='<b>+'+n+' base attack</b> for the rest of the run (now +'+SCRIM.qdAtk+')'; }
  else if(k==='career'){ const lf=SCRIM.lf||0, ip=lf*n; META.ip=(META.ip||0)+ip; metaSave(); SCRIM.lf=0; msg='<b>+'+ip+' Intellect Points</b> for '+lf+' Late Fees ('+n+'× rate)'; }
  return msg;
}
/* the check page: question (optional bonus) → roll → outcome */
function qdScreen(){
  const ev=SCRIM_EVENTS[SCRIM.event], C=QD_CHECKS[SCRIM.event], Q=ABC_QD.st, b=qdBonus(C.skill);
  let body='';
  if(Q.stage==='q'){
    const q=Q.q;
    body=q?('<div class="qd-step">Steady your mind — answer correctly for <b>+5</b> to the roll.</div><div class="qd-q">'+stEsc(q.q)+'</div><div class="qd-opts">'
      +q.opts.map(function(o,i){ return '<button type="button" class="qd-opt" data-st="qd:ans:'+i+'">'+stEsc(o)+'</button>'; }).join('')+'</div><button type="button" class="qd-skip" data-st="qd:ans:-1">Roll without answering ›</button>')
      :'<div class="qd-step">No question to hand — roll on your wits alone.</div><button class="bigbtn" data-st="qd:ans:-1">Roll the d20 ›</button>';
  } else {
    const q=Q.q, tb=Q.correct?5:0;
    const ansLine=Q.ans==null||Q.ans<0?'':(Q.correct?'<div class="qd-ans ok">✓ Correct — <b>+5</b> to the roll.</div>':'<div class="qd-ans bad">✗ The answer was “'+stEsc(q.opts[q.ans])+'.” No bonus.</div>');
    const die='<div class="qd-d20'+(Q.stage==='roll'?' spin':'')+'" id="qdDie"><svg viewBox="0 0 100 100" aria-hidden="true"><polygon points="50,3 93,27 93,73 50,97 7,73 7,27" fill="#8e2a1c" stroke="#3b140c" stroke-width="4"/><polygon points="50,22 77,66 23,66" fill="none" stroke="#f3d9b0" stroke-width="2" opacity=".6"/></svg><span>'+(Q.stage==='done'?Q.roll:'?')+'</span></div>';
    let res='';
    if(Q.stage==='done'){
      res='<div class="qd-sum">'+Q.roll+(b.n?' + '+b.n+' (party)':'')+(tb?' + 5 (answer)':'')+' = <b>'+Q.total+'</b> against DC '+C.dc+'</div>'
        +'<div class="qd-verdict '+(Q.ok?'ok':'bad')+'">'+(Q.roll===20?'Natural 20! ':(Q.roll===1?'Natural 1. ':''))+(Q.ok?'Success':'Failure')+'</div>';
    }
    body=ansLine+'<div class="qd-rollrow">'+die+'<div>'+res+'</div></div>'
      +(Q.stage==='roll'?'':'<div class="qd-go"><button class="bigbtn" data-st="qd:finish">Continue ›</button></div>');
  }
  return '<div class="scrim-wrap scrim-ink"><div class="scrim-panel evt qd-panel"><div class="evt-ic">'+ev.ic+'</div><div class="st-runhead">A SKILL CHECK · '+C.skill.toUpperCase()+' · DC '+C.dc+'</div>'
    +'<div class="scrim-title sm">'+stEsc(C.label)+'</div>'
    +'<p class="qd-bonus">'+(b.n?('Your party adds <b>+'+b.n+'</b> ('+stEsc(b.who.join(' & '))+' — '+C.skill+')'):'No one in your party is suited to '+C.skill+' (+0)')+'. A natural 20 always succeeds; a natural 1 always fails.</p>'
    +body+'</div></div>';
}
function qdStart(){ ABC_QD.st={ ev:SCRIM.event, stage:'q', q:qdQuestion(), ans:null, correct:false, roll:0, total:0, ok:false }; render(); }
function qdAnswer(i){
  const Q=ABC_QD.st; if(!Q||Q.stage!=='q') return;
  Q.ans=i; Q.correct=!!(Q.q && i>=0 && i===Q.q.ans);
  try{ SFX.card(Q.correct?'card_slide':'book_flip',0.5); }catch(e){}
  Q.stage='roll'; render();
  const C=QD_CHECKS[Q.ev], b=qdBonus(C.skill), roll=1+rnd(20), ms=(typeof stCalm==='function'&&stCalm())?0:Math.round(typeof abcPace==='function'?abcPace(1100):1100);
  Q.roll=roll; Q.total=roll+b.n+(Q.correct?5:0); Q.ok=roll===20 || (roll!==1 && Q.total>=C.dc);
  let k=0; const spin=setInterval(function(){ const s=document.querySelector('#qdDie span'); if(s) s.textContent=1+rnd(20); if(++k>8) clearInterval(spin); }, Math.max(40,ms/10));
  setTimeout(function(){ clearInterval(spin); Q.stage='done'; render(); try{ SFX.card('book_flip',0.7); }catch(e){} }, ms);
}
function qdFinish(){
  const Q=ABC_QD.st; if(!Q||Q.stage!=='done') return; const C=QD_CHECKS[Q.ev]; ABC_QD.st=null;
  const head='<span class="qd-tag '+(Q.ok?'ok':'bad')+'">d20 '+Q.roll+' → '+Q.total+' vs DC '+C.dc+' · '+(Q.ok?'Success':'Failure')+'</span><br>';
  const fx=Q.ok?C.ok:C.no;
  if(fx[0]==='base'){ scrimEventChoose(fx[1]); SCRIM._eventResult=head+stEsc(C.noT)+'. '+(SCRIM._eventResult||''); render(); scrimSave(); return; }
  let msg=qdApply(fx,Q.ok);
  if(Q.ok && Q.roll===20){ META.ip=(META.ip||0)+15; metaSave(); msg+=' — and <b>+15 IP</b> for the natural 20'; }
  SCRIM._eventResult=head+stEsc(Q.ok?C.okT:C.noT)+': '+msg+'.'; render(); scrimSave();
}
/* the event page gains the check; while a check is under way it owns the page */
const qdEventBase=scrimEventScreen;
scrimEventScreen=function(){
  const C=QD_CHECKS[SCRIM.event];
  if(C && ABC_QD.st && ABC_QD.st.ev===SCRIM.event && !SCRIM._eventResult) return qdScreen();
  const h=qdEventBase.apply(this,arguments);
  if(!C || SCRIM._eventResult) return h;
  const b=qdBonus(C.skill);
  const btn='<button class="evt-choice qd-check'+(C.force?' qd-forced':'')+'" data-st="qd:start"><span class="qd-dc">DC '+C.dc+'</span><span>'+stEsc(C.label)+'<small>'+C.skill+' check'+(b.n?' · +'+b.n+' from your party':'')+' · answer correctly for +5</small></span><span class="qd-d">🎲</span></button>';
  if(C.force){ const i=h.indexOf('<div class="evt-choices">'); if(i>=0) return h.slice(0,i)+'<div class="qd-force">No walking away — the dice decide.</div><div class="evt-choices">'+btn+'</div></div></div>'; }
  return h.replace('<div class="evt-choices">','<div class="evt-choices">'+btn);
};
/* ---------- the illuminated bestiary page before each Algorithm boss ---------- */
function qdBossPage(){
  const R=ABC_QD.reveal, node=SCRIM.map.cols[R.c][R.r], B=SCRIM_BOSSES[node.boss]; if(!B) return '';
  const img=(window.ABC_BOSS_IMG||{})[node.boss], pos=(window.ABC_BOSS_IMGPOS||{})[node.boss]||'50% 30%';
  let hp=B.hp; try{ hp=Math.round(B.hp*scrimActMul()); }catch(e){}
  /* the battle picks its curse when it starts (half the time the alternate; always the alternate in the Doctoral Program) */
  const curses=SCRIM.doctoral&&B.altName?[[B.altName,B.altText]]:[[B.shiftName,B.shiftText]].concat(B.altName?[[B.altName,B.altText]]:[]);
  const mv=function(m,ic){ return m?'<div class="qd-mv"><b>'+ic+' '+stEsc(m.n)+'</b> '+stEsc(m.t||'')+'</div>':''; };
  const first=String(B.name||'?').charAt(0), rest=String(B.name||'').slice(1);
  const lore=(typeof BOSS_LORE!=='undefined'&&BOSS_LORE[node.boss])||'';
  return `<div class="scrim-wrap scrim-ink st-desk"><div class="qd-boss"><div class="qd-candle"></div>
    <div class="st-runhead qd-gold">FROM THE BESTIARY · ${SCRIM.doctoral?('SEMESTER '+(SCRIM.semester||1)):('ACT '+stRoman(SCRIM.act||1))}</div>
    <div class="qd-arch">${img?`<img src="${img}" alt="" style="object-position:${pos}">`:`<span class="qd-glyph">♛</span>`}</div>
    <h2 class="qd-name"><span class="qd-cap">${stEsc(first)}</span>${stEsc(rest)}</h2>
    <div class="qd-sub">${stEsc(B.sub||'An Algorithm Core')} · ${hp} HP</div>
    ${lore?`<p class="qd-lore">${lore}</p>`:''}
    <div class="qd-curse">${curses.length>1?'<i>It will unleash one of two curses:</i>':''}${curses.map(function(c){ return '<p><b>Curse · '+stEsc(c[0]||'')+'</b><br>'+stEsc(c[1]||'')+'</p>'; }).join('')}</div>
    <div class="qd-moves">${mv(B.atk,'⚔')}${mv(B.blk,'⛊')}</div>
    <div class="qd-btns"><button class="st-tab" data-st="qd:bossback">‹ Back to the map</button><button class="bigbtn" data-st="qd:fight">Draw steel ›</button></div>
  </div></div>`;
}
const qdScreenBase=scrimScreen;
scrimScreen=function(){ if(SCRIM.view==='bossreveal' && ABC_QD.reveal){ try{ const h=qdBossPage(); if(h) return h; }catch(e){} } return qdScreenBase.apply(this,arguments); };
const qdHandleBase=handleScrim;
handleScrim=function(cmd){
  const p=String(cmd||'').split(':');
  if(p[0]==='node' && !ABC_QD.pass){
    try{ const c=+p[1], r=+p[2], node=SCRIM.map&&SCRIM.map.cols[c]&&SCRIM.map.cols[c][r];
      if(node && node.boss && SCRIM_BOSSES[node.boss] && scrimReachable(c,r)){ ABC_QD.reveal={c:c,r:r,cmd:cmd}; SCRIM.view='bossreveal'; try{ SFX.card('book_flip',0.7); }catch(e){} render(); return; } }catch(e){}
  }
  return qdHandleBase.apply(this,arguments);
};
window.addEventListener('click',function(e){
  const b=e.target&&e.target.closest&&e.target.closest('[data-st^="qd:"]'); if(!b) return;
  e.stopPropagation(); e.preventDefault();
  const p=b.getAttribute('data-st').split(':');
  if(p[1]==='start') qdStart();
  else if(p[1]==='ans') qdAnswer(+p[2]);
  else if(p[1]==='finish') qdFinish();
  else if(p[1]==='fight' && ABC_QD.reveal){ const cmd=ABC_QD.reveal.cmd; ABC_QD.reveal=null; SCRIM.view='map'; ABC_QD.pass=true; try{ handleScrim(cmd); } finally{ ABC_QD.pass=false; } }
  else if(p[1]==='bossback'){ ABC_QD.reveal=null; SCRIM.view='map'; render(); }
},true);
if(typeof window!=='undefined') window.ABC_QDX={ qd:ABC_QD, checks:QD_CHECKS, skills:QD_SKILLS, bonus:qdBonus, start:qdStart, answer:qdAnswer, finish:qdFinish };
'''
CSS = r"""
/* fix_scrim_d20 */
/* the check choice on an event page */
body[data-screen="scrim"] .evt-choice.qd-check{ display:grid!important; grid-template-columns:auto 1fr auto; gap:10px; align-items:center; text-align:left; border-color:var(--st-rub)!important; background:rgba(142,42,28,.07)!important; }
.qd-check small{ display:block; font:italic 13px/1.3 var(--st-fell); color:var(--st-rub); }
.qd-dc,.qd-tag{ font:700 11px/1 var(--st-cinzel); letter-spacing:.06em; color:#f6e6c4; background:var(--st-ink); border-radius:4px; padding:6px 7px; white-space:nowrap; }
.qd-tag{ display:inline-block; margin-bottom:6px; }
.qd-tag.ok{ background:#1F6A6A; } .qd-tag.bad{ background:var(--st-rub); }
.qd-d{ font-size:20px; }
/* the check page */
.qd-panel{ text-align:center; }
.qd-bonus{ font:italic 15px/1.45 var(--st-fell); color:var(--st-ink2); margin:4px auto 12px; max-width:560px; }
.qd-step{ font:15px/1.4 'Spectral',Georgia,serif; color:var(--st-ink2); margin:6px 0; }
.qd-q{ font:400 22px/1.3 var(--st-fell); color:var(--st-ink); margin:8px auto 12px; max-width:560px; }
.qd-opts{ display:grid; gap:8px; max-width:520px; margin:0 auto; }
.qd-opt{ font:16px/1.3 'Spectral',Georgia,serif; color:var(--st-ink); background:rgba(255,248,226,.65); border:1.5px solid var(--st-ink2); border-radius:6px; box-shadow:0 2px 0 var(--st-ink2); padding:10px 12px; cursor:pointer; text-align:left; }
.qd-opt:hover{ background:#fff4d8; }
.qd-skip{ margin-top:10px; font:italic 14px/1 var(--st-fell); color:var(--st-ink2); background:none; border:0; cursor:pointer; text-decoration:underline; }
.qd-ans{ font:16px/1.4 'Spectral',Georgia,serif; margin:4px 0 6px; } .qd-ans.ok{ color:#1F6A6A; } .qd-ans.bad{ color:var(--st-rub); }
.qd-rollrow{ display:flex; align-items:center; justify-content:center; gap:20px; margin:12px 0 4px; min-height:110px; text-align:left; }
.qd-d20{ position:relative; width:96px; height:96px; flex:none; display:grid; place-items:center; }
.qd-d20 svg{ position:absolute; inset:0; }
.qd-d20 span{ position:relative; z-index:1; font:700 32px/1 var(--st-cinzel); color:#fff7e4; text-shadow:0 2px 0 rgba(0,0,0,.35); }
.qd-d20.spin{ animation:qdSpin .5s linear infinite; }
@keyframes qdSpin{ from{ transform:rotate(0) } to{ transform:rotate(360deg) } }
.qd-sum{ font:16px/1.4 'Spectral',Georgia,serif; color:var(--st-ink2); }
.qd-verdict{ font:400 30px/1.1 var(--st-fell); } .qd-verdict.ok{ color:#1F6A6A; } .qd-verdict.bad{ color:var(--st-rub); }
.qd-go{ margin-top:10px; }
/* the illuminated bestiary page (Concept C) */
.qd-boss{ position:relative; width:min(620px,96vw); margin:0 auto; padding:30px 34px 28px; text-align:center; color:#efe2c0; background:radial-gradient(80% 60% at 50% 25%,#2e2238,#16101c 75%);
  border-radius:6px; box-shadow:0 28px 46px rgba(0,0,0,.6),0 0 0 2px #6b4a22; overflow:hidden; }
.qd-boss::before{ content:""; position:absolute; inset:10px; border:2px solid #b8892c; border-radius:4px; pointer-events:none; box-shadow:inset 0 0 0 4px rgba(184,137,44,.18); }
.qd-boss::after{ content:""; position:absolute; inset:18px; border:1px dashed rgba(227,180,80,.35); border-radius:3px; pointer-events:none; }
.qd-candle{ position:absolute; inset:0; pointer-events:none; background:radial-gradient(60% 45% at 50% 28%,rgba(255,190,90,.16),transparent 70%); animation:stFlick 3.4s ease-in-out infinite; }
.qd-gold{ color:#d9b66a!important; position:relative; }
.qd-arch{ position:relative; width:220px; height:262px; margin:10px auto 14px; border-radius:110px 110px 8px 8px; overflow:hidden; border:4px solid #e3b450;
  background:radial-gradient(circle at 50% 35%,#5b4580,#20162b); box-shadow:0 0 0 3px #1c1520,0 0 0 6px #6b4a22,0 12px 30px rgba(0,0,0,.5); display:grid; place-items:center; }
.qd-arch img{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }
.qd-glyph{ font:400 90px/1 var(--st-cinzel); color:#e3b450; }
.qd-name{ position:relative; font:400 40px/1 var(--st-fell); color:#f3d58a; margin:6px 0 4px; }
.qd-cap{ display:inline-grid; place-items:center; width:54px; height:54px; margin-right:4px; vertical-align:-6px; font:400 40px/1 var(--st-fell); color:#fff4d6;
  background:linear-gradient(135deg,#8e2a1c,#5e1a10); border:2px solid #e3b450; box-shadow:inset 0 0 0 2px rgba(227,180,80,.5); }
.qd-sub{ position:relative; font:italic 16px/1.3 var(--st-fell); color:#c9b48a; }
.qd-curse{ position:relative; margin:16px auto 0; max-width:460px; border:1px solid #6b4a22; border-radius:6px; padding:10px 14px; font:14px/1.45 'Spectral',Georgia,serif; background:rgba(239,226,192,.06); text-align:left; }
.qd-curse i{ display:block; font:italic 13px/1.3 var(--st-fell); color:#c9b48a; margin-bottom:4px; }
.qd-curse p{ margin:4px 0; } .qd-curse b{ font:400 17px/1.2 var(--st-fell); color:#f3d58a; }
.qd-moves{ position:relative; margin:10px auto 0; max-width:460px; text-align:left; font:13.5px/1.4 'Spectral',Georgia,serif; color:#d8c7a2; }
.qd-mv b{ color:#efe2c0; font-weight:600; }
.qd-btns{ position:relative; display:flex; justify-content:center; align-items:center; gap:12px; margin-top:18px; flex-wrap:wrap; }
.qd-btns .st-tab{ border-radius:5px; }
@media (prefers-reduced-motion:reduce){ .qd-candle,.qd-d20.spin{ animation:none; } }
.qd-force{ font:italic 15px/1.3 var(--st-fell,'IM Fell English',Georgia,serif); color:var(--st-rub,#8e2a1c); text-align:center; margin:-2px 0 10px; }
.qd-check.qd-forced{ border-style:solid; box-shadow:0 0 0 2px var(--st-rub,#8e2a1c),0 2px 0 #4a3522; }
.qd-lore{ max-width:460px; margin:6px auto 12px; font:italic 15px/1.5 'Spectral',Georgia,serif; color:#e9dcc0; text-align:center; opacity:.92; }
"""

SRC=os.path.join('src','game.src.html'); MARK='/* fix_scrim_d20 */'
def apply(s, TAG):
    if MARK in s: sys.exit(f'{TAG} Already applied -- nothing to do.')
    for need,who in [('/* fix_scrim_tome */','fix_scrim_tome.py'),('function scrimEventChoose(','Literary Scrimmage'),('const SCRIM_EVENTS','Literary Scrimmage')]:
        if need not in s: sys.exit(f'{TAG} ERROR: run {who} first. Nothing written.')
    for l,a in [('end of <head> styles',"</style>\n</head>"),('JS insertion point',"function menuScreen(){\n")]:
        if s.count(a)!=1: sys.exit(f'{TAG} ERROR: anchor "{l}" found {s.count(a)} times (expected 1). Nothing written.')
    s=s.replace("</style>\n</head>",CSS+"</style>\n</head>",1)
    s=s.replace("function menuScreen(){\n",JS+"\nfunction menuScreen(){\n",1)
    DMG="  if(S.scrim && side==='you' && scrimHas('gutenberg')){ dmg+=5;"
    if s.count(DMG)!=1: sys.exit(f'{TAG} ERROR: anchor "Scrimmage attack bonuses" found {s.count(DMG)} times (expected 1). Nothing written.')
    s=s.replace(DMG,"  if(S.scrim && side==='you' && SCRIM.qdAtk){ dmg+=SCRIM.qdAtk; pushLog('Mystery Meat \u2014 +'+SCRIM.qdAtk+' base attack.'); }\n"+DMG,1)
    for need in [MARK,'SCRIM.qdAtk){ dmg+=SCRIM.qdAtk;','function qdBossPage(','.qd-boss{','scrimEventScreen=function']:
        if need not in s: sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
    return s

TAG='[fix_scrim_d20]'
if not os.path.exists(SRC): sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s=apply(open(SRC,encoding='utf-8').read(),TAG)
bak=SRC+'.bak_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); shutil.copyfile(SRC,bak)
open(SRC,'w',encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:',bak); print(f'{TAG} Next: python3 build.py')
