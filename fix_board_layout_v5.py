#!/usr/bin/env python3
"""fix_board_layout_v5.py -- Small-screen / embed fixes for the Arena board (needs v1-v4).

Run from the repo root:   python3 fix_board_layout_v5.py
Undo:                     restore src/game.src.html from the .bak this writes.

THE BUG (seen in the Google Sites embed on iPhone): the old phone stylesheet is
written as viewport media queries (max-width:560px, max-height:560/640/700px).
Inside a Google Sites iframe the viewport is the IFRAME -- about 296x487 on an
iPhone -- so those old rules switched on and reached into the new fixed stage:
  * max-width:560px turned .board::after into the "swipe between boards" hint:
    translateX(-50%) + 70% opacity. That shoved YOUR page half off the stage,
    which is why your side looked cut off on the left and half-empty on the right.
  * max-height:560px hid the empty Lens slot.
The stage is a fixed size, so viewport rules have no business inside it. This
patch pins those properties back for both stages (desktop embeds shorter than
~700px were exposed to the same rules).

ALSO:
  * Phone hand: cards now overlap just enough to fit all of them inside the stage
    (it was fanning wider than the 390px stage and getting clipped at both edges).
  * Phone: a touched hand card only lifts slightly, and the action buttons sit above
    the hand, so a lifted card can no longer cover Draw / Done / End turn.
  * Move names break between words (or hyphenate) instead of mid-word
    ("Affectionat / e Plea").
  * Phone HP badge keeps its width when the name wraps to two lines ("00/90").
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_board_layout_v5 */'
if not os.path.exists(SRC):
    sys.exit('[fix_board_layout_v5] ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit('[fix_board_layout_v5] Already applied -- nothing to do.')
for v in ('v1', 'v2', 'v3', 'v4'):
    if f'/* fix_board_layout_{v} */' not in s:
        sys.exit(f'[fix_board_layout_v5] ERROR: run fix_board_layout_{v}.py first.')

A_CSS = "</style>\n</head>"
if s.count(A_CSS) != 1:
    sys.exit('[fix_board_layout_v5] ERROR: anchor "end of <head> styles" not unique. Nothing written.')

P = 'body.abc-arena[data-screen="play"]'
Q = 'body.abc-arena.abc-phone[data-screen="play"]'
CSS = """
/* fix_board_layout_v5 */
/* ---- shield the fixed stage from the old viewport media queries ---- */
/* max-width:560px restyled .board::after as a fixed 'swipe' hint (translateX(-50%), 70% opacity) */
P .board::before,P .board::after{transform:none;opacity:1;font-size:0;letter-spacing:0;color:transparent}
/* max-height:560px hid the empty Lens slot */
P .lenschip.empty{display:flex!important}
/* ---- move names: break between words, hyphenate long ones ---- */
P .side .char .pc-mn{word-break:normal!important;overflow-wrap:normal!important;-webkit-hyphens:auto;hyphens:auto}
/* ---- phone: the whole hand fits inside the 390px stage ---- */
Q .hand{--card-h:118px;--fan-step:3deg;--fan-lift:6px;--fan-scale:1.04}
/* a lifted (touched) hand card must never cover the action buttons */
Q .actions{z-index:31}
Q .hand .hc{margin-left:calc(min(0px, (330px - var(--n,1) * var(--card-w)) / max(1, var(--n,1) - 1)))!important}
Q .hand .hc:first-child{margin-left:0!important}
Q .side .char .pc-mn{font-size:10px}
Q .side .char .pc-hp{min-width:46px;flex-shrink:0}
""".replace('\nP ', '\n' + P + ' ').replace(',P ', ',' + P + ' ').replace('\nQ ', '\n' + Q + ' ').replace(',Q ', ',' + Q + ' ')

s = s.replace(A_CSS, CSS + A_CSS, 1)
if MARK not in s:
    sys.exit('[fix_board_layout_v5] ERROR: post-check failed. Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print('[fix_board_layout_v5] Applied.  Backup:', bak)
print('[fix_board_layout_v5] Next: python3 build.py')
