#!/usr/bin/env python3
"""fix_pixel_fx2.py -- Pixel effects part 2: evolution + trivia stamps (needs fix_pixel_fx.py).

Run from the repo root:   python3 fix_pixel_fx2.py
Undo:                     restore src/game.src.html from the .bak this writes.

WHAT IT ADDS (pixel mode only -- the Tune switch / Reduce motion keep the current effects)
  * Evolution: after the Act card's flight lands, an "ACT II!" / "ACT III!" banner with the
    new card's name, then the transformation plays on the character that evolved (Active or
    Backstage, yours or the AI's). Act II cracks open and shatters; Act III parts red curtains
    under a spotlight with confetti.
  * Trivia: a pixel stamp over the question -- green check + "CORRECT!", or a scribbled red X
    with ink splats + "NOT QUITE".
  * 4 new sprite strips drawn in code (no asset bytes added).

HOW IT HOOKS IN (2 lines added to existing functions, nothing removed)
  * actEvolve(): abcPxEvolve(side, c, a.act) just before it returns.
  * triviaStamp(): if the pixel stamp plays, the classic stamp is skipped.
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_pixel_fx2 */'
TAG = '[fix_pixel_fx2]'
if not os.path.exists(SRC):
    sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit(f'{TAG} Already applied -- nothing to do.')
if '/* fix_pixel_fx */' not in s:
    sys.exit(f'{TAG} ERROR: run fix_pixel_fx.py first.')

A_BLOCK = "abcPxFx(); },1500);   /* pre-draw strips off the critical path */\n}\n"
A_EVO   = "  try{ SFX.card('book_flip',0.7); }catch(e){}\n  return true;\n}\nfunction actGatePick"
A_STAMP = "  if(typeof document==='undefined') return;\n  const el=document.createElement('div');\n  el.className='tri-stamp fixed '"
A_CSS   = "</style>\n</head>"
for a, l in [(A_BLOCK, 'end of fix_pixel_fx block'), (A_EVO, 'actEvolve tail'), (A_STAMP, 'triviaStamp body'), (A_CSS, 'end of <head> styles')]:
    n = s.count(a)
    if n != 1:
        sys.exit(f'{TAG} ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')

NEW_EVO   = "  try{ SFX.card('book_flip',0.7); }catch(e){}\n  try{ abcPxEvolve(side, c, a.act); }catch(e){}   /* fix_pixel_fx2 */\n  return true;\n}\nfunction actGatePick"
NEW_STAMP = "  if(typeof document==='undefined') return;\n  try{ if(abcPxStamp(ok)) return; }catch(e){}   /* fix_pixel_fx2: pixel stamp replaces the classic one */\n  const el=document.createElement('div');\n  el.className='tri-stamp fixed '"

JS = r'''/* fix_pixel_fx2 */ /* ---- pixel effects, part 2: evolution + trivia stamps ---------------------
   Adds four strips to PXD (drawn with the part-1 toolkit) and two entry points:
     abcPxEvolve(side, ch, act)  -- "ACT II!/ACT III!" banner, then the transformation
                                    sprite on the evolved character (Active or Backstage)
     abcPxStamp(ok)              -- pixel check / cross stamp over the question
   Both return quietly (classic effects stay) when pixel mode is off. */
const PX_CHECK=["...........##","..........###",".........###.","........###..","##.....###...","###...###....",".###.###.....","..#####......","...###.......","....#........"];
PXD.evolve2={frames:14,fps:12,draw:function(P,f){ const C=PXC;   /* Act II: the old self cracks open */
  if(f<4){ const r=pxRng(13); for(let i=0;i<16;i++){ const a=r()*6.28, d=(30+r()*6)*(1-(f+1)/4.6);
      P.px(32+Math.cos(a)*d,32+Math.sin(a)*d,i%3?C.gold2:C.white); P.px(32+Math.cos(a)*(d+2),32+Math.sin(a)*(d+2),C.gold,1); }
    P.disc(32,32,f,C.white); }
  if(f>=4&&f<=8){ const w=Math.min(14,4+(f-4)*5), h=Math.round(w*1.35), flash=f===8;
    for(let y=-h;y<=h;y++) for(let x=-w;x<=w;x++){ const edge=Math.abs(x)===w||Math.abs(y)===h; P.px(32+x,32+y,flash?C.white:(edge?C.gold2:C.cream)); }
    if(f>=6&&!flash){ const paths=[[[32,32],[27,25],[29,19],[24,14]],[[32,32],[38,27],[36,21],[41,15]],[[32,32],[27,39],[30,45],[25,50]],[[32,32],[38,38],[35,44],[40,49]],[[32,32],[22,31]],[[32,32],[42,33]]];
      const n=f===6?2:3; paths.forEach(function(p){ for(let i=0;i<Math.min(n,p.length-1);i++){ P.line(p[i][0]+1,p[i][1],p[i+1][0]+1,p[i+1][1],C.gold); P.line(p[i][0],p[i][1],p[i+1][0],p[i+1][1],C.ink); } }); }
    if(f>=7) P.ring(32,32,22,C.gold2,1); }
  if(f>=9){ const k=f-8, r=pxRng(17), d=k>=4?1:0;
    for(let i=0;i<16;i++){ const a=r()*6.28, sp=5+r()*4, x=32+Math.cos(a)*k*sp, y=32+Math.sin(a)*k*sp, c=i%2?C.cream:C.gold2;
      P.px(x,y,c,d); P.px(x+1,y,c,d); P.px(x,y+1,C.gold,d); }
    P.ring(32,32,6+k*6,C.gold2,k>=3?1:0); P.ring(32,32,4+k*6,C.yellow,2);
    if(k<=3){ P.star4(32,32,6-k,C.yellow); } }
}};
PXD.evolve3={frames:14,fps:12,draw:function(P,f){ const C=PXC;   /* Act III: the curtain rises on the finale */
  const fade=f>=12?2:(f>=10?1:0);
  if(f>=3){ for(let y=6;y<64;y++){ const half=3+(y-6)*.42; for(let x=-half;x<=half;x++){ P.px(32+x,y,C.yellow,f>=11?2:2); if(Math.abs(x)<half*.35) P.px(32+x,y,C.white,f>=11?2:1); } } }
  if(f===6) P.disc(32,36,11,C.white);
  if(f>=6){ const k=f-5; P.ring(32,36,k*6,C.gold2,k>=4?1:0); const r=pxRng(23), cols=[C.gold2,C.red2,C.blue2,C.green2,C.white];
    for(let i=0;i<18;i++){ const x=r()*64, y=r()*22+k*5-6, c=cols[i%5]; P.px(x,y,c,k>=6?1:0); P.px(x+1,y,c,k>=6?1:0); } }
  if(f<12){ const o=f<2?0:Math.min(34,(f-1)*6);
    for(let x=0;x<64;x++){ const left=x<32-o, right=x>=32+o; if(!left&&!right) continue;
      const fx=(left?x:63-x)%7, c=fx===0?C.dred:(fx===3?C.red2:C.red), sway=Math.round(Math.sin(x*.5+f)*1.5);
      for(let y=6;y<62+sway;y++) P.px(x,y,c,fade); } }
  if(f<12){ for(let x=0;x<64;x++){ P.px(x,0,C.gold2,fade); for(let y=1;y<6;y++) P.px(x,y,C.gold,fade); const sc=(x%8); if(sc>1&&sc<6) P.px(x,6,C.gold,fade); if(sc>2&&sc<5) P.px(x,7,C.gold,fade); } }
}};
PXD.tyes={frames:10,fps:14,draw:function(P,f){ const C=PXC;   /* correct: green check slams down */
  const s=f===0?2:(f===1?5:4), w=13*s, x=32-w/2+(s===5?0:0), y=32-10*s/2, d=f>=8?(f===9?2:1):0;
  P.glyph(PX_CHECK,x,y,s,f===2?C.white:C.green2,d?null:C.ink);
  if(f>=2&&f<=7){ const k=f-1; P.ring(32,32,8+k*5,C.green2,k>=4?1:0); P.ring(32,32,6+k*5,C.white,2); }
  if(f>=3&&f<=8){ const r=pxRng(41); for(let i=0;i<6;i++){ const a=r()*6.28, rr=14+r()*14+(f-3)*2; P.star4(32+Math.cos(a)*rr,32+Math.sin(a)*rr,(f+i)%2?1:2,C.green2); } }
}};
PXD.tno={frames:10,fps:14,draw:function(P,f){ const C=PXC;   /* not quite: red cross scribbled, ink splats, a shake */
  const dx=[0,0,0,0,-2,2,-1,1,0,0][f], d=f>=8?(f===9?2:1):0, g1=Math.min(1,(f+1)/2), g2=Math.max(0,Math.min(1,(f-1)/2));
  const stroke=function(x0,y0,x1,y1,g){ if(g<=0) return; const ex=x0+(x1-x0)*g, ey=y0+(y1-y0)*g; P.thick(x0+dx,y0,ex+dx,ey,3,C.ink,d); P.thick(x0+dx,y0,ex+dx,ey,2,C.red2,d); P.line(x0+dx-1,y0,ex+dx-1,ey,C.yellow,d?2:1); };
  stroke(14,14,50,50,g1); stroke(50,14,14,50,g2);
  if(f>=3&&f<=8){ const r=pxRng(43); for(let i=0;i<9;i++){ const a=r()*6.28, rr=20+r()*10+(f-3), x=32+Math.cos(a)*rr+dx, y=32+Math.sin(a)*rr;
      P.disc(x,y,r()<.4?2:1,i%2?C.dred:C.ink,f>=7?1:0); } }
}};
function abcPxBox(el){ const r=el&&el.getBoundingClientRect?el.getBoundingClientRect():null; return r&&r.width?r:null; }
function abcPxLayer(r,z){ const o=document.createElement('div'); o.className='cfx px';
  o.style.cssText='left:'+Math.round(r.left)+'px;top:'+Math.round(r.top)+'px;width:'+Math.round(r.width)+'px;height:'+Math.round(r.height)+'px'+(z?';z-index:'+z:''); return o; }
function abcPxEvolve(side,ch,act){
  if(!abcPxOn()||!side) return;
  const name=(ch&&ch.name)||'', uid=ch&&ch.uid, k=act===3?'evolve3':'evolve2';
  let wait=60;   /* the Act card's flight lands first (card-play patch), then the show starts */
  try{ if(side==='you' && document.body.classList.contains('abc-arena') && typeof ABC_FLY_MS==='number') wait=Math.round(ABC_FLY_MS*.88); }catch(e){}
  setTimeout(function(){
    abcPxCut(act===3?'ACT III!':'ACT II!', name, act===3?'act3':'act2');
    setTimeout(function(){ try{
      let el=null; if(uid!=null) el=document.querySelector('.'+side+'-side .bench-mini[data-charuid="'+uid+'"]');
      const a=document.querySelector('.char.'+side); if(!el||(a&&a.querySelector('.pc-name')&&a.querySelector('.pc-name').textContent.trim()===name.trim())) el=a;
      const r=abcPxBox(el); if(!r) return;
      const o=abcPxLayer(r), sc=Math.max(1,Math.round(r.width*1.25/PXN));
      const ms=abcPxSprite(o,k,sc,r.width/2,r.height/2); document.body.appendChild(o); setTimeout(function(){ o.remove(); },ms+80);
    }catch(e){} }, 700);
  }, wait);
}
function abcPxStamp(ok){
  if(!abcPxOn()) return false;
  const fx=abcPxFx(); if(!fx||!fx.tyes) return false;
  const W=window.innerWidth, H=window.innerHeight, sc=Math.max(2,Math.min(4,Math.round(Math.min(W,H)*.3/PXN))), size=PXN*sc;
  const o=abcPxLayer({left:W/2-size/2,top:H*.46-size/2,width:size,height:size},999); o.classList.add('pxstamp');
  const ms=abcPxSprite(o,ok?'tyes':'tno',sc,size/2,size/2);
  abcPxPop(o,ok?'CORRECT!':'NOT QUITE',ok?PXC.green2:PXC.red2,Math.max(2,sc-1),96);
  document.body.appendChild(o); setTimeout(function(){ o.remove(); },Math.max(ms,1050)+60);
  return true;
}
if(typeof window!=='undefined' && window.ABC_PXFX){ window.ABC_PXFX.evolve=abcPxEvolve; window.ABC_PXFX.stamp=abcPxStamp; }
'''
CSS = """
/* fix_pixel_fx2 */
#abcPxCut.act2{border-color:#ffd45e}
#abcPxCut.act2 .pxc-lines{background:repeating-linear-gradient(90deg,rgba(255,239,107,.18) 0 12px,transparent 12px 52px)}
#abcPxCut.act3{border-color:#ff6a3d;background:#3a0f16}
#abcPxCut.act3 .pxc-lines{background:repeating-linear-gradient(90deg,rgba(255,106,61,.18) 0 12px,transparent 12px 52px)}
"""

s = s.replace(A_BLOCK, A_BLOCK + JS, 1)
s = s.replace(A_EVO, NEW_EVO, 1)
s = s.replace(A_STAMP, NEW_STAMP, 1)
s = s.replace(A_CSS, CSS + A_CSS, 1)
for need in [MARK, 'abcPxEvolve(side, c, a.act)', 'if(abcPxStamp(ok)) return;', 'PXD.evolve3=', '#abcPxCut.act3{']:
    if need not in s:
        sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:', bak)
print(f'{TAG} Next: python3 build.py')
