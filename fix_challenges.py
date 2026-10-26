#!/usr/bin/env python3
"""fix_challenges.py -- Daily & weekly challenges.

Run from the repo root:   python3 fix_challenges.py
Undo:                     restore src/game.src.html from the .bak this writes.
Needs:                    nothing else (works with or without the pixel / board patches; uses the pixel
                          font for the banner when fix_pixel_fx is present).

WHAT IT ADDS
  * Main menu > Challenges: 3 dailies (Easy / Medium / Hard, new each local midnight) and 3 weeklies
    (new each Monday). The same challenges for everyone on a given date (picked from the date, no
    server). One free swap a day on an unstarted daily. Claim for Intellect Points (8 / 12 / 20,
    weekly 40); clearing all three weeklies opens a free Silver pack. Day streak for claiming a daily.
  * 28-challenge pool, incl. the escalating "cards in one turn" ladder: 3 (easy), 4 (medium),
    5 (hard), 6 "Full Hand" (weekly; the standard-rules maximum). Never two from one family a day.
  * In a match, a non-blocking "CHALLENGE COMPLETE!" banner (pixel type when the pixel patch is in).
  * Counts only your side in Quickplay, Literary Scrimmage and PreCon Arena vs the AI, on standard
    rules (attaches per turn <= 2). Never in AI-vs-AI sims, Custom Play, Pagemaster or with dev open.
  * Progress lives in META.challenges (saved with the rest of META). It is NOT added to the Transcript
    Code: dailies expire on their own, and the frozen code order stays untouched.

HOW IT HOOKS IN (17 one-line insertions + 1 menu button, nothing removed)
  charge, trivia answer, Bookmark commit, Lens deploy, thesis, evolve, character played, status
  inflicted, KO, Siphon drain, turn start, match end (Quickplay/Arena + Scrimmage), screen route,
  menu button, click handler; plus the data/tracker block and CSS.
"""
import os, sys, shutil, datetime
SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_challenges */'
TAG = '[fix_challenges]'
if not os.path.exists(SRC):
    sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit(f'{TAG} Already applied -- nothing to do.')

JS = r'''/* fix_challenges */ /* ---- Daily / weekly challenges: data + tracker (shared by the preview and, later, the patch) ----
   Events in (from ~10 engine hooks), progress out. Challenges are plain data, so adding one never
   touches the engine. Selection is seeded by the date, so every player sees the same dailies. */
const CH_POOL=[
  /* ---- dailies: easy ---- */
  {id:'win1',     fam:'win',    tier:'easy', name:'Back to the Books', text:'Win a match.', ev:'win', scope:'match', n:1},
  {id:'combo3',   fam:'combo',  tier:'easy', name:'Three-Card Trick', text:'Play 3 cards from your hand in one turn.', ev:'play', scope:'turn', n:3},
  {id:'bm2t',     fam:'bm',     tier:'easy', name:'Dog-Eared', text:'Play 2 Bookmarks in one turn.', ev:'bookmark', scope:'turn', n:2},
  {id:'abc4',     fam:'abc',    tier:'easy', name:'Well Read', text:'Charge 4 ABCs in one match.', ev:'charge', scope:'match', n:4},
  {id:'ko2',      fam:'ko',     tier:'easy', name:'Plot Twist', text:'Knock out 2 characters in one match.', ev:'ko', scope:'match', n:2},
  {id:'lens1',    fam:'lens',   tier:'easy', name:'New Perspective', text:'Deploy a Critical Lens.', ev:'lens', scope:'match', n:1},
  {id:'stat2',    fam:'status', tier:'easy', name:'Marginalia', text:'Inflict 2 different statuses in one match.', ev:'status', scope:'match', n:2, distinct:true},
  /* ---- dailies: medium ---- */
  {id:'combo4',   fam:'combo',  tier:'med',  name:'Four-Card Flourish', text:'Play 4 cards from your hand in one turn.', ev:'play', scope:'turn', n:4},
  {id:'streak5',  fam:'trivia', tier:'med',  name:'On a Roll', text:'Answer 5 trivia questions correctly in a row.', ev:'answer', scope:'streak', n:5},
  {id:'clean3',   fam:'abc',    tier:'med',  name:'Clean Copy', text:'Charge 3 ABCs in one match without a wrong answer.', ev:'charge', scope:'match', n:3, noMiss:true},
  {id:'stat3',    fam:'status', tier:'med',  name:'Annotated Edition', text:'Inflict 3 different statuses in one match.', ev:'status', scope:'match', n:3, distinct:true},
  {id:'thesis1',  fam:'lens',   tier:'med',  name:'Thesis Defended', text:'Fulfil a Critical Lens thesis.', ev:'thesis', scope:'match', n:1},
  {id:'evo2',     fam:'evo',    tier:'med',  name:'Rising Action', text:'Evolve a character to Act II.', ev:'evolve', scope:'match', n:1, act:2, hint:'Decks with Act cards'},
  {id:'ko3',      fam:'ko',     tier:'med',  name:'Body Count', text:'Knock out 3 characters in one match.', ev:'ko', scope:'match', n:3},
  /* ---- dailies: hard ---- */
  {id:'combo5',   fam:'combo',  tier:'hard', name:'Five-Card Frenzy', text:'Play 5 cards from your hand in one turn.', ev:'play', scope:'turn', n:5},
  {id:'oneturn',  fam:'ko',     tier:'hard', name:'In One Stroke', text:'Knock out a character that started your turn at full HP.', ev:'koFull', scope:'match', n:1},
  {id:'perfect',  fam:'trivia', tier:'hard', name:'Perfect Recall', text:'Win a match with every trivia answer correct (at least 3).', ev:'winPerfect', scope:'match', n:1},
  {id:'bmrun',    fam:'bm',     tier:'hard', name:'Bookworm', text:'Play 2 Bookmarks a turn, 3 turns in a row.', ev:'bmTurn2', scope:'run', n:3},
  {id:'evo3',     fam:'evo',    tier:'hard', name:'Climax', text:'Evolve a character to Act III.', ev:'evolve', scope:'match', n:1, act:3, hint:'Decks with Act cards'},
  /* ---- weeklies ---- */
  {id:'combo6',   fam:'combo',  tier:'week', name:'Full Hand', text:'Play 6 cards from your hand in one turn — the most the standard rules allow.', ev:'play', scope:'turn', n:6},
  {id:'bm6',      fam:'bm',     tier:'week', name:'Annotated to Death', text:'Play 6 Bookmarks in one match.', ev:'bookmark', scope:'match', n:6},
  {id:'decks3',   fam:'win',    tier:'week', name:'Wide Reader', text:'Win 3 matches with 3 different decks.', ev:'win', scope:'week', n:3, distinctDeck:true},
  {id:'untouch',  fam:'ko',     tier:'week', name:'Untouchable', text:'Win a match without your Active ever being knocked out.', ev:'winClean', scope:'match', n:1},
  {id:'boss1',    fam:'boss',   tier:'week', name:'Algorithm Breaker', text:'Defeat a Literary Scrimmage boss.', ev:'boss', scope:'week', n:1},
  {id:'triv25',   fam:'trivia', tier:'week', name:'Close Reader', text:'Answer 25 trivia questions correctly this week.', ev:'answer', scope:'week', n:25},
  {id:'siphon3',  fam:'siphon', tier:'week', name:'Leech Lit', text:'Drain HP from 3 different enemy characters with Siphon.', ev:'siphon', scope:'week', n:3, distinct:true, hint:'Decks with Siphon moves'},
  {id:'evo3x2',   fam:'evo',    tier:'week', name:'Three-Act Structure', text:'Evolve characters to Act III twice this week.', ev:'evolve', scope:'week', n:2, act:3, hint:'Decks with Act cards'}
];
const CH_REWARD={easy:8, med:12, hard:20, week:40};
const CH_WEEK_BONUS='silver';   /* clear all three weeklies: a free Silver pack */
function chHash(str){ let h=2166136261; for(let i=0;i<str.length;i++){ h^=str.charCodeAt(i); h=Math.imul(h,16777619); } return h>>>0; }
function chRng(seed){ let s=seed>>>0; return function(){ s=(s+0x6D2B79F5)>>>0; let t=Math.imul(s^s>>>15,1|s); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }; }
function chDayKey(d){ d=d||new Date(); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
function chWeekKey(d){ d=new Date((d||new Date()).getTime()); const day=(d.getDay()+6)%7; d.setDate(d.getDate()-day+3); const w1=new Date(d.getFullYear(),0,4);
  return d.getFullYear()+'-W'+String(1+Math.round(((d-w1)/864e5-3+((w1.getDay()+6)%7))/7)).padStart(2,'0'); }
/* pick one from a tier, skipping families already used today */
function chPick(r,tier,used){ const c=CH_POOL.filter(function(x){ return x.tier===tier && used.indexOf(x.fam)<0; }); return c.length?c[Math.floor(r()*c.length)]:null; }
function chDailies(dayKey,rerolls){ const r=chRng(chHash('abc-daily-'+dayKey)), used=[], out=[];
  ['easy','med','hard'].forEach(function(t){ const c=chPick(r,t,used); if(c){ used.push(c.fam); out.push(c.id); } });
  (rerolls||[]).forEach(function(slot,i){ const t=['easy','med','hard'][slot], r2=chRng(chHash('abc-reroll-'+dayKey+'-'+i)), u=out.map(function(id){ return chById(id).fam; });
    const c=chPick(r2,t,u); if(c) out[slot]=c.id; });
  return out; }
function chWeeklies(weekKey){ const r=chRng(chHash('abc-weekly-'+weekKey)), used=[], out=[]; for(let i=0;i<3;i++){ const c=chPick(r,'week',used); if(c){ used.push(c.fam); out.push(c.id); } } return out; }
function chById(id){ return CH_POOL.find(function(x){ return x.id===id; }); }
/* state: {day, week, daily:[{id,p,done,claimed,set:{}}], weekly:[...], rerolls:[], streak, lastDone, bonusClaimed} */
function chFresh(st,now){ st=st||{}; const dk=chDayKey(now), wk=chWeekKey(now);
  if(st.day!==dk){ const y=new Date((now||new Date()).getTime()-864e5); if(st.lastDone!==chDayKey(y) && st.lastDone!==dk) st.streak=0;
    st.day=dk; st.rerolls=[]; st.daily=chDailies(dk,[]).map(function(id){ return {id:id,p:0,done:false,claimed:false}; }); }
  if(st.week!==wk){ st.week=wk; st.bonusClaimed=false; st.weekly=chWeeklies(wk).map(function(id){ return {id:id,p:0,done:false,claimed:false}; }); }
  st.streak=st.streak||0; return st; }
/* per-match / per-turn scratch kept outside the save */
let CHT={turn:{play:0,bookmark:0}, match:{}, run:0, lastBmTurn:-1};
function chMatchStart(){ CHT={turn:{play:0,bookmark:0}, match:{charge:0,miss:0,ko:0,bookmark:0,status:{},answers:0,wrong:0,activeKO:false}, run:CHT.run||0, lastBmTurn:-1, turnNo:0, ansStreak:CHT.ansStreak||0}; }
function chTurnStart(){ CHT.turnNo=(CHT.turnNo||0)+1; CHT.turn={play:0,bookmark:0}; if(CHT.lastBmTurn<CHT.turnNo-1) CHT.run=0; }
/* the one entry point. ev: {t:'play'|'bookmark'|'charge'|'answer'|'ko'|'koFull'|'lens'|'thesis'|'status'|'evolve'|'siphon'|'win'|'lose'|'boss'|'activeKO', ...} */
function chEvent(st,ev,onDone){
  const M=CHT.match, T=CHT.turn;
  if(ev.t==='play'){ T.play++; }
  if(ev.t==='bookmark'){ T.bookmark++; M.bookmark=(M.bookmark||0)+1; T.play++; if(T.bookmark===2){ CHT.run=(CHT.lastBmTurn===CHT.turnNo-1)?CHT.run+1:1; CHT.lastBmTurn=CHT.turnNo; } }
  if(ev.t==='charge'){ M.charge++; }
  if(ev.t==='answer'){ M.answers++; if(ev.ok){ CHT.ansStreak=(CHT.ansStreak||0)+1; } else { CHT.ansStreak=0; M.wrong++; M.miss++; } }
  if(ev.t==='ko'){ M.ko++; }
  if(ev.t==='status'){ M.status[ev.k]=1; }
  if(ev.t==='activeKO'){ M.activeKO=true; }
  [].concat(st.daily||[],st.weekly||[]).forEach(function(c){ if(c.done) return; const d=chById(c.id); let p=c.p;
    switch(d.ev){
      case 'play': if(ev.t==='play'||ev.t==='bookmark') p=Math.max(p,T.play); break;
      case 'bookmark': if(ev.t==='bookmark') p=d.scope==='turn'?Math.max(p,T.bookmark):M.bookmark; break;
      case 'bmTurn2': if(ev.t==='bookmark') p=Math.max(p,CHT.run); break;
      case 'charge': if(ev.t==='charge'||ev.t==='answer') p=(d.noMiss&&M.miss)?0:M.charge; break;
      case 'answer': if(ev.t==='answer') p=d.scope==='streak'?Math.max(p,CHT.ansStreak):(ev.ok?p+1:p); break;
      case 'ko': if(ev.t==='ko') p=M.ko; break;
      case 'koFull': if(ev.t==='ko'&&ev.full) p=1; break;
      case 'lens': if(ev.t==='lens') p=1; break;
      case 'thesis': if(ev.t==='thesis') p=1; break;
      case 'status': if(ev.t==='status') p=Object.keys(M.status).length; break;
      case 'evolve': if(ev.t==='evolve'&&ev.act>=d.act) p=d.scope==='week'?p+1:1; break;
      case 'siphon': if(ev.t==='siphon'){ c.set=c.set||{}; c.set[ev.uid]=1; p=Object.keys(c.set).length; } break;
      case 'win': if(ev.t==='win'){ if(d.distinctDeck){ c.set=c.set||{}; c.set[ev.deck]=1; p=Object.keys(c.set).length; } else p++; } break;
      case 'winPerfect': if(ev.t==='win'&&M.answers>=3&&!M.wrong) p=1; break;
      case 'winClean': if(ev.t==='win'&&!M.activeKO) p=1; break;
      case 'boss': if(ev.t==='boss') p++; break;
    }
    c.p=Math.min(d.n,p); if(c.p>=d.n){ c.done=true; if(onDone) onDone(c,d); } });
}
function chClaim(st,c){ if(!c.done||c.claimed) return 0; c.claimed=true; const d=chById(c.id); if(st.daily.indexOf(c)>=0){ st.lastDone=st.day; if(st.daily.filter(function(x){ return x.claimed; }).length===1) st.streak=(st.streak||0)+1; } return CH_REWARD[d.tier]; }
function chReroll(st,slot){ if((st.rerolls||[]).length>=1) return false; const c=st.daily[slot]; if(c.p>0||c.done) return false;
  st.rerolls=[slot]; const ids=chDailies(st.day,st.rerolls); st.daily[slot]={id:ids[slot],p:0,done:false,claimed:false}; return true; }

/* ---- challenges: game glue (eligibility, match/turn tracking, save, banner, screen) ---- */
let CH_S=null, CH_FULL={}, CH_END=null;
function abcChState(){ META.challenges=chFresh(META.challenges,new Date()); return META.challenges; }
function abcChOk(side){
  try{ if(side!=='you'||!S||S._sim||APP.dev) return false;
    if(['quick','scrim','arena'].indexOf(APP.mode)<0) return false;
    if(((S.settings&&S.settings.maxAttaches)||2)>2) return false;   /* standard rules only */
    return true; }catch(e){ return false; }
}
function abcChSnap(){ CH_FULL={}; try{ S.opp.team.forEach(function(c){ if(c.hp>0&&c.hp>=c.maxHp) CH_FULL[c.uid]=1; }); }catch(e){} }
function abcChMatch(){ if(S!==CH_S){ CH_S=S; CH_END=null; chMatchStart(); chTurnStart(); abcChSnap(); } }
function abcChDone(c,d){ try{ metaSave(); }catch(e){} abcChBanner(d); }
function abcChEv(side,e){
  if(!abcChOk(side)) return; abcChMatch();
  const st=abcChState();
  chEvent(st,e,abcChDone);
  if(e.t==='charge'||e.t==='lens'||e.t==='evolve'||e.t==='char') chEvent(st,{t:'play'},abcChDone);
}
function abcChTurn(){ try{ if(!S||S.turn!=='you'||!abcChOk('you')) return; abcChMatch(); chTurnStart(); abcChSnap(); try{ metaSave(); }catch(e){} }catch(e){} }
function abcChKO(side,a){
  try{ if(!a) return;
    if(side==='opp'){ abcChEv('you',{t:'ko',full:!!(CH_FULL[a.uid]&&S.turn==='you')}); }
    else if(side==='you'){ const P=S.you; if(P.team[P.activeIdx]===a) abcChEv('you',{t:'activeKO'}); } }catch(e){}
}
function abcChEnd(win,boss){
  try{ if(!abcChOk('you')||CH_END===S) return; CH_END=S; abcChMatch();
    if(win){ abcChEv('you',{t:'win',deck:(S.you&&S.you.setKey)||''}); if(boss) abcChEv('you',{t:'boss'}); }
    metaSave(); }catch(e){}
}
function abcChBanner(d){
  try{
    const old=document.getElementById('abcChBanner'); if(old) old.remove();
    const el=document.createElement('div'); el.id='abcChBanner';
    const px=(typeof abcPxText==='function'), a=px?abcPxText('CHALLENGE COMPLETE!','#ffd45e'):null, b=px?abcPxText(d.name.toUpperCase()+'  +'+CH_REWARD[d.tier]+' IP','#f6eedb'):null;
    el.innerHTML=(a&&b)?'<img alt="Challenge complete" src="'+a.url+'" style="width:'+(a.w*3)+'px;height:'+(a.h*3)+'px"><img alt="'+d.name+'" src="'+b.url+'" style="width:'+(b.w*2)+'px;height:'+(b.h*2)+'px">'
      :'<b>Challenge complete!</b><span>'+d.name+' · +'+CH_REWARD[d.tier]+' IP</span>';
    document.body.appendChild(el);
    const calm=document.body.classList.contains('calm-fx');
    if(el.animate&&!calm) el.animate([{transform:'translate(-50%,-140%)'},{transform:'translate(-50%,0)',offset:.12},{transform:'translate(-50%,0)',offset:.86},{transform:'translate(-50%,-140%)'}],{duration:2800,easing:'steps(20)',fill:'forwards'});
    setTimeout(function(){ el.remove(); },2850);
  }catch(e){}
}
function abcChClaimable(){ try{ const st=abcChState(); return [].concat(st.daily,st.weekly).filter(function(c){ return c.done&&!c.claimed; }).length+((!st.bonusClaimed&&st.weekly.every(function(c){ return c.claimed; }))?1:0); }catch(e){ return 0; } }
function abcChCard(c,i,daily,st){
  const d=chById(c.id), seg=Math.min(d.n,12), on=Math.round(c.p/d.n*seg); let bar=''; for(let k=0;k<seg;k++) bar+='<i class="'+(k<on?'':'off')+'"></i>';
  const tn={easy:'Easy',med:'Medium',hard:'Hard',week:'Weekly'}[d.tier];
  return '<div class="chs-c '+(c.claimed?'claimed':(c.done?'done':''))+'"><div class="chs-t '+d.tier+'">'+tn+'</div><div><b>'+d.name+'</b><p>'+d.text+(d.hint?' <span class="chs-h">('+d.hint+')</span>':'')+'</p><div class="chs-bar">'+bar+'</div></div>'
    +'<div class="chs-s"><span class="chs-r">+'+CH_REWARD[d.tier]+' IP</span>'+(c.claimed?'<span>Claimed</span>':(c.done?'<button class="bigbtn" data-do="ch-claim:'+(daily?'d':'w')+i+'">Claim</button>':'<span>'+c.p+'/'+d.n+'</span>'))
    +(daily&&!c.done&&!c.p&&!(st.rerolls||[]).length?'<button class="chs-swap" data-do="ch-swap:'+i+'">Swap (1 a day)</button>':'')+'</div></div>';
}
function chScreen(){
  const st=abcChState(), now=new Date(), mid=new Date(now); mid.setHours(24,0,0,0);
  const left=mid-now, hh=Math.floor(left/36e5), mm=Math.floor(left%36e5/6e4), dl=(8-((now.getDay()+6)%7+1))%7||7, allW=st.weekly.every(function(c){ return c.claimed; });
  const title=(typeof abcPxText==='function')?abcPxText('CHALLENGES','#b5402a'):null;
  return `<div class="title-screen sub-screen chs">
    <img class="title-logo sm" src="${window.ABC_LOGO||''}" alt="Academic Battle Cards">
    <div class="chs-p">
      <div class="chs-top">${title?'<img class="chs-title" alt="Challenges" src="'+title.url+'" style="width:'+(title.w*3)+'px;height:'+(title.h*3)+'px">':'<h2 class="sub-h">Challenges</h2>'}
        <div class="chs-meta"><span class="chs-pill streak">🔥 ${st.streak}-day streak</span><span class="chs-pill ip">🧠 ${META.ip||0} IP</span></div></div>
      <div class="chs-sec">Today<small>New dailies in ${hh}h ${mm}m</small></div>
      ${st.daily.map(function(c,i){ return abcChCard(c,i,true,st); }).join('')}
      <div class="chs-sec">This week<small>Resets Monday · ${dl} day${dl>1?'s':''} left</small></div>
      ${st.weekly.map(function(c,i){ return abcChCard(c,i,false,st); }).join('')}
      <div class="chs-bonus"><span>📦 <b>Clear all three weeklies</b> for a free <b>Silver booster pack</b>.</span>${st.bonusClaimed?'<b>Opened</b>':(allW?'<button class="bigbtn" data-do="ch-bonus">Open pack</button>':'<span>'+st.weekly.filter(function(c){ return c.claimed; }).length+'/3</span>')}</div>
      <div class="chs-foot">Counts in Quickplay, Literary Scrimmage and PreCon Arena (you vs the AI) on standard rules. “Cards played” means cards that resolve: a charged ABC, a Bookmark, a Lens, a character or an Act card. A wrong answer doesn’t count.</div>
    </div>
    <div class="sub-actions"><button class="toolbtn" data-do="menu">‹ Back to menu</button></div>
  </div>`;
}
function abcChClick(d){
  const st=abcChState();
  if(d.indexOf('ch-claim:')===0){ const k=d.slice(9), c=(k[0]==='d'?st.daily:st.weekly)[+k.slice(1)]; if(c){ const g=chClaim(st,c); if(g){ META.ip=(META.ip||0)+g; try{ toast('+'+g+' Intellect Points'); }catch(e){} } } metaSave(); render(); return true; }
  if(d.indexOf('ch-swap:')===0){ chReroll(st,+d.slice(8)); metaSave(); render(); return true; }
  if(d==='ch-bonus'){ if(!st.bonusClaimed && st.weekly.every(function(c){ return c.claimed; })){ st.bonusClaimed=true; META.packs=(META.packs||0)+1;
      const cards=scrimRollPack(CH_WEEK_BONUS); scrimApplyPack(cards); try{ validateLoadout(); }catch(e){} metaSave(); try{ SFX.card('pack_open',0.8); }catch(e){} packOverlayShow(CH_WEEK_BONUS,cards); render(); } return true; }
  return false;
}
if(typeof window!=='undefined') window.ABC_CH={state:abcChState, ev:abcChEv, end:abcChEnd, claimable:abcChClaimable, scratch:function(){ return CHT; }, fresh:chFresh, dailies:chDailies, weeklies:chWeeklies, byId:chById, claim:chClaim};
'''
CSS = """
/* fix_challenges */
.chs-p{width:min(760px,96vw);margin:0 auto;background:#f3e8cd;color:#241f1b;border:3px solid #241f1b;border-radius:14px;box-shadow:0 0 0 3px #e7d8b6,0 0 0 5px #241f1b,8px 10px 0 5px rgba(0,0,0,.35);padding:16px;text-align:left}
.chs-top{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:6px}
.chs-title{display:block;image-rendering:pixelated}
.chs-meta{display:flex;gap:8px;flex-wrap:wrap;font:700 12px/1 Arial,sans-serif}
.chs-pill{border:2px solid #241f1b;border-radius:999px;padding:6px 10px;background:#fff8e6}
.chs-pill.streak{background:#2a1408;color:#ffd45e;border-color:#E3A92B}
.chs-pill.ip{background:#1F6A6A;color:#fff}
.chs-sec{display:flex;justify-content:space-between;align-items:baseline;margin:14px 0 8px;font:700 11px/1 Arial,sans-serif;letter-spacing:2px;text-transform:uppercase;color:#7a1d10}
.chs-sec small{letter-spacing:.3px;text-transform:none;color:#6b5f52;font-weight:400}
.chs-c{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;background:#fffaf0;border:2px solid #241f1b;border-radius:10px;padding:10px;margin-bottom:8px;box-shadow:3px 3px 0 rgba(36,31,27,.25)}
.chs-c.done{background:#eef8e6}.chs-c.claimed{opacity:.6}
.chs-t{font:900 10px/1 Arial,sans-serif;letter-spacing:1px;padding:5px 6px;border:2px solid #241f1b;border-radius:6px;text-transform:uppercase;writing-mode:vertical-rl;transform:rotate(180deg);min-height:58px;text-align:center}
.chs-t.easy{background:#c9ecc0}.chs-t.med{background:#ffe7a6}.chs-t.hard{background:#f3c7bf}.chs-t.week{background:#d9c8f0}
.chs-c b{display:block;font:700 15px/1.2 Georgia,serif}
.chs-c p{margin:2px 0 6px;font:13px/1.35 Arial,sans-serif;color:#3a332a}
.chs-h{font-size:11px;color:#7a6a50;font-style:italic}
.chs-bar{height:12px;background:#3d332c;border:2px solid #241f1b;display:flex;gap:1px;padding:1px;max-width:260px}
.chs-bar i{flex:1;background:#E3A92B}.chs-bar i.off{background:#6b5f52}.chs-c.done .chs-bar i{background:#6fbf5a}
.chs-s{display:flex;flex-direction:column;gap:6px;align-items:flex-end;font:700 12px/1 Arial,sans-serif}
.chs-r{border:2px solid #241f1b;border-radius:8px;padding:5px 8px;background:#1F6A6A;color:#fff;white-space:nowrap}
.chs-s .bigbtn{padding:7px 12px;min-height:32px;font-size:13px}
.chs-swap{background:none;border:0;color:#6b5f52;padding:0;font:12px Arial,sans-serif;text-decoration:underline;cursor:pointer}
.chs-bonus{display:flex;gap:10px;align-items:center;justify-content:space-between;border:2px dashed #7a1d10;border-radius:10px;padding:10px;font:13px/1.35 Arial,sans-serif;background:#fff3e0}
.chs-foot{margin-top:12px;font:12px/1.45 Arial,sans-serif;color:#5a4f40}
.chs-badge{display:inline-block;min-width:18px;padding:2px 6px;margin-left:6px;border-radius:999px;background:#b5402a;color:#fff;font:700 11px/1.2 Arial,sans-serif;vertical-align:middle}
#abcChBanner{position:fixed;left:50%;top:12px;transform:translate(-50%,0);z-index:61;pointer-events:none;background:#1b1410;border:3px solid #E3A92B;box-shadow:0 3px 0 #6e1d12,6px 6px 0 rgba(0,0,0,.4);padding:8px 14px;display:flex;flex-direction:column;align-items:center;gap:6px;color:#f6eedb;font:700 14px/1.2 Arial,sans-serif}
#abcChBanner img{display:block;image-rendering:crisp-edges;image-rendering:pixelated}
"""
EDITS = [('end of <head> styles', '</style>\n</head>', None, 'css'), ('chargeReport head', 'function chargeReport(side, ch, before){\n  if(!ch||!before) return;\n', "function chargeReport(side, ch, before){\n  if(!ch||!before) return;\n  try{ abcChEv(side,{t:'charge'}); }catch(e){}   /* fix_challenges */\n", None), ('triviaStamp head', 'function triviaStamp(ok){\n', "function triviaStamp(ok){\n  try{ abcChEv('you',{t:'answer',ok:!!ok}); }catch(e){}   /* fix_challenges */\n", None), ('playBookmark commit()', '  const commit=()=>{', "  const commit=()=>{ try{ abcChEv(side,{t:'bookmark'}); }catch(e){}   /* fix_challenges */", None), ('Lens deploy log', '    pushLog(`${who(P)} deploys the ${card.name}. Passive Focus is now active.`);\n', "    pushLog(`${who(P)} deploys the ${card.name}. Passive Focus is now active.`);\n    try{ abcChEv(side,{t:'lens'}); }catch(e){}   /* fix_challenges */\n", None), ('thesis log', '  pushLog(`${who(P)} fulfils the ${C.name} thesis! ${C.reward}`);\n', "  pushLog(`${who(P)} fulfils the ${C.name} thesis! ${C.reward}`);\n  try{ abcChEv(side,{t:'thesis'}); }catch(e){}   /* fix_challenges */\n", None), ('actEvolve log', '  pushLog(`\\u2605 ${from} evolves into ${a.name} (Act ${roman(a.act)})', "  try{ abcChEv(side,{t:'evolve',act:a.act}); }catch(e){}   /* fix_challenges */\n  pushLog(`\\u2605 ${from} evolves into ${a.name} (Act ${roman(a.act)})", None), ('drawnPlayChar', '  p.hand.splice(idx,1); p.team.push(ch); ch._grow=0;\n  if(!liveAct){', "  p.hand.splice(idx,1); p.team.push(ch); ch._grow=0;\n  try{ abcChEv('you',{t:'char'}); }catch(e){}   /* fix_challenges */\n  if(!liveAct){", None), ('inflict', "  t.status[k]=true; fxStatus(sideOfChar(t),statusName(k),'neg'); return true;", "  t.status[k]=true; fxStatus(sideOfChar(t),statusName(k),'neg'); try{ if(sideOfChar(t)==='opp') abcChEv('you',{t:'status',k:k}); }catch(e){}   /* fix_challenges */ return true;", None), ('checkKO spawnKO', '    spawnKO(side, a.name);\n', '    try{ abcChKO(side,a); }catch(e){}   /* fix_challenges */\n    spawnKO(side, a.name);\n', None), ('Siphon tick', '      sp.turns=(sp.turns||1)-1;\n      if(sp.turns<=0){ delete c.status.siphon;', "      try{ if(_sk==='opp' && mode==='hp' && own && own.P===S.you) abcChEv('you',{t:'siphon',uid:c.uid}); }catch(e){}   /* fix_challenges */\n      sp.turns=(sp.turns||1)-1;\n      if(sp.turns<=0){ delete c.status.siphon;", None), ('startTurn head', 'function startTurn(){\n  if(!S) return;\n', 'function startTurn(){\n  if(!S) return;\n  try{ abcChTurn(); }catch(e){}   /* fix_challenges */\n', None), ('overModal head', "function overModal(){\n  const win=S.winner==='you';\n", "function overModal(){\n  const win=S.winner==='you';\n  try{ abcChEnd(win,false); }catch(e){}   /* fix_challenges */\n", None), ('scrimOverModal head', '  const won = !S.opp.team.some(c=>c.hp>0);\n', '  const won = !S.opp.team.some(c=>c.hp>0);\n  try{ abcChEnd(won,!!(S.scrim&&S.scrim.node&&(S.scrim.node.boss||S.scrim.node.superboss))); }catch(e){}   /* fix_challenges */\n', None), ('render route', "  if(APP.screen==='guide'){ root.innerHTML=guideScreen()+_ov(); return; }\n", "  if(APP.screen==='challenges'){ root.innerHTML=chScreen()+_ov(); return; }   /* fix_challenges */\n  if(APP.screen==='guide'){ root.innerHTML=guideScreen()+_ov(); return; }\n", None), ('menu builder button', '      <button class="menu-btn" data-do="builder">', '      <button class="menu-btn" data-do="go-challenges"><span class="menu-ic">\\uD83C\\uDFAF</span><span class="menu-tx"><b>Challenges${(function(){ const n=abcChClaimable(); return n?\' <span class="chs-badge">\'+n+\'</span>\':\'\'; })()}</b><small>Daily &amp; weekly goals \\u2014 earn Intellect Points</small></span><span class="menu-go">\\u203a</span></button><!-- fix_challenges -->\n      <button class="menu-btn" data-do="builder">', None), ('click handler', "    else if(d==='go-guide'){ APP.screen='guide'; render(); }\n", "    else if(d==='go-challenges'){ APP.screen='challenges'; render(); }   /* fix_challenges */\n    else if(d.indexOf('ch-')===0 && abcChClick(d)){ }\n    else if(d==='go-guide'){ APP.screen='guide'; render(); }\n", None), ('JS insertion point (before menuScreen)', 'function menuScreen(){\n', None, 'js')]

for l, a, _, kind in EDITS:
    n = s.count(a)
    if n != 1:
        sys.exit(f'{TAG} ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')
for l, a, rep, kind in EDITS:
    if kind == 'css': rep = CSS + a
    elif kind == 'js': rep = JS + '\n' + a
    s = s.replace(a, rep, 1)
for need in [MARK, 'function chEvent(', "abcChEv(side,{t:'charge'})", "abcChEv('you',{t:'answer'", 'abcChKO(side,a)', 'abcChTurn()', 'abcChEnd(win,false)', "APP.screen==='challenges'", 'data-do="go-challenges"', 'abcChClick(d)', '#abcChBanner{']:
    if need not in s:
        sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:', bak)
print(f'{TAG} Next: python3 build.py')
