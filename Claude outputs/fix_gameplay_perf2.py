#!/usr/bin/env python3
"""fix_gameplay_perf2.py -- gameplay lag, part 2 (run after fix_gameplay_perf.py).

Run from the repo root:   python3 fix_gameplay_perf2.py
                          python3 build.py
Undo:                     restore src/game.src.html from the .bak this writes.

WHAT IT DOES
  * Tune > "Animation speed": Fast (new default) / Normal / Instant.
      - Card-play flight 1.3 s -> 0.65 s (Fast) or skipped (Instant). Your answer -> card settled waits that long.
      - AI turn pacing x0.55 (Fast) or x0.2 (Instant); Normal keeps today's timing exactly.
  * Looping glows (attack READY, thesis met, 1st Edition holo + sheen) now animate opacity/transform, so the board is
    no longer repainted 60 times a second while an attack is ready.
  * Hand hover animates only the lift; the big shadow switches instead of animating its blur.
  * Tune > 'Performance meter': a small corner readout (fps, worst frame, stutters) to pin down any lag left on your Mac.
  * Sound: one shared white-noise buffer instead of generating fresh random samples for every snare, hat and hit.
"""
import os, sys, shutil, datetime
SRC=os.path.join('src','game.src.html'); MARK='/* fix_gameplay_perf2 */'; TAG='[fix_gameplay_perf2]'
if not os.path.exists(SRC): sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s=open(SRC,encoding='utf-8').read()
if MARK in s: sys.exit(f'{TAG} Already applied -- nothing to do.')
if '/* fix_gameplay_perf */' not in s: sys.exit(f'{TAG} ERROR: run fix_gameplay_perf.py first. Nothing written.')

JS = r'''/* fix_gameplay_perf2 */
/* fix_gameplay_perf2: Animation speed (Tune) + cheaper effects and sound. */
function abcSpeed(){ try{ const v=localStorage.getItem('abc_speed'); return (v==='normal'||v==='instant')?v:'fast'; }catch(e){ return 'fast'; } }
function abcFlyMsFor(){ const s=abcSpeed(); return s==='normal'?1300:(s==='instant'?0:650); }
/* AI pacing: every AI step delay goes through this (Normal 1x, Fast 0.55x, Instant 0.2x) */
function abcPace(ms){ const s=abcSpeed(); return Math.round(ms*(s==='normal'?1:(s==='instant'?0.2:0.55))); }
function abcSpeedSet(v){ try{ localStorage.setItem('abc_speed', v); }catch(e){} try{ ABC_FLY_MS=abcFlyMsFor(); }catch(e){} }
/* one shared white-noise buffer per audio context instead of generating fresh random samples on every hit */
const ABC_NOISE=new WeakMap();
function abcNoiseBuf(ctx){
  let b=ABC_NOISE.get(ctx); if(b) return b;
  const n=Math.floor(ctx.sampleRate*2); b=ctx.createBuffer(1,n,ctx.sampleRate); const ch=b.getChannelData(0);
  for(let i=0;i<n;i++) ch[i]=Math.random()*2-1;
  ABC_NOISE.set(ctx,b); return b;
}
/* Tune > Performance meter: frames per second, worst frame and stutters over the last 3 s (rAF loop only while on) */
let ABC_PM=null;
function abcPerfOn(){ try{ return localStorage.getItem('abc_perfmeter')==='on'; }catch(e){ return false; } }
function abcPerfSet(on){ try{ localStorage.setItem('abc_perfmeter', on?'on':'off'); }catch(e){} abcPerfMeter(on); }
function abcPerfMeter(on){
  if(!on){ if(ABC_PM){ ABC_PM.stop=true; ABC_PM.el.remove(); ABC_PM=null; } return; }
  if(ABC_PM) return;
  const el=document.createElement('div'); el.id='abcPerfMeter';
  el.style.cssText='position:fixed;right:8px;bottom:8px;z-index:99999;pointer-events:none;background:rgba(20,17,14,.88);color:#e8dcc4;font:600 11px/1.35 ui-monospace,Menlo,monospace;padding:6px 9px;border-radius:7px;border:1px solid #4a4036;white-space:pre';
  document.body.appendChild(el);
  const st={el:el, stop:false, f:[], last:performance.now(), shown:0};
  ABC_PM=st;
  (function loop(t){ if(st.stop) return; const d=t-st.last; st.last=t; st.f.push([t,d]); while(st.f.length && t-st.f[0][0]>3000) st.f.shift();
    if(t-st.shown>500){ st.shown=t; const ds=st.f.map(x=>x[1]); const worst=Math.max.apply(null,ds.concat([0])); const jank=ds.filter(x=>x>50).length;
      el.textContent='fps '+Math.round(st.f.length/3)+'  worst '+Math.round(worst)+'ms  stutters '+jank+(document.body.classList.contains('abc-tilt')?'  tilt':'')+(document.body.classList.contains('abc-light')?'  light':'');
      el.style.color=jank>2?'#ff9b7a':(worst>34?'#ffd45e':'#a6f07a'); }
    requestAnimationFrame(loop); })(performance.now());
}
setTimeout(function(){ if(abcPerfOn()) abcPerfMeter(true); }, 0);
if(typeof window!=='undefined') window.ABC_SPEED={get:abcSpeed, set:abcSpeedSet, pace:abcPace, flyMs:function(){ return ABC_FLY_MS; }, noise:abcNoiseBuf};
'''
CSS = r"""
/* fix_gameplay_perf2: looping glows run on the compositor (opacity/transform) instead of repainting the board every frame */
.pc-move.atk.ready{animation:none!important;position:relative}
.pc-move.atk.ready::before{content:"";position:absolute;inset:-3px;border-radius:inherit;box-shadow:0 0 0 2px var(--gold,#E3A92B),0 0 10px rgba(227,169,43,.55);
  pointer-events:none;opacity:0;animation:abcRing 2.2s ease-in-out infinite;will-change:opacity}
.lc-thesis.met{animation:none!important;position:relative}
.lc-thesis.met::before{content:"";position:absolute;inset:-3px;border-radius:inherit;box-shadow:0 0 0 2px var(--gold,#E3A92B),0 0 12px rgba(230,200,120,.75);
  pointer-events:none;opacity:0;animation:abcRing 2.2s ease-in-out infinite;will-change:opacity}
@keyframes abcRing{0%,100%{opacity:0}50%{opacity:1}}
.char.fe .pc-art::after,.bench-mini.fe .bm-init::after{inset:0 auto 0 0!important;width:200%!important;background-size:50% 100%!important;background-repeat:repeat-x!important;
  background-image:linear-gradient(90deg,rgba(255,0,128,.16),rgba(255,214,0,.16) 25%,rgba(0,224,255,.16) 50%,rgba(140,60,255,.16) 75%,rgba(255,0,128,.16))!important;
  animation:abcHolo 6.5s linear infinite!important;will-change:transform}
@keyframes abcHolo{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.char.fe .pc-art::before{background-size:100% 100%!important;animation:abcSheen 4.2s ease-in-out infinite!important;will-change:transform}
@keyframes abcSheen{0%{transform:translateX(-110%)}55%,100%{transform:translateX(110%)}}
/* hand hover: the lift animates; the shadow just switches (animating a 24px blur repainted the card each frame) */
body[data-screen="play"] .hand .hc{transition:transform .16s ease!important}
@media (prefers-reduced-motion:reduce){.pc-move.atk.ready::before,.lc-thesis.met::before{animation:none;opacity:1}}
body.calm-fx .pc-move.atk.ready::before,body.calm-fx .lc-thesis.met::before{opacity:1}
"""
EDITS = [('end of <head> styles', '</style>\n</head>', None, 'css', 1), ('card-play length follows Animation speed', 'const ABC_FLY_MS=1300;', 'let ABC_FLY_MS=abcFlyMsFor();   /* fix_gameplay_perf2 */', None, 1), ('Instant skips the card flight', "function abcFlyCalm(){ try{ return document.body.classList.contains('calm-fx') ||", "function abcFlyCalm(){ try{ return abcSpeed()==='instant' || document.body.classList.contains('calm-fx') ||", None, 1), ('AI attach step', 'setTimeout(step,400);', 'setTimeout(step,abcPace(400));', None, 1), ('AI to engage', 'setTimeout(aiEngage,400);', 'setTimeout(aiEngage,abcPace(400));', None, 1), ('AI turn start delay', '    }; step();\n  },400);\n}\nfunction aiEngage(){', '    }; step();\n  },abcPace(400));   /* fix_gameplay_perf2 */\n}\nfunction aiEngage(){', None, 1), ('AI attack delay', "    else { pushLog('Opponent has no charged attack — passes.'); endAiTurn(); }\n  },500);", "    else { pushLog('Opponent has no charged attack — passes.'); endAiTurn(); }\n  },abcPace(500));   /* fix_gameplay_perf2 */", None, 1), ('AI hand-back delay', "  S.turn='you'; startTurn(); } },700); }", "  S.turn='you'; startTurn(); } },abcPace(700)); }   /* fix_gameplay_perf2 */", None, 1), ('AI end delays (x2)', "S.phase='engage'; render(); setTimeout(endAiTurn,1000); return;", "S.phase='engage'; render(); setTimeout(endAiTurn,abcPace(1000)); return;", None, 2), ('sound: noise buffer', '    if(!ctx) return; const n=Math.max(1,Math.floor(ctx.sampleRate*dur)), buf=ctx.createBuffer(1,n,ctx.sampleRate), ch=buf.getChannelData(0);\n    for(let i=0;i<n;i++) ch[i]=Math.random()*2-1;\n    const src=ctx.createBufferSource(); src.buffer=buf;', '    if(!ctx) return; const buf=abcNoiseBuf(ctx);   /* fix_gameplay_perf2 */\n    const src=ctx.createBufferSource(); src.buffer=buf;', None, 1), ('sound: snare buffer', '    const src=ctx.createBufferSource(), nb=ctx.createBuffer(1,Math.floor(ctx.sampleRate*0.2),ctx.sampleRate), c=nb.getChannelData(0);\n    for(let i=0;i<c.length;i++) c[i]=Math.random()*2-1; src.buffer=nb;', '    const src=ctx.createBufferSource(), nb=abcNoiseBuf(ctx); src.buffer=nb;   /* fix_gameplay_perf2 */', None, 1), ('Tune row', "    ${row('Tabletop tilt (3D board)',", '    ${row(\'Animation speed\',`<select data-abcspeed>${[\'fast\',\'normal\',\'instant\'].map(v=>`<option value="${v}" ${abcSpeed()===v?\'selected\':\'\'}>${v===\'fast\'?\'Fast\':(v===\'normal\'?\'Normal\':\'Instant\')}</option>`).join(\'\')}</select>`)}   <!-- fix_gameplay_perf2 -->\n    ${row(\'Performance meter\',`<input type="checkbox" data-abcperf ${abcPerfOn()?\'checked\':\'\'}>`)}   <!-- fix_gameplay_perf2 -->\n    ${row(\'Tabletop tilt (3D board)\',', None, 1), ('Tune handler', '  if(t.dataset.abctilt!=null){ abcTiltSet(!!t.checked); return; }', '  if(t.dataset.abcspeed!=null){ abcSpeedSet(t.value); return; }   /* fix_gameplay_perf2 */\n  if(t.dataset.abcperf!=null){ abcPerfSet(!!t.checked); return; }   /* fix_gameplay_perf2 */\n  if(t.dataset.abctilt!=null){ abcTiltSet(!!t.checked); return; }', None, 1), ('JS insertion point (before menuScreen)', 'function menuScreen(){\n', None, 'js', 1)]

for l,a,_,k,n in EDITS:
    c=s.count(a)
    if c!=n: sys.exit(f'{TAG} ERROR: anchor "{l}" found {c} times (expected {n}). Nothing written.')
for l,a,rep,k,n in EDITS:
    if k=='css': rep=CSS+a
    elif k=='js': rep=JS+'\n'+a
    s=s.replace(a,rep) if n>1 else s.replace(a,rep,1)
for need in [MARK,'let ABC_FLY_MS=abcFlyMsFor();','abcPace(400)','data-abcspeed','abcNoiseBuf(ctx)','@keyframes abcRing']:
    if need not in s: sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
if 'Math.random()*2-1; src.buffer=nb;' in s: sys.exit(f'{TAG} ERROR: post-check failed (snare). Nothing written.')
bak=SRC+'.bak_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); shutil.copyfile(SRC,bak)
open(SRC,'w',encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:',bak); print(f'{TAG} Next: python3 build.py')
