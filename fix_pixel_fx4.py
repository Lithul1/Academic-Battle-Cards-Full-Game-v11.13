#!/usr/bin/env python3
"""fix_pixel_fx4.py -- Pixel effects part 4: ticks, Lens, Bookmarks, Siphon, Offstage, R.I.P., match end
(needs fix_pixel_fx + fix_pixel_fx2 + fix_pixel_fx3).

Run from the repo root:   python3 fix_pixel_fx4.py
Undo:                     restore src/game.src.html from the .bak this writes.

WHAT IT ADDS (pixel mode only -- the Tune switch / Reduce motion keep the current behaviour)
  * Burn / Spill start-of-turn damage shows on the card (Active or Backstage) with a pixel number.
  * Critical Lens: lens flare on the Lens slot when played; THESIS MET! banner + flare when fulfilled.
  * Bookmark played: ribbon drop-and-snap on the Active (both players).
  * Siphon tick: drained card pulses, a pixel trail arcs to the Siphon's owner, the owner pulses.
  * Offstage: dust poof + OFFSTAGE badge, then a trail hops to the hand.
  * R.I.P.: pixel tombstone (with the name) replaces the classic gravestone overlay.
  * Match end: VICTORY! / DEFEAT / DRAW splash once per match (confetti / rain), the result
    card's title in pixel type; Literary Scrimmage end screens get the splash too.
  * 7 new sprite strips drawn in code (no asset bytes added).

HOW IT HOOKS IN (nothing removed)
  8 one-line insertions beside existing code (Lens deploy, thesis, Burn/Spill tick, Siphon tick,
  spawnKO, arenaOffstage, overModal, scrimOverModal) and 1 edited line: playBookmark's commit()
  helper (runs once for every Bookmark that resolves) calls abcPxBookmark(side) first.
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_pixel_fx4 */'
TAG = '[fix_pixel_fx4]'
if not os.path.exists(SRC):
    sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit(f'{TAG} Already applied -- nothing to do.')
for m, n in [('/* fix_pixel_fx */', 'fix_pixel_fx.py'), ('/* fix_pixel_fx2 */', 'fix_pixel_fx2.py'), ('/* fix_pixel_fx3 */', 'fix_pixel_fx3.py')]:
    if m not in s:
        sys.exit(f'{TAG} ERROR: run {n} first.')

H = '   /* fix_pixel_fx4 */'
EDITS = [   # (label, anchor, replacement)
  ('end of fix_pixel_fx3 block',
   "if(typeof window!=='undefined' && window.ABC_PXFX){ window.ABC_PXFX.ready=abcPxReady; window.ABC_PXFX.turn=abcPxTurn; }\n", None),
  ('Lens deploy log',
   "    pushLog(`${who(P)} deploys the ${card.name}. Passive Focus is now active.`);\n",
   "    pushLog(`${who(P)} deploys the ${card.name}. Passive Focus is now active.`);\n    try{ abcPxLens(side,'deploy'); }catch(e){}"+H+"\n"),
  ('thesis fulfil log',
   "  pushLog(`${who(P)} fulfils the ${C.name} thesis! ${C.reward}`);\n",
   "  pushLog(`${who(P)} fulfils the ${C.name} thesis! ${C.reward}`);\n  try{ abcPxLens(side,'thesis',C.name); }catch(e){}"+H+"\n"),
  ('playBookmark commit()',
   "  const commit=()=>{ P.flags.bmCount=(P.flags.bmCount||0)+1;",
   "  const commit=()=>{ try{ abcPxBookmark(side); }catch(e){}"+H+" P.flags.bmCount=(P.flags.bmCount||0)+1;"),
  ('Burn/Spill tick',
   "\n      flashLog(_tk,'neg',`${c.status.burn?'Burn':'Spill'} \\u2014 ${c.name} loses ${_bs} HP.`,3); } }",
   "\n      try{ abcPxTick(_tk,c,c.status.burn?'burn':'spill',_bs); }catch(e){}"+H+"\n      flashLog(_tk,'neg',`${c.status.burn?'Burn':'Spill'} \\u2014 ${c.name} loses ${_bs} HP.`,3); } }"),
  ('Siphon tick',
   "      sp.turns=(sp.turns||1)-1;\n      if(sp.turns<=0){ delete c.status.siphon;",
   "      try{ abcPxSiphon(_sk,c,own,mode); }catch(e){}"+H+"\n      sp.turns=(sp.turns||1)-1;\n      if(sp.turns<=0){ delete c.status.siphon;"),
  ('spawnKO head',
   "  try{ SFX.ko(); }catch(e){}\n  const el=document.querySelector('.char.'+side); if(!el||!el.getBoundingClientRect) return;\n",
   "  try{ SFX.ko(); }catch(e){}\n  try{ if(abcPxGrave(side,name)) return; }catch(e){}"+H+"\n  const el=document.querySelector('.char.'+side); if(!el||!el.getBoundingClientRect) return;\n"),
  ('arenaOffstage removal',
   "  const i=p.team.indexOf(c); p.team.splice(i,1); if(i<p.activeIdx) p.activeIdx--;\n  p.hand.push(card); p.flags._offTurn",
   "  try{ abcPxOffstage(side,c); }catch(e){}"+H+"\n  const i=p.team.indexOf(c); p.team.splice(i,1); if(i<p.activeIdx) p.activeIdx--;\n  p.hand.push(card); p.flags._offTurn"),
  ('overModal head',
   "function overModal(){\n  const win=S.winner==='you';\n",
   "function overModal(){\n  const win=S.winner==='you';\n  try{ abcPxOver(S.winner, !!S._arenaDraw); }catch(e){}"+H+"\n"),
  ('scrimOverModal head',
   "  const won = !S.opp.team.some(c=>c.hp>0);\n  const node=S.scrim.node;",
   "  const won = !S.opp.team.some(c=>c.hp>0);\n  try{ abcPxOver(won?'you':'opp', false); }catch(e){}"+H+"\n  const node=S.scrim.node;"),
  ('end of <head> styles', "</style>\n</head>", None),
]
for l, a, _ in EDITS:
    n = s.count(a)
    if n != 1:
        sys.exit(f'{TAG} ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')

JS = r'''/* fix_pixel_fx4 */ /* ---- pixel effects, part 4: ticks, Lens, Bookmarks, Siphon, Offstage, R.I.P., match end --
     abcPxTick(side, ch, 'burn'|'spill', n)  -- start-of-turn Burn/Spill damage on the card
     abcPxLens(side, 'deploy'|'thesis', nm)  -- lens flare on the Lens slot (+ THESIS MET! banner)
     abcPxBookmark(side)                     -- ribbon snap on the Active
     abcPxSiphon(side, ch, own, mode)        -- drain beam from the victim to the Siphon's owner
     abcPxOffstage(side, ch)                 -- dust poof + hop trail to the hand
     abcPxGrave(side, name)                  -- pixel tombstone (replaces the R.I.P. overlay)
     abcPxOver(winner, draw)                 -- VICTORY / DEFEAT / DRAW splash + pixel modal title */
PXD.tickburn={frames:6,fps:10,draw:PXD.burn.draw};
PXD.lensflare={frames:12,fps:14,draw:function(P,f){ const C=PXC, d=f>=10?(f===11?2:1):0;   /* a lens catches the light */
  const r=f<2?6+f*5:16; P.disc(32,32,r-1,C.blue2,2); P.ring(32,32,r,C.gold,d); P.ring(32,32,r+1,C.ink,d); P.ring(32,32,r-2,C.gold2,d?2:1);
  if(f>=2&&f<=8){ const k=f-2, a0=k*.35; for(let i=0;i<4;i++){ const a=a0+i*Math.PI/2, L=10+k*3; P.line(32+Math.cos(a)*(r+2),32+Math.sin(a)*(r+2),32+Math.cos(a)*(r+L),32+Math.sin(a)*(r+L),C.yellow,k>=5?1:0); } }
  if(f>=3&&f<=7){ const gx=18+(f-3)*7; for(let y=-r+2;y<r-1;y++){ const x=gx+Math.round(y*.4); if((x-32)*(x-32)+y*y<(r-2)*(r-2)){ P.px(x,32+y,C.white); P.px(x+1,32+y,C.white,1); } } }
  if(f===4) P.star4(32,32,8,C.yellow);
  if(f>=5){ const rr=pxRng(91); for(let i=0;i<5;i++) P.star4(8+rr()*48,8+rr()*48,(f+i)%2?1:2,C.gold2); } }};
PXD.ribbon={frames:10,fps:14,draw:function(P,f){ const C=PXC, d=f>=8?(f===9?2:1):0;   /* a bookmark ribbon drops and snaps */
  const len=Math.min(48,f*14), sway=[0,0,0,-4,3,-2,1,0,0,0][f];
  for(let y=0;y<len;y++){ const x0=26+Math.round(sway*y/48); for(let x=0;x<12;x++){ const c=x===0||x===11?C.dred:(x<3?C.red2:C.red); P.px(x0+x,4+y,c,d); } }
  if(len>=48){ const x0=26+sway; for(let i=0;i<6;i++){ for(let x=i;x<12-i;x++) if(x<6-i||x>5+i) P.px(x0+x,52+i,x<6?C.red:C.red2,d); } }
  for(let x=20;x<44;x++){ P.px(x,2,C.gold2,d); P.px(x,3,C.gold,d); P.px(x,4,C.ink,d); }
  if(f===3||f===4){ for(let k=0;k<3;k++) P.line(14-k*3,18+k*10,20-k*3,16+k*10,C.white); for(let k=0;k<3;k++) P.line(50+k*3,18+k*10,44+k*3,16+k*10,C.white); }
  if(f>=4){ const r=pxRng(93); for(let i=0;i<4;i++) P.star4(14+r()*36,10+r()*44,(f+i)%2?1:2,C.gold2); } }};
PXD.poof={frames:9,fps:16,draw:function(P,f){ const C=PXC, d=f>=6?(f>=8?2:1):0;   /* dust puff */
  const r=pxRng(95); for(let i=0;i<7;i++){ const a=i*.9, dist=4+f*3.2, rad=Math.max(1,6-Math.abs(f-3)); P.disc(32+Math.cos(a)*dist,36+Math.sin(a)*dist*.7,rad,i%2?C.grey2:C.cream,d); }
  if(f<3) P.disc(32,36,4+f*3,C.white,f===2?1:0);
  if(f>=2&&f<=7){ for(let i=0;i<4;i++) P.star4(16+r()*32,14+r()*30,1,C.gold2); } }};
const PX_RIP=["###..###.###.","#..#..#..#..#","###...#..###.","#.#...#..#...","#..#.###.#..."];
PXD.grave={frames:16,fps:12,draw:function(P,f){ const C=PXC, rise=Math.min(1,pxEase((f+1)/6)), base=54, h=Math.round(36*rise), d=f>=14?(f===15?2:1):0;   /* a tombstone rises */
  for(let x=4;x<60;x++){ P.px(x,base+1,C.grey,d); P.px(x,base+2,C.ink,d); }
  if(h>0){ const top=base-h, w=15; for(let y=top;y<=base;y++){ const dy=y-top, half=dy<w?Math.round(Math.sqrt(Math.max(0,w*w-(w-dy)*(w-dy)))):w;
      for(let x=-half;x<=half;x++){ const edge=Math.abs(x)===half||y===top; P.px(32+x,y,edge?C.ink:(x<-half+3?C.steel2:C.grey2),d); } }
    if(rise>=1){ P.glyph(PX_RIP,26,top+12,1,C.ink); P.glyph(PX_RIP,25,top+11,1,C.grey); if(f>=8){ P.line(40,top+6,37,top+14,C.ink,d); P.line(37,top+14,40,top+19,C.ink,d); } } }
  if(f<=7){ const r=pxRng(97); for(let i=0;i<8;i++){ const s=i%2?1:-1; P.disc(32+s*(14+r()*8+f*2),base-1-r()*3-f*.6,1,C.grey2,f>=5?1:0); } }
  if(f>=8){ const k=f-8, gy=base-40-k*3, gx=32+Math.round(Math.sin(k*.9)*3); P.disc(gx,gy,3,C.white,k>=5?1:0); P.disc(gx,gy+3,2,C.white,k>=5?1:2); P.px(gx-1,gy-1,C.ink); P.px(gx+1,gy-1,C.ink); } }};
PXD.confetti={frames:12,fps:12,loops:2,draw:function(P,f){ const C=PXC, cols=[C.gold2,C.red2,C.blue2,C.green2,C.white,C.purple2], r=pxRng(99);
  for(let i=0;i<22;i++){ const x0=r()*64, sp=3+r()*3, ph=r()*64, c=cols[i%6], y=(ph+f*sp*16/12)%64, x=x0+Math.sin((f+i)*.8)*2, flip=(f+i)%3;
    P.px(x,y,c); if(flip!==1) P.px(x+1,y,c); if(flip===2) P.px(x,y+1,c); } }};
PXD.rain={frames:8,fps:12,loops:3,draw:function(P,f){ const C=PXC, r=pxRng(101);
  for(let i=0;i<16;i++){ const x=r()*64, y=(r()*64+f*8)%64; for(let k=0;k<5;k++) P.px(x-k*.3,y-k,k===0?C.steel2:C.steel,k>2?1:0); } }};
function abcPxCharEl(side,ch){
  try{ const P=S[side]; if(ch && P && P.team[P.activeIdx]!==ch){
      let el=ch.uid!=null?document.querySelector('.'+side+'-side .bench-mini[data-charuid="'+ch.uid+'"]'):null;
      if(!el){ const bench=P.team.filter(function(c,i){ return i!==P.activeIdx; }), k=bench.indexOf(ch), all=document.querySelectorAll('.'+side+'-side .bench-mini'); if(k>=0&&all[k]) el=all[k]; }
      if(el) return el; } }catch(e){}
  return document.querySelector('.char.'+side);
}
function abcPxFlyWait(side){ try{ if(side==='you' && document.body.classList.contains('abc-arena') && typeof ABC_FLY_MS==='number') return Math.round(ABC_FLY_MS*.88); }catch(e){} return 0; }
function abcPxAt(el,k,opt){ opt=opt||{}; const r=abcPxBox(el); if(!r) return 0;
  const o=abcPxLayer(r,opt.z), sc=opt.sc||Math.max(1,Math.round(Math.min(r.width,opt.max||9999)*(opt.mul||1.1)/PXN)), ms=abcPxSprite(o,k,sc,r.width/2,r.height*(opt.cy||.5));
  if(opt.pop) abcPxPop(o,opt.pop[0],opt.pop[1],Math.max(2,opt.ts||sc+1),opt.pop[2]!=null?opt.pop[2]:36,!!opt.pop[3]);
  document.body.appendChild(o); setTimeout(function(){ o.remove(); },Math.max(ms,opt.pop?1100:0)+80); return ms; }
function abcPxTick(side,ch,kind,n){
  if(!abcPxOn()) return;
  setTimeout(function(){ try{ const el=abcPxCharEl(side,ch); abcPxAt(el,kind==='spill'?'spill':'tickburn',{pop:['-'+n,kind==='spill'?PXC.blue2:PXC.red2,34]}); }catch(e){} },450);
}
function abcPxLens(side,what,nm){
  if(!abcPxOn()||!side) return;
  const go=function(){ try{ abcPxAt(document.querySelector('.'+side+'-side .lenschip')||document.querySelector('.char.'+side),'lensflare',{max:90,mul:1.4,z:59}); }catch(e){} };
  if(what==='thesis'){ abcPxCut('THESIS MET!', nm||'', 'thesis'); setTimeout(go,650); }
  else setTimeout(go,abcPxFlyWait(side)+60);
}
const _pxBmAt={};
function abcPxBookmark(side){
  if(!abcPxOn()||!side) return; const now=Date.now(); if(_pxBmAt[side]&&now-_pxBmAt[side]<300) return; _pxBmAt[side]=now;
  setTimeout(function(){ try{ abcPxAt(document.querySelector('.char.'+side),'ribbon',{}); }catch(e){} },abcPxFlyWait(side)+60);
}
function abcPxBeam(a,b,c1,c2,ms){
  const A=abcPxBox(a), B=abcPxBox(b); if(!A||!B) return;
  const ax=A.left+A.width/2, ay=A.top+A.height/2, bx=B.left+B.width/2, by=B.top+B.height/2, sz=Math.max(4,Math.round(Math.min(A.width,B.width)/22/2)*2);
  const L=document.createElement('div'); L.className='px-beam'; document.body.appendChild(L);
  for(let i=0;i<14;i++){ const q=document.createElement('i'); q.style.cssText='width:'+sz+'px;height:'+sz+'px;background:'+(i%3?c1:c2)+';left:'+Math.round(ax-sz/2)+'px;top:'+Math.round(ay-sz/2)+'px';
    L.appendChild(q); const mx=(ax+bx)/2+(i%2?1:-1)*(10+i*2), my=Math.min(ay,by)-30-i*2;
    if(q.animate) q.animate([{transform:'translate(0,0)',opacity:0},{opacity:1,offset:.1},{transform:'translate('+Math.round(mx-ax)+'px,'+Math.round(my-ay)+'px)',offset:.5},{transform:'translate('+Math.round(bx-ax)+'px,'+Math.round(by-ay)+'px)',opacity:1,offset:.95},{transform:'translate('+Math.round(bx-ax)+'px,'+Math.round(by-ay)+'px)',opacity:0}],{duration:ms,delay:i*35,easing:'steps(12)',fill:'both'}); }
  setTimeout(function(){ L.remove(); },ms+14*35+60);
}
function abcPxSiphon(side,ch,own,mode){
  if(!abcPxOn()) return;
  const oside=side==='you'?'opp':'you';
  setTimeout(function(){ try{
    const from=abcPxCharEl(side,ch), to=own&&own.c?abcPxCharEl(oside,own.c):null;
    abcPxAt(from,'siphon',{});
    if(to){ abcPxBeam(from,to,PXC.purple2,PXC.white,700); setTimeout(function(){ abcPxAt(to,'siphon',{mul:.8}); },900); }
  }catch(e){} },500);
}
function abcPxOffstage(side,ch){
  if(!abcPxOn()) return;
  try{ const el=abcPxCharEl(side,ch), r=abcPxBox(el); if(!r) return;
    const ghost={getBoundingClientRect:function(){ return r; }}, hand=side==='you'?document.querySelector('.hand'):null;
    abcPxAt(ghost,'poof',{pop:['OFFSTAGE',PXC.cream,10,true]});
    if(hand){ const H=hand.getBoundingClientRect(), tgt={getBoundingClientRect:function(){ return {left:H.left+H.width/2-20,top:H.top+10,width:40,height:40}; }}; abcPxBeam(ghost,tgt,PXC.gold2,PXC.white,650); }
  }catch(e){}
}
function abcPxGrave(side,name){
  if(!abcPxOn()) return false;
  const el=document.querySelector('.char.'+side), r=abcPxBox(el); if(!r) return false;
  const ghost={getBoundingClientRect:function(){ return r; }};
  setTimeout(function(){ try{ abcPxAt(ghost,'grave',{z:60,pop:[String(name||''),PXC.cream,88,true],ts:2}); }catch(e){} },1250);   /* after the K.O. banner and K.O. sprite */
  return true;
}
let _pxOverFor=0;
function abcPxOver(winner,draw,force){
  if(!abcPxOn()) return;
  const res=draw?'draw':(winner==='you'?'win':'lose');
  setTimeout(function(){ try{   /* pixel title inside the result card (re-applied on every repaint) */
    const t=document.querySelector('.modal-bg .over-title'); if(t && !t.querySelector('img.px-title')){
      const label=res==='win'?'YOU WIN!':(res==='draw'?'DRAW':'YOU LOSE'), tx=abcPxText(label,res==='win'?PXC.gold2:(res==='draw'?PXC.cream:PXC.steel2));
      if(tx && t.classList.contains('over-title')){ t.setAttribute('aria-label',label); t.innerHTML='<img class="px-title" alt="'+label+'" src="'+tx.url+'" style="width:'+(tx.w*4)+'px;height:'+(tx.h*4)+'px">'; } }
  }catch(e){} },0);
  let key=null; try{ key=S; }catch(e){}
  if(_pxOverFor===key && !force) return; _pxOverFor=key;   /* the splash plays once per match */
  try{
    const W=window.innerWidth, H=window.innerHeight, big=res==='win'?'VICTORY!':(res==='draw'?'DRAW':'DEFEAT');
    const bt=abcPxText(big,res==='win'?PXC.gold2:(res==='draw'?PXC.cream:PXC.steel2)); if(!bt) return;
    let sub=''; try{ sub='KOS '+S.you.kos+' - '+S.opp.kos; }catch(e){}
    const st=sub?abcPxText(sub,PXC.cream):null, s=Math.max(4,Math.min(12,Math.floor(W*.7/bt.w))), s2=Math.max(2,Math.floor(s/3));
    const el=document.createElement('div'); el.id='abcPxOver'; el.className=res;
    el.innerHTML='<div class="pxo-fx"></div><img alt="'+big+'" class="pxo-big" src="'+bt.url+'" style="width:'+(bt.w*s)+'px;height:'+(bt.h*s)+'px">'+(st?'<img alt="" class="pxo-sub" src="'+st.url+'" style="width:'+(st.w*s2)+'px;height:'+(st.h*s2)+'px;margin-top:'+s+'px">':'');
    document.body.appendChild(el);
    const fx=el.querySelector('.pxo-fx'), k=res==='win'?'confetti':'rain', tsc=Math.max(2,Math.round(Math.min(W,H)/260)), tile=PXN*tsc, d=abcPxFx()[k];
    if(res!=='draw'&&d){ for(let y=0;y<H;y+=tile) for(let x=0;x<W;x+=tile){ const t=document.createElement('i'); t.style.cssText='left:'+x+'px;top:'+y+'px;width:'+tile+'px;height:'+tile+'px;background-image:url('+d.url+');background-size:'+(d.frames*tile)+'px '+tile+'px';
        fx.appendChild(t); if(t.animate) t.animate([{backgroundPosition:'0 0'},{backgroundPosition:(-d.frames*tile)+'px 0'}],{duration:d.ms,iterations:Infinity,easing:'steps('+d.frames+')',delay:-((x*7+y*3)%d.ms)}); } }
    const T=2600;
    if(el.animate){ el.animate([{opacity:0},{opacity:1,offset:.06},{opacity:1,offset:.86},{opacity:0}],{duration:T,easing:'steps(20)',fill:'forwards'});
      el.querySelector('.pxo-big').animate([{transform:'translateY('+(-H*.6)+'px)'},{transform:'translateY(12px)',offset:.14},{transform:'translateY(-6px)',offset:.2},{transform:'translateY(0)',offset:.25},{transform:'translateY(0)'}],{duration:T,easing:'steps(40)',fill:'forwards'}); }
    setTimeout(function(){ el.remove(); },T+40);
  }catch(e){}
}
if(typeof window!=='undefined' && window.ABC_PXFX){ Object.assign(window.ABC_PXFX,{tick:abcPxTick,lens:abcPxLens,bookmark:abcPxBookmark,siphon:abcPxSiphon,offstage:abcPxOffstage,grave:abcPxGrave,over:abcPxOver,beam:abcPxBeam}); }
'''
CSS = """
/* fix_pixel_fx4 */
#abcPxCut.thesis{border-color:#ffd45e;background:#14233a}
#abcPxCut.thesis .pxc-lines{background:repeating-linear-gradient(90deg,rgba(168,212,255,.16) 0 12px,transparent 12px 52px)}
.px-beam{position:fixed;left:0;top:0;width:0;height:0;z-index:59;pointer-events:none}
.px-beam i{position:absolute;display:block;box-shadow:0 0 0 1px #1b1410}
#abcPxOver{position:fixed;inset:0;z-index:1000;pointer-events:none;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(18,13,10,.62);opacity:0}
#abcPxOver.lose{background:rgba(10,14,22,.66)}
#abcPxOver .pxo-fx{position:absolute;inset:0;overflow:hidden}
#abcPxOver .pxo-fx i{position:absolute;display:block;background-repeat:no-repeat;image-rendering:crisp-edges;image-rendering:pixelated}
#abcPxOver img,.over-title img.px-title{position:relative;display:block;margin:0 auto;image-rendering:crisp-edges;image-rendering:pixelated}
"""

for l, a, rep in EDITS:
    if l == 'end of fix_pixel_fx3 block': rep = a + JS
    elif l == 'end of <head> styles': rep = CSS + a
    s = s.replace(a, rep, 1)
for need in [MARK, "abcPxLens(side,'thesis',C.name)", 'abcPxBookmark(side)', 'abcPxTick(_tk,c', 'abcPxSiphon(_sk,c,own,mode)', 'abcPxGrave(side,name)', 'abcPxOffstage(side,c)', 'abcPxOver(S.winner', "abcPxOver(won?'you':'opp'", 'PXD.grave=', '#abcPxOver{']:
    if need not in s:
        sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:', bak)
print(f'{TAG} Next: python3 build.py')
