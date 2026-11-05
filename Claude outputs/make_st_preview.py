#!/usr/bin/env python3
"""make_st_preview.py -- PREVIEW ONLY. Builds dist/ABC_scrimtome_preview.html from your src + assets with the
Scrimmage tome look applied in memory. src/ and assets/ are not touched.

Run from the repo root:   python3 make_st_preview.py
Then open dist/ABC_scrimtome_preview.html and go to Literary Scrimmage.
"""
import os, sys, re, json
JS = r'''/* fix_scrim_tome */
/* fix_scrim_tome: Literary Scrimmage as an adventurer's tome -- the map as an open campaign book (party sheets on the
   left, a hand-inked route of wax seals on the right), tome-styled pages for every Scrimmage screen, a candlelit
   tabletop for battles inside a run, and small effects: ink trail + seal stamp when travelling, a page turn between Acts.
   Every Scrimmage action keeps its data-scrim command, so all game logic runs unchanged. */
const ST_GLYPH={ start:'★', scrim:'⚔', archives:'✒', rest:'☕', fair:'⚖', office:'?', elite:'☠', boss:'♛', corrupted:'✖' };
const ST={ busy:false, turn:false };
function stRoman(n){ return (typeof roman==='function')?roman(n):String(n); }
function stEsc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
function stCalm(){ try{ return document.body.classList.contains('calm-fx') || (typeof abcSpeed==='function' && abcSpeed()==='instant') || matchMedia('(prefers-reduced-motion: reduce)').matches; }catch(e){ return false; } }
/* party as character sheets */
function stSheets(){
  return SCRIM.team.map(function(rec){
    const def=rec.fe?firstedById(rec.id):(DATA.characters[rec.deck]||[]).find(function(c){ return c.id===rec.id; }); if(!def) return '';
    const pct=Math.max(0,Math.min(100,(rec.curHp/rec.maxHp)*100)), dead=rec.curHp<=0;
    const im=rec.fe?feImg(def):(def.img?{img:def.img,pos:def.imgpos}:null);
    const por=im&&im.img?'<img src="'+im.img+'" alt="" style="object-position:'+(im.pos||'50% 18%')+'">':'<span>'+stEsc(initials(def.name))+'</span>';
    return '<div class="st-sheet'+(dead?' dead':'')+'"><div class="st-por">'+por+'</div><div class="st-who"><div class="st-nm">'+stEsc(def.name)+'</div>'
      +'<div class="st-cl">'+stEsc(def.archetype||'Adventurer')+(rec.fe?' · 1st Edition':'')+(dead?' · fallen':'')+'</div><div class="st-hpbar"><i style="width:'+pct+'%"></i></div></div>'
      +'<div class="st-stat"><b>'+Math.max(0,rec.curHp)+'</b><small>OF '+rec.maxHp+'</small></div></div>';
  }).join('');
}
function stRelics(){
  if(!SCRIM.artifacts.length) return '<span class="st-none">No relics yet</span>';
  return SCRIM.artifacts.map(function(id){ const a=SCRIM_ART[id]; return a?'<span class="st-relic" title="'+stEsc(a.text)+'">'+a.ic+' '+stEsc(a.name)+'</span>':''; }).join('');
}
scrimMapScreen=function(){
  const m=SCRIM.map, deckN=(SCRIM.deck.ab.length+SCRIM.deck.bm.length+SCRIM.deck.cr.length);
  const rows=m.cols.map(function(col,c){
    return '<div class="smap-col" data-col="'+c+'">'+col.map(function(node,r){
      const meta=SCRIM_NODE[node.type]||{ic:'?',name:'?'}, isPos=(m.pos.c===c&&m.pos.r===r), reach=scrimReachable(c,r);
      const cls=['smap-node','st-seal',node.type,isPos?'pos':'',reach?'reach':'',node.done&&!isPos?'done':''].filter(Boolean).join(' ');
      const label=node.boss?SCRIM_BOSSES[node.boss].name:meta.name;
      return '<button class="'+cls+'" '+(reach?'data-scrim="node:'+c+':'+r+'"':'disabled')+' title="'+stEsc(label)+'" aria-label="'+stEsc(label)+'"><span class="st-wax">'+(ST_GLYPH[node.type]||meta.ic)+'</span><span class="st-lbl">'+stEsc(label)+'</span></button>';
    }).join('')+'</div>';
  }).join('');
  const legend=Object.keys(SCRIM_NODE).map(function(k){ return '<span class="st-lg"><span class="st-wax sm '+k+'">'+(ST_GLYPH[k]||SCRIM_NODE[k].ic)+'</span>'+stEsc(SCRIM_NODE[k].name)+'</span>'; }).join('');
  const kit=(typeof SCRIM_KITS!=='undefined'&&SCRIM_KITS[SCRIM.kit])?SCRIM_KITS[SCRIM.kit].name:'the Unknown';
  const chap=SCRIM.doctoral?('Semester '+(SCRIM.semester||1)):('Act '+stRoman(SCRIM.act||1));
  const folio=2*((SCRIM.act||1)*6)+(m.pos.c||0);
  return `<div class="scrim-wrap scrim-ink st-desk"><div class="st-tome${ST.turn?' st-turn':''}">
    <div class="st-page l">
      <div class="st-ribbon" aria-hidden="true"></div>
      <button class="st-back" data-scrim="endrun">‹ Library card <small>(run saved)</small></button>
      <div class="st-runhead">THE CAMPAIGN OF</div>
      <h2 class="st-chap">The ${stEsc(kit)}<small>${chap}${(SCRIM.honors||0)>0?' · Honors '+stRoman(SCRIM.honors):''}</small></h2>
      <div class="st-orn">✦</div>
      <div class="st-party">${stSheets()}</div>
      <div class="st-ledger">
        <button class="st-row st-deck" data-scrim="rundeck" title="See everything collected this run"><span>Deck</span><b>${deckN} ›</b></button>
        <div class="st-row"><span>Intellect</span><b>🧠 ${META.ip||0}</b></div>
        <div class="st-row"><span>Late Fees</span><b>💳 ${SCRIM.lf||0}</b></div>
        <div class="st-row"><span>${SCRIM.doctoral?'Semester':'Act'}</span><b>${SCRIM.doctoral?(SCRIM.semester||1):stRoman(SCRIM.act||1)}</b></div>
      </div>
      <div class="st-sub">Relics</div><div class="st-relics">${stRelics()}</div>
      <div class="st-sub">Map key</div><div class="st-legend">${legend}</div>
      <div class="st-folio">— ${stRoman(folio)} —</div>
    </div>
    <div class="st-page r">
      <div class="st-runhead">THE ROUTE</div>
      <div class="smap-scroll st-route-wrap"><div class="smap st-route" id="smap">${rows}</div><svg class="smap-lines st-lines" id="smapLines" aria-hidden="true"></svg></div>
      <svg class="st-compass" viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="50" r="44" fill="none" stroke="#4a3522" stroke-width="1.5"/><polygon points="50,6 57,50 50,94 43,50" fill="#4a3522"/><polygon points="6,50 50,43 94,50 50,57" fill="#8e2a1c" opacity=".7"/><text x="50" y="22" text-anchor="middle" font-family="Cinzel,serif" font-size="11" fill="#2b1d12">N</text></svg>
      <div class="st-folio">— ${stRoman(folio+1)} —</div>
    </div>
  </div></div>`;
};
/* the route in ink: walked roads in red, roads open from here in solid ink, the rest faint; the party token sits on its seal */
function stCurve(x1,y1,x2,y2){ const my=(y1+y2)/2; return 'M'+x1+','+y1+' C'+x1+','+my+' '+x2+','+my+' '+x2+','+y2; }
scrimDrawConnectors=function(){
  if(typeof document==='undefined') return;
  const smap=document.getElementById('smap'), svg=document.getElementById('smapLines'); if(!smap||!svg) return;
  const wrap=smap.getBoundingClientRect(); if(!wrap.width) return;
  const m=SCRIM.map, rows=smap.querySelectorAll('.smap-col'); let p='';
  const at=function(c,r){ const el=rows[c]&&rows[c].children[r]; if(!el) return null; const q=el.getBoundingClientRect(); return [q.left+q.width/2-wrap.left, q.top+q.height/2-wrap.top]; };
  m.cols.forEach(function(col,c){ if(c>=m.cols.length-1) return;
    col.forEach(function(node,r){ (node.next||[]).forEach(function(ni){
      const a=at(c,r), b=at(c+1,ni); if(!a||!b) return;
      const nb=m.cols[c+1][ni], walked=(node.done||(m.pos.c===c&&m.pos.r===r)) && (nb.done||(m.pos.c===c+1&&m.pos.r===ni)) && c<m.pos.c;
      const open=(m.pos.c===c&&m.pos.r===r);
      p+='<path class="st-ink'+(walked?' trail':(open?' open':' faint'))+'" d="'+stCurve(a[0],a[1],b[0],b[1])+'"/>';
    }); });
  });
  svg.setAttribute('width',wrap.width); svg.setAttribute('height',wrap.height);
  svg.style.width=wrap.width+'px'; svg.style.height=wrap.height+'px';
  const here=at(m.pos.c,m.pos.r);
  if(here) p+='<g class="st-token" transform="translate('+here[0]+','+(here[1]-30)+')"><ellipse cx="0" cy="28" rx="10" ry="3" fill="rgba(0,0,0,.25)"/><path d="M0 -6c4 0 7 3 7 7 0 3-2 5-3 6l4 16h-16l4-16c-1-1-3-3-3-6 0-4 3-7 7-7z" fill="#1F6A6A" stroke="#0f3535" stroke-width="1.5"/></g>';
  svg.innerHTML=p;
  /* keep the party in view on tall routes */
  try{ const sc=smap.parentElement, cur=rows[m.pos.c]; if(sc && cur && sc.scrollHeight>sc.clientHeight+4){ const t=cur.offsetTop-sc.clientHeight/2; sc.scrollTop=Math.max(0,t); } }catch(e){}
};
/* travelling: ink the road in red, walk the token, stamp the seal -- then the node resolves as before */
window.addEventListener('click',function(e){
  const b=e.target&&e.target.closest&&e.target.closest('.st-tome .smap-node.reach[data-scrim^="node:"]'); if(!b) return;
  if(ST.busy){ e.stopPropagation(); e.preventDefault(); return; }
  if(stCalm()) return;   /* calm effects / Instant speed: straight through */
  e.stopPropagation(); e.preventDefault();
  const cmd=b.getAttribute('data-scrim'), smap=document.getElementById('smap'), svg=document.getElementById('smapLines'), m=SCRIM.map;
  const rows=smap.querySelectorAll('.smap-col'), wrap=smap.getBoundingClientRect();
  const from=rows[m.pos.c]&&rows[m.pos.c].children[m.pos.r];
  const ms=Math.round((typeof abcPace==='function'?abcPace(700):700));
  ST.busy=true;
  try{
    if(from && svg){
      const qa=from.getBoundingClientRect(), qb=b.getBoundingClientRect();
      const x1=qa.left+qa.width/2-wrap.left, y1=qa.top+qa.height/2-wrap.top, x2=qb.left+qb.width/2-wrap.left, y2=qb.top+qb.height/2-wrap.top;
      const ns='http://www.w3.org/2000/svg', path=document.createElementNS(ns,'path');
      path.setAttribute('d',stCurve(x1,y1,x2,y2)); path.setAttribute('class','st-ink trail st-draw'); svg.appendChild(path);
      const L=path.getTotalLength(); path.style.strokeDasharray=L; path.style.strokeDashoffset=L; path.style.transition='stroke-dashoffset '+ms+'ms ease-in-out';
      const tok=svg.querySelector('.st-token'); if(tok){ tok.style.transition='transform '+ms+'ms ease-in-out'; }
      requestAnimationFrame(function(){ path.style.strokeDashoffset='0'; if(tok) tok.setAttribute('transform','translate('+x2+','+(y2-30)+')'); });
    }
    b.classList.add('st-stamp');
    try{ SFX.card('card_slide',0.5); }catch(err){}
  }catch(err){}
  setTimeout(function(){ ST.busy=false; handleScrim(cmd); }, ms+260);
},true);
/* a page turn when a new Act begins */
const stAdvanceActBase=scrimAdvanceAct;
scrimAdvanceAct=function(){ ST.turn=!stCalm(); try{ return stAdvanceActBase.apply(this,arguments); } finally{ setTimeout(function(){ ST.turn=false; },900); } };
/* battles inside a run sit on a candlelit table */
function stTableSync(){
  const b=document.body; if(!b) return;
  const on=!!(typeof APP!=='undefined' && APP.mode==='scrim' && b.getAttribute('data-screen')==='play');
  if(b.classList.contains('st-table')!==on) b.classList.toggle('st-table',on);
  let c=document.getElementById('stCandles');
  if(on && !c){ c=document.createElement('div'); c.id='stCandles'; c.setAttribute('aria-hidden','true'); c.innerHTML='<i class="l"></i><i class="r"></i>'; b.appendChild(c); }
  if(c) c.style.display=on?'':'none';
}
const stRenderBase=render;
render=function(){ const r=stRenderBase.apply(this,arguments); try{ stTableSync(); }catch(e){} return r; };
if(typeof window!=='undefined') window.ABC_ST={ st:ST, glyph:ST_GLYPH, table:stTableSync };
'''
CSS = r"""
/* fix_scrim_tome */
/* ---------- palette + parchment (all gradients; no images, no filters) ---------- */
:root{ --st-ink:#2b1d12; --st-ink2:#4a3522; --st-rub:#8e2a1c; --st-gold:#b8892c; --st-gold2:#e3b450;
  --st-fell:'IM Fell English',Georgia,serif; --st-fellsc:'IM Fell English SC',Georgia,serif; --st-cinzel:'Cinzel',Georgia,serif;
  --st-parch:radial-gradient(120% 90% at 50% 50%,transparent 55%,rgba(110,70,20,.26) 100%),radial-gradient(40% 30% at 18% 22%,rgba(160,110,40,.13),transparent 70%),radial-gradient(30% 26% at 82% 74%,rgba(140,90,30,.15),transparent 70%),linear-gradient(180deg,#f2e6c6,#e8d6aa); }
body[data-screen="scrim"]{ background:#221a13!important; }
body[data-screen="scrim"] .scrim-ink{ background:radial-gradient(70% 60% at 50% 30%,#3a2a1a,#1d1610 75%)!important; }
body[data-screen="scrim"][data-scrimview="intro"] .scrim-ink,body[data-screen="scrim"][data-scrimview="kit"] .scrim-ink{ background:radial-gradient(70% 60% at 50% 30%,#3a2a1a,#1d1610 75%)!important; }
body[data-screen="scrim"]::before{ display:none!important; }

/* ---------- every Scrimmage page: a leaf of the tome ---------- */
body[data-screen="scrim"] .scrim-panel,body[data-screen="scrim"] .vbody{ background:var(--st-parch)!important; border:0!important; border-radius:6px!important;
  box-shadow:0 26px 44px rgba(0,0,0,.55),0 3px 0 #6b4a22,0 6px 0 #4a3216!important; color:var(--st-ink); position:relative; }
body[data-screen="scrim"] .scrim-panel::after,body[data-screen="scrim"] .vbody::after{ content:""; position:absolute; inset:9px; border:1px solid rgba(74,53,34,.35); border-radius:3px; pointer-events:none; }
body[data-screen="scrim"] .scrim-title{ font:400 34px/1.05 var(--st-fell)!important; letter-spacing:0!important; color:var(--st-ink)!important; text-shadow:none!important; }
body[data-screen="scrim"] .scrim-title.sm{ font-size:28px!important; }
body[data-screen="scrim"] .scrim-title::after{ content:"✦"; display:block; margin:8px auto 4px; width:200px; font:14px/1 serif; color:var(--st-gold);
  background:linear-gradient(currentColor,currentColor) left 50%/80px 1px no-repeat,linear-gradient(currentColor,currentColor) right 50%/80px 1px no-repeat; }
body[data-screen="scrim"] .scrim-tag,body[data-screen="scrim"] .vault-tabtitle{ font-family:var(--st-fell)!important; }
body[data-screen="scrim"] .scrim-intro-copy,body[data-screen="scrim"] .scrim-note{ font:italic 16px/1.5 var(--st-fell)!important; color:var(--st-ink2)!important; }
body[data-screen="scrim"] .bigbtn{ font:400 18px/1 var(--st-fell)!important; letter-spacing:0!important; text-transform:none!important; color:#f7ead0!important;
  background:linear-gradient(#8e2a1c,#6e1f14)!important; border:2px solid #3b140c!important; border-radius:6px!important; box-shadow:0 3px 0 #3b140c!important; }
body[data-screen="scrim"] .toolbtn,body[data-screen="scrim"] .rest-opt,body[data-screen="scrim"] .evt-choice{ font-family:var(--st-fell)!important; letter-spacing:0!important; text-transform:none!important; color:var(--st-ink)!important;
  background:rgba(255,248,226,.6)!important; border:1.5px solid var(--st-ink2)!important; border-radius:6px!important; box-shadow:0 2px 0 var(--st-ink2)!important; }
body[data-screen="scrim"] .rest-opt:not(.off):hover,body[data-screen="scrim"] .evt-choice:hover{ background:#fff4d8!important; }
body[data-screen="scrim"] .rest-opt{ font-size:16px!important; }
/* kit choice: campaign classes */
body[data-screen="scrim"] .kit-card{ background:rgba(255,250,236,.72)!important; border:1.5px solid var(--st-ink2)!important; border-radius:6px!important; box-shadow:0 3px 0 var(--st-ink2)!important; position:relative; }
body[data-screen="scrim"] .kit-card::after{ content:""; position:absolute; inset:4px; border:1px solid rgba(74,53,34,.3); border-radius:3px; pointer-events:none; }
body[data-screen="scrim"] .kit-nm{ font:400 21px/1.1 var(--st-fell)!important; color:var(--st-ink)!important; }
body[data-screen="scrim"] .kit-ic{ width:46px; height:46px; display:grid; place-items:center; border-radius:50%; color:#f6e2c8; font-size:20px;
  background:radial-gradient(circle at 38% 32%,#b54a38,#8e2a1c 55%,#5e1a10); box-shadow:0 0 0 3px #6e1f14,0 3px 0 2px rgba(0,0,0,.25); }
body[data-screen="scrim"] .kit-sig b{ color:var(--st-rub)!important; }
body[data-screen="scrim"] .hon-pick{ background:rgba(43,29,18,.85)!important; border-radius:6px!important; }
/* the Vault: bookmark ribbons on a tome */
body[data-screen="scrim"] .vtabs{ gap:4px!important; padding-left:16px; }
body[data-screen="scrim"] .vtab{ font:400 13px/1 var(--st-cinzel)!important; letter-spacing:.12em!important; color:#f3e3c0!important; background:linear-gradient(#7c1f14,#5e170f)!important;
  border:0!important; border-radius:4px 4px 0 0!important; padding:9px 12px 12px!important; box-shadow:none!important; clip-path:polygon(0 0,100% 0,100% 100%,50% 82%,0 100%); }
body[data-screen="scrim"] .vtab.on{ background:linear-gradient(#e3b450,#b8892c)!important; color:#241608!important; }
body[data-screen="scrim"] .vtab.back{ background:linear-gradient(#4a3522,#2b1d12)!important; }
/* team strips on rest/fair pages become little portraits on parchment */
body[data-screen="scrim"] .st-char .st-nm,body[data-screen="scrim"] .st-hpn{ font-family:var(--st-fell)!important; color:var(--st-ink)!important; }

/* ---------- the map: an open campaign book ---------- */
.st-desk{ padding-top:22px!important; }
.st-tome{ position:relative; width:min(1180px,98vw); display:grid; grid-template-columns:minmax(300px,1fr) 1.35fr; border-radius:6px 6px 10px 10px;
  box-shadow:0 30px 50px rgba(0,0,0,.6),0 4px 0 #6b4a22,0 8px 0 #4a3216; color:var(--st-ink); font-family:'Spectral',Georgia,serif; }
.st-tome::before{ content:""; position:absolute; left:42.5%; top:0; bottom:0; width:60px; transform:translateX(-50%); z-index:2; pointer-events:none;
  background:linear-gradient(90deg,transparent,rgba(70,40,10,.3) 45%,rgba(40,20,0,.42) 50%,rgba(70,40,10,.3) 55%,transparent); }
.st-page{ position:relative; padding:30px 34px 40px; background:var(--st-parch); min-width:0; }
.st-page.l{ border-radius:6px 0 0 10px; }
.st-page.r{ border-radius:0 6px 10px 0; display:flex; flex-direction:column; }
.st-ribbon{ position:absolute; right:30px; top:-8px; width:24px; height:110px; z-index:3; background:linear-gradient(90deg,#7c1f14,#a2321f 50%,#7c1f14); clip-path:polygon(0 0,100% 0,100% 100%,50% 86%,0 100%); }
.st-back{ font:italic 14px/1 var(--st-fell); color:var(--st-rub); background:none; border:0; padding:0 0 10px; cursor:pointer; }
.st-back small{ color:var(--st-ink2); }
.st-back:hover{ text-decoration:underline; }
.st-runhead{ font:400 12px/1 var(--st-cinzel); letter-spacing:.28em; color:var(--st-rub); text-align:center; margin-bottom:6px; }
.st-chap{ font:400 32px/1.05 var(--st-fell); text-align:center; margin:0; color:var(--st-ink); }
.st-chap small{ display:block; font:italic 15px/1.3 var(--st-fell); color:var(--st-ink2); margin-top:6px; }
.st-orn{ display:flex; align-items:center; gap:10px; justify-content:center; margin:10px 0 14px; color:var(--st-gold); }
.st-orn::before,.st-orn::after{ content:""; height:1px; width:80px; background:currentColor; }
.st-party{ display:grid; gap:9px; }
.st-sheet{ display:grid; grid-template-columns:54px 1fr auto; gap:11px; align-items:center; border:1.5px solid var(--st-ink2); border-radius:4px; padding:7px 9px; background:rgba(255,248,226,.5); position:relative; }
.st-sheet::after{ content:""; position:absolute; inset:3px; border:1px solid rgba(74,53,34,.3); border-radius:2px; pointer-events:none; }
.st-sheet.dead{ opacity:.55; }
.st-por{ width:54px; height:54px; border-radius:50%; overflow:hidden; border:2px solid var(--st-ink); background:radial-gradient(circle at 40% 35%,#c9a46a,#6b4a22); display:grid; place-items:center; font:400 22px/1 var(--st-fell); color:#fff3d8; }
.st-por img{ width:100%; height:100%; object-fit:cover; }
.st-nm{ font:400 18px/1.1 var(--st-fell); }
.st-cl{ font:italic 13px/1.2 var(--st-fell); color:var(--st-rub); }
.st-hpbar{ height:7px; border:1px solid var(--st-ink); border-radius:5px; background:#e6d3a8; margin-top:5px; overflow:hidden; }
.st-hpbar i{ display:block; height:100%; background:linear-gradient(#a3312a,#7d1f19); }
.st-stat{ min-width:46px; text-align:center; border:1.5px solid var(--st-ink); border-radius:50% 50% 8px 8px; padding:5px 3px 4px; background:#f7edd4; }
.st-stat b{ display:block; font:700 15px/1 var(--st-cinzel); }
.st-stat small{ font:600 8px/1 var(--st-cinzel); letter-spacing:.08em; color:var(--st-ink2); }
.st-ledger{ display:grid; grid-template-columns:1fr 1fr; gap:5px 18px; margin-top:14px; }
.st-row{ display:flex; justify-content:space-between; font:15px/1.4 var(--st-fell); color:var(--st-ink); border:0; border-bottom:1px dotted rgba(74,53,34,.5); background:none; padding:0; text-align:left; }
button.st-row{ cursor:pointer; }
button.st-row:hover b{ color:var(--st-rub); }
.st-sub{ margin:14px 0 6px; font:400 11px/1 var(--st-cinzel); letter-spacing:.24em; color:var(--st-rub); text-transform:uppercase; }
.st-relics{ display:flex; flex-wrap:wrap; gap:6px; }
.st-relic{ font:13px/1 var(--st-fell); border:1px solid var(--st-ink2); border-radius:999px; padding:4px 9px; background:rgba(255,248,226,.6); cursor:help; }
.st-none{ font:italic 13px/1 var(--st-fell); color:var(--st-ink2); }
.st-legend{ display:grid; grid-template-columns:1fr 1fr; gap:5px 10px; font:13px/1.2 var(--st-fell); color:var(--st-ink2); }
.st-lg{ display:flex; align-items:center; gap:7px; }
.st-folio{ position:absolute; bottom:12px; left:0; right:0; text-align:center; font:italic 13px/1 var(--st-fell); color:#7a6440; }
/* the route */
.st-page.r .st-route-wrap{ position:relative; flex:1 1 auto; min-height:560px; max-height:min(76vh,760px); overflow-y:auto; overflow-x:hidden; padding:8px 4px 24px!important; background:none!important; border:0!important; }
.st-route{ display:flex!important; flex-direction:column!important; justify-content:space-between!important; gap:22px!important; min-width:0!important; width:100%!important; height:auto!important; min-height:100%; padding:10px 0!important; position:relative; z-index:2; }
.st-route .smap-col{ display:flex!important; flex-direction:row!important; justify-content:space-evenly!important; align-items:center; gap:10px!important; }
.st-lines{ position:absolute; left:0; top:0; z-index:1; pointer-events:none; overflow:visible; }
.st-ink{ fill:none; stroke:var(--st-ink); stroke-width:2.4; stroke-linecap:round; }
.st-ink.faint{ stroke:rgba(43,29,18,.3); stroke-dasharray:2 7; }
.st-ink.open{ stroke:var(--st-ink); }
.st-ink.trail{ stroke:var(--st-rub); stroke-width:3.2; }
.st-token{ transition:transform .7s ease-in-out; }
.st-compass{ position:absolute; right:14px; bottom:22px; width:70px; height:70px; opacity:.65; pointer-events:none; }
/* wax-seal nodes */
.st-tome .smap-node.st-seal{ width:52px!important; height:52px!important; padding:0!important; border:0!important; border-radius:50%!important; background:none!important; box-shadow:none!important;
  position:relative; display:grid; place-items:center; animation:none!important; filter:none!important; opacity:1!important; overflow:visible; }
.st-wax{ --c:#7a6440; position:relative; width:44px; height:44px; border-radius:50%; display:grid; place-items:center; font:700 18px/1 var(--st-cinzel); color:#f6e2c8; z-index:1;
  background:radial-gradient(circle at 38% 32%,rgba(255,255,255,.28),transparent 45%),var(--c); box-shadow:0 0 0 3px rgba(0,0,0,.18),inset 0 -3px 0 rgba(0,0,0,.18),0 3px 0 1px rgba(0,0,0,.22); text-shadow:0 1px 0 rgba(0,0,0,.4); }
.st-wax::before{ content:""; position:absolute; inset:-5px; border-radius:46% 54% 50% 50%/52% 46% 54% 48%; background:var(--c); opacity:.5; z-index:-1; }
.st-wax.sm{ width:22px; height:22px; font-size:11px; flex:none; }
.st-wax.sm::before{ inset:-2px; }
.st-wax.boss,.smap-node.boss .st-wax{ --c:#3b2b55; }
.st-wax.elite,.smap-node.elite .st-wax{ --c:#5a2a44; }
.st-wax.corrupted,.smap-node.corrupted .st-wax{ --c:#2a3a2a; }
.smap-node.reach .st-wax{ --c:#8e2a1c; animation:stBeckon 2.2s ease-in-out infinite; }
.smap-node.boss.reach .st-wax{ --c:#4a2f7a; }
.smap-node.done .st-wax{ --c:#5a4a36; opacity:.8; }
.smap-node.pos .st-wax{ --c:#1F6A6A; box-shadow:0 0 0 3px #e3b450,0 3px 0 1px rgba(0,0,0,.22); }
.st-tome .smap-node.boss{ width:66px!important; height:66px!important; }
.smap-node.boss .st-wax{ width:58px; height:58px; font-size:24px; }
.smap-node.reach{ cursor:pointer; }
.smap-node.reach:hover .st-wax{ transform:scale(1.1); animation:none; }
.smap-node:disabled{ cursor:default; }
.st-lbl{ position:absolute; top:100%; left:50%; transform:translateX(-50%); margin-top:6px; white-space:nowrap; font:italic 12.5px/1 var(--st-fell); color:var(--st-ink2); opacity:0; transition:opacity .15s; pointer-events:none; z-index:3; text-shadow:0 0 3px #f2e6c6,0 0 6px #f2e6c6; }
.smap-node.reach .st-lbl,.smap-node:hover .st-lbl,.smap-node.pos .st-lbl{ opacity:1; }
.smap-node.st-stamp .st-wax{ animation:stStamp .45s cubic-bezier(.2,1.4,.4,1) .45s both; }
@keyframes stBeckon{ 0%,100%{ transform:scale(1) } 50%{ transform:scale(1.08) } }
@keyframes stStamp{ 0%{ transform:scale(1.9) rotate(-14deg); opacity:.2 } 100%{ transform:scale(1) rotate(-4deg); opacity:1 } }
/* page turn into a new Act */
.st-turn .st-page.r{ transform-origin:left center; animation:stTurn .75s cubic-bezier(.3,.1,.2,1) both; }
.st-turn{ perspective:1800px; }
@keyframes stTurn{ 0%{ transform:rotateY(-95deg); opacity:.4 } 100%{ transform:rotateY(0); opacity:1 } }
@media (max-width:860px){
  .st-tome{ grid-template-columns:1fr; }
  .st-tome::before{ display:none; }
  .st-page.l,.st-page.r{ border-radius:6px; }
  .st-page.r{ order:-1; }
  .st-page{ padding:22px 16px 34px; }
  .st-page.r .st-route-wrap{ min-height:480px; max-height:none; }
  .st-legend{ grid-template-columns:1fr 1fr 1fr; }
  .st-ribbon{ display:none; }
  .st-folio{ display:none; }
}

/* ---------- battles inside a run: the candlelit table ---------- */
body.st-table{ background:radial-gradient(75% 65% at 50% 45%,#4a3018,#21150a 78%)!important; }
body.st-table::before{ background:radial-gradient(rgba(0,0,0,.2) 1px,transparent 1.4px) 0 0/7px 7px!important; opacity:.6; }
body.st-table .abc-stage{ background-color:transparent!important; }
#stCandles{ position:fixed; inset:0; pointer-events:none; z-index:1; }
#stCandles i{ position:absolute; bottom:14px; width:14px; height:56px; border-radius:3px; background:linear-gradient(#f3e3b8,#c9b07a); box-shadow:0 0 0 1px rgba(0,0,0,.3); }
#stCandles i.l{ left:12px; }#stCandles i.r{ right:12px; }
#stCandles i::before{ content:""; position:absolute; left:2px; top:-20px; width:10px; height:18px; border-radius:50% 50% 45% 45%; background:radial-gradient(circle at 50% 70%,#fff3c4,#ffb340 60%,transparent 72%); animation:stFlick 1.7s ease-in-out infinite; }
#stCandles i::after{ content:""; position:absolute; left:-70px; top:-110px; width:154px; height:154px; border-radius:50%; background:radial-gradient(circle,rgba(255,190,90,.22),transparent 68%); animation:stFlick 3.1s ease-in-out infinite; }
@keyframes stFlick{ 0%,100%{ opacity:.85 } 25%{ opacity:1 } 50%{ opacity:.7 } 75%{ opacity:.95 } }
body.abc-phone #stCandles{ display:none!important; }
@media (prefers-reduced-motion:reduce){ .smap-node.reach .st-wax,#stCandles i::before,#stCandles i::after,.st-turn .st-page.r,.smap-node.st-stamp .st-wax{ animation:none!important; } }
"""

SRC=os.path.join('src','game.src.html'); MARK='/* fix_scrim_tome */'
FONT_OLD='family=Spectral:ital,wght@0,400;0,600;1,400&display=swap'
FONT_NEW='family=Spectral:ital,wght@0,400;0,600;1,400&family=IM+Fell+English:ital@0;1&family=IM+Fell+English+SC&family=Cinzel:wght@500;700&display=swap'
def apply(s, TAG):
    if MARK in s: sys.exit(f'{TAG} Already applied -- nothing to do.')
    for need,who in [('function scrimMapScreen(','Literary Scrimmage'),('function scrimDrawConnectors(','Literary Scrimmage'),('function scrimAdvanceAct(','Literary Scrimmage')]:
        if need not in s: sys.exit(f'{TAG} ERROR: {who} code not found ({need}). Nothing written.')
    for l,a in [('end of <head> styles',"</style>\n</head>"),('JS insertion point',"function menuScreen(){\n"),('Google Fonts link',FONT_OLD)]:
        if s.count(a)!=1: sys.exit(f'{TAG} ERROR: anchor "{l}" found {s.count(a)} times (expected 1). Nothing written.')
    s=s.replace(FONT_OLD,FONT_NEW,1)
    s=s.replace("</style>\n</head>",CSS+"</style>\n</head>",1)
    s=s.replace("function menuScreen(){\n",JS+"\nfunction menuScreen(){\n",1)
    for need in [MARK,'scrimMapScreen=function','.st-tome{','family=Cinzel']:
        if need not in s: sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
    return s

TAG='[st_preview]'
if not os.path.exists(SRC): sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s=apply(open(SRC,encoding='utf-8').read(),TAG)
A=json.load(open(os.path.join('assets','assets.json')))
out=re.sub(r'__ABCASSET_(\d+)__',lambda m:A['a'+m.group(1)],s)
os.makedirs('dist',exist_ok=True); p=os.path.join('dist','ABC_scrimtome_preview.html'); open(p,'w',encoding='utf-8').write(out)
print(f'{TAG} wrote',p,f'({len(out):,} bytes) -- src/ untouched.')
