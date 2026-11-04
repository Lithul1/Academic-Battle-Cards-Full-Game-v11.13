#!/usr/bin/env python3
"""make_dd_preview3.py -- PREVIEW v3 ONLY. Builds dist/ABC_dragdrop_preview.html from your src + assets with the
drag-and-drop + new card view applied in memory. src/ and your normal build are not touched.

Run from the repo root:   python3 make_dd_preview3.py
Then open dist/ABC_dragdrop_preview.html (Safari or Chrome).
"""
import os, sys, re, json
JS = r'''/* fix_dragdrop_cards */
/* fix_dragdrop_cards: hand-card view with labelled icon buttons, readable lens text, and drag-and-drop for
   ABC charges, character cards, Critical Lenses, bookmarks that stay in play and bookmarks that target a character. */

/* ---------- which cards drag, and where to ---------- */
const ABC_BM_ACTIVE=['highlight','laminate','hardcover','marginNotes','ironcurtain','antiquarian','plotarmor'];   /* stay in play, on your Active */
const ABC_BM_SIDE=['supercharge','truce','cliffnotes','dogear','extracredit','saga','censorship','cliffhanger'];      /* stay in play, side-wide */
const ABC_BM_OWN=['horizonspromise','heal','porchstories','mucksurvival'];          /* ask "which of your characters?" */
const ABC_BM_BENCH=['mac2_gekokujo','f77_boost_bench','f77_guard_bench','trading'];  /* ask "which Backstage ally?" */
const ABC_BM_FOE=['f77_rip_bench','f77_burn_bench'];                                 /* ask "which enemy reserve?" */
function abcDdKind(c){
  if(!c) return '';
  if(c.cat==='abc') return 'abc';
  if(c.cat==='char') return (S&&S.drawn)?'char':'';
  if(c.cat==='crit') return (S&&S.you&&!S.you.crit)?'lens':'';
  if(c.cat==='bookmark'){ const e=c.effect;
    if(ABC_BM_OWN.indexOf(e)>=0) return 'bmown'; if(ABC_BM_BENCH.indexOf(e)>=0) return 'bmbench'; if(ABC_BM_FOE.indexOf(e)>=0) return 'bmfoe';
    if(ABC_BM_ACTIVE.indexOf(e)>=0) return 'bmact'; if(ABC_BM_SIDE.indexOf(e)>=0) return 'bmside'; }
  return '';
}

/* ---------- A. hand-card view ---------- */
function abcHvKind(c){ return !c?'':(c.cat==='crit'?'lens':(c.cat==='bookmark'?'bm':(c.cat==='abc'?'abc':'other'))); }
handViewModal=function(){
  const i=S._handView; if(i==null) return '';
  const c=S.you.hand[i]; if(!c) return '';
  const k=abcHvKind(c), place=!!(S.drawn&&S.phase==='place'), disc=S.you.discardsLeft||0;
  const lensFace=(k==='lens' && typeof abcPfOn==='function' && abcPfOn());
  const card=lensFace?('<div class="hc crit pc-lens hv2-lens"><div class="pfl-wrap">'+abcPcLensFace(c,'full',abcPcLensPanels(c))+'</div></div>'):handCard(c,i);
  /* lens text is on the card, and a framed bookmark already prints its effect: no second copy below */
  const info=(lensFace || (k==='bm' && /\bpfb\b/.test(card)))?'':(handViewInfo(c)||'');
  const lensBusy=(k==='lens' && !!S.you.crit);
  const B=function(cls,d,ico,lbl,extra,dis,tip){ return '<button type="button" class="hv2-b '+cls+(dis?' off':'')+'" data-do="'+d+'"'+(dis?' disabled':'')+' title="'+(tip||lbl)+'" aria-label="'+(tip||lbl)+'"><span class="hv2-ico">'+ico+'</span>'+(extra||'')+'<span class="hv2-lbl">'+lbl+'</span></button>'; };
  let acts='';
  if(!place) acts+=B('hv2-play','playhand','▶','Play','',lensBusy,lensBusy?'A Lens is already active':'Play card');
  if(!place) acts+=B('hv2-disc','dischand','🗑','Discard','<i>'+disc+'</i>',disc<=0,'Discard ('+disc+' left this turn)');
  acts+=B('hv2-close','closehand','✕','Close');
  return `<div class="modal-bg" data-do="closehand"><div class="hand-view hv2 hv2-k-${k}">
    <div class="hv2-row"><div class="hv2-col"><div class="hv-card">${card}</div>${info?`<div class="hv2-info">${info}</div>`:''}${lensBusy?'<div class="hv2-note">A Lens is already active</div>':''}</div><div class="hv2-acts">${acts}</div></div>
    ${S._discConfirm!=null?`<div class="hv-confirm"><b>Discard a Bookmark?</b><span>Bookmarks are scarce. This cannot be undone.</span>
      <div class="hv-cacts"><button class="hv-play" data-do="dischand-yes">Yes, shed it</button><button class="hv-close" data-do="dischand-no">Keep it</button></div></div>`:''}
    </div></div>`;
};
/* readable first: the text stays on the plates only while it fits at 12 px or more; otherwise the card switches to
   the stacked layout (art cropped, full text in panels below) at a comfortable size */
function abcHvFit(){
  const L=document.querySelector('.hand-view.hv2 .hv2-lens'); if(!L) return;
  if(L.offsetWidth<300){ L.classList.remove('hv2-stack'); return; }   /* narrow (phone): already the stacked layout */
  L.classList.remove('hv2-stack');
  let fits=true;
  L.querySelectorAll('.pfl-pan').forEach(function(p){
    const sp=p.querySelector('span'); if(!sp) return;
    const over=function(){ return sp.scrollHeight>p.clientHeight+1; };
    let f=3.4; p.style.setProperty('--pfs',f+'cqw');
    while(over() && f>3.3){ f=Math.round((f-0.1)*10)/10; p.style.setProperty('--pfs',f+'cqw'); }
    if(over()) fits=false;
  });
  if(!fits){ L.classList.add('hv2-stack'); L.querySelectorAll('.pfl-pan').forEach(function(p){ p.style.removeProperty('--pfs'); }); }
}

/* ---------- B. drag-and-drop ---------- */
const ABC_DD={ on:false, idx:-1, kind:'', card:null, ghost:null, src:null, zones:[], chips:[], hot:null, endAt:0, pickUid:null };
function abcDdGate(kind){
  try{
    if(!S || S.turn!=='you' || busy || S.over) return false;
    if(kind==='char') return S.phase==='strategize' || S.phase==='place';   /* characters can also be placed in the opening */
    return S.phase==='strategize' && !(typeof drawnLocked==='function' && drawnLocked());
  }catch(e){ return false; }
}
function abcDdShort(n){ try{ return abcShortName(n); }catch(e){ return String(n||''); } }
function abcDdUid(el){ return el.getAttribute('data-charuid') || ((el.getAttribute('data-benchinfo')||'').split(':')[1]) || ''; }
function abcDdTargets(kind,card){
  const d=document, out=[], P=S.you, F=S.opp;
  const alive=function(side,u){ const c=(side==='you'?P:F).team.find(function(x){ return x.uid===u; }); return c && c.hp>0 ? c : null; };
  const act=d.querySelector('#game .char.you[data-charuid]');
  const bench=Array.from(d.querySelectorAll('#game .bench-mini[data-benchinfo^="you:"]'));
  const foeBench=Array.from(d.querySelectorAll('#game .bench-mini[data-benchinfo^="opp:"]'));
  const nm=card.name||'Bookmark';
  const each=function(els,side,lab){ els.forEach(function(el){ const ch=alive(side,abcDdUid(el)); if(ch) out.push({el:el, uid:ch.uid, label:lab(ch), short:'＋'}); }); };
  if(kind==='abc'){
    const noAttach=(P.attachesLeft||0)<=0 && !((P.flags&&P.flags.feFree)||0);
    (act?[act]:[]).concat(bench).forEach(function(el){ const ch=alive('you',abcDdUid(el)); if(!ch) return;
      let lbl='', sh='';
      try{ const atk=card.type==='ATTACK', have=(atk?ch.atkCharge:ch.blkCharge).length, need=atk?attackCostFor('you',ch.atk):blockCostFor(ch,ch.blk);
        const cnt=have+'→'+(have+1)+(need!=null&&isFinite(need)?'/'+need:''); lbl=(atk?'⚔ ':'⛊ ')+abcDdShort(ch.name)+' '+cnt; sh=(atk?'⚔ ':'⛊ ')+cnt; }catch(e){ lbl='Charge '+abcDdShort(ch.name); sh='＋'; }
      out.push({el:el, uid:ch.uid, label:noAttach?'No attaches left':lbl, short:noAttach?'✕':sh, no:noAttach}); });
  } else if(kind==='char'){
    const side=d.querySelector('#game .you-side'), row=d.querySelector('#game .you-side .row'); if(!side) return out;
    const sr=side.getBoundingClientRect(), rr=row?row.getBoundingClientRect():null;
    const big=function(r){ return r && r.width>=60 && r.height>=30; };   /* .row is display:contents in some layouts */
    let br=d.querySelector('#game .you-side .bench'); br=br&&br.getBoundingClientRect();
    if(!big(br)) br=big(rr)?rr:{left:sr.left, top:sr.top+sr.height*0.62, right:sr.right, bottom:sr.bottom};
    const actRect={l:sr.left, t:sr.top, rr:sr.right, b:(br.top>sr.top+80)?br.top:sr.bottom};
    const live=(typeof drawnHasActive==='function') && drawnHasActive(P);
    const full=(typeof drawnBench==='function' && typeof DRAWN_BENCH_MAX!=='undefined') && drawnBench(P)>=DRAWN_BENCH_MAX;
    const nmc=abcDdShort(card.name), placing=S.phase==='place';
    if(!live) out.push({el:side, region:true, rect:actRect, where:'active', uid:null, label:'Place '+nmc+' as your Active'});
    if(live || placing) out.push({el:row||side, region:true, rect:{l:br.left,t:br.top,rr:br.right,b:br.bottom}, where:'bench', uid:null, label:full?'Backstage is full':'Send '+nmc+' Backstage', no:full});
  } else if(kind==='lens'){
    const z=d.querySelector('#game .you-side .lenschip') || d.querySelector('#game .lenschip'); if(z) out.push({el:z, uid:null, label:'Equip Lens'});
  } else if(kind==='bmact'){
    if(act){ const ch=alive('you',abcDdUid(act)); if(ch) out.push({el:act, uid:ch.uid, label:nm+' → '+abcDdShort(ch.name)}); }
  } else if(kind==='bmside'){
    if(act) out.push({el:act, uid:null, label:'Play '+nm});
    const z=d.querySelector('#game .you-side .abm-zone'); if(z) out.push({el:z, uid:null, label:'Play '+nm});
  } else if(kind==='bmown'){ each((act?[act]:[]).concat(bench),'you',function(ch){ return nm+' → '+abcDdShort(ch.name); }); }
  else if(kind==='bmbench'){ each(bench,'you',function(ch){ return nm+' → '+abcDdShort(ch.name); }); }
  else if(kind==='bmfoe'){ each(foeBench,'opp',function(ch){ return nm+' → '+abcDdShort(ch.name); }); }
  return out;
}
function abcDdMark(){
  const D=ABC_DD; D.chips.forEach(function(c){ c.remove(); }); D.chips=[];
  D.zones.forEach(function(z){
    const er=z.el.getBoundingClientRect(), q=z.rect||{l:er.left,t:er.top,rr:er.right,b:er.bottom}; z.r=q; const r={left:q.l,top:q.t,width:q.rr-q.l,height:q.b-q.t};
    if(!z.region) z.el.classList.add('dd-zone');
    const ring=document.createElement('div'), chip=document.createElement('div');
    ring.className='dd-ring'+(z.region?' region':'')+(z.no?' no':'')+(D.hot===z?' hot':'');
    ring.style.cssText='left:'+Math.round(r.left-5)+'px;top:'+Math.round(r.top-5)+'px;width:'+Math.round(r.width+10)+'px;height:'+Math.round(r.height+10)+'px';
    z.small=r.width<110;   /* Backstage minis: short chip, full label on the one under the pointer */
    chip.className='dd-chip'+(z.no?' no':'')+(D.hot===z?' hot':''); chip.textContent=(z.small&&D.hot!==z)?(z.short||z.label):z.label;
    if(z.region){ chip.style.left=Math.round(r.left+r.width/2)+'px'; chip.style.top=Math.round(r.top+r.height/2)+'px'; chip.classList.add('mid'); }
    else { chip.style.left=Math.round(r.left+r.width/2)+'px'; chip.style.top=Math.round(Math.max(4,r.top-8))+'px'; }
    document.body.appendChild(ring); document.body.appendChild(chip); z.ring=ring; z.chip=chip; D.chips.push(ring,chip); });
}
function abcDdZoneAt(x,y){
  const D=ABC_DD, L=document.elementsFromPoint?document.elementsFromPoint(x,y):[document.elementFromPoint(x,y)];
  for(let i=0;i<L.length;i++){ const e=L[i]; if(!e || (D.ghost && D.ghost.contains(e))) continue;
    const zEl=e.closest&&e.closest('.dd-zone'); if(zEl){ const z=D.zones.find(function(q){ return q.el===zEl; }); if(z) return z; } }
  for(let i=0;i<D.zones.length;i++){ const z=D.zones[i]; if(z.region && z.r && x>=z.r.l && x<=z.r.rr && y>=z.r.t && y<=z.r.b) return z; }   /* board areas */
  return null;
}
function abcDdPos(x,y,over){ const D=ABC_DD; return 'translate3d('+Math.round(x-D.gx)+'px,'+Math.round(y-D.gy)+'px,0) rotate('+(over?0:-4)+'deg) scale('+(over?0.82:1.04)+')'; }
function abcDdBegin(idx,srcEl,x,y){
  const card=S.you.hand[idx], kind=abcDdKind(card); if(!kind || !srcEl) return false;
  const D=ABC_DD; D.on=true; D.idx=idx; D.kind=kind; D.card=card; D.hot=null;
  D.zones=abcDdTargets(kind,card);
  document.body.classList.add('dd-on');
  const r=srcEl.getBoundingClientRect(), g=srcEl.cloneNode(true);
  g.classList.add('dd-ghost'); g.removeAttribute('data-idx'); g.style.width=r.width+'px'; g.style.height=r.height+'px';
  D.gx=x-r.left; D.gy=y-r.top;
  g.style.left='0px'; g.style.top='0px'; g.style.transition='none'; g.style.transform=abcDdPos(x,y,false);   /* placed before it is shown: no slide in from the corner */
  D.ghost=g; D.src=srcEl; srcEl.classList.add('dd-src'); document.body.appendChild(g);
  abcDdMark(); abcDdMove(x,y);
  return true;
}
function abcDdMove(x,y){
  const D=ABC_DD, g=D.ghost; if(!g) return;
  const z=abcDdZoneAt(x,y);
  if(z!==D.hot){
    const off=D.hot; if(off){ if(off.ring) off.ring.classList.remove('hot'); if(off.chip){ off.chip.classList.remove('hot'); if(off.small) off.chip.textContent=off.short||off.label; } }
    D.hot=z||null; if(z){ if(z.ring) z.ring.classList.add('hot'); if(z.chip){ z.chip.classList.add('hot'); z.chip.textContent=z.label; } } }
  g.style.transform=abcDdPos(x,y,!!z); g.classList.toggle('over',!!z);
}
function abcDdEnd(drop){
  const D=ABC_DD; if(!D.on) return;
  const z=drop, idx=D.idx, kind=D.kind, g=D.ghost, src=D.src;
  D.on=false; D.endAt=Date.now(); window._dragJustEnded=Date.now();
  document.body.classList.remove('dd-on');
  D.zones.forEach(function(q){ q.el.classList.remove('dd-zone'); }); D.chips.forEach(function(c){ c.remove(); }); D.chips=[]; D.hot=null;
  const ok=!!(z && !z.no && abcDdGate(kind));
  const finish=function(){ if(g) g.remove(); if(src) src.classList.remove('dd-src'); D.ghost=null; D.src=null; if(ok) abcDdAct(idx,kind,z); };
  if(g){
    if(ok){ const tx=(z.r.l+z.r.rr)/2-g.offsetWidth/2, ty=(z.r.t+z.r.b)/2-g.offsetHeight/2;
      g.style.transition='transform .17s ease-in, opacity .17s ease-in'; g.style.transform='translate3d('+Math.round(tx)+'px,'+Math.round(ty)+'px,0) scale(.35)'; g.style.opacity='0'; }
    else if(src && src.isConnected){ const r=src.getBoundingClientRect(); g.style.transition='transform .2s ease-out'; g.style.transform='translate3d('+Math.round(r.left)+'px,'+Math.round(r.top)+'px,0)'; }
    else g.style.opacity='0';
    setTimeout(finish, ok?170:200);
  } else finish();
}
function abcDdAct(idx,kind,z){
  const c=S.you.hand[idx]; if(!c || c!==ABC_DD.card) return;
  if(kind==='abc'){ tryPlayHandCard(idx,z.uid); return; }
  if(kind==='char' && S.phase==='place'){ drawnPlace(idx, z.where); return; }
  if(z.uid && (kind==='bmown'||kind==='bmbench'||kind==='bmfoe')){ ABC_DD.pickUid=z.uid; try{ tryPlayHandCard(idx); } finally{ setTimeout(function(){ ABC_DD.pickUid=null; },0); } return; }
  tryPlayHandCard(idx);
}
/* a drop on a character answers the bookmark's "which character?" question */
const abcAskPickDd=askPick;
askPick=function(title,options,cb){
  const u=ABC_DD.pickUid;
  if(u!=null){ ABC_DD.pickUid=null;
    const o=(options||[]).find(function(x){ return x && (x.val===u || (typeof x.val==='number' && S && S.you.team[x.val] && S.you.team[x.val].uid===u)); });   /* Trading Places lists team positions */
    if(o){ if(cb) cb(o.val); return; } }
  return abcAskPickDd(title,options,cb);
};
/* pointer handling -- capture phase, so the older ABC-only drag never starts alongside this one */
const ABC_DDP={ pid:null, sx:0, sy:0, idx:-1, el:null };
function abcDdIdx(el){   /* hand position: data-idx, or (characters during the opening placement) the ⓘ button's index */
  if(el.dataset.idx!=null) return +el.dataset.idx;
  const b=el.querySelector('[data-do^="dminfo:"]'); return b?+b.getAttribute('data-do').split(':')[1]:-1;
}
window.addEventListener('pointerdown',function(e){
  if(ABC_DD.on || e.button>0) return;
  if(e.target&&e.target.closest&&e.target.closest('button')) return;   /* buttons on a card (ⓘ, ★ Active, ▼ Bench) keep their taps */
  const el=e.target&&e.target.closest&&e.target.closest('#game .hand .hc'); if(!el) return;
  const idx=abcDdIdx(el); if(idx<0) return;
  const c=S&&S.you&&S.you.hand[idx], k=abcDdKind(c); if(!k || !abcDdGate(k)) return;
  ABC_DDP.pid=e.pointerId; ABC_DDP.sx=e.clientX; ABC_DDP.sy=e.clientY; ABC_DDP.idx=idx; ABC_DDP.el=el;
  try{ el.setPointerCapture(e.pointerId); }catch(err){}
  try{ SFX.unlock&&SFX.unlock(); }catch(err){}
  e.stopPropagation();
},true);
window.addEventListener('pointermove',function(e){
  if(ABC_DDP.pid!==e.pointerId) return;
  if(!ABC_DD.on){
    if(Math.hypot(e.clientX-ABC_DDP.sx,e.clientY-ABC_DDP.sy) < (e.pointerType==='touch'?12:7)) return;
    const c=S.you.hand[ABC_DDP.idx];
    if(!abcDdGate(abcDdKind(c)) || !abcDdBegin(ABC_DDP.idx,ABC_DDP.el,e.clientX,e.clientY)){ ABC_DDP.pid=null; return; }
  }
  e.preventDefault(); abcDdMove(e.clientX,e.clientY);
},{capture:true,passive:false});
window.addEventListener('pointerup',function(e){
  if(ABC_DDP.pid!==e.pointerId) return; ABC_DDP.pid=null;
  if(ABC_DD.on){ e.preventDefault(); abcDdMove(e.clientX,e.clientY); abcDdEnd(ABC_DD.hot); }
},true);
window.addEventListener('pointercancel',function(e){ if(ABC_DDP.pid===e.pointerId){ ABC_DDP.pid=null; if(ABC_DD.on) abcDdEnd(null); } },true);
/* the click a drag ends with must not open anything (bench dossier, card view) */
window.addEventListener('click',function(e){ if(!ABC_DD.on && Date.now()-ABC_DD.endAt<350){ e.stopPropagation(); e.preventDefault(); } },true);
document.addEventListener('keydown',function(e){ if(e.key==='Escape' && ABC_DD.on) abcDdEnd(null); });

/* hooks: re-mark zones if the board re-renders mid-drag (it rewrites classes); fit the lens text */
const abcRenderDdBase=render;
render=function(){ const r=abcRenderDdBase.apply(this,arguments);
  try{ if(ABC_DD.on){ if(!abcDdGate(ABC_DD.kind)) abcDdEnd(null); else { ABC_DD.zones=abcDdTargets(ABC_DD.kind,ABC_DD.card); abcDdMark(); } } }catch(e){}
  try{ if(S && S._handView!=null) abcHvFit(); }catch(e){}
  return r; };
if(typeof window!=='undefined') window.ABC_DDX={ dd:ABC_DD, kind:abcDdKind, begin:abcDdBegin, end:abcDdEnd, targets:abcDdTargets, fit:abcHvFit, zoneAt:abcDdZoneAt };
'''
CSS = r"""
/* fix_dragdrop_cards */
/* ---- hand-card view: card + a column of labelled icon buttons (ABC cards: a row underneath) ---- */
.hand-view.hv2{gap:8px;max-height:96vh}
.hv2-row{display:flex;align-items:flex-start;gap:10px}
.hv2-acts{display:flex;flex-direction:column;gap:8px;padding-top:2px}
.hv2-b{position:relative;width:58px;height:60px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;padding:0;color:#241f1b;
  background:#fbf6ea;border:2px solid #241f1b;border-radius:10px;box-shadow:3px 3px 0 #241f1b;cursor:pointer;transition:transform .12s,box-shadow .12s}
.hv2-ico{font:700 21px/1 system-ui,-apple-system,sans-serif}
.hv2-lbl{font:700 10px/1 system-ui,-apple-system,sans-serif;letter-spacing:.06em;text-transform:uppercase}
.hv2-b:hover{transform:translate(-1px,-1px);box-shadow:4px 4px 0 #241f1b}
.hv2-b:active{transform:translate(2px,2px);box-shadow:1px 1px 0 #241f1b}
.hv2-b.hv2-play{background:#E3A92B}
.hv2-b.off{opacity:.45;cursor:default;transform:none!important;box-shadow:3px 3px 0 #241f1b!important}
.hv2-b i{position:absolute;top:-8px;right:-8px;min-width:19px;height:19px;padding:0 4px;border-radius:10px;background:#b5402a;color:#fff;font:700 11px/15px system-ui,sans-serif;font-style:normal;border:2px solid #241f1b;box-sizing:border-box}
.hv2-b.off i{background:#6b5f52}
/* ABC (attack/block) cards are wide and short: buttons go underneath in a row */
.hand-view.hv2-k-abc .hv2-row{flex-direction:column;align-items:center;gap:12px}
.hand-view.hv2-k-abc .hv2-acts{flex-direction:row;gap:10px;padding:0}
.hand-view.hv2-k-abc .hv2-b{width:auto;min-width:84px;height:46px;flex-direction:row;gap:7px;padding:0 13px}
.hand-view.hv2-k-abc .hv2-ico{font-size:17px}
.hand-view.hv2-k-abc .hv2-lbl{font-size:12px}
/* card sizes: always fit the window height */
.hand-view.hv2 .hv2-lens{width:clamp(280px,min(400px,calc((96vh - 40px)*1524/2180),calc(100vw - 104px)),400px)!important;max-width:none!important;min-width:0!important;
  height:auto!important;aspect-ratio:auto!important;padding:0!important;position:relative;background:none!important;border:0!important;box-shadow:0 14px 30px rgba(0,0,0,.5)!important}
.hand-view.hv2 .hc.pfb{width:min(360px,calc((96vh - 40px)*5/7),calc(100vw - 104px))!important}
.hand-view.hv2 .hv2-lens .pfl-wrap{width:100%}
.hand-view.hv2 .hv2-lens .pfl{border-radius:2.5cqw}
.hand-view.hv2 .hv2-lens .pfl-pan{overflow:hidden}
.hand-view.hv2 .hv2-lens .pfl-pan span{display:block}
/* readable layout for lenses whose text does not fit the plates at ~13 px: art cropped, full text below */
.hand-view.hv2 .hv2-lens.hv2-stack .pfl{aspect-ratio:auto;padding:86.6cqw 0 1.5cqw;background:#f7f1e3}
.hand-view.hv2 .hv2-lens.hv2-stack .pfl::before{bottom:auto;height:86.6cqw}
.hand-view.hv2 .hv2-lens.hv2-stack .pfl-pan{position:relative;z-index:3;top:auto;left:auto;right:auto;height:auto;display:block;margin:0 3cqw 2.2cqw;padding:7px 10px 8px;border-radius:6px;text-align:left;
  background:#2b2520 radial-gradient(120% 140% at 30% 20%,#3d342c,#221d19);box-shadow:inset 0 0 0 1px rgba(0,0,0,.5);font:600 14px/1.4 var(--body);color:#f6ead0}
.hand-view.hv2 .hv2-lens.hv2-stack .pfl-pan b{display:block;font:700 11px/1.2 var(--body);letter-spacing:.1em;text-transform:uppercase;color:#f0b43a;margin-bottom:3px;text-align:left}
/* narrow (phone): the stacked layout, a little larger */
@container (max-width:299px){ .hand-view.hv2 .pfl.full .pfl-pan{font-size:13px!important;line-height:1.4!important;padding:6px 9px 7px!important} }
/* the info panels sit under the card itself, exactly its width (not under card + buttons) */
.hv2-col{display:flex;flex-direction:column;align-items:center;gap:8px}
.hv2-col .hv2-info{width:0;min-width:100%;box-sizing:border-box}
.hv2-col .hv2-info>*{margin-left:0!important;margin-right:0!important;max-width:none!important}
.hv2-note{font:600 12px/1.3 system-ui,-apple-system,sans-serif;color:#e8dcc4;letter-spacing:.02em}
@media (max-width:480px){ .hv2-b{width:50px;height:54px} .hv2-ico{font-size:18px} .hv2-row{gap:7px} }

/* ---- drag-and-drop ---- */
.dd-ghost{position:fixed!important;left:0!important;top:0!important;margin:0!important;z-index:9800;pointer-events:none!important;transform-origin:30% 30%;
  box-shadow:0 18px 30px rgba(0,0,0,.55)!important;will-change:transform;animation:none!important;opacity:.97}
.dd-ghost *{pointer-events:none!important}
.dd-ghost.over{box-shadow:0 0 0 3px #ffd45e,0 12px 24px rgba(0,0,0,.5)!important}
#game .hand .hc.dd-src{opacity:.32!important;filter:none!important}
.dd-zone{cursor:copy}
.dd-ring{position:fixed;z-index:9780;pointer-events:none;border:3px dashed rgba(255,212,94,.95);border-radius:12px;box-sizing:border-box}
.dd-ring.region{border-radius:16px;background:rgba(255,212,94,.06)}
.dd-ring.hot{border:4px solid #ffd45e;box-shadow:0 0 0 3px rgba(36,31,27,.55)}
.dd-ring.region.hot{background:rgba(255,212,94,.14)}
.dd-ring.no{border-color:rgba(214,90,64,.9)}
.dd-chip{position:fixed;z-index:9790;transform:translate(-50%,-100%);pointer-events:none;white-space:nowrap;font:700 12px/1 system-ui,-apple-system,sans-serif;
  color:#241a06;background:#ffd45e;border:2px solid #241f1b;border-radius:999px;padding:5px 9px;box-shadow:2px 2px 0 #241f1b;transition:transform .12s}
.dd-chip.mid{transform:translate(-50%,-50%);font-size:14px;padding:8px 13px}
.dd-chip.hot{transform:translate(-50%,-100%) scale(1.12)}
.dd-chip.mid.hot{transform:translate(-50%,-50%) scale(1.08)}
.dd-chip.no{background:#f3c9bd;color:#5a1a10}
/* the older ABC drag's floating label is no longer used */
body.dd-on .drag-ghost,body.dd-on .drag-dot{display:none!important}
@media (prefers-reduced-motion:reduce){ .dd-chip,.hv2-b{transition:none!important} }
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
print(f'{TAG} v3 wrote',p,f'({len(out):,} bytes) -- src/ untouched.')
