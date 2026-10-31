#!/usr/bin/env python3
"""fix_gameplay_perf.py -- gameplay slowdown fixes (no visual or rules changes).

Run from the repo root:   python3 fix_gameplay_perf.py
                          python3 build.py
Undo:                     restore src/game.src.html from the .bak this writes.
Escape hatch:             in the browser console  localStorage.abc_morph='off'  (rebuilds the board the old way).
Needs:                    the board redesign (fix_board_layout_v1+); best with the full current patch stack.

WHAT WAS SLOW (measured on a full-weight build, CPU slowed 4x to stand in for a school laptop / tablet)
  1. Every state change rebuilt the whole board with innerHTML: ~0.5 MB of markup (portraits inlined as base64),
     re-parsed, re-styled, re-laid-out and re-rasterised every card, even if one number changed.
  2. The turn timer shrank by animating its width, which re-laid out and repainted the board 60 times a second,
     all turn long -- even with nobody touching anything.
  3. fitNames shrank names 0.5 px at a time, forcing a full layout on every step.
  4. ~40 images live in :root CSS variables as 40-90 KB data URIs; every style update compared them, doubling the
     cost of each restyle.

WHAT IT DOES
  * abcMorph: renderGame (and the Inspect panel) builds the same markup but patches only what changed. Runtime CSS
    variables (stage scale) are kept, so the board is not fully restyled each render.
  * Images are swapped for short blob: URLs (card data, image maps, logos, :root image variables), converted once in
    small idle batches after load. A self-test keeps data URIs where blob URLs are not allowed.
  * Turn timer animates transform:scaleX instead of width.
  * fitNames measures once, jumps to the fitting size and caches it.

RESULT (same scripted turn, 3 runs each, CPU 4x slower)
  stalled time (frames >50 ms) 3.7 s -> 0.95 s;  janky frames 23 -> 9;  worst frame ~370 -> ~255 ms;
  one board render 100-150 ms -> ~22 ms;  idle CPU on the board -88 %;  markup per render 0.5 MB -> 12 KB.
"""
import os, sys, shutil, datetime
SRC=os.path.join('src','game.src.html'); MARK='/* fix_gameplay_perf */'; TAG='[fix_gameplay_perf]'
if not os.path.exists(SRC): sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s=open(SRC,encoding='utf-8').read()
if MARK in s: sys.exit(f'{TAG} Already applied -- nothing to do.')
for need,why in [('function abcInspectHtml(','fix_board_layout_v1'),('function abcInspectPaint(','fix_board_layout_v2')]:
    if need not in s: sys.exit(f'{TAG} ERROR: prerequisite missing ({why}). Nothing written.')

JS = r'''/* fix_gameplay_perf */
/* fix_gameplay_perf: update the board in place instead of rebuilding it.
   renderGame used to replace the whole board with innerHTML on every state change, so every card, portrait and
   frame was re-parsed, re-decoded, re-laid-out and re-rasterised -- even when one number changed. abcMorph builds the
   same markup, compares it with what is on screen and touches only what differs. Unchanged cards keep their pixels. */
const ABC_MORPH_TPL=document.createElement('template');
function abcMorphAttrs(a,b){
  const ba=b.attributes, aa=a.attributes;
  /* CSS variables that layout code sets after a render (e.g. the stage scale --abc-k) are kept, so the whole board
     is not re-styled just because the fresh markup does not carry them yet */
  let keep=null; const st=a.style, bs=b.getAttribute('style');
  if(st && st.length && a.getAttribute('style')!==bs){
    const last=a._abcTplStyle||'';   /* what the markup itself set last time: anything else was added by script */
    for(let i=0;i<st.length;i++){ const p=st[i]; if(p.charCodeAt(0)===45&&p.charCodeAt(1)===45&&last.indexOf(p+':')<0&&(!b.style||!b.style.getPropertyValue(p))) (keep=keep||[]).push([p,st.getPropertyValue(p)]); } }
  a._abcTplStyle=bs||'';
  for(let i=aa.length-1;i>=0;i--){ const n=aa[i].name; if(!b.hasAttribute(n)) a.removeAttribute(n); }
  for(let i=0;i<ba.length;i++){ const n=ba[i].name, v=ba[i].value; if(a.getAttribute(n)!==v) a.setAttribute(n,v); }
  if(keep) for(const k of keep) a.style.setProperty(k[0],k[1]);
  if(a.tagName==='INPUT'){ if(a.type==='checkbox'||a.type==='radio'){ if(a.checked!==b.hasAttribute('checked')) a.checked=b.hasAttribute('checked'); }
    else if(document.activeElement!==a && a.value!==(b.getAttribute('value')||'')) a.value=b.getAttribute('value')||''; }
  else if(a.tagName==='SELECT'){ /* options are morphed as children; keep the chosen one */ const o=b.querySelector('option[selected]'); if(o&&a.value!==o.value) a.value=o.value; }
}
function abcMorphKids(a,b){
  let x=a.firstChild, y=b.firstChild;
  while(y){
    const ny=y.nextSibling;
    if(!x){ a.appendChild(y); y=ny; continue; }
    const nx=x.nextSibling;
    if(x.nodeType===y.nodeType && (x.nodeType!==1 || (x.tagName===y.tagName && x.getAttribute('data-morph')!=='replace'))){
      if(x.nodeType===1){
        /* an <img> whose source changes is swapped whole -- avoids a stale frame flashing while the new image decodes */
        if(x.tagName==='IMG' && x.getAttribute('src')!==y.getAttribute('src')){ a.replaceChild(y,x); }
        else { abcMorphAttrs(x,y); abcMorphKids(x,y); }
      } else if(x.nodeType===3||x.nodeType===8){ if(x.data!==y.data) x.data=y.data; }
    } else a.replaceChild(y,x);
    x=nx; y=ny;
  }
  while(x){ const nx=x.nextSibling; a.removeChild(x); x=nx; }
}
let ABC_MORPH_OFF=false; try{ ABC_MORPH_OFF=localStorage.getItem('abc_morph')==='off'; }catch(e){}   /* escape hatch: localStorage abc_morph=off */
function abcMorph(root,html){
  if(ABC_MORPH_OFF || !root.firstChild || root.getAttribute('data-morph-off')==='1'){ root.innerHTML=abcSlimHtml(html); return; }
  ABC_MORPH_TPL.innerHTML=abcSlimHtml(html);
  abcMorphKids(root, ABC_MORPH_TPL.content);
  ABC_MORPH_TPL.innerHTML='';
}
/* Portraits and frames are inlined as base64 data URIs, so each board render was ~0.5 MB of markup to build, parse
   and compare. Each image is turned into a short blob: URL once and reused; a quick self-test falls back to the data
   URI wherever blob URLs are not allowed (some sandboxed embeds). */
const ABC_BLOB={ map:new Map(), ok:null };
(function(){ try{
  const px='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABpfZFQAAAAABJRU5ErkJggg==';
  const bin=atob(px), u=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++) u[i]=bin.charCodeAt(i);
  const url=URL.createObjectURL(new Blob([u],{type:'image/png'})), im=new Image();
  im.onload=function(){ ABC_BLOB.ok=true; try{ abcSlimVars(); }catch(e){} try{ abcSlimData(); }catch(e){} }; im.onerror=function(){ ABC_BLOB.ok=false; }; im.src=url;
}catch(e){ ABC_BLOB.ok=false; } })();
function abcBlobUrl(d){
  let u=ABC_BLOB.map.get(d); if(u) return u;
  try{ const c=d.indexOf(','), mime=d.slice(5,d.indexOf(';')), bin=atob(d.slice(c+1)), n=bin.length, a=new Uint8Array(n);
    for(let i=0;i<n;i++) a[i]=bin.charCodeAt(i);
    u=URL.createObjectURL(new Blob([a],{type:mime})); }catch(e){ u=d; }
  ABC_BLOB.map.set(d,u); return u;
}
function abcSlimHtml(html){
  if(ABC_BLOB.ok!==true || html.indexOf('data:image/')<0) return html;
  return html.replace(/data:image\/[a-z+.-]+;base64,[A-Za-z0-9+\/=]{1500,}/g, abcBlobUrl);
}
/* fitNames used to shrink each name 0.5 px at a time, forcing a full layout on every step. This measures once,
   jumps straight to the size that fits (text width scales with font size), checks, and remembers the answer. */
const ABC_FIT=new Map();
function abcFitNamesFast(){
  const els=[...document.querySelectorAll('.pc-name')]; if(!els.length) return true;
  els.forEach(function(el){ el.classList.remove('pc-wrap'); el.style.removeProperty('font-size'); });
  const m=els.map(function(el){ return {el:el, cw:el.clientWidth, sw:el.scrollWidth, fs:parseFloat(getComputedStyle(el).fontSize)||15}; });   /* one layout for all */
  m.forEach(function(o){
    if(o.sw<=o.cw+1 || !o.cw) return;
    const key=o.el.textContent+'|'+o.cw+'|'+o.fs;
    let r=ABC_FIT.get(key);
    if(r===undefined){
      let size=Math.max(8.5, Math.floor(o.fs*o.cw/o.sw*2)/2);
      o.el.style.setProperty('font-size',size+'px','important');
      let guard=6; while(o.el.scrollWidth>o.el.clientWidth+1 && size>8.5 && guard-->0){ size-=0.5; o.el.style.setProperty('font-size',size+'px','important'); }
      r=(o.el.scrollWidth>o.el.clientWidth+1)?0:size; ABC_FIT.set(key,r);
    }
    if(r) o.el.style.setProperty('font-size',r+'px','important');
    else { o.el.style.removeProperty('font-size'); o.el.classList.add('pc-wrap'); }
  });
  return true;
}
/* The stylesheet keeps ~40 images (effect sprites, arena art, deck backgrounds, card frames) in :root custom
   properties as data URIs of 40-90 KB each. Custom properties are inherited by every element, and the browser compares
   them on every style update -- which doubled the cost of each recalculation. Swapping each one for a short blob: URL
   keeps every var(--...) working and makes those comparisons trivial. */
function abcSlimVars(){
  const root=document.documentElement, re=/url\((["']?)(data:image\/[a-z+.-]+;base64,[A-Za-z0-9+\/=]{1500,})\1\)/g;
  for(const sh of document.styleSheets){ let rules; try{ rules=sh.cssRules; }catch(e){ continue; }
    for(const r of rules){ if(!r.style || r.selectorText!==':root') continue;
      for(let i=0;i<r.style.length;i++){ const p=r.style[i]; if(p.indexOf('--')!==0) continue;
        const v=r.style.getPropertyValue(p); if(v.length<1500 || v.indexOf('data:image/')<0) continue;
        root.style.setProperty(p, v.replace(re, function(m,q,d){ return 'url("'+abcBlobUrl(d)+'")'; })); } } }
}
/* Card data (DATA, bookmark/deck-box/expansion image maps, logos) holds the same data URIs. Converting them to blob
   URLs once, in small idle batches after load, means renders never build or scan base64 at all. Characters already
   in a running match keep working either way. */
function abcSlimData(){
  const todo=[], seen=new Set();
  const walk=function(o,depth){
    if(!o || typeof o!=='object' || seen.has(o) || depth>7 || o.nodeType || o===window) return; seen.add(o);
    const ks=Array.isArray(o)?o.keys():Object.keys(o);
    for(const k of ks){ let v; try{ v=o[k]; }catch(e){ continue; }
      if(typeof v==='string'){ if(v.length>1500 && v.charCodeAt(0)===100 && v.indexOf('data:image/')===0) todo.push([o,k]); }
      else if(v && typeof v==='object') walk(v,depth+1); }
  };
  try{ walk(window.DATA,0); }catch(e){}
  ['BM_IMG','EXPBM_IMG','DECKBOX','EXPANSIONS','ABC_BOSS_IMG','ABC_IMG','PXB_ART'].forEach(function(n){ try{ walk(window[n],0); }catch(e){} });
  ['ABC_LOGO','ABC_CREST','ABC_EMBLEM'].forEach(function(n){ if(typeof window[n]==='string' && window[n].indexOf('data:image/')===0) todo.push([window,n]); });
  let i=0;
  (function batch(){ const t0=Date.now();
    while(i<todo.length && Date.now()-t0<12){ const o=todo[i][0], k=todo[i][1]; try{ const v=o[k]; if(typeof v==='string' && v.indexOf('data:image/')===0) o[k]=abcBlobUrl(v); }catch(e){} i++; }
    if(i<todo.length) setTimeout(batch,16);
  })();
}
if(typeof window!=='undefined') window.ABC_PERF={morph:abcMorph, blobUrl:abcBlobUrl, slimHtml:abcSlimHtml, slimVars:abcSlimVars, slimData:abcSlimData, blob:ABC_BLOB, fit:ABC_FIT};
'''
CSS = r"""
/* fix_gameplay_perf: the turn timer shrinks with a transform (no layout or repaint every frame) */
.turnbar .tb-fill{width:100%!important;transform-origin:left center;transition:transform .95s linear,background .5s ease;will-change:transform;border-radius:9px}
@media (prefers-reduced-motion:reduce){.turnbar .tb-fill{transition:none}}
body.calm-fx .turnbar .tb-fill{transition:none}
"""
EDITS = [('end of <head> styles', '</style>\n</head>', None, 'css'), ('renderGame: morph instead of innerHTML (open)', '  root.innerHTML=`<div class="abc-stage">${abcInspectPanel()}', '  abcMorph(root,`<div class="abc-stage">${abcInspectPanel()}', None), ('renderGame: morph instead of innerHTML (close)', "${_tbWhere&&_tbWhere!=='board'?turnBarFloatHtml(_tbWhere):''}`;\n  fitNames();", "${_tbWhere&&_tbWhere!=='board'?turnBarFloatHtml(_tbWhere):''}`);   /* fix_gameplay_perf */\n  fitNames();", None), ('turn bar markup', '`<div id="turnbarfill" class="tb-fill" style="width:${_pct}%"></div>`', '`<div id="turnbarfill" class="tb-fill" style="transform:scaleX(${(_pct/100).toFixed(4)})"></div>`', None), ('paintTimer', "  if(fill) fill.style.width=Math.max(0,Math.min(100,(t/tot)*100))+'%';", "  if(fill) fill.style.transform='scaleX('+Math.max(0,Math.min(1,t/tot)).toFixed(4)+')';   /* fix_gameplay_perf */", None), ('fitNames fast path', 'function fitNames(){\n', 'function fitNames(){\n  try{ if(abcFitNamesFast()) return; }catch(e){}   /* fix_gameplay_perf */\n', None), ('Inspect hover paint', "  abcInsp=c; const b=document.querySelector('.abc-inspect .ai-body'); if(b) b.innerHTML=abcInspectHtml();", "  abcInsp=c; const b=document.querySelector('.abc-inspect .ai-body'); if(b) abcMorph(b,abcInspectHtml());   /* fix_gameplay_perf */", None), ('Inspect repaint', "function abcInspectPaint(){ const b=document.querySelector('.abc-inspect .ai-body'); if(b) b.innerHTML=abcInspectHtml(); }", "function abcInspectPaint(){ const b=document.querySelector('.abc-inspect .ai-body'); if(b) abcMorph(b,abcInspectHtml()); }   /* fix_gameplay_perf */", None), ('JS insertion point (before menuScreen)', 'function menuScreen(){\n', None, 'js')]

for l,a,_,k in EDITS:
    n=s.count(a)
    if n!=1: sys.exit(f'{TAG} ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')
for l,a,rep,k in EDITS:
    if k=='css': rep=CSS+a
    elif k=='js': rep=JS+'\n'+a
    s=s.replace(a,rep,1)
for need in [MARK,'function abcMorph(','abcMorph(root,`<div class="abc-stage">','abcFitNamesFast()) return','scaleX(${(_pct/100)','function abcSlimVars(','function abcSlimData(']:
    if need not in s: sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
if 'root.innerHTML=`<div class="abc-stage">' in s: sys.exit(f'{TAG} ERROR: post-check failed (old board write still present). Nothing written.')
bak=SRC+'.bak_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); shutil.copyfile(SRC,bak)
open(SRC,'w',encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:',bak); print(f'{TAG} Next: python3 build.py')
