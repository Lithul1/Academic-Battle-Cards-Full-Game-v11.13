#!/usr/bin/env python3
"""fix_pixel_fx.py -- 16-bit pixel combat effects + full-screen cut-ins (playtest build).

Run from the repo root:   python3 fix_pixel_fx.py
Undo:                     restore src/game.src.html from the .bak this writes.
Needs:                    nothing else (works on the classic board and on the Arena board).

WHAT IT DOES
  * Every existing combat effect is re-skinned as a 16-bit sprite animation, ON the card:
      strike, critical, block, negate, KO, heal, revive, plus an ABC-attach sparkle,
      and the Burn / Tear / Rip / Glue / Siphon / Highlight status cues.
    Damage numbers and status labels become pixel text.
  * Big moments get a short full-screen cut-in banner across the middle of the
    screen: CRITICAL! (60+ damage) and K.O.! (with the character's name). About 1.1s each,
    never blocks a click.
  * The sprites are drawn in code when the page loads: 14 small PNG strips of 64x64 frames, about 70 KB
    in memory, ~30 ms one-time. No asset bytes added to the file. Final art can replace the
    drawing code 1:1 later (same strip format).
  * Tune > Accessibility > "Pixel combat effects (16-bit)" switches between pixel and the
    current effects, per device (localStorage 'abc_pxfx' = 'off' for classic). Default ON
    for playtesting.
  * Reduce motion / prefers-reduced-motion always use the classic effects (which that setting
    already calms).

HOW IT HOOKS IN (2 existing lines touched, everything else additive)
  * fxAt(): one line -- after the classic effect markup is built, pixel mode "dresses" it:
    reads which effect it is from the existing classes (.cfx-img.strike, .cfx-ring.heal,
    .cfx-float.status ...), swaps in the sprite + pixel text, and returns the duration. No
    call site changes anywhere in the engine.
  * chargeReport(): one line -- plays the attach sparkle (timed to land with the
    card-play flight when that patch is present).
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_pixel_fx */'
TAG = '[fix_pixel_fx]'
if not os.path.exists(SRC):
    sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit(f'{TAG} Already applied -- nothing to do.')

A_FXAT = "  o.innerHTML=html; document.body.appendChild(o); setTimeout(()=>o.remove(), dur||1100);\n"
A_CHG  = "function chargeReport(side, ch, before){\n  if(!ch||!before) return;\n"
A_FN   = "function fxRevive(side){ fxAt(side, `<div class=\"cfx-img revive\"></div>`, 1500); }\n"
A_ROW  = "    ${row('Reduce motion &amp; flashing',"
A_CHK  = "  if(t.dataset.calm!=null){"
A_CSS  = "</style>\n</head>"
for a, l in [(A_FXAT, 'fxAt append line'), (A_CHG, 'chargeReport head'), (A_FN, 'fxRevive'),
             (A_ROW, 'Tune Reduce-motion row'), (A_CHK, 'settings change handler (calm)'), (A_CSS, 'end of <head> styles')]:
    n = s.count(a)
    if n != 1:
        sys.exit(f'{TAG} ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')

NEW_FXAT = "  o.innerHTML=html; if(abcPxOn()) dur=abcPxDress(o,side,r,dur);   /* fix_pixel_fx */\n  document.body.appendChild(o); setTimeout(()=>o.remove(), dur||1100);\n"
NEW_CHG = A_CHG + "  abcPxAttach(side);   /* fix_pixel_fx: attach sparkle */\n"
NEW_ROW = "    ${row('Pixel combat effects (16-bit)',`<input type=\"checkbox\" data-abcpx ${abcPxPref()?'checked':''}>`)}   <!-- fix_pixel_fx -->\n" + A_ROW
NEW_CHK = "  if(t.dataset.abcpx!=null){ abcPxSet(!!t.checked); return; }   /* fix_pixel_fx */\n" + A_CHK

JS = r'''/* fix_pixel_fx */ /* ---- 16-bit pixel combat effects ------------------------------------------
   Pixel mode re-skins fxAt() output: abcPxDress() reads the classic markup's classes,
   removes the classic art and adds sprite strips (64x64 frames, stepped with the Web
   Animations API) + pixel text. abcPxCut() is the full-screen banner for CRITICAL / K.O.
   Strips are drawn once, lazily, into data-URL PNGs (abcPxFx). To ship final art, replace
   each PXD entry's draw() with a strip image of the same frame count. */
const PXC={ink:'#1b1410',white:'#fffbe8',cream:'#f3e8cd',gold:'#E3A92B',gold2:'#ffd45e',yellow:'#ffef6b',
  red:'#b5402a',red2:'#ff6a3d',dred:'#6e1d12',teal:'#1F6A6A',teal2:'#6fe3d3',blue:'#3f7fd6',blue2:'#a8d4ff',
  green:'#2f8f4a',green2:'#a6f07a',purple:'#6a3d8a',purple2:'#d39cff',paper:'#e9dcbf'};
const PXN=64;
function abcPxPref(){ try{ return localStorage.getItem('abc_pxfx')!=='off'; }catch(e){ return true; } }
function abcPxSet(on){ try{ localStorage.setItem('abc_pxfx', on?'on':'off'); }catch(e){} }
function abcPxOn(){
  if(typeof document==='undefined'||!document.body||!abcPxPref()) return false;
  if(/jsdom/i.test((typeof navigator!=='undefined'&&navigator.userAgent)||'')) return false;
  if(document.body.classList.contains('calm-fx')) return false;
  try{ if(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return false; }catch(e){}
  return !!abcPxFx();
}
function pxRng(seed){ return function(){ seed|=0; seed=seed+0x6D2B79F5|0; let t=Math.imul(seed^seed>>>15,1|seed); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }; }
const pxEase=t=>1-Math.pow(1-t,3);
function pxPainter(ctx,ox){
  const C=PXC, P={};
  P.px=function(x,y,c,d){ x=Math.round(x); y=Math.round(y); if(x<0||y<0||x>=PXN||y>=PXN) return;
    if(d===1&&(x+y)%2) return; if(d===2&&(x%2||y%2)) return; ctx.fillStyle=c; ctx.fillRect(ox+x,y,1,1); };
  P.line=function(x0,y0,x1,y1,c,d){ x0=Math.round(x0);y0=Math.round(y0);x1=Math.round(x1);y1=Math.round(y1);
    const dx=Math.abs(x1-x0),dy=-Math.abs(y1-y0),sx=x0<x1?1:-1,sy=y0<y1?1:-1; let e=dx+dy;
    for(let i=0;i<200;i++){ P.px(x0,y0,c,d); if(x0===x1&&y0===y1) break; const e2=2*e; if(e2>=dy){e+=dy;x0+=sx;} if(e2<=dx){e+=dx;y0+=sy;} } };
  P.thick=function(x0,y0,x1,y1,w,c,d){ for(let o=-w;o<=w;o++) P.line(x0+o*.7,y0-o*.7,x1+o*.7,y1-o*.7,c,d); };
  P.ring=function(cx,cy,r,c,d){ for(let a=0;a<Math.PI*2;a+=0.6/Math.max(r,1)) P.px(cx+Math.cos(a)*r,cy+Math.sin(a)*r,c,d); };
  P.disc=function(cx,cy,r,c,d){ for(let y=-r;y<=r;y++) for(let x=-r;x<=r;x++) if(x*x+y*y<=r*r+r*.6) P.px(cx+x,cy+y,c,d); };
  P.star4=function(x,y,s,c,core){ P.px(x,y,core||C.white); for(let i=1;i<=s;i++){ P.px(x+i,y,c); P.px(x-i,y,c); P.px(x,y+i,c); P.px(x,y-i,c); } };
  P.glyph=function(rows,x,y,sc,c,ol){ [ol,c].forEach(function(col,pass){ if(!col) return; rows.forEach(function(r,j){ for(let i=0;i<r.length;i++) if(r[i]==='#')
    for(let a=0;a<sc;a++) for(let b=0;b<sc;b++){ if(pass) P.px(x+i*sc+a,y+j*sc+b,col); else [[-1,0],[1,0],[0,-1],[0,1]].forEach(function(o){ P.px(x+i*sc+a+o[0],y+j*sc+b+o[1],col); }); } }); }); };
  return P;
}
const PX_SHIELD=["....#########....","..##.........##..",".#.............#.",".#.............#.",".#.............#.",".#.............#.",".#.............#.","..#...........#..","..#...........#..","...#.........#...","....#.......#....",".....##...##.....",".......###......."];
const PX_K=["#...#","#..#.","#.#..","##...","#.#..","#..#.","#...#"], PX_O=[".###.","#...#","#...#","#...#","#...#","#...#",".###."];
/* frames, fps, loops, draw(P,f) -- one entry per effect */
const PXD={
strike:{frames:8,fps:16,draw:function(P,f){ const C=PXC, cx=12,cy=54,R=44,a0=-1.55,a1=0.05, head=a0+(a1-a0)*Math.min(1,pxEase((f+1)/4)), tail=a0+(a1-a0)*Math.max(0,(f-2)/4), fade=f>=6?1:0;
  for(let a=tail;a<=head;a+=0.012){ const k=(a-tail)/Math.max(head-tail,.01), w=Math.round(1+3*k);
    for(let dr=-w;dr<=w;dr++){ const c=dr===0?C.white:(Math.abs(dr)<=1?C.gold2:(Math.abs(dr)<=2?C.red2:C.red)); P.px(cx+Math.cos(a)*(R+dr),cy+Math.sin(a)*(R+dr),c,fade); } }
  if(f>=3&&f<=7){ const r=pxRng(7); for(let i=0;i<10;i++){ const ang=r()*6.28, sp=(f-2)*(3+r()*3); P.px(34+Math.cos(ang)*sp,30+Math.sin(ang)*sp,r()<.5?C.gold2:C.white,f>=6?1:0); } }
  if(f===3) P.disc(34,30,4,C.white); }},
crit:{frames:10,fps:16,draw:function(P,f){ const C=PXC, g1=Math.min(1,(f+1)/3), g2=Math.max(0,Math.min(1,(f-1)/3)), fd=f>=8?1:0;
  if(f<9){ P.thick(10,10,10+44*g1,10+44*g1,f<6?2:1,C.white,fd); P.thick(10,10,10+44*g1,10+44*g1,0,C.red2,fd); }
  if(f>=1&&f<9){ P.thick(54,10,54-44*g2,10+44*g2,f<6?2:1,C.white,fd); P.thick(54,10,54-44*g2,10+44*g2,0,C.red2,fd); }
  if(f===4) P.disc(32,32,9,C.white);
  if(f>=4){ const r=(f-3)*5; P.ring(32,32,r,C.gold2,f>=7?1:0); P.ring(32,32,r-2,C.red,f>=7?2:1);
    for(let i=0;i<8;i++){ const a=i*Math.PI/4+.2; P.line(32+Math.cos(a)*(r+2),32+Math.sin(a)*(r+2),32+Math.cos(a)*(r+7),32+Math.sin(a)*(r+7),C.yellow,f>=8?1:0); } } }},
guard:{frames:9,fps:14,draw:function(P,f){ const C=PXC, s=f<2?(f===0?1:2):3, w=17*s, x=32-w/2, y=32-13*s/2, d=f>=7?(f===8?2:1):0;
  PX_SHIELD.forEach(function(r,j){ for(let i=0;i<r.length;i++){ if(r[i]==='#'){ for(let a=0;a<s;a++) for(let b=0;b<s;b++) P.px(x+i*s+a,y+j*s+b,f===3?C.white:C.teal2,d); }
    else if(s===3&&j>0&&j<12&&i>1&&i<15&&r.indexOf('#')<i&&r.lastIndexOf('#')>i){ for(let a=0;a<s;a++) for(let b=0;b<s;b++) P.px(x+i*s+a,y+j*s+b,C.teal,2); } } });
  if(f>=3&&f<=6) P.ring(32,32,(f-2)*7,C.blue2,f>=5?1:0);
  if(f===3) P.star4(32,26,4,C.blue2); }},
negate:{frames:10,fps:14,draw:function(P,f){ const C=PXC, r=f<2?8+f*8:24, d=f>=8?(f===9?2:1):0;
  P.ring(32,32,r,C.blue2,d); P.ring(32,32,r-1,C.blue,d===0?1:2);
  if(f>=2){ for(let a=-2.4;a<-1.6;a+=0.08) P.px(32+Math.cos(a)*(r-4),32+Math.sin(a)*(r-4),C.white,d); }
  if(f===3||f===4) P.thick(4,8,22,22,1,C.red2);
  if(f>=4&&f<=7){ const rd=pxRng(3); for(let i=0;i<9;i++){ const a=rd()*6.28, q=(f-3)*4; P.line(20+Math.cos(a)*q,20+Math.sin(a)*q,20+Math.cos(a)*(q+3),20+Math.sin(a)*(q+3),C.gold2,f>=6?1:0); } }
  if(f>=5&&f<=7) P.ring(32,32,r+2,C.white,1); }},
ko:{frames:12,fps:12,draw:function(P,f){ const C=PXC;
  if(f<5){ const r=4+f*6; P.ring(32,32,r,C.gold2,f>=3?1:0); for(let i=0;i<10;i++){ const a=i*.628; P.line(32+Math.cos(a)*r,32+Math.sin(a)*r,32+Math.cos(a)*(r+6),32+Math.sin(a)*(r+6),C.red2,f>=3?1:0); } }
  if(f>=2){ const bo=[10,-3,2,0][Math.min(3,f-2)]||0; P.glyph(PX_K,12,18+bo,3,C.red2,C.ink); P.glyph(PX_O,35,18+bo,3,C.red2,C.ink);
    for(let i=0;i<3;i++){ const a=f*.7+i*2.09; P.star4(32+Math.cos(a)*24,52+Math.sin(a)*5,2,C.yellow); } } }},
heal:{frames:12,fps:12,draw:function(P,f){ const C=PXC, r=pxRng(11);
  for(let i=0;i<6;i++){ const x=8+r()*48, st=Math.floor(r()*5), life=f-st; if(life<0||life>7) continue;
    const y=54-life*6, d=life>=6?1:0, q=r()<.4?2:1;
    for(let k=-2*q;k<=2*q;k++){ P.px(x+k,y,C.green2,d); P.px(x,y+k,C.green2,d); }
    P.px(x,y,C.white,d); if(q===2){ for(let k=-4;k<=4;k++) P.px(x+k,y+1,C.green,2); } }
  if(f%3===1) P.star4(16+(f*7)%32,20+(f*5)%20,2,C.green2); }},
attach:{frames:9,fps:16,draw:function(P,f){ const C=PXC, r=3+pxEase(f/8)*27, d=f>=6?(f>=8?2:1):0; P.ring(32,32,r,C.gold2,d); P.ring(32,32,r*.7,C.gold,d?2:1);
  const rd=pxRng(5); for(let i=0;i<6;i++){ const a=rd()*6.28, rr=8+rd()*20, st=rd()*4|0; if(f>=st&&f<st+4) P.star4(32+Math.cos(a)*rr,32+Math.sin(a)*rr,(f-st)%2?1:2,C.yellow); }
  if(f<2) P.disc(32,32,3-f,C.white); }},
revive:{frames:12,fps:12,draw:function(P,f){ const C=PXC, h=Math.min(64,f*14), wd=f<6?6:Math.max(1,6-(f-6)), d=f>=9?1:0;
  for(let y=64-h;y<64;y++) for(let x=-wd;x<=wd;x++) P.px(32+x,y,Math.abs(x)<=1?C.white:(Math.abs(x)<=3?C.yellow:C.gold),Math.abs(x)>3?1:d);
  if(f>=4&&f<=8) P.ring(32,44,(f-3)*5,C.gold2,f>=7?1:0);
  const r=pxRng(9); for(let i=0;i<8;i++){ const st=r()*8|0, life=f-st; if(life<0||life>5) continue; P.star4(14+r()*36,58-life*9,1,C.yellow); } }},
burn:{frames:6,fps:10,loops:3,draw:function(P,f){ const C=PXC, r=pxRng(21+f);
  for(let x=6;x<58;x++){ const base=10+Math.sin(x*.45+f*1.3)*4+r()*6+(x>16&&x<48?6:0);
    for(let y=0;y<base;y++){ const t=y/base, c=t<.35?C.red:(t<.65?C.red2:(t<.9?C.gold2:C.yellow)); P.px(x,63-y,c,t>.85?1:0); } }
  for(let i=0;i<4;i++) P.px(10+r()*44,30-r()*20,C.gold2); }},
tear:{frames:7,fps:14,draw:function(P,f){ const C=PXC, prog=Math.min(1,(f+1)/5), pts=[]; for(let i=0;i<=12;i++) pts.push([4+i*4.7,10+i*3.6+(i%2?4:-3)]);
  const n=Math.floor(prog*12);
  for(let i=0;i<n;i++){ const a=pts[i],b=pts[i+1]; P.line(a[0],a[1]-2,b[0],b[1]-2,C.cream); P.line(a[0],a[1],b[0],b[1],C.ink); P.line(a[0],a[1]+1,b[0],b[1]+1,C.dred); P.line(a[0],a[1]+3,b[0],b[1]+3,C.cream); }
  if(f>=4){ const r=pxRng(2); for(let i=0;i<6;i++) P.px(pts[n][0]+r()*8-4+(f-4)*2,pts[n][1]+r()*8-4-(f-4)*3,C.paper); } }},
rip:{frames:8,fps:14,draw:function(P,f){ const C=PXC, gap=f<3?0:Math.min(5,(f-2)*2), pts=[]; for(let j=0;j<=10;j++) pts.push([32+(j%2?4:-4)+(j%3?1:-2),2+j*6]);
  if(f<3){ for(let j=0;j<Math.min(10,(f+1)*4);j++) P.line(pts[j][0],pts[j][1],pts[j+1][0],pts[j+1][1],C.white); return; }
  for(let j=0;j<10;j++){ const a=pts[j],b=pts[j+1]; P.line(a[0]-gap,a[1],b[0]-gap,b[1],C.cream); P.line(a[0]+gap,a[1],b[0]+gap,b[1],C.cream);
    for(let x=-gap+1;x<gap;x++) P.line(a[0]+x,a[1],b[0]+x,b[1],C.ink,x%2?1:0); }
  const r=pxRng(4); for(let i=0;i<8;i++){ const q=(f-2)*4; P.px(32+(r()<.5?-1:1)*(gap+q*r()),8+r()*48-q*.4,C.paper,f>=6?1:0); } }},
glue:{frames:10,fps:10,draw:function(P,f){ const C=PXC, r=pxRng(31);
  for(let i=0;i<7;i++){ const x=6+i*8+r()*4, st=r()*3|0, len=Math.max(0,Math.min(28+r()*12,(f-st)*7));
    for(let y=0;y<len;y++){ P.px(x,y,C.white); P.px(x+1,y,C.cream); P.px(x-1,y,C.paper,1); }
    if(len>4){ P.disc(x,len,2,C.cream); P.px(x-1,len-1,C.white); } }
  for(let x=0;x<64;x++){ P.px(x,0,C.white); P.px(x,1,C.cream); P.px(x,2,C.paper,1); } }},
siphon:{frames:10,fps:12,draw:function(P,f){ const C=PXC;
  for(let i=0;i<14;i++){ const ph=(i/14+f/10)%1, ang=i*2.4+ph*5, rr=26*(1-ph); P.px(32+Math.cos(ang)*rr,32+Math.sin(ang)*rr,ph>.6?C.purple2:C.purple); P.px(32+Math.cos(ang)*rr+1,32+Math.sin(ang)*rr,C.purple,1); }
  P.disc(32,32,2+(f%3),C.purple2); P.px(32,32,C.white);
  for(let k=0;k<4;k++){ const y=28-((f*5+k*9)%28); P.px(30+(k%2)*4,y,C.purple2,y<8?1:0); } }},
highlight:{frames:8,fps:14,draw:function(P,f){ const C=PXC, w=Math.min(60,pxEase((f+1)/6)*60), d=f>=7?1:0;
  for(let x=2;x<2+w;x++){ const y0=26+Math.round((x-32)*-.12); for(let y=0;y<12;y++) P.px(x,y0+y,(y===0||y===11)?C.gold:C.yellow,(y===0||y===11)?0:(d?2:1)); }
  if(f>=5) P.star4(2+w,24,3,C.white); }}
};
let _pxFx=null;
function abcPxFx(){
  if(_pxFx!==null) return _pxFx||null;
  try{
    const out={};
    Object.keys(PXD).forEach(function(k){ const d=PXD[k], cv=document.createElement('canvas'); cv.width=PXN*d.frames; cv.height=PXN;
      const ctx=cv.getContext('2d'); if(!ctx) throw new Error('no 2d');
      for(let f=0;f<d.frames;f++) d.draw(pxPainter(ctx,f*PXN),f);
      out[k]={url:cv.toDataURL('image/png'),frames:d.frames,ms:Math.round(d.frames*1000/d.fps),loops:d.loops||1}; });
    _pxFx=out;
  }catch(e){ _pxFx=false; }
  return _pxFx||null;
}
/* 5x7 pixel font: 7 rows x 5 bits per glyph, hex */
const PX_FONT=(function(){ const src={A:'0e11111f111111',B:'1e11111e11111e',C:'0e11101010110e',D:'1e11111111111e',E:'1f10101e10101f',F:'1f10101e101010',
  G:'0e11101711110f',H:'1111111f111111',I:'0e04040404040e',J:'0702020202120c',K:'11121418141211',L:'1010101010101f',M:'111b1515111111',
  N:'11111915131111',O:'0e11111111110e',P:'1e11111e101010',Q:'0e11111115120d',R:'1e11111e141211',S:'0f10100e01011e',T:'1f040404040404',U:'1111111111110e',
  V:'11111111110a04',W:'1111111515150a',X:'11110a040a1111',Y:'1111110a040404',Z:'1f01020408101f','0':'0e11131519110e','1':'040c040404040e',
  '2':'0e11010204081f','3':'1f02040201110e','4':'02060a121f0202','5':'1f101e0101110e','6':'0608101e11110e','7':'1f010204080808','8':'0e11110e11110e',
  '9':'0e11110f01020c','-':'0000001f000000','+':'0004041f040400','!':'04040404040004','.':'00000000000c0c',"'":'0c040800000000',' ':'00000000000000'};
  const o={}; Object.keys(src).forEach(function(k){ const h=src[k], rows=[]; for(let i=0;i<7;i++) rows.push(parseInt(h.substr(i*2,2),16)); o[k]=rows; }); return o; })();
const _pxTxt={};
function abcPxText(txt,col){
  txt=String(txt||'').toUpperCase().replace(/−/g,'-').split('').filter(function(c){ return PX_FONT[c]; }).join('').replace(/\s+/g,' ').trim();
  if(!txt) return null;
  const key=txt+'|'+col; if(_pxTxt[key]) return _pxTxt[key];
  const w=txt.length*6+1, cv=document.createElement('canvas'); cv.width=w+1; cv.height=9;
  const ctx=cv.getContext('2d'); if(!ctx) return null;
  [PXC.ink,col].forEach(function(c,pass){ ctx.fillStyle=c; txt.split('').forEach(function(ch,i){ PX_FONT[ch].forEach(function(row,y){ for(let x=0;x<5;x++) if(row&(16>>x)){
    if(pass) ctx.fillRect(1+i*6+x,1+y,1,1); else ctx.fillRect(i*6+x,y,3,3); } }); }); });
  return (_pxTxt[key]={url:cv.toDataURL('image/png'),w:cv.width,h:cv.height,txt:txt});
}
function abcPxSprite(o,k,sc,cx,cy,wait){
  const d=abcPxFx()[k], size=PXN*sc, el=document.createElement('div');
  el.className='cfx-px'; el.dataset.fx=k;
  el.style.cssText='width:'+size+'px;height:'+size+'px;left:'+Math.round(cx-size/2)+'px;top:'+Math.round(cy-size/2)+'px;background-image:url('+d.url+');background-size:'+(d.frames*size)+'px '+size+'px';
  o.appendChild(el);
  if(el.animate){ el.animate([{backgroundPosition:'0 0'},{backgroundPosition:(-d.frames*size)+'px 0'}],{duration:d.ms,iterations:d.loops,easing:'steps('+d.frames+')',fill:'forwards',delay:wait||0}); if(wait){ el.style.visibility='hidden'; setTimeout(function(){ el.style.visibility=''; },wait); } }
  return d.ms*d.loops;
}
function abcPxPop(o,txt,col,s,topPct,badge){
  const t=abcPxText(txt,col); if(!t) return false;
  const im=document.createElement('img'); im.className='cfx-pxnum'+(badge?' badge':''); im.alt=''; im.src=t.url;
  im.style.width=(t.w*s)+'px'; im.style.height=(t.h*s)+'px'; im.style.top=topPct+'%';
  if(badge) im.style.padding=s+'px '+(s*2)+'px';
  o.appendChild(im);
  if(im.animate) im.animate([{transform:'translate(-50%,8px)',opacity:0},{transform:'translate(-50%,-10px)',opacity:1,offset:.14},
    {transform:'translate(-50%,-14px)',opacity:1,offset:.72},{transform:'translate(-50%,-38px)',opacity:0}],{duration:1050,easing:'steps(14)',fill:'forwards'});
  return true;
}
function abcPxCharName(side){ try{ const n=document.querySelector('.char.'+side+' .pc-name'); return n?n.textContent:''; }catch(e){ return ''; } }
function abcPxDress(o,side,r,dur){
  const fx=abcPxFx(); if(!fx) return dur;
  o.classList.add('px'); o.style.left=Math.round(r.left)+'px'; o.style.top=Math.round(r.top)+'px';
  const sc=Math.max(1,Math.round(r.width*1.1/PXN)), ts=Math.max(2,sc+1), cx=r.width/2, cy=r.height/2;
  const q=function(x){ return o.querySelector(x); };
  const fl=q('.cfx-float'), ft=fl?fl.textContent:'', num=(ft.match(/\d+/)||[''])[0], names=[];
  const img=q('.cfx-img');
  if(img){ const k=['strike','crit','guard','ko','revive'].find(function(c){ return img.classList.contains(c); }); if(k) names.push(k==='guard'&&/negated/i.test(ft)?'negate':k); }
  if(q('.cfx-ring.heal')) names.push('heal');
  if(q('.cfx-pxattach')) names.push('attach');
  /* CRITICAL / K.O.: the banner plays first, then the hit lands on the card as it clears */
  const big=names.indexOf('crit')>=0||names.indexOf('ko')>=0, wait=big?700:0;
  if(names.indexOf('crit')>=0) abcPxCut('CRITICAL!', num?('-'+num+' DAMAGE'):'', 'crit');
  if(names.indexOf('ko')>=0){ const nm=abcPxCharName(side); abcPxCut('K.O.!', nm?(nm+' is out!'):'', 'ko'); }
  let popped=false;
  if(fl){
    const c=fl.classList;
    if(c.contains('status')){ const label=ft.replace(/^[^A-Za-z]+/,''), key=label.replace(/[^a-z]/gi,'').toLowerCase(); if(fx[key]) names.push(key);
      popped=abcPxPop(o,label,c.contains('neg')?PXC.red2:(c.contains('pos')?PXC.green2:PXC.cream),Math.max(2,sc),16,true); }
    else if(c.contains('heal')) popped=abcPxPop(o,'+'+num,PXC.green2,ts,34);
    else if(c.contains('blk')) popped=abcPxPop(o,num?('BLOCK '+num):'NEGATED',PXC.blue2,Math.max(2,sc),18);
    else popped=abcPxPop(o,'-'+num+(c.contains('crit')?'!':''),c.contains('crit')?PXC.yellow:PXC.red2,c.contains('crit')?ts+1:ts,36);
  }
  o.querySelectorAll('.cfx-img,.cfx-ring,.cfx-cue,.cfx-slash,.cfx-pxattach').forEach(function(n){ n.remove(); });
  if(popped&&fl) fl.remove();
  let ms=0; names.forEach(function(k){ ms=Math.max(ms,abcPxSprite(o,k,sc,cx,cy,wait)); });
  if(wait) o.querySelectorAll('.cfx-pxnum').forEach(function(n){ n.getAnimations&&n.getAnimations().forEach(function(a){ a.effect.updateTiming({delay:wait,fill:'both'}); }); });
  return Math.max(dur||1100, ms+80, popped?1100:0)+wait;
}
function abcPxCut(big,sub,tone){
  try{
    const old=document.getElementById('abcPxCut'); if(old) old.remove();
    const W=window.innerWidth, H=window.innerHeight, bt=abcPxText(big,tone==='ko'?PXC.red2:PXC.yellow); if(!bt) return;
    const s=Math.max(3,Math.min(10,Math.floor(W*.55/bt.w))), st=sub?abcPxText(sub,PXC.cream):null;
    const s2=st?Math.max(2,Math.min(Math.floor(s/2),Math.floor(W*.8/st.w))):0;
    const bh=bt.h*s+(st?st.h*s2+s*2:0)+s*6;
    const el=document.createElement('div'); el.id='abcPxCut'; el.className=tone;
    el.style.top=Math.round(H*.46-bh/2)+'px'; el.style.height=bh+'px';
    el.innerHTML='<div class="pxc-lines"></div><img alt="" class="pxc-big" src="'+bt.url+'" style="width:'+(bt.w*s)+'px;height:'+(bt.h*s)+'px">'
      +(st?'<img alt="" class="pxc-sub" src="'+st.url+'" style="width:'+(st.w*s2)+'px;height:'+(st.h*s2)+'px;margin-top:'+s+'px">':'');
    document.body.appendChild(el);
    const T=950;
    if(el.animate){
      el.animate([{transform:'scaleY(0)'},{transform:'scaleY(1)',offset:.1},{transform:'scaleY(1)',offset:.88},{transform:'scaleY(0)'}],{duration:T,easing:'steps(20)',fill:'forwards'});
      el.querySelectorAll('img').forEach(function(im,i){ im.animate([{transform:'translateX('+(-W)+'px)'},{transform:'translateX(0)',offset:.2+i*.04},{transform:'translateX(0)',offset:.8},{transform:'translateX('+W+'px)'}],{duration:T,easing:'steps(24)',fill:'forwards'}); });
      el.querySelector('.pxc-lines').animate([{backgroundPosition:'0 0'},{backgroundPosition:(-W)+'px 0'}],{duration:T,easing:'steps(18)'});
    }
    setTimeout(function(){ el.remove(); },T+40);
  }catch(e){}
}
function abcPxAttach(side){
  if(!abcPxOn()||!side) return;
  let wait=0;
  try{ if(side==='you' && document.body.classList.contains('abc-arena') && typeof ABC_FLY_MS==='number') wait=Math.round(ABC_FLY_MS*.88); }catch(e){}
  setTimeout(function(){ try{
    const el=document.querySelector('.char.'+side); if(!el) return; const r=el.getBoundingClientRect(); if(!r.width) return;
    const o=document.createElement('div'); o.className='cfx'; o.style.cssText='left:'+r.left+'px;top:'+r.top+'px;width:'+r.width+'px;height:'+r.height+'px';
    o.innerHTML='<div class="cfx-pxattach"></div>'; const d=abcPxDress(o,side,r,700); document.body.appendChild(o); setTimeout(function(){ o.remove(); },d);
  }catch(e){} }, wait);
}
if(typeof window!=='undefined'){
  window.ABC_PXFX={on:abcPxOn, strips:abcPxFx, dress:abcPxDress, cut:abcPxCut, attach:abcPxAttach, heal:function(side,n){ return fxHeal(side,n); }};
  setTimeout(function(){ if(abcPxPref() && !/jsdom/i.test((navigator&&navigator.userAgent)||'')) abcPxFx(); },1500);   /* pre-draw strips off the critical path */
}
'''
CSS = """
/* fix_pixel_fx */
.cfx.px .cfx-px{position:absolute;background-repeat:no-repeat;background-position:0 0;image-rendering:crisp-edges;image-rendering:pixelated}
.cfx.px .cfx-pxnum{position:absolute;left:50%;transform:translate(-50%,0);image-rendering:crisp-edges;image-rendering:pixelated;z-index:2;box-sizing:content-box}
.cfx.px .cfx-pxnum.badge{background:#1b1410;border:2px solid #E3A92B;box-shadow:3px 3px 0 #000}
#abcPxCut{position:fixed;left:0;right:0;z-index:57;pointer-events:none;overflow:hidden;display:flex;flex-direction:column;align-items:center;justify-content:center;
  background:#1b1410;border-top:4px solid #E3A92B;border-bottom:4px solid #E3A92B;box-shadow:0 4px 0 #6e1d12,0 -4px 0 #6e1d12;transform:scaleY(0)}
#abcPxCut.ko{border-color:#ff6a3d}
#abcPxCut img{position:relative;display:block;image-rendering:crisp-edges;image-rendering:pixelated}
#abcPxCut .pxc-lines{position:absolute;inset:0;background:repeating-linear-gradient(90deg,rgba(255,212,94,.15) 0 12px,transparent 12px 52px)}
#abcPxCut.ko .pxc-lines{background:repeating-linear-gradient(90deg,rgba(255,106,61,.16) 0 12px,transparent 12px 52px)}
"""

s = s.replace(A_FXAT, NEW_FXAT, 1)
s = s.replace(A_CHG, NEW_CHG, 1)
s = s.replace(A_FN, A_FN + JS, 1)
s = s.replace(A_ROW, NEW_ROW, 1)
s = s.replace(A_CHK, NEW_CHK, 1)
s = s.replace(A_CSS, CSS + A_CSS, 1)
for need in [MARK, 'dur=abcPxDress(o,side,r,dur)', 'abcPxAttach(side);', 'data-abcpx', 'abcPxSet(!!t.checked)', '#abcPxCut{']:
    if need not in s:
        sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:', bak)
print(f'{TAG} Next: python3 build.py')
