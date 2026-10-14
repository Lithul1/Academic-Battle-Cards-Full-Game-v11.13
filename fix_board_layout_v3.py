#!/usr/bin/env python3
"""fix_board_layout_v3.py -- Tabletop tilt for the Arena board (needs v1 + v2).

Run from the repo root:   python3 fix_board_layout_v3.py
Undo:                     restore src/game.src.html from the .bak this writes.

WHAT CHANGES (arena layout only):
  1. The play surface -- both pages, Backstage rows, Actives + move pickers, Lens
     slots, the spine and scoreboard -- tilts back as ONE plane (default 22deg) with
     a shared vanishing point, like the MTG / Yu-Gi-Oh / Inscryption references.
     Hand, Inspect, piles and action buttons stay flat (the things you read and tap).
  2. Depth cues: cards cast short shadows onto the page, the book shows thickness
     along its front edge, a soft lamp-light pools over the middle of the table.
  3. Tune > Accessibility gets "Tabletop tilt" (on by default, remembered per device
     in localStorage 'abc_tilt'). Off = the flat v2 board, identical to before.

HOW: CSS 3D only. Every tilted piece is a direct child of the fixed 1280x720 stage,
so each one rotates about the same horizontal line (y = 326, the middle of the
spine) via a fixed transform-origin; the stage's `perspective` supplies the shared
vanishing point. Clicks, drag-to-attach and hover go through 3D transforms
natively, and the hit effects (fxAt) measure getBoundingClientRect, which already
returns the tilted card's on-screen box.
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_board_layout_v3 */'
if not os.path.exists(SRC):
    sys.exit('[fix_board_layout_v3] ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit('[fix_board_layout_v3] Already applied -- nothing to do.')
for need, name in [('/* fix_board_layout_v1 */', 'fix_board_layout_v1.py'), ('/* fix_board_layout_v2 */', 'fix_board_layout_v2.py')]:
    if need not in s:
        sys.exit(f'[fix_board_layout_v3] ERROR: run {name} first.')

A_CSS_END = "</style>\n</head>"
A_FIT     = "  if(abcArenaFit()) return;   /* fix_board_layout_v1 */\n"
A_ROW     = "    ${row('Reduce motion &amp; flashing',`<input type=\"checkbox\" data-calm ${(META.calmFx?'checked':'')}>`)}\n"
A_HANDLER = "  if(t.dataset.calm!=null){ META.calmFx=!!t.checked; metaSave(); applyCalmFx(); return; }\n"
A_JSDEF   = "// Uniformly scale the board so both sides + controls always fit the play area (no overlap, no scroll)\nfunction fitBoard(){\n"
for a, l in [(A_CSS_END, 'end of <head> styles'), (A_FIT, 'fitBoard arena hook (v1)'), (A_ROW, 'Tune: reduce-motion row'),
             (A_HANDLER, 'Tune: reduce-motion handler'), (A_JSDEF, 'fitBoard head')]:
    n = s.count(a)
    if n != 1:
        sys.exit(f'[fix_board_layout_v3] ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')

T = 'body.abc-arena.abc-tilt[data-screen="play"]'
# Grid geometry (v1/v2): row tops 0,52,156,306,346,496,600; spine centre y=326.
# transform-origin-y for each piece = 326 - (that piece's own top edge).
CSS = """
/* fix_board_layout_v3 */
/* ===== TABLETOP TILT -- one plane, rotated about y=326 (spine centre) ===== */
T .abc-stage{perspective:1500px;perspective-origin:50% 8%;--abc-tilt:22deg;
  background-image:radial-gradient(ellipse 62% 58% at 50% 46%,rgba(255,214,150,.13),transparent 70%),
                   radial-gradient(rgba(0,0,0,.2) 1px,transparent 1.4px)!important;
  background-size:auto,6px 6px!important}
T .board::before,T .board::after,T .bench,T .opp-side .char,T .you-side .char,T .lenschip,T .phasehud,T .kos.opp,T .kos.you,T .turnbar{
  transform:rotateX(var(--abc-tilt));backface-visibility:hidden}
/* pages (rows 2-3 top 52; rows 5-6 top 346) */
T .board::before{transform-origin:50% 274px}
T .board::after{transform-origin:50% -20px;
  box-shadow:0 0 0 3px #e7d8b6,0 0 0 5px #241f1b,0 9px 0 4px #e7d8b6,0 13px 0 5px #6b4f2a,0 26px 30px rgba(0,0,0,.55),
             inset 0 26px 30px -18px rgba(36,31,27,.55)!important}
/* Backstage rows fill their row exactly (row 2 top 52; row 6 top 496) */
T .bench{align-self:stretch}
T .opp-side .bench{transform-origin:50% 274px}
T .you-side .bench{transform-origin:50% -170px}
/* Actives pinned to the top of their row (row 3 top 156; row 5 top 346) */
T .opp-side .char,T .you-side .char{align-self:start}   /* .side scope: the Inspect dossier is also .char */
T .opp-side .char{transform-origin:50% 170px}
T .you-side .char{transform-origin:50% -20px}
/* Lens: fixed 46px drop into its row so its top edge is known */
T .lenschip{align-self:start;margin-top:46px}
T .opp-side .lenschip{transform-origin:50% 124px}
T .you-side .lenschip{transform-origin:50% -66px}
/* spine pieces (row 4 top 306) */
T .phasehud{transform-origin:50% 20px}
T .kos.opp{align-self:start;margin:8px 0 0 14px;transform-origin:50% 12px}
T .kos.you{align-self:start;margin:8px 0 0 104px;transform-origin:50% 12px}
T .turnbar{align-self:start;margin-top:11px;transform-origin:50% 9px}
/* cards sit ON the page: short cast shadow */
T .bench-mini{box-shadow:0 4px 0 #241f1b,0 9px 12px rgba(0,0,0,.42)}
T .you-side .char{box-shadow:0 0 0 3px #E3A92B,0 6px 0 #241f1b,0 13px 18px rgba(0,0,0,.5)!important}
T .opp-side .char{box-shadow:0 0 0 3px #b5402a,0 6px 0 #241f1b,0 13px 18px rgba(0,0,0,.5)!important}
""".replace('\nT ', '\n' + T + ' ').replace(',T ', ',' + T + ' ')

JS = r"""/* fix_board_layout_v3: tabletop tilt switch (Tune > Accessibility) */
function abcTiltOn(){ try{ return localStorage.getItem('abc_tilt')!=='off'; }catch(e){ return true; } }
function abcTiltSet(on){ try{ localStorage.setItem('abc_tilt', on?'on':'off'); }catch(e){} document.body.classList.toggle('abc-tilt', !!on); }
"""

s = s.replace(A_CSS_END, CSS + A_CSS_END, 1)
s = s.replace(A_JSDEF, JS + A_JSDEF, 1)
s = s.replace(A_FIT, "  document.body.classList.toggle('abc-tilt', abcTiltOn());   /* fix_board_layout_v3 */\n" + A_FIT, 1)
s = s.replace(A_ROW, A_ROW + "    ${row('Tabletop tilt (3D board)',`<input type=\"checkbox\" data-abctilt ${abcTiltOn()?'checked':''}>`)}\n", 1)
s = s.replace(A_HANDLER, "  if(t.dataset.abctilt!=null){ abcTiltSet(!!t.checked); return; }   /* fix_board_layout_v3 */\n" + A_HANDLER, 1)

for need in [MARK, 'function abcTiltOn', 'data-abctilt', "if(t.dataset.abctilt!=null)", "classList.toggle('abc-tilt', abcTiltOn())"]:
    if need not in s:
        sys.exit(f'[fix_board_layout_v3] ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print('[fix_board_layout_v3] Applied.  Backup:', bak)
print('[fix_board_layout_v3] Next: python3 build.py')
