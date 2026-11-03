#!/usr/bin/env python3
"""make_lab.py -- writes dist/ABC_safari_lab.html: your built game + a tilt A/B test panel + the proposed
full-screen controls. PREVIEW ONLY: src/ is not touched, nothing is patched.

Run from the repo root, after python3 build.py:
    python3 make_lab.py
Then open dist/ABC_safari_lab.html in Safari.
"""
import os, sys
CSS = r'''/* ===== ABC Safari Lab (preview only) ===== */
/* Mode B "Still 3D": same tabletop, nothing moves inside the tilted pieces, shadows are hard-edged */
body.lab-still.abc-tilt[data-screen="play"] .board .char.fe .pc-art::after,
body.lab-still.abc-tilt[data-screen="play"] .board .char.fe .pc-art::before,
body.lab-still.abc-tilt[data-screen="play"] .board .bench-mini.fe .bm-init::after{animation:none!important;will-change:auto!important}
body.lab-still.abc-tilt[data-screen="play"] .board .pc-move.atk.ready::before,
body.lab-still.abc-tilt[data-screen="play"] .board .lc-thesis.met::before{animation:none!important;opacity:.9!important;will-change:auto!important}
body.lab-still.abc-tilt[data-screen="play"] .turnbar .tb-fill{transition:none!important}
body.lab-still.abc-tilt[data-screen="play"] .board::after{box-shadow:0 0 0 3px #e7d8b6,0 0 0 5px #241f1b,0 9px 0 4px #e7d8b6,0 13px 0 5px #6b4f2a!important}
body.lab-still.abc-tilt[data-screen="play"] .bench-mini{box-shadow:0 4px 0 #241f1b!important}
body.lab-still.abc-tilt[data-screen="play"] .you-side .char{box-shadow:0 0 0 3px #E3A92B,0 6px 0 #241f1b!important}
body.lab-still.abc-tilt[data-screen="play"] .opp-side .char{box-shadow:0 0 0 3px #b5402a,0 6px 0 #241f1b!important}
/* Mode C "Flat tabletop": no 3D at all -- each piece is squashed toward the spine (2D), so the board still reads as
   lying on a table, with deeper cast shadows to sell it */
body.lab-faux.abc-tilt[data-screen="play"] .abc-stage{perspective:none!important}
body.lab-faux.abc-tilt[data-screen="play"] .board::before,body.lab-faux.abc-tilt[data-screen="play"] .board::after,
body.lab-faux.abc-tilt[data-screen="play"] .bench,body.lab-faux.abc-tilt[data-screen="play"] .opp-side .char,
body.lab-faux.abc-tilt[data-screen="play"] .you-side .char,body.lab-faux.abc-tilt[data-screen="play"] .lenschip,
body.lab-faux.abc-tilt[data-screen="play"] .phasehud,body.lab-faux.abc-tilt[data-screen="play"] .kos.opp,
body.lab-faux.abc-tilt[data-screen="play"] .kos.you,body.lab-faux.abc-tilt[data-screen="play"] .turnbar{transform:scaleY(.927)!important;backface-visibility:visible!important}

/* ---- full-screen controls (proposed design) ---- */
.tb-btns{position:relative}
.tb-btns .abc-fsbtn{position:absolute;right:100%;top:0;bottom:0;margin-right:6px;white-space:nowrap;min-width:0!important;padding-left:9px!important;padding-right:9px!important;font-size:16px!important;line-height:1!important}
#abcFsExit{position:fixed;top:8px;left:50%;margin-left:-78px;z-index:99990;display:none;align-items:center;gap:6px;font:600 13px/1 system-ui,-apple-system,sans-serif;
  color:#241f1b;background:#E3A92B;border:2px solid #241f1b;border-radius:999px;padding:8px 13px 8px 11px;box-shadow:3px 3px 0 #241f1b;cursor:pointer;
  transition:opacity .4s,transform .15s}
#abcFsExit:hover{transform:translate(-1px,-1px);box-shadow:4px 4px 0 #241f1b}
body.abc-fs #abcFsExit{display:flex}
body.abc-fs.abc-fs-idle #abcFsExit{opacity:.18}
body.abc-fs.abc-fs-idle #abcFsExit:hover{opacity:1}

/* ---- lab panel ---- */
#abcLab{position:fixed;left:8px;top:8px;z-index:99999;width:268px;background:rgba(20,17,14,.95);color:#e8dcc4;border:1px solid #4a4036;border-radius:10px;
  font:12px/1.35 system-ui,-apple-system,sans-serif;padding:9px 10px;box-shadow:0 8px 24px rgba(0,0,0,.5)}
#abcLab.min .lab-body{display:none}
#abcLab h4{margin:0 0 6px;font:700 12px/1 system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#E3A92B;display:flex;justify-content:space-between;cursor:pointer}
#abcLab .lab-modes{display:grid;grid-template-columns:1fr 1fr;gap:5px}
#abcLab button{font:600 12px system-ui,sans-serif;border:1px solid #6a5c4c;background:#2c2620;color:#e8dcc4;border-radius:6px;padding:6px 6px;cursor:pointer;text-align:left}
#abcLab button.on{background:#E3A92B;color:#241a06;border-color:#E3A92B}
#abcLab button small{display:block;font-weight:400;opacity:.8;font-size:10.5px}
#abcLab .lab-fps{margin:7px 0;font:600 12px ui-monospace,Menlo,monospace}
#abcLab .lab-run{width:100%;text-align:center;background:#1F6A6A;border-color:#1F6A6A;color:#fff;margin-top:2px}
#abcLab .lab-out{white-space:pre;font:11px/1.35 ui-monospace,Menlo,monospace;color:#cdbf9f;margin-top:6px;overflow:auto;max-height:160px}
#abcLab .lab-copy{width:100%;text-align:center;margin-top:5px;display:none}
#abcLab .lab-note{color:#a89a80;font-size:11px;margin-top:5px}
@media (max-width:600px){#abcLab{top:auto;bottom:8px;right:8px;width:auto}}
'''
JS = r'''/* ===== ABC Safari Lab (preview only): tilt A/B test + proposed full-screen controls ===== */
(function(){
  if(window.__abcLab) return; window.__abcLab=1;
  const MODES=[['full','A · Full 3D','current look'],['still','B · Still 3D','same tilt, no motion inside'],['faux','C · Flat tabletop','2D squash, no 3D'],['off','D · Tilt off','flat board']];
  let tiltSaved=null; try{ tiltSaved=localStorage.getItem('abc_tilt'); }catch(e){}
  function setMode(m){
    const b=document.body; b.classList.remove('lab-still','lab-faux');
    try{ localStorage.setItem('abc_tilt', m==='off'?'off':'on'); }catch(e){}
    b.classList.toggle('abc-tilt', m!=='off' && !b.classList.contains('abc-phone'));
    if(m==='still') b.classList.add('lab-still'); if(m==='faux') b.classList.add('lab-faux');
    cur=m; paint(); try{ ABC_DEBUG.render(); }catch(e){}
  }
  let cur='full';
  /* fps */
  const F=[]; let last=performance.now();
  (function loop(t){ F.push([t,t-last]); last=t; while(F.length&&t-F[0][0]>3000) F.shift(); requestAnimationFrame(loop); })(performance.now());
  function stats(from){ const ds=F.filter(x=>x[0]>=from).map(x=>x[1]); const span=(performance.now()-Math.max(from,F.length?F[0][0]:from))/1000;
    return {fps:Math.round(ds.length/Math.max(span,.001)), worst:Math.round(Math.max(0,...ds)), slow:ds.filter(x=>x>50).length}; }
  /* panel */
  const el=document.createElement('div'); el.id='abcLab';
  el.innerHTML='<h4><span>Safari lab · tilt</span><span class="lab-x">–</span></h4><div class="lab-body"><div class="lab-modes">'+
    MODES.map(m=>'<button data-m="'+m[0]+'">'+m[1]+'<small>'+m[2]+'</small></button>').join('')+
    '</div><div class="lab-fps">fps –</div><button class="lab-run">Run test (≈30 s, hands off)</button><div class="lab-out"></div><button class="lab-copy">Copy results</button>'+
    '<div class="lab-note">Start a PreCon Arena match first. Preview only — nothing is saved except your tilt setting.</div></div>';
  function paint(){ el.querySelectorAll('[data-m]').forEach(b=>b.classList.toggle('on',b.dataset.m===cur)); }
  function mount(){ document.body.appendChild(el); paint();
    el.querySelector('h4').onclick=()=>el.classList.toggle('min');
    el.querySelectorAll('[data-m]').forEach(b=>b.onclick=()=>setMode(b.dataset.m));
    el.querySelector('.lab-run').onclick=run;
    el.querySelector('.lab-copy').onclick=function(){ const t=el.__report||''; const ok=()=>{ this.textContent='Copied ✓'; setTimeout(()=>this.textContent='Copy results',1500); };
      try{ navigator.clipboard.writeText(t).then(ok,()=>fallback(t)); }catch(e){ fallback(t); } };
    setInterval(()=>{ const s=stats(performance.now()-3000); el.querySelector('.lab-fps').textContent='fps '+s.fps+'   worst '+s.worst+'ms   slow '+s.slow+'  · '+cur; },500); }
  function fallback(t){ const ta=document.createElement('textarea'); ta.value=t; ta.style.cssText='position:fixed;left:8px;top:300px;width:300px;height:200px;z-index:99999'; document.body.appendChild(ta); ta.select(); try{ document.execCommand('copy'); }catch(e){} ta.onblur=()=>ta.remove(); }
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  async function run(){
    const out=el.querySelector('.lab-out'), btn=el.querySelector('.lab-run'); btn.disabled=true; const res={};
    if(document.body.getAttribute('data-screen')!=='play'){ out.textContent='Start a match first (PreCon Arena).'; btn.disabled=false; return; }
    for(const m of MODES){ setMode(m[0]); out.textContent='testing '+m[1]+'…'; await wait(1200);
      const t0=performance.now(); for(let i=0;i<3;i++){ await wait(1500); try{ ABC_DEBUG.render(); }catch(e){} } await wait(1000);
      res[m[0]]=stats(t0); }
    setMode(tiltSaved==='off'?'off':'full');   /* back to your own setting */
    const fsx=fsState();
    const rep={lab:'ABC SAFARI LAB v1', ua:navigator.userAgent, window:innerWidth+'x'+innerHeight+'@'+devicePixelRatio, results:res, fullscreen:fsx};
    el.__report='ABC SAFARI LAB\n'+JSON.stringify(rep,null,1);
    out.textContent=MODES.map(m=>(m[1]+'            ').slice(0,18)+String(res[m[0]].fps).padStart(4)+' fps  worst '+String(res[m[0]].worst).padStart(4)+'ms  slow '+res[m[0]].slow).join('\n');
    el.querySelector('.lab-copy').style.display='block'; btn.disabled=false;
  }

  /* ===== full-screen controls (proposed design) ===== */
  const D=document, root=D.documentElement;
  const fsEl=()=>D.fullscreenElement||D.webkitFullscreenElement||null;
  const fsCan=()=>!!(D.fullscreenEnabled||D.webkitFullscreenEnabled);
  const inFrame=(()=>{ try{ return window.top!==window.self; }catch(e){ return true; } })();
  function fsState(){ return {api:fsCan(), inFrame:inFrame, mode:fsCan()?'fullscreen':(inFrame?'new-window':'hidden')}; }
  function fsEnter(){ try{ const p=(root.requestFullscreen||root.webkitRequestFullscreen).call(root); if(p&&p.catch) p.catch(()=>{}); }catch(e){} }
  function fsExit(){ try{ const p=(D.exitFullscreen||D.webkitExitFullscreen).call(D); if(p&&p.catch) p.catch(()=>{}); }catch(e){} }
  function fsToggle(){ if(fsEl()) fsExit(); else if(fsCan()) fsEnter(); else if(inFrame) window.open(location.href,'_blank'); }
  function fsIcon(){ return fsEl()?'⤡':(fsCan()?'⛶':'↗'); }
  function fsLabel(){ return fsEl()?'⤡ Exit full screen':(fsCan()?'⛶ Full screen':'↗ Open full window'); }
  function fsSync(){ const on=!!fsEl(); D.body.classList.toggle('abc-fs',on); D.querySelectorAll('.abc-fsbtn').forEach(b=>{ if(b.dataset.icon){ b.textContent=fsIcon(); b.title=fsLabel().slice(2); } else b.textContent=fsLabel(); }); idle();
    setTimeout(()=>window.dispatchEvent(new Event('resize')),60); }
  ['fullscreenchange','webkitfullscreenchange'].forEach(n=>D.addEventListener(n,fsSync));
  /* floating exit pill: always there in full screen, fades when the mouse rests */
  const pill=D.createElement('button'); pill.id='abcFsExit'; pill.type='button'; pill.innerHTML='✕&nbsp;Exit full screen'; pill.onclick=fsExit;
  let it=0; function idle(){ D.body.classList.remove('abc-fs-idle'); clearTimeout(it); it=setTimeout(()=>D.body.classList.add('abc-fs-idle'),2500); }
  ['mousemove','touchstart','keydown'].forEach(n=>D.addEventListener(n,()=>{ if(fsEl()) idle(); },{passive:true}));
  /* button in the board's top row (and on the menu), re-added after each render */
  let q=0; function ensure(){ q=0; if(!fsCan() && !inFrame) return;
    const row=D.querySelector('#game .tb-btns'); if(row && !row.querySelector('.abc-fsbtn')){ const b=D.createElement('button'); b.className='abc-fsbtn'; b.type='button'; b.dataset.icon='1'; b.textContent=fsIcon(); b.title=b.ariaLabel=fsLabel().slice(2); b.onclick=fsToggle; row.insertBefore(b,row.firstChild); }
    if(!D.querySelector('#abcFsMenu')){ const b=D.createElement('button'); b.id='abcFsMenu'; b.className='abc-fsbtn'; b.type='button'; b.textContent=fsLabel(); b.onclick=fsToggle;
      b.style.cssText='position:fixed;right:12px;bottom:12px;z-index:50;font:600 13px system-ui,-apple-system,sans-serif;background:#f6eedb;color:#241f1b;border:2px solid #241f1b;border-radius:8px;padding:7px 11px;box-shadow:3px 3px 0 #241f1b;cursor:pointer'; D.body.appendChild(b); }
    const mb=D.querySelector('#abcFsMenu'); if(mb) mb.style.display=(D.body.getAttribute('data-screen')==='menu')?'':'none'; }
  setInterval(ensure,1000);   /* screen changes that do not touch #game */
  new MutationObserver(()=>{ if(!q) q=requestAnimationFrame(ensure); }).observe(D.getElementById('game')||D.body,{childList:true,subtree:true});
  function boot(){ D.body.appendChild(pill); mount(); ensure(); }
  if(D.readyState==='loading') D.addEventListener('DOMContentLoaded',()=>setTimeout(boot,300)); else setTimeout(boot,300);
  window.ABC_LAB={setMode, run, fsState, fsToggle};
})();
'''
IN=os.path.join('dist','academic_battle_cards.html'); OUT=os.path.join('dist','ABC_safari_lab.html')
if len(sys.argv)>1: IN=sys.argv[1]
if len(sys.argv)>2: OUT=sys.argv[2]
if not os.path.exists(IN): sys.exit(f'[make_lab] ERROR: {IN} not found -- run python3 build.py first.')
s=open(IN,encoding='utf-8').read()
if '__abcLab' in s: sys.exit('[make_lab] ERROR: input already contains the lab.')
i=s.rfind('</body>')
if i<0: sys.exit('[make_lab] ERROR: no </body> in the build.')
inj='<style id="abcLabCss">'+CSS+'</style>\n<script id="abcLabJs">'+JS+'</script>\n'
open(OUT,'w',encoding='utf-8').write(s[:i]+inj+s[i:])
print('[make_lab] wrote',OUT,f'({len(s)+len(inj):,} bytes)'); print('[make_lab] open it in Safari, start a PreCon Arena match, press "Run test".')
