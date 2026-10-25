#!/usr/bin/env python3
"""fix_pixel_fx3.py -- Pixel effects part 3: 9 more statuses, READY!, turn banners (needs fix_pixel_fx + fix_pixel_fx2).

Run from the repo root:   python3 fix_pixel_fx3.py
Undo:                     restore src/game.src.html from the .bak this writes.

WHAT IT ADDS (pixel mode only -- the Tune switch / Reduce motion keep the current effects)
  * Sprites for Spill, Smudge, Weaken, Exposed, Cost Up, Iron Curtain, Laminate, Hardcover and
    Margin Notes. No hook needed: fix_pixel_fx's dress step already looks statuses up by name.
  * ATTACK READY! / BLOCK READY! on the card when a move fills (yours and the AI's). The
    existing move-row glow stays visible; two at once play one after the other.
  * A short YOUR TURN / OPPONENT'S TURN strip at each turn start (waits for a CRITICAL/K.O.
    banner; skipped in AI-vs-AI simulations and after the match ends).
  * 11 new sprite strips drawn in code (no asset bytes added).

HOW IT HOOKS IN (2 lines added to existing functions, nothing removed)
  * chargeReport(): abcPxReady(side, w) next to the existing fxChargeGlow.
  * startTurn():    abcPxTurn(S.turn) at the top.
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_pixel_fx3 */'
TAG = '[fix_pixel_fx3]'
if not os.path.exists(SRC):
    sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit(f'{TAG} Already applied -- nothing to do.')
for m, n in [('/* fix_pixel_fx */', 'fix_pixel_fx.py'), ('/* fix_pixel_fx2 */', 'fix_pixel_fx2.py')]:
    if m not in s:
        sys.exit(f'{TAG} ERROR: run {n} first.')

A_BLOCK = "if(typeof window!=='undefined' && window.ABC_PXFX){ window.ABC_PXFX.evolve=abcPxEvolve; window.ABC_PXFX.stamp=abcPxStamp; }\n"
A_READY = "      fxChargeGlow(side, ch, w);\n"
A_TURN  = "function startTurn(){\n  if(!S) return;\n"
A_CSS   = "</style>\n</head>"
for a, l in [(A_BLOCK, 'end of fix_pixel_fx2 block'), (A_READY, 'chargeReport glow call'), (A_TURN, 'startTurn head'), (A_CSS, 'end of <head> styles')]:
    n = s.count(a)
    if n != 1:
        sys.exit(f'{TAG} ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')

NEW_READY = A_READY + "      try{ abcPxReady(side, w); }catch(e){}   /* fix_pixel_fx3 */\n"
NEW_TURN  = A_TURN + "  try{ abcPxTurn(S.turn); }catch(e){}   /* fix_pixel_fx3: turn banner */\n"

JS = r'''/* fix_pixel_fx3 */ /* ---- pixel effects, part 3: the other 9 statuses, READY!, turn banners ----------
   Status sprites need no hook: abcPxDress() already looks a status label up in the
   strip set ('Iron Curtain' -> 'ironcurtain'), so adding the strip is enough.
     abcPxReady(side, 'atk'|'blk')  -- chevron burst + "ATTACK READY!" when a move fills
     abcPxTurn(side)                -- short "YOUR TURN" / "OPPONENT'S TURN" strip */
PXC.grey='#8a7e6b'; PXC.grey2='#c9bfa8'; PXC.steel='#5d6b78'; PXC.steel2='#a9b8c6'; PXC.pink='#f29bb0';
function pxEllipse(P,cx,cy,w,h,c,d){ for(let y=-h;y<=h;y++) for(let x=-w;x<=w;x++) if((x*x)/(w*w||1)+(y*y)/(h*h||1)<=1) P.px(cx+x,cy+y,c,d); }
function pxChevron(P,x,y,s,c,d,down){ for(let i=0;i<=s;i++){ const yy=down?y+i:y-i; P.px(x-s+i,yy,c,d); P.px(x+s-i,yy,c,d); P.px(x-s+i,yy+(down?-1:1),c,d); P.px(x+s-i,yy+(down?-1:1),c,d); } }
PXD.spill={frames:12,fps:12,draw:function(P,f){ const C=PXC, d=f>=10?(f===11?2:1):0;   /* ink drops fall, splash, pool */
  [[26,0],[36,2],[31,4]].forEach(function(q){ const y=-6+(f-q[1]/2)*12; if(y>-4&&y<48){ P.disc(q[0],y,2,C.blue); P.px(q[0]-1,y-1,C.blue2); P.px(q[0],y-4,C.blue); } });
  if(f>=3){ const w=Math.min(26,(f-2)*5), h=Math.max(2,Math.round(w*.28)); pxEllipse(P,32,53,w,h,C.blue,d); pxEllipse(P,32,52,Math.max(1,w-4),Math.max(1,h-2),C.blue2,d?2:1);
    if(f>=4&&f<=8){ const k=f-3; [[-1,1],[1,1],[-1,.6],[1,.6]].forEach(function(v,i){ P.disc(32+v[0]*(6+k*4),50-k*5*v[1]+k*k*.9,1,i%2?C.blue2:C.blue); }); } } }};
PXD.smudge={frames:9,fps:14,draw:function(P,f){ const C=PXC, head=Math.min(60,6+f*8), r=pxRng(51);   /* a thumb smears the page */
  for(let x=4;x<head;x++){ const t=(head-x)/56, wob=Math.round(Math.sin(x*.3)*2), th=Math.max(2,Math.round(7-t*3));
    for(let y=-th;y<=th;y++) P.px(x,32+wob+y,t<.15?C.grey:C.grey2,t<.15?0:(t<.5?1:2)); }
  if(f<8){ for(let i=0;i<3;i++) P.ring(head-2,32,2+i*2,C.grey,i?1:0); }
  for(let i=0;i<8;i++) P.px(4+r()*Math.max(4,head-6),22+r()*20,C.grey,f>=7?2:1); }};
PXD.weaken={frames:9,fps:12,draw:function(P,f){ const C=PXC, fd=f>=8?1:0;   /* the blade cracks and droops */
  const top=f>=4?{dx:(f-3)*2,dy:(f-3)*4}:{dx:0,dy:0};
  for(let y=10;y<=26;y++){ const x=32+top.dx*(26-y)/16+top.dx*.5, yy=y+top.dy; P.px(x-1,yy,C.cream,f>=7?1:fd); P.px(x,yy,C.white,f>=7?1:fd); P.px(x+1,yy,C.grey2,f>=7?1:fd); }
  for(let y=27;y<=44;y++){ P.px(31,y,C.cream,fd); P.px(32,y,C.white,fd); P.px(33,y,C.grey2,fd); }
  for(let x=-6;x<=6;x++){ P.px(32+x,45,C.gold,fd); P.px(32+x,46,C.gold2,fd); } for(let y=47;y<=54;y++){ P.px(31,y,C.dred,fd); P.px(32,y,C.red,fd); P.px(33,y,C.dred,fd); }
  if(f===3){ P.line(30,25,34,28,C.ink); P.line(34,28,30,30,C.ink); P.star4(32,27,3,C.white); }
  for(let k=0;k<3;k++){ const y=(f*6+k*20)%56+4; pxChevron(P,12,y,4,C.purple2,f>=7?1:0,true); pxChevron(P,52,y,4,C.purple2,f>=7?1:0,true); } }};
PXD.exposed={frames:9,fps:14,draw:function(P,f){ const C=PXC, dist=f<5?30-f*4:14, d=f>=8?1:0;   /* a reticle locks on */
  [[-1,-1],[1,-1],[-1,1],[1,1]].forEach(function(s){ const cx=32+s[0]*dist, cy=32+s[1]*dist;
    for(let i=0;i<7;i++){ P.px(cx-s[0]*i,cy,C.red2,d); P.px(cx,cy-s[1]*i,C.red2,d); P.px(cx-s[0]*i,cy+s[1],C.ink,d); P.px(cx+s[0],cy-s[1]*i,C.ink,d); } });
  if(f>=4){ for(let i=4;i<11;i++){ P.px(32+i,32,C.red2,d); P.px(32-i,32,C.red2,d); P.px(32,32+i,C.red2,d); P.px(32,32-i,C.red2,d); } P.disc(32,32,1,C.white); }
  if(f===5) P.ring(32,32,12,C.white); if(f>=6) P.ring(32,32,12+(f-6)*4,C.red2,1); }};
PXD.ironcurtain={frames:10,fps:14,draw:function(P,f){ const C=PXC, bot=[14,28,42,56,50,56,56,56,56,56][f], d=f===9?1:0;   /* an iron shutter slams down */
  for(let y=0;y<bot;y++){ const sl=y%6, c=sl===0?C.ink:(sl===1?C.steel2:C.steel); for(let x=4;x<60;x++) P.px(x,y,c,d); }
  for(let x=4;x<60;x++){ P.px(x,bot,C.ink,d); P.px(x,bot+1,C.ink,d); }
  for(let y=3;y<bot;y+=12){ P.px(6,y,C.steel2,d); P.px(57,y,C.steel2,d); }
  if(f>=3&&f<=8){ const k=f-3, r=pxRng(61); for(let i=0;i<8;i++){ const s=i%2?1:-1, x=32+s*(20+r()*10+k*3), y=bot-1-r()*4-k; P.disc(x,y,1+(k<2?1:0),C.grey2,k>=3?1:0); } } }};
const PX_PLUS1=["..#....#.",".###..##.","..#....#.",".......#.","......###"];
PXD.costup={frames:9,fps:14,draw:function(P,f){ const C=PXC, r=f<3?3+f*3:9, d=f>=8?1:0;   /* the next charge costs one more */
  P.disc(32,38,r,C.gold,d); P.ring(32,38,r,C.ink,d); if(r>6){ P.ring(32,38,r-2,C.gold2,d?2:1); P.line(32,34,32,42,C.dred,d); P.px(31,35,C.dred,d); }
  if(f>=2){ const y=Math.max(8,20-(f-2)*3); P.glyph(PX_PLUS1,18,y,3,C.red2,d?null:C.ink); }
  if(f>=3){ for(let k=0;k<2;k++){ const y=58-((f-3)*7+k*14)%40; pxChevron(P,8,y,3,C.red2,d,false); pxChevron(P,56,y,3,C.red2,d,false); } } }};
PXD.laminate={frames:9,fps:14,draw:function(P,f){ const C=PXC, w=17, h=23, d=f>=8?1:0;   /* a glossy sheet seals the card */
  const n=Math.min(1,(f+1)/2); for(let x=-w;x<=w;x++) for(let y=-h;y<=h;y++){ const edge=Math.abs(x)===w||Math.abs(y)===h; if(!edge) continue;
    const corner=Math.min(w-Math.abs(x),h-Math.abs(y)); if(n<1&&corner>6) continue; P.px(32+x,32+y,C.blue2,d); }
  if(f>=2&&f<=6){ const band=-30+(f-2)*15; for(let x=-w+1;x<w;x++) for(let y=-h+1;y<h;y++){ const t=x+y-band; if(t>=0&&t<3) P.px(32+x,32+y,C.white); else if(t>=3&&t<7) P.px(32+x,32+y,C.blue2,1); } }
  if(f>=1&&f<=7){ for(let x=-w+1;x<w;x++) for(let y=-h+1;y<h;y++) P.px(32+x,32+y,C.blue2,2); }
  if(f>=6){ [[-w,-h],[w,-h],[-w,h],[w,h]].forEach(function(c,i){ if((f+i)%2) P.star4(32+c[0],32+c[1],2,C.white); }); } }};
PXD.hardcover={frames:9,fps:14,draw:function(P,f){ const C=PXC, w=16, h=22, gap=f<4?(3-f)*7:0, d=f>=8?1:0;   /* gold corner guards lock on */
  if(f>=3&&f<=6){ for(let x=-w+2;x<w-1;x++) for(let y=-h+2;y<h-1;y++) P.px(32+x,32+y,f===3?C.white:C.teal,f===3?1:2); }
  [[-1,-1],[1,-1],[-1,1],[1,1]].forEach(function(s){ const cx=32+s[0]*(w+gap), cy=32+s[1]*(h+gap);
    for(let t=-1;t<=1;t++) for(let i=0;i<8;i++){ P.px(cx-s[0]*i,cy-s[1]*t,C.gold,d); P.px(cx-s[0]*t,cy-s[1]*i,C.gold,d); }
    for(let i=0;i<9;i++){ P.px(cx-s[0]*i,cy+s[1]*2,C.ink,d); P.px(cx+s[0]*2,cy-s[1]*i,C.ink,d); }
    P.px(cx,cy,C.gold2,d); });
  if(f>=5&&f<=8){ const r=pxRng(71); for(let i=0;i<4;i++) P.star4(16+r()*32,12+r()*40,(f+i)%2?1:2,C.gold2); } }};
PXD.marginnotes={frames:10,fps:12,draw:function(P,f){ const C=PXC, d=f===9?1:0, py=Math.min(56,8+f*6);   /* a pencil annotates the margin */
  for(let k=0;k<6;k++){ const ly=12+k*8; if(ly>py+2) break; const len=ly<py-6?20:Math.max(0,20-(ly-(py-6))*3);
    for(let x=0;x<len;x++) P.px(14+x,ly+Math.round(Math.sin(x*.9+k)*1.2),k%2?C.blue:C.ink,d); }
  if(f<9){ const px=12, tip=py; P.px(px,tip,C.ink); P.px(px+1,tip-1,C.cream); P.px(px+2,tip-2,C.cream);
    for(let i=3;i<15;i++){ P.px(px+i,tip-i,C.yellow); P.px(px+i+1,tip-i,C.gold); P.px(px+i,tip-i-1,C.gold2); }
    for(let i=15;i<18;i++){ P.px(px+i,tip-i,C.pink); P.px(px+i+1,tip-i,C.pink); P.px(px+i,tip-i-1,C.pink); } } }};
function pxReadyDraw(c1,c2){ return function(P,f){ const C=PXC, d=f>=8?(f===9?2:1):0;   /* chevrons surge up, ring pops */
  for(let k=0;k<3;k++){ const y=58-f*6-k*9; if(y<4||y>60) continue; pxChevron(P,32,y,7-k,k===0?C.white:c1,d,false); pxChevron(P,32,y+1,7-k,C.ink,2,false); }
  if(f>=3&&f<=8){ P.ring(32,30,6+(f-3)*5,c2,f>=6?1:0); P.ring(32,30,4+(f-3)*5,C.white,2); }
  if(f>=4){ const r=pxRng(81); for(let i=0;i<5;i++) P.star4(10+r()*44,8+r()*40,(f+i)%2?1:2,c2); } }; }
PXD.readya={frames:10,fps:16,draw:pxReadyDraw(PXC.red2,PXC.gold2)};
PXD.readyb={frames:10,fps:16,draw:pxReadyDraw(PXC.teal2,PXC.blue2)};
const _pxReadyAt={};
function abcPxReady(side,which){
  if(!abcPxOn()||!side) return;
  let wait=450; const now=Date.now();
  try{ if(side==='you' && document.body.classList.contains('abc-arena') && typeof ABC_FLY_MS==='number') wait+=Math.round(ABC_FLY_MS*.88); }catch(e){}
  if(_pxReadyAt[side] && now-_pxReadyAt[side]<250) wait+=750;   /* attack AND block filled at once: one after the other */
  _pxReadyAt[side]=now;
  setTimeout(function(){ try{
    const r=abcPxBox(document.querySelector('.char.'+side)); if(!r) return;
    const o=abcPxLayer(r), sc=Math.max(1,Math.round(r.width*1.1/PXN));
    const ms=abcPxSprite(o,which==='blk'?'readyb':'readya',sc,r.width/2,r.height*.62);
    abcPxPop(o,which==='blk'?'BLOCK READY!':'ATTACK READY!',which==='blk'?PXC.teal2:PXC.gold2,Math.max(2,sc),6,true);
    document.body.appendChild(o); setTimeout(function(){ o.remove(); },Math.max(ms,1100)+60);
  }catch(e){} }, wait);
}
function abcPxTurn(side,tries){
  if(!abcPxOn()||!side) return;
  try{ if(typeof S!=='undefined' && S && (S._sim||S.over)) return; }catch(e){}
  if(document.getElementById('abcPxCut') && (tries||0)<4){ setTimeout(function(){ abcPxTurn(side,(tries||0)+1); },350); return; }   /* let a K.O./CRITICAL banner finish */
  try{
    const old=document.getElementById('abcPxTurn'); if(old) old.remove();
    const W=window.innerWidth, H=window.innerHeight, you=side==='you', t=abcPxText(you?'YOUR TURN':"OPPONENT'S TURN",you?PXC.gold2:PXC.red2); if(!t) return;
    const s=Math.max(2,Math.min(5,Math.floor(W*.34/t.w))), bh=t.h*s+s*4;
    const el=document.createElement('div'); el.id='abcPxTurn'; el.className=you?'you':'opp';
    el.style.top=Math.round(H*.46-bh/2)+'px'; el.style.height=bh+'px';
    el.innerHTML='<img alt="" src="'+t.url+'" style="width:'+(t.w*s)+'px;height:'+(t.h*s)+'px">';
    document.body.appendChild(el);
    const T=900, dir=you?1:-1;
    if(el.animate){ el.animate([{opacity:0,transform:'scaleY(0)'},{opacity:1,transform:'scaleY(1)',offset:.12},{opacity:1,transform:'scaleY(1)',offset:.85},{opacity:0,transform:'scaleY(0)'}],{duration:T,easing:'steps(16)',fill:'forwards'});
      el.querySelector('img').animate([{transform:'translateX('+(-dir*W*.6)+'px)'},{transform:'translateX(0)',offset:.22},{transform:'translateX(0)',offset:.8},{transform:'translateX('+(dir*W*.6)+'px)'}],{duration:T,easing:'steps(20)',fill:'forwards'}); }
    setTimeout(function(){ el.remove(); },T+40);
  }catch(e){}
}
if(typeof window!=='undefined' && window.ABC_PXFX){ window.ABC_PXFX.ready=abcPxReady; window.ABC_PXFX.turn=abcPxTurn; }
'''
CSS = """
/* fix_pixel_fx3 */
#abcPxTurn{position:fixed;left:0;right:0;z-index:56;pointer-events:none;overflow:hidden;display:flex;align-items:center;justify-content:center;
  background:rgba(27,20,16,.92);border-top:3px solid #E3A92B;border-bottom:3px solid #E3A92B;transform:scaleY(0)}
#abcPxTurn.opp{border-color:#ff6a3d}
#abcPxTurn img{display:block;image-rendering:crisp-edges;image-rendering:pixelated}
"""

s = s.replace(A_BLOCK, A_BLOCK + JS, 1)
s = s.replace(A_READY, NEW_READY, 1)
s = s.replace(A_TURN, NEW_TURN, 1)
s = s.replace(A_CSS, CSS + A_CSS, 1)
for need in [MARK, 'abcPxReady(side, w)', 'abcPxTurn(S.turn)', 'PXD.ironcurtain=', '#abcPxTurn{']:
    if need not in s:
        sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:', bak)
print(f'{TAG} Next: python3 build.py')
