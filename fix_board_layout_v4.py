#!/usr/bin/env python3
"""fix_board_layout_v4.py -- Phone portrait stage for the Arena board (needs v1-v3).

Run from the repo root:   python3 fix_board_layout_v4.py
Undo:                     restore src/game.src.html from the .bak this writes.

WHAT CHANGES:
  1. Portrait screens (phones, iPad portrait) get their own fixed 390x844 stage,
     scaled as a whole -- the approved phone artboard. Same DOM as desktop; only the
     grid changes, so every button, drag target and Inspect behaviour carries over.
       top strip   opponent name + Tune / Menu / Log
       opp page    Backstage x4 + deck/discard, Lens badge | Active | move picker
       spine       scoreboard + phases, turn timer as a thin bar along its edge
       your page   Lens badge | Active | move picker, Backstage x4 + deck/discard
       action row  your deck name + Draw / Done / End turn
       hand        fans along the bottom
  2. Inspect becomes a sheet that slides over the board when you tap 'i', a
     Backstage card or the Lens arrow (no hover on touch). Close shuts it.
  3. The tabletop tilt is skipped in portrait (too small to read at an angle);
     the Tune setting is kept for when the device turns back to landscape.
  4. The corner sound buttons hide on the phone stage (they sat on the hand);
     volume is in Tune > Audio.
  5. The Backstage swap button moves to the card's top-left corner on both stages.
     It sat just right of centre, so tapping a card to read it often swapped it
     into the Active slot instead.
  6. Long character names shrink to fit again. The name-fitting code set a plain
     inline size that the arena's sizes overrode, which is what clipped
     "Augustus M..." on desktop; it now wins. Names too long even at the smallest
     size ("The Hound of the Baskervilles") wrap to two lines instead of clipping.
     (Three small lines in fitNames; this also helps the classic board.)
  7. Rotating the device switches between the desktop and phone stages live.
  Phones held LANDSCAPE still use the classic board (about 390px of height is
  too short for either stage). localStorage 'abc_layout'='classic' still forces
  the old board everywhere.
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_board_layout_v4 */'
if not os.path.exists(SRC):
    sys.exit('[fix_board_layout_v4] ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit('[fix_board_layout_v4] Already applied -- nothing to do.')
for need, name in [('/* fix_board_layout_v1 */', 'v1'), ('/* fix_board_layout_v2 */', 'v2'), ('/* fix_board_layout_v3 */', 'v3')]:
    if need not in s:
        sys.exit(f'[fix_board_layout_v4] ERROR: run fix_board_layout_{name}.py first.')

A_ON    = "  return w>=h*1.15 && Math.min(w/1280, h/720)>=0.58;     /* landscape and big enough to read */\n"
A_HOOK  = "  if(abcArenaFit()) return;   /* fix_board_layout_v1 */\n"
A_SCALE = "  if(st) st.style.setProperty('--abc-k', Math.min(window.innerWidth/1280, window.innerHeight/720).toFixed(4));\n"
A_CSS   = "</style>\n</head>"
A_JS    = "function abcTiltOn(){"
A_FIT0  = "    el.style.fontSize='';\n    let size=parseFloat(getComputedStyle(el).fontSize)||15, guard=48;"
A_FIT   = "while(el.scrollWidth>el.clientWidth+1 && size>8.5 && guard-->0){ size-=0.5; el.style.fontSize=size+'px'; }"
for a, l in [(A_ON, 'abcArenaOn landscape test (v1)'), (A_HOOK, 'fitBoard arena hook (v1)'),
             (A_SCALE, 'stage scale line (v1)'), (A_CSS, 'end of <head> styles'), (A_JS, 'abcTiltOn (v3)'), (A_FIT, 'fitNames shrink loop'), (A_FIT0, 'fitNames reset')]:
    n = s.count(a)
    if n != 1:
        sys.exit(f'[fix_board_layout_v4] ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')

Q = 'body.abc-arena.abc-phone[data-screen="play"]'
# Phone grid: cols 8 | 110 | 140 | 124 | 8 ; rows 52 | 98 | 170 | 36 | 170 | 98 | 60 | 160  (=390 x 844)
CSS = """
/* fix_board_layout_v4 */
/* ===== PHONE PORTRAIT STAGE -- 390x844, same parts, different grid ===== */
Q .abc-stage{width:390px;height:844px;
  grid-template-columns:8px 110px 140px 124px 8px;
  grid-template-rows:52px 98px 170px 36px 170px 98px 60px 160px}
Q .board::before{grid-column:2/5;grid-row:2/4}
Q .board::after{grid-column:2/5;grid-row:5/7}
/* top strip */
Q .opp-side .side-meta{grid-column:2;grid-row:1;align-self:center;font-size:11px!important;line-height:1.15}
Q .tb-btns{grid-column:3/5;grid-row:1;justify-self:end;align-self:center;margin-right:58px;gap:4px}
Q .tb-btns button{min-height:38px;padding:4px 8px;font-size:11px}
Q .logtoggle{grid-column:4;grid-row:1;justify-self:end;align-self:center;min-height:38px;padding:4px 8px;font-size:11px}
/* Backstage rows + piles share a row: bench left, deck/discard right */
Q .bench{grid-column:2/5;justify-content:flex-start;padding-left:5px;gap:5px!important}
Q .bench-mini{width:56px!important;height:82px!important}
Q .bench-mini .bm-name{font-size:9.5px!important}
Q .piles{grid-column:4;justify-self:end;align-self:center!important;margin:0 6px 0 0!important;flex-wrap:nowrap;gap:6px!important}
Q .opp-side .piles{grid-row:2}
Q .you-side .piles{grid-row:6}
Q .piles .deckstack,Q .piles .discardpile{width:40px!important;height:56px!important}
Q .piles .abm-zone,Q .piles>*:not(.deckstack):not(.discardpile){display:none!important}
/* Actives + move picker (.side scope: the Inspect dossier is also .char) */
Q .side .char{grid-column:3;width:136px!important;padding:4px!important}
Q .side .char .pc-name{font-size:10px!important}
Q .side .char .pc-hp{min-width:40px}
Q .side .char .pc-hp b{font-size:8.5px!important;padding:1px 3px}
Q .side .char .pc-art{height:86px!important}
Q .side .char .pc-moves{width:118px;left:calc(100% + 6px);padding:4px;gap:4px;border-width:2px}
Q .side .char .pc-move{min-height:44px;padding:3px 4px;gap:3px}
Q .side .char .pc-mc{display:none}
Q .side .char .pc-mn{font-size:10.5px}
Q .side .char .pc-chip{font-size:11px;min-width:0;padding:3px 4px}
/* Lens badge, left of each Active */
Q .lenschip{grid-column:2;width:104px!important;max-width:104px!important;min-height:0;padding:5px;
  flex-direction:column;align-items:center;text-align:center;gap:4px;font-size:10px}
Q .lenschip .lc-port{width:32px;height:32px;flex:0 0 32px}
Q .lenschip .lc-nm{font-size:10px}
Q .lenschip .lc-thesis{font-size:9.5px;padding:2px 5px}
Q .lenschip .lc-toggle{position:absolute;top:2px;right:2px}
Q .lenschip.empty{min-height:46px}
/* spine: scoreboard left, phases right, timer as a thin bar on its lower edge */
Q .phasehud{grid-column:2/5;grid-row:4;justify-content:flex-end;padding-right:4px;gap:0}
Q .phasehud .ph{font-size:10px;padding:3px 5px;letter-spacing:.6px}
Q .phasehud .ph-arrow{font-size:10px}
Q .kos.opp{grid-column:2/4;grid-row:4;align-self:center;margin:0 0 0 6px!important;font-size:10px!important;padding:2px 6px}
Q .kos.you{grid-column:2/4;grid-row:4;align-self:center;margin:0 0 0 64px!important;font-size:10px!important;padding:2px 6px}
Q .turnbar{grid-column:2/5;grid-row:4;align-self:end;justify-self:stretch;width:auto!important;height:4px!important;
  margin:0!important;border:0!important;border-radius:0!important;box-shadow:none!important}
Q .turnbar .tb-text{display:none}
/* action row */
Q .you-side .side-meta{grid-column:2;grid-row:7;align-self:center;font-size:11px!important;line-height:1.15}
Q .actions{grid-column:3/5;grid-row:7;flex-direction:row;align-items:center;justify-content:flex-end;padding:0 4px 0 0!important;gap:6px}
Q .actions .bigbtn{width:auto;font-size:13px;line-height:1.1;padding:9px 12px;border-width:3px;white-space:nowrap}
Q .actions .toolbtn{width:auto;font-size:11px;padding:6px 8px}
Q .actions .hint{display:none}
/* hand */
Q .hand-wrap{grid-column:1/6;grid-row:8}
Q .hand{--card-h:124px;--fan-step:5deg;--fan-arc:2px;--fan-lift:30px;--fan-scale:1.08;--tuck-frac:0.14}
/* Inspect: a sheet over the board, only while something is pinned */
Q .abc-inspect{display:none!important}
Q .abc-inspect:has(.ai-dossier),Q .abc-inspect:has(.ai-lens){display:flex!important;position:absolute;grid-row:auto!important;grid-column:auto!important;left:12px;right:12px;top:58px;bottom:168px;
  z-index:50;margin:0;background:rgba(29,25,21,.97);border:3px solid #E3A92B;border-radius:14px;padding:10px;
  box-shadow:0 20px 40px rgba(0,0,0,.6)}
Q .ai-dossier .bv-art{height:170px!important}
Q .ai-dossier .bench-view{width:auto!important}
/* Backstage swap button moves to the top-left corner (all arena sizes): it sat
   just right of centre, so a tap meant to read a card swapped it in instead */
body.abc-arena[data-screen="play"] .bench-mini .bm-swap{top:4px;left:4px;bottom:auto;right:auto;width:20px;height:20px;line-height:17px}
/* names too long to fit even at the smallest size wrap to two lines instead of clipping */
.pc-name.pc-wrap{white-space:normal!important;font-size:9px!important;line-height:1.05;text-overflow:clip;
  display:-webkit-box!important;-webkit-box-orient:vertical;-webkit-line-clamp:2;text-align:center}
/* sound buttons: covered the hand on phones -- volume lives in Tune > Audio */
body.abc-arena.abc-phone[data-screen="play"] #audioCtl{display:none}
/* overlays */
Q .feed{top:60px!important;left:12px!important;right:12px!important;width:auto!important}
Q .log{right:8px!important;top:52px!important;width:calc(100% - 16px)!important}
""".replace('\nQ ', '\n' + Q + ' ').replace(',Q ', ',' + Q + ' ')

JS = r"""/* fix_board_layout_v4: portrait screens use the 390x844 phone stage */
function abcPhoneOn(){
  try{ if(localStorage.getItem('abc_layout')==='classic') return false; }catch(e){}
  return window.innerHeight>=window.innerWidth*1.15;
}
"""

s = s.replace(A_CSS, CSS + A_CSS, 1)
s = s.replace(A_JS, JS + A_JS, 1)
# fitNames must beat the arena's !important name sizes, or long names clip ("Augustus M...")
s = s.replace(A_FIT, A_FIT.replace("el.style.fontSize=size+'px';", "el.style.setProperty('font-size',size+'px','important');")
              + "\n    if(el.scrollWidth>el.clientWidth+1){ el.style.removeProperty('font-size'); el.classList.add('pc-wrap'); }   /* fix_board_layout_v4: too long even at the floor -> two lines */", 1)
s = s.replace(A_FIT0, "    el.classList.remove('pc-wrap');   /* fix_board_layout_v4 */\n" + A_FIT0, 1)
s = s.replace(A_ON, "  if(abcPhoneOn()) return true;   /* fix_board_layout_v4 */\n" + A_ON, 1)
s = s.replace(A_HOOK, "  { const ph=abcPhoneOn(); if(document.body.classList.contains('abc-phone')!==ph){ document.body.classList.toggle('abc-phone', ph); fitNames(); } if(ph) document.body.classList.remove('abc-tilt'); }   /* fix_board_layout_v4: refit names after a stage switch */\n" + A_HOOK, 1)
s = s.replace(A_SCALE, A_SCALE + "  if(st && abcPhoneOn()) st.style.setProperty('--abc-k', Math.min(window.innerWidth/390, window.innerHeight/844).toFixed(4));   /* fix_board_layout_v4 */\n", 1)

for need in [MARK, "setProperty('font-size',size+'px','important')", 'function abcPhoneOn', 'if(abcPhoneOn()) return true;', "classList.toggle('abc-phone', ph)", 'window.innerWidth/390']:
    if need not in s:
        sys.exit(f'[fix_board_layout_v4] ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print('[fix_board_layout_v4] Applied.  Backup:', bak)
print('[fix_board_layout_v4] Next: python3 build.py')
