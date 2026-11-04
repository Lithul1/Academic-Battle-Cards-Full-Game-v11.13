#!/usr/bin/env python3
"""make_dd_preview.py -- PREVIEW ONLY. Builds dist/ABC_dragdrop_preview.html from your src + assets with the
drag-and-drop + new card view applied in memory. src/ and your normal build are not touched.

Run from the repo root:   python3 make_dd_preview.py
Then open dist/ABC_dragdrop_preview.html (Safari or Chrome).
"""
import os, sys, re, json
JS = r'''/* fix_dragdrop_cards */
/* fix_dragdrop_cards: hand-card view with an icon column, lens text on the card's own plates,
   and drag-and-drop / tap-to-place for ABC charges, bookmarks that stay in play, and Critical Lenses. */

/* ---------- A. hand-card view ---------- */
const ABC_HELD_CHAR=['highlight','laminate','hardcover','marginNotes','ironcurtain','antiquarian','plotarmor','horizonspromise'];
const ABC_HELD_PICK=['horizonspromise'];          /* these ask which character -- a drop answers the question */
const ABC_HELD_SIDE=['supercharge','truce','cliffnotes','dogear','extracredit','saga','censorship','cliffhanger'];
function abcHvKind(c){ return !c?'':(c.cat==='crit'?'lens':(c.cat==='bookmark'?'bm':(c.cat==='abc'?'abc':'other'))); }
function abcHvLensFace(c){
  const pan=function(k,t){ return '<p><b>'+k+'</b>'+(t||'')+'</p>'; };
  return '<div class="hc crit pc-lens hv2-lens"><div class="pfl-wrap">'+abcPcLensFace(c,'full',abcPcLensPanels(c))+'</div>'
    +'<div class="hv2-readp">'+pan('Passive',c.passive)+pan('Thesis',c.thesis)+pan('Reward',c.reward)+'</div></div>';
}
handViewModal=function(){
  const i=S._handView; if(i==null) return '';
  const c=S.you.hand[i]; if(!c) return '';
  const k=abcHvKind(c), place=!!(S.drawn&&S.phase==='place'), disc=S.you.discardsLeft||0;
  const lensFace=(k==='lens' && typeof abcPfOn==='function' && abcPfOn());
  const card=lensFace?abcHvLensFace(c):handCard(c,i);
  /* the lens text now sits on the card, and a framed bookmark already prints its effect: no second copy below */
  const info=(lensFace || (k==='bm' && /\bpfb\b/.test(card)))?'':(handViewInfo(c)||'');
  const lensBusy=(k==='lens' && !!S.you.crit);
  const canPlace=!place && !!abcDdKind(c);
  const B=function(cls,d,ico,lbl,extra,dis){ return '<button type="button" class="hv2-b '+cls+(dis?' off':'')+'" '+(d?'data-do="'+d+'"':'')+(dis?' disabled':'')+' title="'+lbl+'" aria-label="'+lbl+'">'+ico+(extra||'')+'<span class="hv2-lbl">'+lbl.split(' (')[0]+'</span></button>'; };
  let acts='';
  if(!place) acts+=B('hv2-play','playhand','▶',lensBusy?'A Lens is already active':'Play card','',lensBusy);
  if(canPlace) acts+=B('hv2-place','placehand','◎','Choose where');
  if(!place) acts+=B('hv2-disc','dischand','🗑',`Discard (${disc} left this turn)`,'<i>'+disc+'</i>',disc<=0);
  acts+=B('hv2-close','closehand','✕','Close');
  return `<div class="modal-bg" data-do="closehand"><div class="hand-view hv2 hv2-${k}">
    <div class="hv2-row"><div class="hv-card">${card}</div><div class="hv2-acts">${acts}</div></div>
    ${info?`<div class="hv2-info">${info}</div>`:''}
    <div class="hv2-note" hidden></div>
    ${S._discConfirm!=null?`<div class="hv-confirm"><b>Discard a Bookmark?</b><span>Bookmarks are scarce. This cannot be undone.</span>
      <div class="hv-cacts"><button class="hv-play" data-do="dischand-yes">Yes, shed it</button><button class="hv-close" data-do="dischand-no">Keep it</button></div></div>`:''}
    </div></div>`;
};
/* fit each plate's text: shrink to a readable minimum; anything still too long becomes "tap the card to read it" */
function abcHvFit(){
  const L=document.querySelector('.hand-view.hv2 .hv2-lens'); if(!L) return;
  let clipped=false;
  L.querySelectorAll('.pfl-pan').forEach(function(p){
    const sp=p.querySelector('span'); if(!sp) return; p.classList.remove('hv2-clip');
    const over=function(){ return sp.scrollHeight>p.clientHeight+1; };
    let f=3.4; p.style.setProperty('--pfs',f+'cqw');
    while(over() && f>2.6){ f=Math.round((f-0.2)*10)/10; p.style.setProperty('--pfs',f+'cqw'); }
    if(over()){ p.classList.add('hv2-clip'); clipped=true; }
  });
  if(clipped){ const W=L.closest('.hv-card')||L; W.setAttribute('data-do','hvread'); L.classList.add('hv2-more'); const n=document.querySelector('.hand-view.hv2 .hv2-note'); if(n){ n.hidden=false; n.textContent='Tap the card to read the full text'; } }
}

/* ---------- B. drag-and-drop + tap-to-place ---------- */
function abcDdKind(c){
  if(!c) return '';
  if(c.cat==='abc') return 'abc';
  if(c.cat==='crit') return (S&&S.you&&!S.you.crit)?'lens':'';
  if(c.cat==='bookmark'){ const e=c.effect; if(ABC_HELD_PICK.indexOf(e)>=0) return 'bmpick'; if(ABC_HELD_CHAR.indexOf(e)>=0) return 'bmchar'; if(ABC_HELD_SIDE.indexOf(e)>=0) return 'bmside'; }
  return '';
}
const ABC_DD={ on:false, mode:'', idx:-1, kind:'', p:null, ghost:null, src:null, zones:[], chips:[], hot:null, endAt:0, pickUid:null, bar:null };
function abcDdGate(){ try{ return !!S && S.turn==='you' && S.phase==='strategize' && !busy && !S.over && !(typeof drawnLocked==='function' && drawnLocked()); }catch(e){ return false; } }
function abcDdShort(n){ try{ return abcShortName(n); }catch(e){ return String(n||''); } }
function abcDdUid(el){ return el.getAttribute('data-charuid') || ((el.getAttribute('data-benchinfo')||'').split(':')[1]) || ''; }
function abcDdTargets(kind,card){
  const d=document, out=[], P=S.you, alive=function(u){ const c=P.team.find(function(x){ return x.uid===u; }); return c && c.hp>0 ? c : null; };
  const act=d.querySelector('#game .char.you[data-charuid]');
  const bench=Array.from(d.querySelectorAll('#game .bench-mini[data-benchinfo^="you:"]'));
  const chars=function(withBench){ const L=[]; if(act) L.push(act); if(withBench) bench.forEach(function(b){ L.push(b); }); return L; };
  const noAttach=(P.attachesLeft||0)<=0 && !((P.flags&&P.flags.feFree)||0);
  if(kind==='abc'){
    chars(true).forEach(function(el){ const ch=alive(abcDdUid(el)); if(!ch) return;
      let lbl='', no=noAttach;
      try{ const atk=card.type==='ATTACK', have=(atk?ch.atkCharge:ch.blkCharge).length, need=atk?attackCostFor('you',ch.atk):blockCostFor(ch,ch.blk);
        lbl=(atk?'⚔ ':'⛊ ')+abcDdShort(ch.name)+' '+have+'→'+Math.min(have+1,99)+(need!=null&&isFinite(need)?'/'+need:''); }catch(e){ lbl='Charge '+abcDdShort(ch.name); }
      out.push({el:el, uid:ch.uid, label:no?'No attaches left':lbl, short:no?'✕':lbl.replace(/^(\S+) \S.*? (\d+→)/,'$1 $2'), no:no}); });
  } else if(kind==='bmpick'){
    chars(true).forEach(function(el){ const ch=alive(abcDdUid(el)); if(ch) out.push({el:el, uid:ch.uid, label:(card.name||'Bookmark')+' → '+abcDdShort(ch.name), short:'＋'}); });
  } else if(kind==='bmchar'){
    if(act){ const ch=alive(abcDdUid(act)); if(ch) out.push({el:act, uid:ch.uid, label:(card.name||'Bookmark')+' → '+abcDdShort(ch.name)}); }
  } else if(kind==='bmside'){
    if(act) out.push({el:act, uid:null, label:'Play '+(card.name||'Bookmark')});
    const z=d.querySelector('#game .you-side .abm-zone'); if(z) out.push({el:z, uid:null, label:'Play '+(card.name||'Bookmark')});
  } else if(kind==='lens'){
    const z=d.querySelector('#game .you-side .lenschip') || d.querySelector('#game .lenschip'); if(z) out.push({el:z, uid:null, label:'Equip Lens'});
  }
  return out;
}
function abcDdMark(){
  const D=ABC_DD; D.chips.forEach(function(c){ c.remove(); }); D.chips=[];
  D.zones.forEach(function(z){ z.el.classList.add('dd-zone');
    const r=z.el.getBoundingClientRect(), ring=document.createElement('div'), chip=document.createElement('div');
    ring.className='dd-ring'+(z.no?' no':'')+(D.hot===z?' hot':''); ring.style.cssText='left:'+Math.round(r.left-5)+'px;top:'+Math.round(r.top-5)+'px;width:'+Math.round(r.width+10)+'px;height:'+Math.round(r.height+10)+'px';
    /* small zones (Backstage minis) carry a short chip; the full label appears on the zone under the pointer */
    z.small=r.width<110; chip.className='dd-chip'+(z.no?' no':'')+(D.hot===z?' hot':''); chip.textContent=(z.small&&D.hot!==z)?(z.short||z.label):z.label;
    chip.style.left=Math.round(r.left+r.width/2)+'px'; chip.style.top=Math.round(Math.max(4,r.top-8))+'px';
    document.body.appendChild(ring); document.body.appendChild(chip); z.ring=ring; z.chip=chip; D.chips.push(ring,chip); });
}
function abcDdBegin(mode,idx,srcEl,x,y){
  const card=S.you.hand[idx], kind=abcDdKind(card); if(!kind) return false;
  const D=ABC_DD; D.on=true; D.mode=mode; D.idx=idx; D.kind=kind; D.card=card; D.hot=null;
  D.zones=abcDdTargets(kind,card);
  document.body.classList.add('dd-on','dd-'+mode);
  if(mode==='drag' && srcEl){
    const r=srcEl.getBoundingClientRect(), g=srcEl.cloneNode(true);
    g.classList.add('dd-ghost'); g.removeAttribute('data-idx'); g.style.width=r.width+'px'; g.style.height=r.height+'px';
    D.gx=x-r.left; D.gy=y-r.top; D.ghost=g; D.src=srcEl; srcEl.classList.add('dd-src');
    document.body.appendChild(g); abcDdMove(x,y);
  }
  if(mode==='place'){
    const bar=document.createElement('div'); bar.className='dd-bar';
    bar.innerHTML='<span>Tap where to place <b></b></span><button type="button" data-dd="cancel">Cancel</button>';
    bar.querySelector('b').textContent=card.name||(card.type==='ATTACK'?'⚔ '+card.power:(card.type==='BLOCK'?'⛊ '+card.power:'this card'));
    document.body.appendChild(bar); D.bar=bar;
  }
  abcDdMark();
  try{ SFX.unlock&&SFX.unlock(); }catch(e){}
  return true;
}
function abcDdZoneAt(x,y){   /* every layer under the point, so the ghost or a chip never hides a zone */
  const D=ABC_DD, L=document.elementsFromPoint?document.elementsFromPoint(x,y):[document.elementFromPoint(x,y)];
  for(let i=0;i<L.length;i++){ const e=L[i]; if(!e || (D.ghost && D.ghost.contains(e))) continue; const zEl=e.closest&&e.closest('.dd-zone'); if(zEl){ const z=D.zones.find(function(q){ return q.el===zEl; }); if(z) return z; } }
  return null;
}
function abcDdMove(x,y){
  const D=ABC_DD, g=D.ghost; if(!g) return;
  const z=abcDdZoneAt(x,y);
  if(z!==D.hot){
    const off=D.hot; if(off){ if(off.ring) off.ring.classList.remove('hot'); if(off.chip){ off.chip.classList.remove('hot'); if(off.small) off.chip.textContent=off.short||off.label; } }
    D.hot=z||null; if(z){ if(z.ring) z.ring.classList.add('hot'); if(z.chip){ z.chip.classList.add('hot'); z.chip.textContent=z.label; } } }
  g.style.transform='translate3d('+(x-D.gx)+'px,'+(y-D.gy)+'px,0) rotate('+(z?0:-4)+'deg) scale('+(z?0.82:1.04)+')';
  g.classList.toggle('over',!!z);
}
function abcDdEnd(drop){
  const D=ABC_DD; if(!D.on) return;
  const z=drop, idx=D.idx, kind=D.kind, g=D.ghost, src=D.src;
  D.on=false; D.endAt=Date.now(); window._dragJustEnded=Date.now();
  document.body.classList.remove('dd-on','dd-drag','dd-place');
  D.zones.forEach(function(q){ q.el.classList.remove('dd-zone'); }); D.chips.forEach(function(c){ c.remove(); }); D.chips=[]; D.hot=null;
  if(D.bar){ D.bar.remove(); D.bar=null; }
  const ok=!!(z && !z.no && abcDdGate());
  const finish=function(){ if(g) g.remove(); if(src) src.classList.remove('dd-src'); D.ghost=null; D.src=null; if(ok) abcDdAct(idx,kind,z); };
  if(g){
    let tx, ty;
    if(ok){ const r=z.el.getBoundingClientRect(); tx=r.left+r.width/2-g.offsetWidth/2; ty=r.top+r.height/2-g.offsetHeight/2; g.style.transition='transform .17s ease-in, opacity .17s ease-in'; g.style.transform='translate3d('+tx+'px,'+ty+'px,0) scale(.35)'; g.style.opacity='0'; }
    else if(src && src.isConnected){ const r=src.getBoundingClientRect(); g.style.transition='transform .2s ease-out'; g.style.transform='translate3d('+r.left+'px,'+r.top+'px,0)'; }
    else g.style.opacity='0';
    setTimeout(finish, ok?170:200);
  } else finish();
}
function abcDdAct(idx,kind,z){
  const c=S.you.hand[idx]; if(!c || c!==ABC_DD.card) return;
  if(kind==='abc'){ tryPlayHandCard(idx,z.uid); return; }
  if(kind==='bmpick'){ ABC_DD.pickUid=z.uid; try{ tryPlayHandCard(idx); } finally{ setTimeout(function(){ ABC_DD.pickUid=null; },0); } return; }
  tryPlayHandCard(idx);
}
/* a drop on a character answers the "which character?" question the bookmark would otherwise ask */
const abcAskPickDd=askPick;
askPick=function(title,options,cb){
  const u=ABC_DD.pickUid;
  if(u!=null){ ABC_DD.pickUid=null; const o=(options||[]).find(function(x){ return x && x.val===u; }); if(o){ if(cb) cb(o.val); return; } }
  return abcAskPickDd(title,options,cb);
};
/* pointer handling -- capture phase, so the older ABC-only drag never starts alongside this one */
const ABC_DDP={ pid:null, sx:0, sy:0, idx:-1, el:null };
window.addEventListener('pointerdown',function(e){
  if(ABC_DD.on || e.button>0) return;
  const el=e.target&&e.target.closest&&e.target.closest('#game .hand .hc[data-idx]'); if(!el || !abcDdGate()) return;
  const idx=+el.dataset.idx, c=S.you.hand[idx]; if(!abcDdKind(c)) return;
  ABC_DDP.pid=e.pointerId; ABC_DDP.sx=e.clientX; ABC_DDP.sy=e.clientY; ABC_DDP.idx=idx; ABC_DDP.el=el;
  try{ el.setPointerCapture(e.pointerId); }catch(err){}
  try{ SFX.unlock&&SFX.unlock(); }catch(err){}
  e.stopPropagation();
},true);
window.addEventListener('pointermove',function(e){
  if(ABC_DDP.pid!==e.pointerId) return;
  if(!ABC_DD.on){
    if(Math.hypot(e.clientX-ABC_DDP.sx,e.clientY-ABC_DDP.sy) < (e.pointerType==='touch'?12:7)) return;
    if(!abcDdGate() || !abcDdBegin('drag',ABC_DDP.idx,ABC_DDP.el,e.clientX,e.clientY)){ ABC_DDP.pid=null; return; }
  }
  e.preventDefault(); abcDdMove(e.clientX,e.clientY);
},{capture:true,passive:false});
window.addEventListener('pointerup',function(e){
  if(ABC_DDP.pid!==e.pointerId) return; ABC_DDP.pid=null;
  if(ABC_DD.on && ABC_DD.mode==='drag'){ e.preventDefault(); abcDdMove(e.clientX,e.clientY); abcDdEnd(ABC_DD.hot); }
},true);
window.addEventListener('pointercancel',function(e){ if(ABC_DDP.pid===e.pointerId){ ABC_DDP.pid=null; if(ABC_DD.on&&ABC_DD.mode==='drag') abcDdEnd(null); } },true);
/* clicks: swallow the click a drag ends with; run tap-to-place; open "Choose where"; tap-to-read on long lenses */
window.addEventListener('click',function(e){
  const D=ABC_DD, t=e.target;
  if(Date.now()-D.endAt<350 && !D.on){ e.stopPropagation(); e.preventDefault(); return; }
  if(D.on && D.mode==='place'){
    e.stopPropagation(); e.preventDefault();
    if(t.closest&&t.closest('[data-dd="cancel"]')){ abcDdEnd(null); return; }
    abcDdEnd(abcDdZoneAt(e.clientX,e.clientY)); return;
  }
  const b=t.closest&&t.closest('[data-do="placehand"],[data-do="hvread"]'); if(!b) return;
  e.stopPropagation(); e.preventDefault();
  if(b.dataset.do==='hvread'){ const L=b.querySelector('.hv2-lens')||b; L.classList.toggle('hv2-read'); return; }
  const i=S&&S._handView; if(i==null) return; S._handView=null; render();
  if(abcDdGate()) abcDdBegin('place',i,null,0,0);
},true);
document.addEventListener('keydown',function(e){ if(e.key==='Escape' && ABC_DD.on){ abcDdEnd(null); } });

/* hooks: re-mark zones if the board re-renders mid-drag (it re-writes classes); fit the lens plates */
const abcRenderDdBase=render;
render=function(){ const r=abcRenderDdBase.apply(this,arguments);
  try{ if(ABC_DD.on){ if(!abcDdGate()) abcDdEnd(null); else { ABC_DD.zones=abcDdTargets(ABC_DD.kind,ABC_DD.card); abcDdMark(); } } }catch(e){}
  try{ if(S && S._handView!=null) abcHvFit(); }catch(e){}
  return r; };
if(typeof window!=='undefined') window.ABC_DDX={ dd:ABC_DD, kind:abcDdKind, begin:abcDdBegin, end:abcDdEnd, targets:abcDdTargets, fit:abcHvFit };
'''
CSS = r"""
/* fix_dragdrop_cards */
/* ---- hand-card view: card left, icon column right; nothing below for lenses and framed bookmarks ---- */
.hand-view.hv2{gap:8px;max-height:96vh}
.hv2-row{display:flex;align-items:flex-start;gap:10px}
.hv2-acts{display:flex;flex-direction:column;gap:8px;padding-top:2px}
.hv2-b{position:relative;width:52px;height:52px;display:grid;place-items:center;padding:0;font:700 22px/1 system-ui,-apple-system,sans-serif;color:#241f1b;
  background:#fbf6ea;border:2px solid #241f1b;border-radius:10px;box-shadow:3px 3px 0 #241f1b;cursor:pointer;transition:transform .12s,box-shadow .12s}
.hv2-b:hover{transform:translate(-1px,-1px);box-shadow:4px 4px 0 #241f1b}
.hv2-b:active{transform:translate(2px,2px);box-shadow:1px 1px 0 #241f1b}
.hv2-b.hv2-play{background:#E3A92B}
.hv2-b.hv2-place{background:#1F6A6A;color:#fff}
.hv2-b.off{opacity:.45;cursor:default;transform:none!important;box-shadow:3px 3px 0 #241f1b!important}
.hv2-b i{position:absolute;top:-7px;right:-7px;min-width:19px;height:19px;padding:0 4px;border-radius:10px;background:#b5402a;color:#fff;font:700 11px/19px system-ui,sans-serif;font-style:normal;border:2px solid #241f1b}
.hv2-b.off i{background:#6b5f52}
/* label: tooltip on hover (desktop), hidden on touch */
.hv2-lbl{position:absolute;left:calc(100% + 8px);top:50%;transform:translateY(-50%);white-space:nowrap;font:600 12px/1 system-ui,-apple-system,sans-serif;color:#f6eedb;
  background:#241f1b;border-radius:6px;padding:6px 8px;opacity:0;pointer-events:none;transition:opacity .12s}
@media (hover:hover){ .hv2-b:hover .hv2-lbl,.hv2-b:focus-visible .hv2-lbl{opacity:1} }
/* card sizes: always fits the window height */
.hand-view.hv2 .hv2-lens{width:clamp(280px,min(400px,calc((96vh - 40px)*1524/2180),calc(100vw - 96px)),400px)!important;max-width:none!important;min-width:0!important;font-size:inherit!important;height:auto!important;aspect-ratio:auto!important;padding:0!important;
  position:relative;background:none!important;border:0!important;box-shadow:0 14px 30px rgba(0,0,0,.5)!important}
.hand-view.hv2 .hc.pfb{width:min(360px,calc((96vh - 40px)*5/7),calc(100vw - 96px))!important}
.hand-view.hv2 .hv2-lens .pfl-wrap{width:100%}
.hand-view.hv2 .hv2-lens .pfl{border-radius:2.5cqw}
.hand-view.hv2 .hv2-lens .pfl-pan{overflow:hidden}
.hand-view.hv2 .hv2-lens .pfl-pan span{display:block}
.hand-view.hv2 .hv2-lens .pfl-pan.hv2-clip span{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2}
.hand-view.hv2 .hv2-lens.hv2-more{cursor:pointer}
/* tap-to-read panel for the few lenses whose text is too long for the plates */
.hv2-readp{position:absolute;inset:16% 4% 5% 4%;z-index:5;display:none;overflow:auto;background:#fbf6ea;border:2px solid #241f1b;border-radius:8px;padding:10px 12px;text-align:left;
  font:500 14px/1.4 var(--body);color:#241f1b;box-shadow:0 6px 16px rgba(0,0,0,.35)}
.hv2-readp p{margin:0 0 9px}
.hv2-readp b{display:block;font:700 11px/1.2 var(--cond,system-ui);letter-spacing:.14em;text-transform:uppercase;color:#b5402a;margin-bottom:2px}
.hv2-lens.hv2-read .hv2-readp{display:block}
.hv2-info{max-width:min(400px,calc(100vw - 32px))}
.hv2-note{font:600 12px/1.3 system-ui,-apple-system,sans-serif;color:#e8dcc4;letter-spacing:.02em}
@media (max-width:480px){ .hv2-b{width:46px;height:46px;font-size:19px} .hv2-row{gap:7px} }

/* ---- drag-and-drop / tap-to-place ---- */
.dd-ghost{position:fixed!important;left:0!important;top:0!important;margin:0!important;z-index:9800;pointer-events:none!important;transform-origin:30% 30%;
  box-shadow:0 18px 30px rgba(0,0,0,.55)!important;transition:transform .07s linear;will-change:transform;animation:none!important;opacity:.97}
.dd-ghost.over{box-shadow:0 0 0 3px #ffd45e,0 12px 24px rgba(0,0,0,.5)!important}
.dd-ghost *{pointer-events:none!important}
#game .hand .hc.dd-src{opacity:.32!important;filter:none!important}
.dd-zone{cursor:copy}
.dd-ring{position:fixed;z-index:9780;pointer-events:none;border:3px dashed rgba(255,212,94,.95);border-radius:12px;box-sizing:border-box;transition:border-color .1s}
.dd-ring.hot{border:4px solid #ffd45e;box-shadow:0 0 0 3px rgba(36,31,27,.55)}
.dd-ring.no{border-color:rgba(214,90,64,.9)}
.dd-chip{position:fixed;z-index:9790;transform:translate(-50%,-100%);pointer-events:none;white-space:nowrap;font:700 12px/1 system-ui,-apple-system,sans-serif;
  color:#241a06;background:#ffd45e;border:2px solid #241f1b;border-radius:999px;padding:5px 9px;box-shadow:2px 2px 0 #241f1b;transition:transform .12s}
.dd-chip.hot{transform:translate(-50%,-100%) scale(1.12)}
.dd-chip.no{background:#f3c9bd;color:#5a1a10}
.dd-bar{position:fixed;left:50%;bottom:14px;transform:translateX(-50%);z-index:9810;display:flex;align-items:center;gap:12px;background:#241f1b;color:#f6eedb;
  border:2px solid #ffd45e;border-radius:12px;padding:9px 10px 9px 14px;font:500 14px/1.3 system-ui,-apple-system,sans-serif;box-shadow:0 8px 20px rgba(0,0,0,.45)}
.dd-bar button{font:600 13px system-ui,sans-serif;border:0;border-radius:6px;padding:7px 11px;cursor:pointer;background:#E3A92B;color:#241a06}
body.dd-place .dd-zone{cursor:pointer}
/* the older ABC drag's floating label is no longer used */
body.dd-on .drag-ghost,body.dd-on .drag-dot{display:none!important}
@media (prefers-reduced-motion:reduce){ .dd-ghost,.dd-chip,.hv2-b{transition:none!important} }
"""

SRC=os.path.join('src','game.src.html'); MARK='/* fix_dragdrop_cards */'
def apply(s, TAG):
    if MARK in s: sys.exit(f'{TAG} Already applied -- nothing to do.')
    for need,who in [('function abcPcLensFace(','fix_print_cards.py'),('function abcMorph(','fix_gameplay_perf.py'),('function handViewModal(','the base game')]:
        if need not in s: sys.exit(f'{TAG} ERROR: run {who} first. Nothing written.')
    for a in ["</style>\n</head>","function menuScreen(){\n"]:
        if s.count(a)!=1: sys.exit(f'{TAG} ERROR: anchor {a[:20]!r} found {s.count(a)} times (expected 1). Nothing written.')
    s=s.replace("</style>\n</head>",CSS+"</style>\n</head>",1).replace("function menuScreen(){\n",JS+"\nfunction menuScreen(){\n",1)
    for need in [MARK,'handViewModal=function','.dd-ghost{','abcDdBegin']:
        if need not in s: sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
    return s

TAG='[dd_preview]'
if not os.path.exists(SRC): sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s=apply(open(SRC,encoding='utf-8').read(),TAG)
A=json.load(open(os.path.join('assets','assets.json')))
out=re.sub(r'__ABCASSET_(\d+)__',lambda m:A['a'+m.group(1)],s)
if re.search(r'__ABCASSET_\d+__',out): sys.exit(f'{TAG} ERROR: unresolved asset placeholders.')
os.makedirs('dist',exist_ok=True); p=os.path.join('dist','ABC_dragdrop_preview.html'); open(p,'w',encoding='utf-8').write(out)
print(f'{TAG} wrote',p,f'({len(out):,} bytes) -- src/ untouched.')
