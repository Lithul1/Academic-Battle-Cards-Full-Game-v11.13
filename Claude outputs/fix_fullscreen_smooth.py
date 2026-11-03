#!/usr/bin/env python3
"""fix_fullscreen_smooth.py -- full screen, image pre-loading, auto flat-board safety net, Performance meter v3.

Run from the repo root:   python3 fix_fullscreen_smooth.py
                          python3 build.py
Undo:                     restore src/game.src.html from the .bak this writes.
Needs:                    fix_safari_perf.py.

WHAT IT DOES
  * Full screen: a square icon left of Tune on the board and a button bottom right on the menu. In full screen a
    fading "Exit full screen" pill sits top centre (Esc works too) and the board resizes to fill the screen. Inside an
    embed that blocks full screen the button opens the game in a new window; on iPhone (no full screen) it is hidden.
  * Image pre-loading: at the start of a match both teams' card art and the print frames are decoded in the
    background, one at a time, so a card's first appearance does not stall.
  * Auto flat board: if the tilted board spends most of 3 seconds in slow frames, tilt switches off for the rest of the
    match with a note ("Keep 3D" undoes it). Tune > "Auto flat board when slow" turns this off.
  * Performance meter v3: the report records what was on screen at slow frames (phase, Inspect, hand/board counts,
    running animations, hover, page size) and any auto-flat events.
"""
import os, sys, shutil, datetime
SRC=os.path.join('src','game.src.html'); MARK='/* fix_fullscreen_smooth */'; TAG='[fix_fullscreen_smooth]'
if not os.path.exists(SRC): sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s=open(SRC,encoding='utf-8').read()
if MARK in s: sys.exit(f'{TAG} Already applied -- nothing to do.')
for need,who in [('/* fix_safari_perf */','fix_safari_perf.py'),('function abcPdTick(','fix_safari_perf.py'),('function abcTiltSet(','fix_board_layout_v3.py')]:
    if need not in s: sys.exit(f'{TAG} ERROR: run {who} first. Nothing written.')
if s.find('/* fix_safari_perf */')>s.find("function menuScreen(){\n"): sys.exit(f'{TAG} ERROR: fix_safari_perf block not where expected. Nothing written.')

JS = r'''/* fix_fullscreen_smooth */
/* fix_fullscreen_smooth: full screen, image pre-loading, auto flat-board safety net, Performance meter v3 */

/* ---------- 1. Full screen ----------
   Board: a square icon left of Tune. Menu: a button bottom right. In full screen a fading "Exit full screen" pill sits
   top centre (Esc works too). Where the browser blocks full screen inside an embed, the button opens the game in a new
   window instead; where it is not available at all (iPhone Safari) the button is not shown. */
const ABC_FS={ it:0, inFrame:(function(){ try{ return window.top!==window.self; }catch(e){ return true; } })() };
function abcFsEl(){ return document.fullscreenElement||document.webkitFullscreenElement||null; }
function abcFsCan(){ return !!(document.fullscreenEnabled||document.webkitFullscreenEnabled); }
function abcFsMode(){ return abcFsCan()?'fullscreen':(ABC_FS.inFrame?'window':'none'); }
function abcFsIcon(){ return abcFsEl()?'⤡':(abcFsCan()?'⛶':'↗'); }
function abcFsLabel(){ return abcFsEl()?'Exit full screen':(abcFsCan()?'Full screen':'Open full window'); }
function abcFsToggle(){
  const d=document, r=d.documentElement;
  try{
    if(abcFsEl()){ const p=(d.exitFullscreen||d.webkitExitFullscreen).call(d); if(p&&p.catch) p.catch(function(){}); }
    else if(abcFsCan()){ const p=(r.requestFullscreen||r.webkitRequestFullscreen).call(r); if(p&&p.catch) p.catch(function(){}); }
    else if(ABC_FS.inFrame) window.open(location.href,'_blank');
  }catch(e){}
}
function abcFsIdle(){ const b=document.body; b.classList.remove('abc-fs-idle'); clearTimeout(ABC_FS.it); ABC_FS.it=setTimeout(function(){ b.classList.add('abc-fs-idle'); },2500); }
function abcFsSync(){
  const on=!!abcFsEl(); document.body.classList.toggle('abc-fs',on);
  document.querySelectorAll('.abc-fsbtn').forEach(function(b){ if(b.dataset.icon) b.textContent=abcFsIcon(); else b.textContent=abcFsIcon()+' '+abcFsLabel(); b.title=abcFsLabel(); b.setAttribute('aria-label',abcFsLabel()); });
  if(on) abcFsIdle();
  setTimeout(function(){ try{ window.dispatchEvent(new Event('resize')); }catch(e){} },60);
}
/* runs after every render (and once a second as a fallback): keeps the buttons in place, starts image pre-loading */
function abcFsAfter(){
  const d=document, b=d.body; if(!b) return;
  const scr=b.getAttribute('data-screen');
  if(abcFsMode()!=='none'){
    const row=d.querySelector('#game .tb-btns');
    if(row && !row.querySelector('.abc-fsbtn')){   /* appended last: the board's own buttons keep their places when it re-renders */
      const x=d.createElement('button'); x.type='button'; x.className='abc-fsbtn'; x.dataset.icon='1'; row.appendChild(x); abcFsSyncOne(x); }
    let m=d.getElementById('abcFsMenu');
    if(!m){ m=d.createElement('button'); m.type='button'; m.id='abcFsMenu'; m.className='abc-fsbtn'; b.appendChild(m); abcFsSyncOne(m); }
    m.style.display=(scr==='menu')?'':'none';
  }
  if(!d.getElementById('abcFsExit')){ const p=d.createElement('button'); p.type='button'; p.id='abcFsExit'; p.innerHTML='✕&nbsp;Exit full screen'; b.appendChild(p); }
  abcPreAfter(scr);
}
function abcFsSyncOne(x){ x.textContent=x.dataset.icon?abcFsIcon():abcFsIcon()+' '+abcFsLabel(); x.title=abcFsLabel(); x.setAttribute('aria-label',abcFsLabel()); }
['fullscreenchange','webkitfullscreenchange'].forEach(function(n){ document.addEventListener(n,abcFsSync); });
document.addEventListener('click',function(e){
  const t=e.target&&e.target.closest&&e.target.closest('.abc-fsbtn,#abcFsExit'); if(!t) return;
  e.preventDefault(); e.stopPropagation();
  if(t.id==='abcFsExit'){ if(abcFsEl()) abcFsToggle(); } else abcFsToggle();
},true);
['mousemove','touchstart','keydown'].forEach(function(n){ document.addEventListener(n,function(){ if(abcFsEl()) abcFsIdle(); },{passive:true}); });

/* ---------- 2. Image pre-loading ----------
   When a match starts, both teams' card art and the print frames are decoded ahead of time, one image at a time, so
   the first time a card is shown (Inspect, evolution, switching in) the browser does not stall decoding it. */
const ABC_PRE={ key:'', q:[], keep:[], busy:false, done:0 };
function abcPreAfter(scr){
  if(scr!=='play'){ if(ABC_PRE.key){ ABC_PRE.key=''; ABC_PRE.q=[]; ABC_PRE.keep=[]; } return; }
  try{
    if(typeof S==='undefined' || !S || !S.you || !S.opp) return;
    const t=function(P){ return (P.team||[]).map(function(c){ return c&&c.uid; }).join(','); };
    const key=t(S.you)+'|'+t(S.opp); if(!key || key===ABC_PRE.key) return;
    ABC_PRE.key=key; ABC_PRE.keep=[];
    const urls=new Set();
    [S.you,S.opp].forEach(function(P){ (P.team||[]).forEach(function(c){ if(c && typeof c.img==='string' && c.img.length>30) urls.add(c.img); }); });
    const rs=document.documentElement.style;
    for(let i=0;i<rs.length;i++){ const p=rs[i]; if(p.indexOf('--pf-')!==0) continue; const m=/url\(["']?([^"')]+)["']?\)/.exec(rs.getPropertyValue(p)); if(m) urls.add(m[1]); }
    ABC_PRE.q=Array.from(urls); if(!ABC_PRE.busy) abcPrePump();
  }catch(e){}
}
function abcPrePump(){
  const u=ABC_PRE.q.shift(); if(!u){ ABC_PRE.busy=false; return; } ABC_PRE.busy=true;
  const im=new Image(); im.decoding='async'; ABC_PRE.keep.push(im);
  let fin=false; const go=function(){ if(fin) return; fin=true; ABC_PRE.done++; setTimeout(abcPrePump,40); };
  im.onerror=go; im.src=u;
  if(im.decode) im.decode().then(go,go); else im.onload=go;
}

/* ---------- 3. Auto flat-board safety net ----------
   If the tilted board spends most of 3 seconds in slow frames (over 50 ms -- not a 30 fps power-saving cap), tilt is
   switched off for the rest of the match with a note and a "Keep 3D" button. Turning tilt back on (note or Tune)
   stops the safety net for this visit. Off switch: localStorage abc_autoflat = off. */
const ABC_SAFE={ flat:false, user:false, f:[], last:0, log:[], note:null };
function abcSafeOff(){ try{ return localStorage.getItem('abc_autoflat')==='off'; }catch(e){ return false; } }
const abcTiltOnBase=abcTiltOn;
abcTiltOn=function(){ return ABC_SAFE.flat?false:abcTiltOnBase(); };
const abcTiltSetBase=abcTiltSet;
abcTiltSet=function(on){ if(on){ ABC_SAFE.user=ABC_SAFE.user||ABC_SAFE.flat||ABC_SAFE.log.length>0; ABC_SAFE.flat=false; abcSafeNoteHide(); } abcTiltSetBase(on); };
function abcSafeLoop(t){
  const b=document.body, scr=b&&b.getAttribute('data-screen');
  if(ABC_SAFE.flat && scr!=='play'){ ABC_SAFE.flat=false; abcSafeNoteHide(); }   /* next match starts tilted again */
  const watch=!!b && scr==='play' && !ABC_SAFE.flat && !ABC_SAFE.user && b.classList.contains('abc-tilt') && document.visibilityState==='visible' && !abcSafeOff();
  if(!watch){ ABC_SAFE.f.length=0; ABC_SAFE.last=0; setTimeout(function(){ requestAnimationFrame(abcSafeLoop); },1000); return; }
  const F=ABC_SAFE.f;
  if(ABC_SAFE.last){ const d=t-ABC_SAFE.last; if(d>1000) F.length=0; else F.push([t,d]); }
  ABC_SAFE.last=t;
  while(F.length && t-F[0][0]>3000) F.shift();
  if(F.length>5 && t-F[0][0]>2800){
    let slow=0; for(let i=0;i<F.length;i++) if(F[i][1]>50) slow+=F[i][1];
    if(slow>=1800){ abcSafeFire(slow,F.length); }
  }
  requestAnimationFrame(abcSafeLoop);
}
function abcSafeFire(slow,n){
  ABC_SAFE.flat=true; ABC_SAFE.f.length=0;
  ABC_SAFE.log.push({t:Math.round(performance.now()), slowMs:Math.round(slow), frames:n, snap:abcSnap()}); if(ABC_SAFE.log.length>5) ABC_SAFE.log.shift();
  document.body.classList.remove('abc-tilt');
  try{ if(typeof fitBoard==='function') fitBoard(); if(typeof placeTurnBar==='function') placeTurnBar(); }catch(e){}
  abcSafeNote();
}
function abcSafeNote(){
  let el=ABC_SAFE.note; if(!el){ el=document.createElement('div'); el.id='abcSafeNote'; el.setAttribute('role','status'); document.body.appendChild(el); ABC_SAFE.note=el;
    el.addEventListener('click',function(e){ const k=e.target.closest('[data-safe]'); if(!k) return; e.stopPropagation(); if(k.dataset.safe==='keep') abcTiltSet(true); abcSafeNoteHide(); }); }
  el.innerHTML='<span>Board was running slowly — switched to flat view.</span><button type="button" data-safe="keep">Keep 3D</button><button type="button" data-safe="ok" aria-label="Dismiss">✕</button>';
  el.className='show'; clearTimeout(el._t); el._t=setTimeout(abcSafeNoteHide,9000);
}
function abcSafeNoteHide(){ const el=ABC_SAFE.note; if(el){ el.className=''; clearTimeout(el._t); } }
requestAnimationFrame(abcSafeLoop);

/* ---------- 4. Performance meter v3: what was on screen when it got slow ---------- */
const ABC_SNAP={ hover:'', list:[], lastT:0 };
document.addEventListener('mouseover',function(e){ const t=e.target; if(t && t.className && typeof t.className==='string') ABC_SNAP.hover=t.className.slice(0,40); },{passive:true});
function abcSnap(){
  const d=document, b=d.body, q=function(s){ return d.querySelectorAll(s).length; }, anims={};
  try{ d.getAnimations().forEach(function(a){ const n=a.animationName||(a.transitionProperty?'transition:'+a.transitionProperty:'js'); anims[n]=(anims[n]||0)+1; }); }catch(e){}
  const ins=d.querySelector('.abc-inspect .ai-body');
  let st={}; try{ if(typeof S!=='undefined' && S) st={phase:S.phase, turn:S.turn, over:!!S.over}; }catch(e){}
  return { t:Math.round(performance.now()), view:abcPdView(), phase:st.phase, turn:st.turn, over:st.over,
    hand:q('#game .hand .hc'), bench:q('#game .bench-mini'), chars:q('#game .char'), flying:q('.abc-fly-hand,.fly-card'),
    effects:q('.cfx,.pxo-fx'), modal:q('.modal-bg'), inspect:ins?(ins.firstElementChild?String(ins.firstElementChild.className).slice(0,30):'empty'):'none',
    hover:ABC_SNAP.hover, dom:d.getElementsByTagName('*').length, anims:anims, tilt:b.classList.contains('abc-tilt'),
    autoFlat:ABC_SAFE.flat, fullscreen:!!abcFsEl(), window:innerWidth+'x'+innerHeight };
}
const abcPdTickBase=abcPdTick;
abcPdTick=function(gap,t){
  abcPdTickBase(gap,t);
  if(gap>50 && ABC_PD.on && t-ABC_SNAP.lastT>1000){ ABC_SNAP.lastT=t; const s=abcSnap(); s.frameMs=Math.round(gap); ABC_SNAP.list.push(s); if(ABC_SNAP.list.length>12) ABC_SNAP.list.shift(); }
};
const abcPdReportBase=abcPdReport;
abcPdReport=function(){
  const s=abcPdReportBase(); const i=s.indexOf('\n');
  try{ const r=JSON.parse(s.slice(i+1)); r.meter='v3'; r.now=abcSnap(); r.slowSnapshots=ABC_SNAP.list.slice(); r.autoFlat={ active:ABC_SAFE.flat, keep3d:ABC_SAFE.user, events:ABC_SAFE.log.slice() };
    r.fullscreen={ mode:abcFsMode(), on:!!abcFsEl() }; r.preload={ done:ABC_PRE.done, queued:ABC_PRE.q.length };
    return s.slice(0,i+1)+JSON.stringify(r,null,1); }catch(e){ return s; }
};
if(typeof window!=='undefined' && window.ABC_PD) window.ABC_PD.report=abcPdReport;

/* hooks */
const abcRenderFsBase=render;
render=function(){ const r=abcRenderFsBase.apply(this,arguments); try{ abcFsAfter(); }catch(e){} return r; };
setInterval(function(){ try{ abcFsAfter(); }catch(e){} },1000);
if(typeof window!=='undefined') window.ABC_FSX={ fs:ABC_FS, toggle:abcFsToggle, mode:abcFsMode, pre:ABC_PRE, safe:ABC_SAFE, fire:abcSafeFire, snap:abcSnap, after:abcFsAfter };
'''
CSS = r"""
/* fix_fullscreen_smooth */
/* board: square icon hung just left of Tune, so the Tune/Menu/Log row keeps its width and place */
body[data-screen="play"] .tb-btns{position:relative}
.tb-btns .abc-fsbtn{position:absolute;right:100%;top:0;bottom:0;margin-right:6px;white-space:nowrap;min-width:0!important;padding:0 10px!important;font-size:16px!important;line-height:1!important}
body:not([data-screen="play"]) .tb-btns .abc-fsbtn{display:none}
/* menu: matches the gold music/sound buttons, bottom right */
#abcFsMenu{position:fixed;right:14px;bottom:14px;z-index:50;display:flex;align-items:center;gap:6px;font:600 13px/1 var(--cond,system-ui),system-ui,sans-serif;letter-spacing:.06em;
  color:#241f1b;background:#E3A92B;border:2px solid #241f1b;border-radius:10px;padding:9px 12px;box-shadow:3px 3px 0 #241f1b;cursor:pointer;transition:transform .15s,box-shadow .15s}
#abcFsMenu:hover{transform:translate(-1px,-1px);box-shadow:4px 4px 0 #241f1b}
#abcFsMenu:active{transform:translate(2px,2px);box-shadow:1px 1px 0 #241f1b}
/* exit pill: top centre while in full screen, fades after 2.5 s without the mouse moving */
#abcFsExit{position:fixed;top:8px;left:50%;transform:translateX(-50%);z-index:99990;display:none;align-items:center;gap:4px;font:600 13px/1 system-ui,-apple-system,sans-serif;
  color:#241f1b;background:#E3A92B;border:2px solid #241f1b;border-radius:999px;padding:8px 14px 8px 12px;box-shadow:3px 3px 0 #241f1b;cursor:pointer;transition:opacity .4s}
body.abc-fs #abcFsExit{display:flex}
body.abc-fs.abc-fs-idle #abcFsExit{opacity:.18}
body.abc-fs.abc-fs-idle #abcFsExit:hover,body.abc-fs #abcFsExit:focus-visible{opacity:1}
/* auto flat-board note */
#abcSafeNote{position:fixed;left:50%;top:54px;transform:translate(-50%,-12px);z-index:9500;display:flex;align-items:center;gap:10px;max-width:min(560px,92vw);
  background:#241f1b;color:#f6eedb;border:2px solid #E3A92B;border-radius:10px;padding:9px 10px 9px 14px;font:500 14px/1.3 system-ui,-apple-system,sans-serif;
  box-shadow:0 8px 20px rgba(0,0,0,.45);opacity:0;pointer-events:none;transition:opacity .25s,transform .25s}
#abcSafeNote.show{opacity:1;transform:translate(-50%,0);pointer-events:auto}
#abcSafeNote button{font:600 13px system-ui,-apple-system,sans-serif;border:0;border-radius:6px;padding:6px 10px;cursor:pointer;background:#E3A92B;color:#241a06;white-space:nowrap}
#abcSafeNote button[data-safe="ok"]{background:transparent;color:#cdbf9f;padding:6px}
@media (prefers-reduced-motion:reduce){#abcSafeNote,#abcFsExit{transition:none}}
"""
EDITS = [('end of <head> styles', '</style>\n</head>', None, 'css', 1), ('Tune row', "    ${row('Tabletop tilt (3D board)',", '    ${row(\'Auto flat board when slow\',`<input type="checkbox" data-abcautoflat ${abcSafeOff()?\'\':\'checked\'}>`)}   <!-- fix_fullscreen_smooth -->\n    ${row(\'Tabletop tilt (3D board)\',', None, 1), ('Tune handler', '  if(t.dataset.abctilt!=null){ abcTiltSet(!!t.checked); return; }', "  if(t.dataset.abcautoflat!=null){ try{ localStorage.setItem('abc_autoflat', t.checked?'on':'off'); }catch(e){} return; }   /* fix_fullscreen_smooth */\n  if(t.dataset.abctilt!=null){ abcTiltSet(!!t.checked); return; }", None, 1), ('JS insertion point (before menuScreen)', 'function menuScreen(){\n', None, 'js', 1)]

for l,a,_,k,n in EDITS:
    c=s.count(a)
    if c!=n: sys.exit(f'{TAG} ERROR: anchor "{l}" found {c} times (expected {n}). Nothing written.')
for l,a,rep,k,n in EDITS:
    if k=='css': rep=CSS+a
    elif k=='js': rep=JS+'\n'+a
    s=s.replace(a,rep,1)
for need in [MARK,'function abcFsToggle(','data-abcautoflat','#abcFsExit{','abcSafeLoop']:
    if need not in s: sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
bak=SRC+'.bak_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); shutil.copyfile(SRC,bak)
open(SRC,'w',encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:',bak); print(f'{TAG} Next: python3 build.py')
