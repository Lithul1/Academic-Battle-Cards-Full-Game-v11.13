#!/usr/bin/env python3
"""fix_safari_perf.py -- smoother Safari: no base64 decoding loops after load + script timing in the meter.

Run from the repo root:   python3 fix_safari_perf.py
                          python3 build.py
Undo:                     restore src/game.src.html from the .bak this writes.
Needs:                    fix_perf_diag.py.

WHAT IT DOES
  1. Card art, frames and effect sprites are turned into blob: URLs by the browser itself (fetch), a few at a time,
     instead of a JavaScript loop decoding megabytes of base64. That loop left tens of MB of garbage for Safari to
     collect -- the likely cause of the one-second freezes right after loading / opening the shop. Images not yet
     converted just stay as they are; nothing looks different.
  2. Performance meter: in Safari (which cannot name slow scripts) the game now times its own heavy functions, so each
     slow frame shows "game script X ms / browser Y ms" plus the top functions, and Copy report includes them.
     Timing runs only while the meter is on.
"""
import os, sys, shutil, datetime
JS = r'''/* fix_safari_perf */
/* fix_safari_perf: Safari-friendly image handling + script timing in the Performance meter where the browser
   cannot name slow scripts itself (Safari, Firefox). */
/* 1. Images become blob: URLs through the browser's own fetch (decoded natively, off the main thread), instead of
      decoding base64 in a JavaScript loop -- that loop churned tens of MB of memory after load and Safari paid for it in
      long garbage-collection pauses. Until an image is converted it simply stays a data URI. */
const ABC_BQ={ q:[], busy:0, pend:new Map(), ok:(typeof fetch==='function') };
function abcBlobUrl(d){
  const u=ABC_BLOB.map.get(d); if(u) return u;
  abcBlobQueue(d,null); return d;
}
function abcBlobQueue(d,cb){
  if(ABC_BLOB.map.has(d)){ if(cb) cb(ABC_BLOB.map.get(d)); return; }
  let p=ABC_BQ.pend.get(d); if(p){ if(cb) p.push(cb); return; }
  ABC_BQ.pend.set(d, cb?[cb]:[]); ABC_BQ.q.push(d); abcBlobPump();
}
function abcBlobPump(){
  while(ABC_BQ.busy<3 && ABC_BQ.q.length){
    const d=ABC_BQ.q.shift(); ABC_BQ.busy++;
    const done=function(u){ ABC_BQ.busy--; ABC_BLOB.map.set(d,u); const cbs=ABC_BQ.pend.get(d)||[]; ABC_BQ.pend.delete(d); cbs.forEach(function(f){ try{ f(u); }catch(e){} }); setTimeout(abcBlobPump,0); };
    if(!ABC_BQ.ok || ABC_BLOB.ok!==true){ done(d); continue; }
    fetch(d).then(function(r){ return r.blob(); }).then(function(b){ done(URL.createObjectURL(b)); }).catch(function(){ done(d); });
  }
}
function abcSlimHtml(html){
  if(ABC_BLOB.ok!==true || html.indexOf('data:image/')<0) return html;
  return html.replace(/data:image\/[a-z+.-]+;base64,[A-Za-z0-9+\/=]{1500,}/g, abcBlobUrl);
}
function abcSlimVars(){
  const root=document.documentElement, re=/url\((["']?)(data:image\/[a-z+.-]+;base64,[A-Za-z0-9+\/=]{1500,})\1\)/;
  for(const sh of document.styleSheets){ let rules; try{ rules=sh.cssRules; }catch(e){ continue; }
    for(const r of rules){ if(!r.style || r.selectorText!==':root') continue;
      for(let i=0;i<r.style.length;i++){ const p=r.style[i]; if(p.indexOf('--')!==0) continue;
        const v=r.style.getPropertyValue(p); if(v.length<1500 || v.indexOf('data:image/')<0) continue;
        const m=v.match(re); if(!m) continue;
        abcBlobQueue(m[2], function(u){ if(u!==m[2]) root.style.setProperty(p, v.replace(m[0],'url("'+u+'")')); }); } } }
}
function abcSlimData(){
  const seen=new Set();
  const walk=function(o,depth){
    if(!o || typeof o!=='object' || seen.has(o) || depth>7 || o.nodeType || o===window) return; seen.add(o);
    const ks=Array.isArray(o)?o.keys():Object.keys(o);
    for(const k of ks){ let v; try{ v=o[k]; }catch(e){ continue; }
      if(typeof v==='string'){ if(v.length>1500 && v.charCodeAt(0)===100 && v.indexOf('data:image/')===0) abcBlobQueue(v, function(u){ try{ if(o[k]===v) o[k]=u; }catch(e){} }); }
      else if(v && typeof v==='object') walk(v,depth+1); }
  };
  try{ walk(window.DATA,0); }catch(e){}
  ['BM_IMG','EXPBM_IMG','DECKBOX','EXPANSIONS','ABC_BOSS_IMG','ABC_IMG','PXB_ART'].forEach(function(n){ try{ walk(window[n],0); }catch(e){} });
  ['ABC_LOGO','ABC_CREST','ABC_EMBLEM'].forEach(function(n){ const v=window[n]; if(typeof v==='string' && v.indexOf('data:image/')===0) abcBlobQueue(v,function(u){ if(window[n]===v) window[n]=u; }); });
}
/* 2. Script timing for the Performance meter: the game's heavy functions report how long they ran, so a slow frame can
      be split into "game script" vs "browser drawing" even in Safari. Only measures while the meter is on. */
const ABC_PJ={ depth:0, frame:0, names:{} };
function abcPdWrap(name,f){
  const w=function(){
    if(!ABC_PD.on) return f.apply(this,arguments);
    const t=performance.now(); ABC_PJ.depth++;
    try{ return f.apply(this,arguments); }
    finally{ ABC_PJ.depth--; const d=performance.now()-t; ABC_PJ.names[name]=(ABC_PJ.names[name]||0)+d; if(!ABC_PJ.depth) ABC_PJ.frame+=d; }
  };
  w._abcOrig=f; return w;
}
try{ if(typeof render==='function') render=abcPdWrap('render',render); }catch(e){}
try{ if(typeof renderGame==='function') renderGame=abcPdWrap('renderGame',renderGame); }catch(e){}
try{ if(typeof abcMorph==='function') abcMorph=abcPdWrap('abcMorph',abcMorph); }catch(e){}
try{ if(typeof fitNames==='function') fitNames=abcPdWrap('fitNames',fitNames); }catch(e){}
try{ if(typeof fitBoard==='function') fitBoard=abcPdWrap('fitBoard',fitBoard); }catch(e){}
try{ if(typeof placeTurnBar==='function') placeTurnBar=abcPdWrap('placeTurnBar',placeTurnBar); }catch(e){}
try{ if(typeof abcFlyRun==='function') abcFlyRun=abcPdWrap('abcFlyRun',abcFlyRun); }catch(e){}
try{ if(typeof abcFlySnap==='function') abcFlySnap=abcPdWrap('abcFlySnap',abcFlySnap); }catch(e){}
try{ if(typeof performAttack==='function') performAttack=abcPdWrap('performAttack',performAttack); }catch(e){}
try{ if(typeof finishAttack==='function') finishAttack=abcPdWrap('finishAttack',finishAttack); }catch(e){}
try{ if(typeof doBlock==='function') doBlock=abcPdWrap('doBlock',doBlock); }catch(e){}
try{ if(typeof attach==='function') attach=abcPdWrap('attach',attach); }catch(e){}
try{ if(typeof chargeReport==='function') chargeReport=abcPdWrap('chargeReport',chargeReport); }catch(e){}
try{ if(typeof checkKO==='function') checkKO=abcPdWrap('checkKO',checkKO); }catch(e){}
try{ if(typeof startTurn==='function') startTurn=abcPdWrap('startTurn',startTurn); }catch(e){}
try{ if(typeof endTurn==='function') endTurn=abcPdWrap('endTurn',endTurn); }catch(e){}
try{ if(typeof aiTurn==='function') aiTurn=abcPdWrap('aiTurn',aiTurn); }catch(e){}
try{ if(typeof aiEngage==='function') aiEngage=abcPdWrap('aiEngage',aiEngage); }catch(e){}
try{ if(typeof endAiTurn==='function') endAiTurn=abcPdWrap('endAiTurn',endAiTurn); }catch(e){}
try{ if(typeof fxAt==='function') fxAt=abcPdWrap('fxAt',fxAt); }catch(e){}
try{ if(typeof abcPxAt==='function') abcPxAt=abcPdWrap('abcPxAt',abcPxAt); }catch(e){}
try{ if(typeof abcPxDress==='function') abcPxDress=abcPdWrap('abcPxDress',abcPxDress); }catch(e){}
try{ if(typeof abcPxBossSync==='function') abcPxBossSync=abcPdWrap('abcPxBossSync',abcPxBossSync); }catch(e){}
try{ if(typeof abcInspectPaint==='function') abcInspectPaint=abcPdWrap('abcInspectPaint',abcInspectPaint); }catch(e){}
try{ if(typeof tryPlayHandCard==='function') tryPlayHandCard=abcPdWrap('tryPlayHandCard',tryPlayHandCard); }catch(e){}
try{ if(typeof answerTrivia==='function') answerTrivia=abcPdWrap('answerTrivia',answerTrivia); }catch(e){}
try{ if(typeof playBookmark==='function') playBookmark=abcPdWrap('playBookmark',playBookmark); }catch(e){}
try{ if(typeof scrimScreen==='function') scrimScreen=abcPdWrap('scrimScreen',scrimScreen); }catch(e){}
try{ if(typeof metaSave==='function') metaSave=abcPdWrap('metaSave',metaSave); }catch(e){}
try{ if(typeof abcChEv==='function') abcChEv=abcPdWrap('abcChEv',abcChEv); }catch(e){}
try{ if(typeof abcPxEvolve==='function') abcPxEvolve=abcPdWrap('abcPxEvolve',abcPxEvolve); }catch(e){}
try{ if(typeof spawnKO==='function') spawnKO=abcPdWrap('spawnKO',spawnKO); }catch(e){}
/* the meter loop: per frame, collect the game-script time; a frame over 50 ms is logged with its top functions */
function abcPdTick(gap,t){
  const js=ABC_PJ.frame, nm=ABC_PJ.names; ABC_PJ.frame=0; ABC_PJ.names={};
  if(gap>50 && ABC_PD.api!=='loaf'){
    const top=Object.keys(nm).sort(function(a,b){ return nm[b]-nm[a]; }).slice(0,3).map(function(k){ return {name:k, ms:Math.round(nm[k])}; });
    ABC_PD.lo.push({t:Math.round(t), ms:Math.round(gap), js:Math.round(js), browser:Math.max(0,Math.round(gap-js)), view:abcPdView(), scripts:top});
    if(ABC_PD.lo.length>40) ABC_PD.lo.shift();
  }
}
/* hook the meter: a light second rAF loop (only while the meter is on) feeds abcPdTick and shows the split */
const ABC_SF={ raf:0, last:0 };
const abcPerfMeterPd=abcPerfMeter;
abcPerfMeter=function(on){
  abcPerfMeterPd(on); cancelAnimationFrame(ABC_SF.raf);
  if(!on || !ABC_PD.on || !ABC_PD.el) return;
  let l3=ABC_PD.el.querySelector('.pd-l3');
  if(!l3){ l3=document.createElement('div'); l3.className='pd-l3'; l3.style.cssText='color:#9fd3c7;font-weight:400'; ABC_PD.el.insertBefore(l3, ABC_PD.el.querySelector('.pd-copy')); }
  ABC_PJ.frame=0; ABC_PJ.names={}; ABC_SF.last=performance.now(); let shown=0;
  (function loop(t){ if(!ABC_PD.on) return; const d=t-ABC_SF.last; ABC_SF.last=t; abcPdTick(d,t);
    if(t-shown>500){ shown=t; const now=performance.now(); let W=null;
      ABC_PD.lo.forEach(function(x){ if(x.js!=null && now-x.t<10000 && (!W||x.ms>W.ms)) W=x; });
      l3.textContent=W?('that frame: game script '+W.js+'ms · browser (style/layout/draw/GC) '+W.browser+'ms'):(ABC_PD.api==='loaf'?'':'script timing on (game functions)'); }
    ABC_SF.raf=requestAnimationFrame(loop); })(performance.now());
};

/* 3. Pixel-effect sprite strips: the game pre-drew ALL of them in one go 1.5 s after load -- thousands of 1-px
      fillRects plus PNG encoding, ~0.4 s even on a fast PC and much longer in Safari, whose canvas is slow at this.
      Now each strip is drawn the first time it is needed (or quietly in the background, one per idle moment), and the
      painter only changes colour when the colour actually changes. Same pixels, same timing on screen. */
pxPainter=function(ctx,ox){
  const C=PXC, P={}; let last=null;   /* setting fillStyle parses a colour string every time -- skip it when unchanged */
  P.px=function(x,y,c,d){ x=Math.round(x); y=Math.round(y); if(x<0||y<0||x>=PXN||y>=PXN) return;
    if(d===1&&(x+y)%2) return; if(d===2&&(x%2||y%2)) return; if(c!==last){ ctx.fillStyle=c; last=c; } ctx.fillRect(ox+x,y,1,1); };
  P.line=function(x0,y0,x1,y1,c,d){ x0=Math.round(x0);y0=Math.round(y0);x1=Math.round(x1);y1=Math.round(y1);
    const dx=Math.abs(x1-x0),dy=-Math.abs(y1-y0),sx=x0<x1?1:-1,sy=y0<y1?1:-1; let e=dx+dy;
    for(let i=0;i<200;i++){ P.px(x0,y0,c,d); if(x0===x1&&y0===y1) break; const e2=2*e; if(e2>=dy){e+=dy;x0+=sx;} if(e2<=dx){e+=dx;y0+=sy;} } };
  P.thick=function(x0,y0,x1,y1,w,c,d){ for(let o=-w;o<=w;o++) P.line(x0+o*.7,y0-o*.7,x1+o*.7,y1-o*.7,c,d); };
  P.ring=function(cx,cy,r,c,d){ for(let a=0;a<Math.PI*2;a+=0.6/Math.max(r,1)) P.px(cx+Math.cos(a)*r,cy+Math.sin(a)*r,c,d); };
  P.disc=function(cx,cy,r,c,d){ for(let y=-r;y<=r;y++) for(let x=-r;x<=r;x++) if(x*x+y*y<=r*r+r*.6) P.px(cx+x,cy+y,c,d); };
  P.star4=function(x,y,s,c,core){ P.px(x,y,core||C.white); for(let i=1;i<=s;i++){ P.px(x+i,y,c); P.px(x-i,y,c); P.px(x,y+i,c); P.px(x,y-i,c); } };
  P.glyph=function(rows,x,y,sc,c,ol){ [ol,c].forEach(function(col,pass){ if(!col) return; rows.forEach(function(r,j){ for(let i=0;i<r.length;i++) if(r[i]==='#')
    for(let a=0;a<sc;a++) for(let b=0;b<sc;b++){ if(pass) P.px(x+i*sc+a,y+j*sc+b,col); else [[-1,0],[1,0],[0,-1],[0,1]].forEach(function(o){ P.px(x+i*sc+a+o[0],y+j*sc+b+o[1],col); }); } }); }); };
  return P;
};

function abcPxStrip(k){
  const d=PXD[k];
  try{ const cv=document.createElement('canvas'); cv.width=PXN*d.frames; cv.height=PXN; const ctx=cv.getContext('2d');
    for(let f=0;f<d.frames;f++) d.draw(pxPainter(ctx,f*PXN),f);
    return {url:cv.toDataURL('image/png'),frames:d.frames,ms:Math.round(d.frames*1000/d.fps),loops:d.loops||1}; }
  catch(e){ return {url:'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==',frames:1,ms:Math.round(((d&&d.frames)||1)*1000/((d&&d.fps)||12)),loops:1}; }
}
const ABC_PXL={ cache:{}, drawn:0, warm:[] };
abcPxFx=function(){   /* assigned, not declared: the original is declared later in the file and would win */
  if(_pxFx!==null) return _pxFx||null;
  try{
    const t=document.createElement('canvas').getContext('2d'); if(!t) throw new Error('no 2d');
    const out={};
    Object.keys(PXD).forEach(function(k){ Object.defineProperty(out,k,{enumerable:true,configurable:true,
      get:function(){ let v=ABC_PXL.cache[k]; if(!v){ v=ABC_PXL.cache[k]=abcPxStrip(k); ABC_PXL.drawn++; } return v; }}); });
    _pxFx=out; ABC_PXL.warm=Object.keys(PXD); setTimeout(abcPxWarm,1200);
  }catch(e){ _pxFx=false; }
  return _pxFx||null;
};
function abcPxWarm(){   /* one strip per idle slot, skipped while an effect or a flying card is on screen */
  const L=ABC_PXL; if(!_pxFx || !L.warm.length) return;
  const busy=!!document.querySelector('.pxo-fx,.abc-fly-hand,.fly-card');
  if(!busy){ const k=L.warm.shift(); if(!L.cache[k]) void _pxFx[k]; }
  const next=function(){ setTimeout(abcPxWarm, busy?400:90); };
  if(window.requestIdleCallback) requestIdleCallback(next,{timeout:1500}); else next();
}
if(typeof window!=='undefined') window.ABC_SF={ queue:ABC_BQ, timing:ABC_PJ, blobAsync:abcBlobQueue, wrap:abcPdWrap, px:ABC_PXL };
'''
SRC=os.path.join('src','game.src.html'); MARK='/* fix_safari_perf */'; TAG='[fix_safari_perf]'
if not os.path.exists(SRC): sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s=open(SRC,encoding='utf-8').read()
if MARK in s: sys.exit(f'{TAG} Already applied -- nothing to do.')
for need,who in [('function abcPdReport(','fix_perf_diag.py'),('function abcSlimData(','fix_gameplay_perf.py'),('const ABC_BLOB=','fix_gameplay_perf.py')]:
  if need not in s: sys.exit(f'{TAG} ERROR: run {who} first. Nothing written.')
A="function menuScreen(){\n"
if s.count(A)!=1: sys.exit(f'{TAG} ERROR: anchor "menuScreen" found {s.count(A)} times (expected 1). Nothing written.')
if s.find('/* fix_perf_diag */')>s.find(A): sys.exit(f'{TAG} ERROR: fix_perf_diag block not where expected. Nothing written.')
s=s.replace(A,JS+'\n'+A,1)
if MARK not in s or 'function abcPdTick(' not in s: sys.exit(f'{TAG} ERROR: post-check failed. Nothing written.')
bak=SRC+'.bak_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); shutil.copyfile(SRC,bak)
open(SRC,'w',encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:',bak); print(f'{TAG} Next: python3 build.py')
