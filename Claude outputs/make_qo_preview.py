#!/usr/bin/env python3
"""make_qo_preview.py -- PREVIEW ONLY. Builds dist/ABC_quests_preview.html from your src + assets with the
Quests + Oaths applied in memory. src/ and assets/ are not touched.

Run from the repo root:   python3 make_qo_preview.py
Then open dist/ABC_quests_preview.html and start a Literary Scrimmage run.
"""
import os, sys, re, json
JS = r'''/* fix_scrim_quests */
/* fix_scrim_quests: Quests + Oaths for Literary Scrimmage.
   At the start of each Act (each Semester in the Doctoral Program) the Notice Board offers three Quests -- pick one --
   and two Oaths -- swear one or none. Goals and rewards scale with the run's tier (Honors level, Doctoral = one step up).
   Quests pay out the moment they are fulfilled; an Oath kept to the Act's boss pays bonus IP. Rules of play never change:
   everything is read from the events the game already reports. */
const QO_TIERS=['Normal','Honors I','Honors II','Honors III'];
const QO_IP=[25,35,50,70], QO_OATH_IP=[30,45,65,90], QO_LF=[6,8,10,12];
const QO_ART=[['common','uncommon'],['common','uncommon'],['uncommon','rare'],['uncommon','rare']];
const QO_QUESTS={
  unbroken:{ ic:'⚔', name:'The Unbroken Line', n:[2,3,3,4], rw:'art', txt:function(n){ return 'Win '+n+' battles in a row without any of your characters being knocked out.'; } },
  recite:{ ic:'✒', name:'Perfect Recitation', n:[8,10,12,15], rw:'ip', txt:function(n){ return 'Answer '+n+' trivia questions correctly in a row.'; } },
  bookworm:{ ic:'❦', name:'The Bookworm', n:[6,8,10,12], rw:'lf', txt:function(n){ return 'Play '+n+' Bookmarks this Act.'; } },
  thesis:{ ic:'⚜', name:'Defend the Thesis', n:[1,2,2,3], rw:'art', txt:function(n){ return 'Fulfil '+n+' Critical Lens thesis'+(n>1?'es':'')+' this Act.'; } },
  swift:{ ic:'➶', name:'The Swift Pen', n:[7,6,5,4], rw:'ip', txt:function(n){ return 'Win a battle within '+n+' of your turns.'; } },
  scourge:{ ic:'☄', name:'Scourge of the Feed', n:[5,7,9,12], rw:'lf', txt:function(n){ return 'Inflict '+n+' statuses on enemies this Act.'; } },
  carto:{ ic:'✠', name:'The Cartographer', n:[4,5,5,6], rw:'ip', txt:function(n){ return 'Visit '+n+' different kinds of place on the map this Act.'; } },
  frugal:{ ic:'⚖', name:'The Frugal Scholar', n:[6,10,14,18], rw:'art', end:true, txt:function(n){ return 'Reach the Act’s boss holding '+n+' or more Late Fees.'; } },
  medic:{ ic:'✚', name:'Field Medic', n:[1,1,1,1], rw:'ip', end:true, txt:function(){ return 'Defeat the Act’s boss with every character alive and above half HP.'; } },
  flourish:{ ic:'✺', name:'Flourish', n:[4,4,5,5], rw:'lf', txt:function(n){ return 'Play '+n+' or more cards in a single turn.'; } },
  slayer:{ ic:'☠', name:'Slay the Lesser Feed', n:[1,1,1,1], rw:'art', txt:function(n,t){ return 'Defeat a Thesis Defense'+(t>=2?' without a knockout':'')+'.'; } }
};
const QO_OATHS={
  unplugged:{ ic:'☕', name:'Oath of the Unplugged', txt:'Visit no Coffee Break this Act.' },
  austerity:{ ic:'⚖', name:'Oath of Austerity', txt:'Buy nothing at a Book Fair this Act.' },
  ironwill:{ ic:'⚔', name:'Oath of the Iron Will', txt:'Let no character be knocked out this Act.' },
  ascetic:{ ic:'✒', name:'Oath of the Ascetic', txt:'Take no card at a Study Break this Act.' }
};
const ABC_QO={ S:null, ko:0, turns:0, plays:0, banner:null };
function qoTier(){ const h=Math.max(0,Math.min(3,SCRIM.honors||0)); return Math.min(3,h+(SCRIM.doctoral?1:0)); }
function qoKey(){ return SCRIM.doctoral?('S'+(SCRIM.semester||1)):('A'+(SCRIM.act||1)); }
function qoPick(pool,k){ const a=pool.slice(), out=[]; while(a.length && out.length<k){ out.push(a.splice(rnd(a.length),1)[0]); } return out; }
function qoNeedBoard(){ return !!(SCRIM.active && (!SCRIM.quest || SCRIM.quest.key!==qoKey() || !SCRIM.quest.set)); }
function qoFresh(){
  const t=qoTier();
  SCRIM.quest={ key:qoKey(), tier:t, offered:qoPick(Object.keys(QO_QUESTS),3), oaths:qoPick(Object.keys(QO_OATHS),2), q:null, prog:0, done:false, paid:false, oath:null, broken:false, oathPaid:false, seen:[], set:false };
}
function qoGoal(){ const Q=SCRIM.quest, d=Q&&Q.q&&QO_QUESTS[Q.q]; return d?d.n[Q.tier]:0; }
function qoRewardText(id,t){ const d=QO_QUESTS[id], ip=QO_IP[t];
  if(d.rw==='ip') return '+'+Math.round(ip*1.6)+' IP';
  return (d.rw==='art'?(t>=2?'Rare relic':'Relic'):QO_LF[t]+' Late Fees')+' + '+ip+' IP'; }
/* progress */
function qoAdd(n,abs){ const Q=SCRIM.quest; if(!Q||!Q.q||Q.done) return; Q.prog=abs?n:Math.max(0,(Q.prog||0)+n); if(Q.prog>=qoGoal() && !QO_QUESTS[Q.q].end) qoComplete(); try{ scrimSave(); }catch(e){} }
function qoComplete(){
  const Q=SCRIM.quest; if(!Q||Q.done) return; Q.done=true; Q.prog=Math.max(Q.prog,qoGoal());
  const d=QO_QUESTS[Q.q], t=Q.tier; let ip=QO_IP[t], extra='';
  if(d.rw==='ip') ip=Math.round(ip*1.6);
  if(d.rw==='lf'){ SCRIM.lf=(SCRIM.lf||0)+QO_LF[t]; extra=' · +'+QO_LF[t]+' Late Fees'; }
  if(d.rw==='art'){ let id=null; try{ id=scrimGrantArtifact(QO_ART[t]); }catch(e){} if(!id){ ip+=20; } else if(SCRIM_ART[id]) extra=' · '+SCRIM_ART[id].ic+' '+SCRIM_ART[id].name; }
  META.ip=(META.ip||0)+ip; Q.paid=true; try{ metaSave(); }catch(e){} try{ scrimSave(); }catch(e){}
  qoBanner('QUEST FULFILLED', d.name+' · +'+ip+' IP'+extra);
}
function qoBreak(){ const Q=SCRIM.quest; if(Q && Q.oath && !Q.broken){ Q.broken=true; try{ scrimSave(); }catch(e){} qoBanner('OATH BROKEN', QO_OATHS[Q.oath].name, true); } }
function qoActEnd(team){
  const Q=SCRIM.quest; if(!Q || Q.key!==qoKey()) return;
  if(Q.q && !Q.done){
    if(Q.q==='frugal'){ if((SCRIM.lf||0)>=qoGoal()) qoComplete(); }
    if(Q.q==='medic'){ const ok=(team||[]).length && team.every(function(c){ return c.hp>0 && c.hp>c.maxHp/2; }); if(ok) qoComplete(); }
  }
  if(Q.oath && !Q.broken && !Q.oathPaid){ Q.oathPaid=true; const ip=QO_OATH_IP[Q.tier]; META.ip=(META.ip||0)+ip; try{ metaSave(); }catch(e){}
    setTimeout(function(){ qoBanner('OATH KEPT', QO_OATHS[Q.oath].name+' · +'+ip+' IP'); }, Q.done?3000:0); }
  try{ scrimSave(); }catch(e){}
}
/* the game's own event stream (the same one Daily Challenges use), Scrimmage runs only */
function qoInRun(){ try{ return APP.mode==='scrim' && SCRIM.active && !(S&&S._sim); }catch(e){ return false; } }
function qoBattle(){ if(S!==ABC_QO.S){ ABC_QO.S=S; ABC_QO.ko=0; ABC_QO.turns=0; ABC_QO.plays=0; } }
function qoEv(side,e){
  if(side!=='you' || !qoInRun() || !SCRIM.quest) return; qoBattle();
  const Q=SCRIM.quest, q=Q.q;
  if(e.t==='activeKO'){ ABC_QO.ko++; if(q==='unbroken') qoAdd(0,true); if(Q.oath==='ironwill') qoBreak(); }
  if(e.t==='play'||e.t==='bookmark'){ ABC_QO.plays++; if(q==='flourish' && ABC_QO.plays>=qoGoal()) qoAdd(qoGoal(),true); }
  if(!q || Q.done) return;
  if(e.t==='answer'){ if(q==='recite') qoAdd(e.ok?1:0,!e.ok); }
  else if(e.t==='bookmark'){ if(q==='bookworm') qoAdd(1); }
  else if(e.t==='thesis'){ if(q==='thesis') qoAdd(1); }
  else if(e.t==='status'){ if(q==='scourge') qoAdd(1); }
  else if(e.t==='win'){
    const pn=SCRIM.pending&&SCRIM.map&&SCRIM.map.cols[SCRIM.pending.c]&&SCRIM.map.cols[SCRIM.pending.c][SCRIM.pending.r];
    if(q==='unbroken') qoAdd(ABC_QO.ko?0:1, !!ABC_QO.ko);
    if(q==='swift' && ABC_QO.turns<=qoGoal()) qoAdd(qoGoal(),true);
    if(q==='slayer' && pn && pn.type==='elite' && !(Q.tier>=2 && ABC_QO.ko)) qoAdd(1);
  }
}
const qoChEvBase=abcChEv;
abcChEv=function(side,e){ try{ qoEv(side,e); if(e && (e.t==='charge'||e.t==='lens'||e.t==='evolve'||e.t==='char')) qoEv(side,{t:'play'}); }catch(err){} return qoChEvBase.apply(this,arguments); };
const qoChKOBase=abcChKO;
abcChKO=function(side,a){ try{ if(side==='you' && a && qoInRun() && SCRIM.quest){ const P=S.you; if(P.team[P.activeIdx]!==a) qoEv('you',{t:'activeKO'}); } }catch(e){} return qoChKOBase.apply(this,arguments); };   /* a Backstage knockout counts too */
const qoChTurnBase=abcChTurn;
abcChTurn=function(){ try{ if(S && S.turn==='you' && qoInRun()){ qoBattle(); ABC_QO.turns++; ABC_QO.plays=0; } }catch(e){} return qoChTurnBase.apply(this,arguments); };
const qoChEndBase=abcChEnd;
abcChEnd=function(win,boss){ const r=qoChEndBase.apply(this,arguments); try{ if(win && boss && qoInRun()) qoActEnd(S&&S.you&&S.you.team); }catch(e){} return r; };
/* the map: places visited, Coffee Breaks */
const qoResolveBase=scrimResolveNode;
scrimResolveNode=function(c,r){
  try{ const Q=SCRIM.quest, node=SCRIM.map.cols[c][r];
    if(Q && node){ if(Q.seen.indexOf(node.type)<0 && node.type!=='start') Q.seen.push(node.type);
      if(Q.q==='carto' && !Q.done) qoAdd(Q.seen.length,true);
      if(node.type==='rest' && Q.oath==='unplugged') qoBreak(); } }catch(e){}
  return qoResolveBase.apply(this,arguments);
};
/* Book Fair purchases and Study Break picks (checked by what actually changed) */
const qoHandleBase=handleScrim;
handleScrim=function(cmd){
  const op=String(cmd||'').split(':')[0], lf0=SCRIM.lf||0, d0=SCRIM.deck?(SCRIM.deck.ab.length+SCRIM.deck.bm.length+SCRIM.deck.cr.length):0;
  const r=qoHandleBase.apply(this,arguments);
  try{ const Q=SCRIM.quest; if(Q && Q.oath){
    if(op==='fairbuy' && Q.oath==='austerity' && (SCRIM.lf||0)<lf0) qoBreak();
    if(op==='draftpick' && Q.oath==='ascetic'){ const d1=SCRIM.deck.ab.length+SCRIM.deck.bm.length+SCRIM.deck.cr.length; if(d1>d0) qoBreak(); } } }catch(e){}
  return r;
};
/* a new run starts clean; the quest state is saved and resumed with the run */
const qoStartKitBase=scrimStartKit;
scrimStartKit=function(){ SCRIM.quest=null; return qoStartKitBase.apply(this,arguments); };
const qoSaveBase=scrimSave;
scrimSave=function(){ const r=qoSaveBase.apply(this,arguments); try{ if(SCRIM.active) localStorage.setItem('abc_scrim_quest',JSON.stringify(SCRIM.quest||null)); }catch(e){} return r; };
const qoLoadBase=scrimLoadSave;
scrimLoadSave=function(){ const ok=qoLoadBase.apply(this,arguments); try{ if(ok){ const j=localStorage.getItem('abc_scrim_quest'); SCRIM.quest=j?JSON.parse(j):null; } }catch(e){ SCRIM.quest=null; } return ok; };
const qoClearBase=scrimClearSave;
scrimClearSave=function(){ try{ localStorage.removeItem('abc_scrim_quest'); }catch(e){} return qoClearBase.apply(this,arguments); };

/* ---------- the Notice Board (shown in place of the map until the Act's quest is set) ---------- */
function qoBoard(){
  if(!SCRIM.quest || SCRIM.quest.key!==qoKey()) qoFresh();
  const Q=SCRIM.quest, t=Q.tier, chap=SCRIM.doctoral?('Semester '+(SCRIM.semester||1)):('Act '+stRoman(SCRIM.act||1));
  const quests=Q.offered.map(function(id){ const d=QO_QUESTS[id], n=d.n[t];
    return '<button type="button" class="qo-q'+(Q.q===id?' on':'')+'" data-st="qo:q:'+id+'"><span class="st-wax">'+d.ic+'</span><span class="qo-qt"><b>'+stEsc(d.name)+'</b><span>'+stEsc(d.txt(n,t))+'</span></span><span class="qo-rw">'+stEsc(qoRewardText(id,t))+'</span></button>'; }).join('');
  const oaths=Q.oaths.map(function(id){ const o=QO_OATHS[id];
    return '<button type="button" class="qo-o'+(Q.oath===id?' on':'')+'" data-st="qo:o:'+id+'"><span class="st-wax sm">'+o.ic+'</span><span><b>'+stEsc(o.name)+'</b> — '+stEsc(o.txt)+'</span><span class="qo-rw">+'+QO_OATH_IP[t]+' IP if kept</span></button>'; }).join('')
    +'<button type="button" class="qo-o'+(Q.oath===null&&Q._oathPicked?' on':'')+'" data-st="qo:o:none"><span class="st-wax sm">—</span><span>Swear no oath</span><span class="qo-rw"></span></button>';
  const ready=!!Q.q;
  return `<div class="scrim-wrap scrim-ink st-desk"><div class="st-wrapcol qo-wrap">
    <div class="st-bar"><button class="st-tab" data-scrim="endrun">‹ Scrimmage menu</button><button class="st-tab gold" data-st="shop">🏛 Shop</button><span class="st-saved">Run saved automatically</span></div>
    <div class="scrim-panel qo-board">
      <div class="st-runhead">${chap.toUpperCase()} · THE NOTICE BOARD</div>
      <div class="scrim-title sm">Choose a Quest</div>
      <p class="scrim-intro-copy">One quest per ${SCRIM.doctoral?'Semester':'Act'}. It pays out the moment it is fulfilled. <span class="qo-tier">${QO_TIERS[t]}${SCRIM.doctoral?' · Doctoral':''} goals &amp; rewards</span></p>
      <div class="qo-qs">${quests}</div>
      <div class="st-sub">An Oath (optional)</div>
      <p class="qo-small">Swear one and keep it until the ${SCRIM.doctoral?'Semester':'Act'}’s boss falls for bonus IP. Breaking it costs nothing but the bonus.</p>
      <div class="qo-os">${oaths}</div>
      <div class="qo-go"><button class="bigbtn" data-st="qo:go" ${ready?'':'disabled'}>${ready?'Set out ›':'Choose a quest'}</button></div>
    </div></div></div>`;
}
const qoScreenBase=scrimScreen;
scrimScreen=function(){ try{ if(SCRIM.view==='map' && qoNeedBoard()) return qoBoard(); }catch(e){} return qoScreenBase.apply(this,arguments); };
window.addEventListener('click',function(e){
  const b=e.target&&e.target.closest&&e.target.closest('[data-st^="qo:"]'); if(!b) return;
  e.stopPropagation(); e.preventDefault();
  const p=b.getAttribute('data-st').split(':'), Q=SCRIM.quest; if(!Q) return;
  if(p[1]==='q'){ Q.q=p[2]; Q.prog=0; }
  else if(p[1]==='o'){ Q.oath=(p[2]==='none')?null:p[2]; Q._oathPicked=true; }
  else if(p[1]==='go' && Q.q){ Q.set=true; Q.prog=(Q.q==='carto')?0:0; try{ SFX.card('book_flip',0.6); }catch(err){} try{ scrimSave(); }catch(err){} }
  render();
},true);
/* the quest + oath on the map's left page */
function qoLedger(){
  const Q=SCRIM.quest; if(!Q || !Q.set) return '';
  let h='<div class="st-sub">Quest</div>';
  if(Q.q){ const d=QO_QUESTS[Q.q], n=qoGoal(), p=Q.done?n:Math.min(n,Q.q==='frugal'?(SCRIM.lf||0):(Q.prog||0));
    h+='<div class="qo-led'+(Q.done?' done':'')+'"><span class="st-wax sm">'+(Q.done?'✓':d.ic)+'</span><div><b>'+stEsc(d.name)+'</b><span>'+stEsc(d.txt(n,Q.tier))+'</span>'
      +(n>1?'<div class="qo-bar"><i style="width:'+Math.round(100*p/n)+'%"></i></div><small>'+p+' / '+n+'</small>':'')+(Q.done?'<small class="ok">Fulfilled</small>':'')+'</div></div>'; }
  if(Q.oath){ const o=QO_OATHS[Q.oath]; h+='<div class="qo-led oath'+(Q.broken?' broken':'')+'"><span class="st-wax sm">'+o.ic+'</span><div><b>'+stEsc(o.name)+'</b><span>'+stEsc(o.txt)+'</span><small class="'+(Q.broken?'bad':'ok')+'">'+(Q.broken?'Broken':(Q.oathPaid?'Kept':'Sworn · +'+QO_OATH_IP[Q.tier]+' IP if kept'))+'</small></div></div>'; }
  return h;
}
const qoMapBase=scrimMapScreen;
scrimMapScreen=function(){ const h=qoMapBase.apply(this,arguments); try{ const led=qoLedger(); if(led) return h.replace('<div class="st-sub">Relics</div>',led+'<div class="st-sub">Relics</div>'); }catch(e){} return h; };
/* banner, in the tome's colours: works over the map and over a battle */
function qoBanner(head,line,bad){
  try{ const old=document.getElementById('qoBanner'); if(old) old.remove();
    const el=document.createElement('div'); el.id='qoBanner'; el.className=bad?'bad':'';
    el.innerHTML='<b>'+stEsc(head)+'</b><span>'+stEsc(line)+'</span>'; document.body.appendChild(el);
    try{ SFX.card(bad?'card_slide':'book_flip',0.7); }catch(e){}
    setTimeout(function(){ el.classList.add('out'); },2600); setTimeout(function(){ el.remove(); },3000); }catch(e){}
}
if(typeof window!=='undefined') window.ABC_QO={ qo:ABC_QO, quests:QO_QUESTS, oaths:QO_OATHS, tier:qoTier, fresh:qoFresh, complete:qoComplete, actEnd:qoActEnd, ev:qoEv };
'''
CSS = r"""
/* fix_scrim_quests */
.st-wrapcol.qo-wrap{ width:min(860px,98vw); }
.qo-board{ width:100%!important; box-sizing:border-box; padding:30px 34px 28px!important; }
.qo-board .st-runhead{ margin-bottom:4px; }
.qo-tier{ display:inline-block; font:600 11px/1 var(--st-cinzel); letter-spacing:.12em; font-style:normal; color:#f6e6c4; background:var(--st-rub); border-radius:4px; padding:5px 8px; margin-left:6px; vertical-align:2px; }
.qo-qs{ display:grid; gap:10px; margin-top:12px; }
.qo-q{ display:grid; grid-template-columns:auto 1fr auto; gap:14px; align-items:center; text-align:left; padding:12px 14px; cursor:pointer; color:var(--st-ink);
  background:rgba(255,248,226,.55); border:1.5px solid var(--st-ink2); border-radius:6px; box-shadow:0 2px 0 var(--st-ink2); }
.qo-q:hover{ background:#fff4d8; }
.qo-q.on{ background:#fff0c8; border-color:var(--st-rub); box-shadow:0 0 0 2px var(--st-rub),0 2px 0 var(--st-ink2); }
.qo-q.on .st-wax{ --c:#8e2a1c; }
.qo-qt b{ display:block; font:400 20px/1.1 var(--st-fell); }
.qo-qt span{ display:block; font:14.5px/1.4 'Spectral',Georgia,serif; color:var(--st-ink2); margin-top:3px; }
.qo-rw{ font:700 11.5px/1.3 var(--st-cinzel); letter-spacing:.05em; color:var(--st-rub); text-align:right; max-width:150px; }
.qo-small{ font:italic 14px/1.4 var(--st-fell); color:var(--st-ink2); margin:0 0 8px; }
.qo-os{ display:grid; gap:7px; }
.qo-o{ display:grid; grid-template-columns:auto 1fr auto; gap:10px; align-items:center; text-align:left; padding:9px 12px; cursor:pointer; color:var(--st-ink); font:14.5px/1.35 'Spectral',Georgia,serif;
  background:rgba(142,42,28,.05); border:1.5px dashed var(--st-rub); border-radius:6px; }
.qo-o b{ font:400 16px/1.1 var(--st-fell); }
.qo-o:hover{ background:rgba(142,42,28,.1); }
.qo-o.on{ border-style:solid; background:rgba(142,42,28,.14); box-shadow:0 0 0 1px var(--st-rub); }
.qo-go{ text-align:center; margin-top:18px; }
.qo-go .bigbtn[disabled]{ opacity:.5; cursor:default; }
/* map left page */
.qo-led{ display:grid; grid-template-columns:auto 1fr; gap:9px; align-items:start; margin-bottom:8px; }
.qo-led b{ display:block; font:400 16px/1.1 var(--st-fell); }
.qo-led span:not(.st-wax){ display:block; font:13px/1.35 'Spectral',Georgia,serif; color:var(--st-ink2); }
.qo-led small{ display:block; font:600 11px/1.3 var(--st-cinzel); letter-spacing:.06em; color:var(--st-ink2); margin-top:2px; }
.qo-led small.ok{ color:#1F6A6A; } .qo-led small.bad{ color:var(--st-rub); }
.qo-led.done .st-wax{ --c:#1F6A6A; }
.qo-led.broken{ opacity:.6; } .qo-led.broken b{ text-decoration:line-through; }
.qo-bar{ height:6px; border:1px solid var(--st-ink2); border-radius:4px; margin-top:5px; overflow:hidden; background:#eadbb6; }
.qo-bar i{ display:block; height:100%; background:#1F6A6A; }
/* banner */
#qoBanner{ position:fixed; left:50%; top:16px; transform:translateX(-50%); z-index:9700; display:flex; flex-direction:column; align-items:center; gap:4px; min-width:280px;
  padding:12px 26px 13px; background:linear-gradient(#f4e8c8,#e8d6aa); color:#2b1d12; border:2px solid #4a3522; border-radius:6px; box-shadow:0 10px 24px rgba(0,0,0,.45),0 0 0 4px rgba(184,137,44,.6);
  animation:qoIn .35s cubic-bezier(.2,1.3,.4,1) both; pointer-events:none; text-align:center; }
#qoBanner b{ font:700 14px/1 'Cinzel',Georgia,serif; letter-spacing:.24em; color:#1F6A6A; }
#qoBanner span{ font:400 18px/1.2 'IM Fell English',Georgia,serif; }
#qoBanner.bad b{ color:#8e2a1c; }
#qoBanner.out{ transition:opacity .35s, transform .35s; opacity:0; transform:translate(-50%,-20px); }
@keyframes qoIn{ from{ opacity:0; transform:translate(-50%,-24px) scale(.96); } to{ opacity:1; transform:translate(-50%,0) scale(1); } }
@media (max-width:640px){ .qo-board{ padding:24px 14px 22px!important; } .qo-q{ grid-template-columns:auto 1fr; } .qo-q .qo-rw{ grid-column:2; text-align:left; max-width:none; } .qo-o{ grid-template-columns:auto 1fr; } .qo-o .qo-rw{ grid-column:2; text-align:left; } }
@media (prefers-reduced-motion:reduce){ #qoBanner{ animation:none; } }
"""

SRC=os.path.join('src','game.src.html'); MARK='/* fix_scrim_quests */'
def apply(s, TAG):
    if MARK in s: sys.exit(f'{TAG} Already applied -- nothing to do.')
    for need,who in [('/* fix_scrim_tome */','fix_scrim_tome.py'),('function abcChEv(','fix_challenges.py'),('function abcChTurn(','fix_challenges.py')]:
        if need not in s: sys.exit(f'{TAG} ERROR: run {who} first. Nothing written.')
    for l,a in [('end of <head> styles',"</style>\n</head>"),('JS insertion point',"function menuScreen(){\n")]:
        if s.count(a)!=1: sys.exit(f'{TAG} ERROR: anchor "{l}" found {s.count(a)} times (expected 1). Nothing written.')
    s=s.replace("</style>\n</head>",CSS+"</style>\n</head>",1)
    s=s.replace("function menuScreen(){\n",JS+"\nfunction menuScreen(){\n",1)
    for need in [MARK,'function qoBoard(','#qoBanner{','abcChEv=function']:
        if need not in s: sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
    return s

TAG='[qo_preview]'
if not os.path.exists(SRC): sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s=apply(open(SRC,encoding='utf-8').read(),TAG)
A=json.load(open(os.path.join('assets','assets.json')))
out=re.sub(r'__ABCASSET_(\d+)__',lambda m:A['a'+m.group(1)],s)
os.makedirs('dist',exist_ok=True); p=os.path.join('dist','ABC_quests_preview.html'); open(p,'w',encoding='utf-8').write(out)
print(f'{TAG} wrote',p,f'({len(out):,} bytes) -- src/ untouched.')
