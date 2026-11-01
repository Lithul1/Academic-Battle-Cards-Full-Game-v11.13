#!/usr/bin/env python3
"""fix_perf_diag.py -- Performance meter v2 (diagnostics only; no gameplay change).

Run from the repo root:   python3 fix_perf_diag.py
                          python3 build.py
Undo:                     restore src/game.src.html from the .bak this writes.
Needs:                    fix_gameplay_perf2.py (it adds the Tune switch this upgrades).

WHAT IT DOES
  Tune > Performance meter now also shows, for the latest slow frame: how long it took, how much was drawing vs
  style/layout, and the busiest script by name (Chrome/Edge: Long Animation Frames API; other browsers: timing only).
  The current screen is shown too (e.g. scrim/shop:shop). "Copy report" copies the last 25 slow frames + browser,
  screen, view, DOM size, memory -- paste it back so the exact cause can be fixed. Nothing runs while the meter is off.
"""
import os, sys, shutil, datetime
JS = r'''/* fix_perf_diag */
/* fix_perf_diag: Performance meter v2 -- names the work behind each slow frame and copies a report to paste back.
   Uses the Long Animation Frames API where the browser has it (Chrome/Edge 123+); elsewhere falls back to plain
   long-task timing. Costs nothing while the meter is off. */
const ABC_PD={ on:false, frames:[], lo:[], obs:null, el:null, raf:0, last:0, shown:0 };
function abcPdView(){ const b=document.body; return (b.getAttribute('data-screen')||'?')+(b.getAttribute('data-menuscreen')&&b.getAttribute('data-screen')==='menu'?'/'+b.getAttribute('data-menuscreen'):'')+(b.getAttribute('data-screen')==='scrim'?'/'+(b.getAttribute('data-scrimview')||'')+((typeof SCRIM!=='undefined')&&SCRIM.vaultTab&&b.getAttribute('data-scrimview')==='shop'?':'+SCRIM.vaultTab:''):''); }
function abcPdName(s){ const f=(s.sourceFunctionName||'').trim(), inv=(s.invoker||'').replace(/^.*?(TimerHandler|FrameRequestCallback|Window\.requestAnimationFrame|.*onclick|.*\.on\w+).*$/,'$1');
  return (f||'(anonymous)')+(s.sourceCharPosition>=0?' @'+s.sourceCharPosition:'')+' ['+(s.invokerType||'')+(inv?' '+inv.slice(0,40):'')+']'; }
function abcPerfMeter(on){
  const P=ABC_PD;
  if(!on){ P.on=false; cancelAnimationFrame(P.raf); if(P.obs){ try{ P.obs.disconnect(); }catch(e){} P.obs=null; } if(P.el){ P.el.remove(); P.el=null; } return; }
  if(P.on) return; P.on=true; P.frames=[]; P.lo=[];
  const el=document.createElement('div'); el.id='abcPerfMeter';
  el.style.cssText='position:fixed;right:8px;bottom:8px;z-index:99999;max-width:min(430px,94vw);background:rgba(20,17,14,.92);color:#e8dcc4;font:600 11px/1.4 ui-monospace,Menlo,monospace;padding:7px 9px;border-radius:8px;border:1px solid #4a4036;white-space:pre-wrap;word-break:break-word';
  el.innerHTML='<div class="pd-l1"></div><div class="pd-l2" style="color:#cdbf9f;font-weight:400"></div><button type="button" class="pd-copy" style="margin-top:5px;font:600 11px system-ui,sans-serif;background:#E3A92B;color:#241a06;border:0;border-radius:5px;padding:4px 8px;cursor:pointer">Copy report</button>';
  document.body.appendChild(el); P.el=el;
  el.querySelector('.pd-copy').onclick=function(e){ e.stopPropagation(); abcPdCopy(this); };
  try{
    if(PerformanceObserver.supportedEntryTypes && PerformanceObserver.supportedEntryTypes.indexOf('long-animation-frame')>=0){
      P.obs=new PerformanceObserver(function(l){ l.getEntries().forEach(function(e){
        const render=Math.max(0,(e.startTime+e.duration)-(e.renderStart||e.startTime+e.duration)), layout=e.styleAndLayoutStart?Math.max(0,(e.startTime+e.duration)-e.styleAndLayoutStart):0;
        const scripts=(e.scripts||[]).slice().sort(function(a,b){ return b.duration-a.duration; }).slice(0,3).map(function(s){ return {name:abcPdName(s), ms:Math.round(s.duration), src:(s.sourceURL||'').slice(-30)}; });
        P.lo.push({t:Math.round(e.startTime), ms:Math.round(e.duration), block:Math.round(e.blockingDuration||0), render:Math.round(render), styleLayout:Math.round(layout), view:abcPdView(), scripts:scripts});
        if(P.lo.length>40) P.lo.shift(); }); });
      P.obs.observe({type:'long-animation-frame', buffered:false}); P.api='loaf';
    } else if(PerformanceObserver.supportedEntryTypes && PerformanceObserver.supportedEntryTypes.indexOf('longtask')>=0){
      P.obs=new PerformanceObserver(function(l){ l.getEntries().forEach(function(e){ P.lo.push({t:Math.round(e.startTime), ms:Math.round(e.duration), view:abcPdView(), scripts:[]}); if(P.lo.length>40) P.lo.shift(); }); });
      P.obs.observe({type:'longtask', buffered:false}); P.api='longtask';
    } else P.api='none';
  }catch(e){ P.api='none'; }
  P.last=performance.now();
  (function loop(t){ if(!P.on) return; const d=t-P.last; P.last=t; P.frames.push([t,d]); while(P.frames.length && t-P.frames[0][0]>3000) P.frames.shift();
    if(t-P.shown>500 && P.el){ P.shown=t; const ds=P.frames.map(function(x){ return x[1]; }), worst=Math.max.apply(null,ds.concat([0])), jank=ds.filter(function(x){ return x>50; }).length;
      P.el.querySelector('.pd-l1').textContent='fps '+Math.round(P.frames.length/3)+'  worst '+Math.round(worst)+'ms  stutters '+jank+'  · '+abcPdView();
      const now=performance.now(), recent=P.lo.filter(function(x){ return now-x.t<10000; });
      let L=null, agg={}; recent.forEach(function(x){ if(!L||x.ms>L.ms) L=x; (x.scripts||[]).forEach(function(sc){ agg[sc.name]=(agg[sc.name]||0)+sc.ms; }); });
      const top=Object.keys(agg).sort(function(a,b){ return agg[b]-agg[a]; })[0];
      P.el.querySelector('.pd-l2').textContent=L?('worst slow frame (10s) '+L.ms+'ms'+(L.render!=null?' (draw '+L.render+'ms, style+layout '+L.styleLayout+'ms)':'')+(top?'\nbusiest script: '+top+' '+agg[top]+'ms':'')):('no slow frames in 10s · '+P.api);
      P.el.querySelector('.pd-l1').style.color=jank>2?'#ff9b7a':(worst>34?'#ffd45e':'#a6f07a'); }
    P.raf=requestAnimationFrame(loop); })(performance.now());
}
function abcPdReport(){
  const P=ABC_PD, b=document.body, ds=P.frames.map(function(x){ return x[1]; });
  const r={ when:new Date().toISOString(), ua:navigator.userAgent, screen:screen.width+'x'+screen.height+'@'+devicePixelRatio, window:innerWidth+'x'+innerHeight,
    view:abcPdView(), bodyClass:b.className, api:P.api, fps3s:Math.round(P.frames.length/3), worst3s:Math.round(Math.max.apply(null,ds.concat([0]))),
    dom:document.getElementsByTagName('*').length, imgs:document.images.length, anims:(document.getAnimations?document.getAnimations().map(function(a){ return a.animationName||'js'; }).slice(0,20):[]),
    mem:(performance.memory?Math.round(performance.memory.usedJSHeapSize/1048576)+'MB used / '+Math.round(performance.memory.jsHeapSizeLimit/1048576)+'MB':'n/a'),
    speed:(typeof abcSpeed==='function'?abcSpeed():''), slowFrames:P.lo.slice(-25) };
  return 'ABC PERF REPORT\n'+JSON.stringify(r,null,1);
}
function abcPdCopy(btn){
  const txt=abcPdReport(), done=function(ok){ if(btn){ btn.textContent=ok?'Copied ✓':'Select + copy below'; setTimeout(function(){ btn.textContent='Copy report'; },1600); } };
  try{ navigator.clipboard.writeText(txt).then(function(){ done(true); },function(){ abcPdFallback(txt); done(false); }); }
  catch(e){ abcPdFallback(txt); done(false); }
}
function abcPdFallback(txt){ const ta=document.createElement('textarea'); ta.value=txt; ta.style.cssText='position:fixed;left:8px;right:8px;bottom:120px;height:40vh;z-index:99999;font:11px monospace'; document.body.appendChild(ta); ta.focus(); ta.select(); try{ document.execCommand('copy'); }catch(e){} ta.onblur=function(){ ta.remove(); }; }
if(typeof window!=='undefined') window.ABC_PD={ state:ABC_PD, report:abcPdReport };
'''
SRC=os.path.join('src','game.src.html'); MARK='/* fix_perf_diag */'; TAG='[fix_perf_diag]'
if not os.path.exists(SRC): sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s=open(SRC,encoding='utf-8').read()
if MARK in s: sys.exit(f'{TAG} Already applied -- nothing to do.')
if 'function abcPerfMeter(' not in s: sys.exit(f'{TAG} ERROR: run fix_gameplay_perf2.py first. Nothing written.')
A="function menuScreen(){\n"
if s.count(A)!=1: sys.exit(f'{TAG} ERROR: anchor "menuScreen" found {s.count(A)} times (expected 1). Nothing written.')
s=s.replace(A,JS+'\n'+A,1)
if MARK not in s or 'function abcPdReport(' not in s: sys.exit(f'{TAG} ERROR: post-check failed. Nothing written.')
bak=SRC+'.bak_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); shutil.copyfile(SRC,bak)
open(SRC,'w',encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:',bak); print(f'{TAG} Next: python3 build.py')
