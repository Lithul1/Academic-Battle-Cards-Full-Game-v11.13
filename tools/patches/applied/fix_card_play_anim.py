#!/usr/bin/env python3
"""fix_card_play_anim.py -- Card-play animation: a played card flies from your hand to
where it went on the table. (Needs fix_board_layout_v1-v6.)

Run from the repo root:   python3 fix_card_play_anim.py
Undo:                     restore src/game.src.html from the .bak this writes.

WHAT YOU SEE
  When a card leaves your hand it lifts, arcs over the table and lands where it went:
    ABC (correct answer)      -> the character it charged (Active or Backstage card)
    ABC (wrong answer)        -> your discard pile (so a miss reads as a miss)
    Critical Lens             -> your Lens slot
    Bookmark held in play     -> your Active Bookmarks tray
    Bookmark used up / shed   -> your discard pile
    Character / Act card      -> your Active
    Card returned to the deck -> your deck
  The target gives a short gold flash as the card lands. ~0.55s, desktop and phone.

HOW (no engine changes, nothing waits on it)
  renderGame() already rebuilds the board on every change. Before it does, we note
  which hand cards (by object) have disappeared since the last frame and grab their
  on-screen position and look; after the new board is drawn we find where each card
  now lives (charge pile, crit slot, activeBm, discard, deck) and fly a copy there.
  The copy is purely visual (pointer-events:none) and never blocks a click; the game
  state has already moved on underneath it.

GUARDS
  * Skipped when 4+ cards leave at once (mulligan / reshuffle), on a new game, and
    for the opponent (the existing "Opponent plays" zoom already covers the AI).
  * Off when Tune > Accessibility > Reduce motion is on, or the OS asks for reduced
    motion.
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_card_play_anim */'
if not os.path.exists(SRC):
    sys.exit('[fix_card_play_anim] ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit('[fix_card_play_anim] Already applied -- nothing to do.')
for v in ('v1', 'v2', 'v3', 'v4', 'v5', 'v6'):
    if f'/* fix_board_layout_{v} */' not in s:
        sys.exit(f'[fix_card_play_anim] ERROR: run fix_board_layout_{v}.py first.')

A_CSS   = "</style>\n</head>"
A_HEAD  = "  abcLayoutSync();   /* fix_board_layout_v1 */\n"
A_TAIL  = "  fitNames();\n  fitBoard();\n  placeTurnBar();\n}\n"
A_JSDEF = "// Uniformly scale the board so both sides + controls always fit the play area (no overlap, no scroll)\nfunction fitBoard(){\n"
for a, l in [(A_CSS, 'end of <head> styles'), (A_HEAD, 'renderGame head (v1)'), (A_TAIL, 'renderGame tail'), (A_JSDEF, 'fitBoard head')]:
    n = s.count(a)
    if n != 1:
        sys.exit(f'[fix_card_play_anim] ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')

CSS = """
/* fix_card_play_anim */
.abc-fly-hand{position:absolute!important;left:0;top:0;display:block!important;padding:0!important;margin:0!important;
  pointer-events:none;z-index:60;transform-origin:50% 50%;will-change:transform,opacity;filter:drop-shadow(0 14px 18px rgba(0,0,0,.5))}
body:not(.abc-arena) .abc-fly-hand{position:fixed!important;z-index:9000}
.abc-fly-hand .hc{position:relative!important;transform:none!important;margin:0!important;opacity:1!important;filter:none!important;
  box-shadow:0 0 0 3px #E3A92B,0 6px 0 #241f1b!important}
@keyframes abcLand{0%{filter:brightness(1.55) drop-shadow(0 0 10px rgba(227,169,43,.95))}100%{filter:none}}
.abc-land{animation:abcLand .42s ease-out}
"""

JS = r"""/* fix_card_play_anim: a played card flies from your hand to where it went */
let abcLastHand=null, abcLastS=null;
function abcFlyCalm(){ try{ return document.body.classList.contains('calm-fx') || (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches); }catch(e){ return false; } }
/* before the board is rebuilt: which hand cards left, and where were they on screen? */
function abcFlySnap(){
  const last=abcLastHand; abcLastHand=null;                 /* consumed: a nested render takes no snapshot */
  if(!last || !S || abcLastS!==S || abcFlyCalm()) return null;
  const gone=last.filter(function(c){ return S.you.hand.indexOf(c)<0; });
  if(!gone.length || gone.length>3) return null;           /* 4+ at once = mulligan / reshuffle, not a play */
  const out=[];
  gone.forEach(function(c){
    const el=document.querySelector('.hand .hc[data-idx="'+last.indexOf(c)+'"]'); if(!el) return;
    const r=el.getBoundingClientRect(); if(!r.width) return;
    const cl=el.cloneNode(true); cl.classList.remove('deal-in','sel','drag-src','playable');
    out.push({card:c, r:r, w:el.offsetWidth, h:el.offsetHeight, node:cl});
  });
  return out.length?out:null;
}
function abcFlyTarget(card){
  const p=S.you, q=function(sel){ return document.querySelector(sel); };
  for(const ch of p.team){
    if((ch.atkCharge||[]).indexOf(card)>=0 || (ch.blkCharge||[]).indexOf(card)>=0)
      return ch===active(p) ? q('.char.you') : (q('.bench-mini[data-charuid="'+ch.uid+'"]') || q('.char.you'));
  }
  if(p.crit===card) return q('.you-side .lenschip');
  if((p.activeBm||[]).indexOf(card)>=0) return q('.you-side .abm-zone') || q('.discardpile[data-pile="you"]');
  if((p.deck||[]).indexOf(card)>=0) return q('.deckstack.you');
  if(card.cat==='char' || card.cat==='act') return q('.char.you');
  return q('.discardpile[data-pile="you"]') || q('.char.you');
}
/* after the board is rebuilt: fly each copy to its new home */
function abcFlyRun(snap){
  abcLastHand=S?S.you.hand.slice():null; abcLastS=S;
  if(!snap) return;
  const arena=document.body.classList.contains('abc-arena'), st=arena?document.querySelector('.abc-stage'):null;
  const host=st||document.body, k=st?(parseFloat(st.style.getPropertyValue('--abc-k'))||1):1;
  const o=st?st.getBoundingClientRect():{left:0,top:0};
  const loc=function(r){ return {x:(r.left+r.width/2-o.left)/k, y:(r.top+r.height/2-o.top)/k, h:r.height/k}; };
  snap.forEach(function(f,i){
    const tgt=abcFlyTarget(f.card); if(!tgt) return;
    const tr=tgt.getBoundingClientRect(); if(!tr.width) return;
    const a=loc(f.r), b=loc(tr);
    const wrap=document.createElement('div'); wrap.className='hand abc-fly-hand';
    wrap.style.width=f.w+'px'; wrap.style.height=f.h+'px'; wrap.appendChild(f.node); host.appendChild(wrap);
    const T=function(x,y){ return 'translate('+(x-f.w/2).toFixed(1)+'px,'+(y-f.h/2).toFixed(1)+'px)'; };
    const sc=Math.max(.35, Math.min(.8, b.h/f.h)), mx=(a.x+b.x)/2, my=Math.min(a.y,b.y)-70;
    if(!wrap.animate){ wrap.remove(); return; }
    const an=wrap.animate([
      {transform:T(a.x,a.y)+' scale(1) rotate(0deg)', opacity:1},
      {transform:T(mx,my)+' scale(1.1) rotate(-6deg)', opacity:1, offset:.4},
      {transform:T(b.x,b.y)+' scale('+sc+') rotate(0deg)', opacity:.95, offset:.85},
      {transform:T(b.x,b.y)+' scale('+(sc*.9)+') rotate(0deg)', opacity:0}
    ], {duration:560, delay:i*70, easing:'cubic-bezier(.3,.7,.25,1)', fill:'both'});
    an.onfinish=function(){ wrap.remove();
      const t2=abcFlyTarget(f.card); if(t2){ t2.classList.remove('abc-land'); void t2.offsetWidth; t2.classList.add('abc-land');
        setTimeout(function(){ t2.classList.remove('abc-land'); }, 450); } };
  });
}
"""

s = s.replace(A_CSS, CSS + A_CSS, 1)
s = s.replace(A_JSDEF, JS + A_JSDEF, 1)
s = s.replace(A_HEAD, A_HEAD + "  const _abcFly=abcFlySnap();   /* fix_card_play_anim */\n", 1)
s = s.replace(A_TAIL, "  fitNames();\n  fitBoard();\n  placeTurnBar();\n  abcFlyRun(_abcFly);   /* fix_card_play_anim */\n}\n", 1)

for need in [MARK, 'function abcFlySnap', 'const _abcFly=abcFlySnap();', 'abcFlyRun(_abcFly);']:
    if need not in s:
        sys.exit(f'[fix_card_play_anim] ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print('[fix_card_play_anim] Applied.  Backup:', bak)
print('[fix_card_play_anim] Next: python3 build.py')
