#!/usr/bin/env python3
"""fix_board_layout_v6.py -- Table lighting + Active Bookmarks in Inspect (needs v1-v5).

Run from the repo root:   python3 fix_board_layout_v6.py
Undo:                     restore src/game.src.html from the .bak this writes.

WHAT CHANGES (arena layout only):
  1. TABLE LIGHTING -- the Inscryption-style atmosphere, kept subtle so cards stay
     readable: a warm lamp pool over the middle of the table (under the cards, over
     the pages), a soft vignette that darkens the corners, and a faint static film
     grain. No animation, so it is safe with Reduce motion.
     Tune > Accessibility gets "Table lighting (vignette & grain)", on by default,
     remembered per device (localStorage 'abc_light').
  2. ACTIVE BOOKMARKS -- the in-play Bookmark tray (hidden on phones since v4) now
     shows on phones as a small "ACTIVE ✦ 2" badge on the deck. Tapping it -- or the
     tray on desktop -- lists each active Bookmark with its full text in Inspect
     (the sheet on phones), same pattern as character and Lens details.
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_board_layout_v6 */'
if not os.path.exists(SRC):
    sys.exit('[fix_board_layout_v6] ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit('[fix_board_layout_v6] Already applied -- nothing to do.')
for v in ('v1', 'v2', 'v3', 'v4', 'v5'):
    if f'/* fix_board_layout_{v} */' not in s:
        sys.exit(f'[fix_board_layout_v6] ERROR: run fix_board_layout_{v}.py first.')

A_CSS   = "</style>\n</head>"
A_PIN   = "function abcPinnedHtml(){\n  if(!S) return '';\n"
A_ROW   = "    ${row('Tabletop tilt (3D board)',`<input type=\"checkbox\" data-abctilt ${abcTiltOn()?'checked':''}>`)}\n"
A_HAND  = "  if(t.dataset.abctilt!=null){ abcTiltSet(!!t.checked); return; }   /* fix_board_layout_v3 */\n"
A_HOOK  = "  if(abcArenaFit()) return;   /* fix_board_layout_v1 */\n"
A_JSDEF = "// Uniformly scale the board so both sides + controls always fit the play area (no overlap, no scroll)\nfunction fitBoard(){\n"
for a, l in [(A_CSS, 'end of <head> styles'), (A_PIN, 'abcPinnedHtml (v2)'), (A_ROW, 'Tune: tilt row (v3)'),
             (A_HAND, 'Tune: tilt handler (v3)'), (A_HOOK, 'fitBoard arena hook (v1)'), (A_JSDEF, 'fitBoard head')]:
    n = s.count(a)
    if n != 1:
        sys.exit(f'[fix_board_layout_v6] ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')

P = 'body.abc-arena[data-screen="play"]'
L = 'body.abc-arena.abc-light[data-screen="play"]'
Q = 'body.abc-arena.abc-phone[data-screen="play"]'
GRAIN = ("url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'>"
         "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/>"
         "<feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .55 0'/></filter>"
         "<rect width='100%' height='100%' filter='url(%23n)'/></svg>\")")
CSS = """
/* fix_board_layout_v6 */
/* ===== TABLE LIGHTING: lamp pool (over the pages, under the cards) + vignette & grain (over all) ===== */
L .abc-stage::before{content:'';position:absolute;inset:0;z-index:1;pointer-events:none;
  background:radial-gradient(ellipse 46% 42% at 50% 44%,rgba(255,206,130,.20),rgba(255,206,130,.06) 55%,transparent 75%);
  mix-blend-mode:screen}
L .abc-stage::after{content:'';position:absolute;inset:0;z-index:45;pointer-events:none;
  background:radial-gradient(ellipse 75% 70% at 50% 46%,transparent 55%,rgba(10,6,2,.38) 82%,rgba(10,6,2,.62) 100%),GRAIN;
  background-size:auto,160px 160px;opacity:.95}
Q.abc-light .abc-stage::before{background:radial-gradient(ellipse 60% 34% at 50% 46%,rgba(255,206,130,.18),transparent 75%)}

/* ===== ACTIVE BOOKMARKS ===== */
P .abm-zone{cursor:pointer}
/* phones: the tray becomes a badge on the deck */
Q .piles{position:relative}
/* (selector mirrors v4's hide rule, one step more specific) */
Q .piles>.abm-zone:not(.deckstack):not(.discardpile){display:flex!important;position:absolute;top:-9px;left:-8px;z-index:25;max-width:none;flex-basis:auto;
  background:#E3A92B;border:2px solid #241f1b;border-radius:999px;padding:1px 7px;box-shadow:0 2px 0 #241f1b}
Q .piles .abm-zone .abm-card{display:none}
Q .piles .abm-zone .abm-label{font-size:9px;opacity:1;color:#241f1b;font-family:var(--cond);letter-spacing:.06em;white-space:nowrap}
/* the list in Inspect (column on desktop, sheet on phones) */
P .abc-inspect:has(.ai-abm){align-self:stretch}
Q .abc-inspect:has(.ai-abm){display:flex!important;position:absolute;grid-row:auto!important;grid-column:auto!important;left:12px;right:12px;top:58px;bottom:168px;
  z-index:50;margin:0;background:rgba(29,25,21,.97);border:3px solid #E3A92B;border-radius:14px;padding:10px;box-shadow:0 20px 40px rgba(0,0,0,.6)}
P .ai-abm{display:flex;flex-direction:column;gap:6px}
P .ai-abm-h{font-family:var(--disp);font-size:14px;color:#f3e8cd}
P .ai-abm .hvi-row b{font-size:11px}
P .ai-abm .hvi-row p{font-size:11.5px;line-height:1.35}
P .ai-abm .abc-abm-close{align-self:center;min-height:36px;padding:4px 16px}
""".replace('GRAIN', GRAIN)
for tok, val in (('\nL ', '\n' + L + ' '), ('\nP ', '\n' + P + ' '), (',P ', ',' + P + ' '), ('\nQ ', '\n' + Q + ' '),
                 ('\nQ.abc-light ', '\nbody.abc-arena.abc-phone.abc-light[data-screen="play"] ')):
    CSS = CSS.replace(tok, val)

JS = r"""/* fix_board_layout_v6: table lighting switch + Active Bookmarks in Inspect */
function abcLightOn(){ try{ return localStorage.getItem('abc_light')!=='off'; }catch(e){ return true; } }
function abcLightSet(on){ try{ localStorage.setItem('abc_light', on?'on':'off'); }catch(e){} document.body.classList.toggle('abc-light', !!on); }
function abcAbmHtml(side){
  const P=S&&S[side]; if(!P||!P.activeBm||!P.activeBm.length) return '';
  const rows=P.activeBm.map(function(c){
    const tag=c._tag==='saga'?('Ch. '+roman(c._stage||0)+' / '+((c.stages||[]).length)):(ABM_TAGTXT[c._tag]||'in play');
    return '<div class="hvi-row th"><b>✦ '+c.name+' · '+tag+'</b><p>'+(c.text||'')+'</p></div>'; }).join('');
  return '<div class="ai-abm"><div class="ai-abm-h">✦ Active Bookmarks — '+(side==='you'?'You':'Opponent')+'</div>'+rows
       + '<button class="pcb-close abc-abm-close">Close ✕</button></div>';
}
document.addEventListener('click', function(e){
  if(!S || !document.body.classList.contains('abc-arena')) return;
  const t=e.target && e.target.closest; if(!t) return;
  if(e.target.closest('.abc-abm-close')){ S._abcAbm=null; abcInspectPaint(); e.stopPropagation(); return; }
  const z=e.target.closest('.abm-zone');
  if(z){ S._abcAbm=z.closest('.opp-side')?'opp':'you'; S._benchView=null; S.you._lensOpen=false; S.opp._lensOpen=false;
         abcInsp=null; abcInspectPaint(); e.stopPropagation(); return; }
  if(e.target.closest('[data-benchinfo],[data-do^="lens:"]')) S._abcAbm=null;   /* one pinned subject at a time */
}, true);
"""

s = s.replace(A_CSS, CSS + A_CSS, 1)
s = s.replace(A_JSDEF, JS + A_JSDEF, 1)
s = s.replace(A_PIN, A_PIN + "  if(S._abcAbm){ const h=abcAbmHtml(S._abcAbm); if(h) return h; S._abcAbm=null; }   /* fix_board_layout_v6 */\n", 1)
s = s.replace(A_ROW, A_ROW + "    ${row('Table lighting (vignette &amp; grain)',`<input type=\"checkbox\" data-abclight ${abcLightOn()?'checked':''}>`)}\n", 1)
s = s.replace(A_HAND, A_HAND + "  if(t.dataset.abclight!=null){ abcLightSet(!!t.checked); return; }   /* fix_board_layout_v6 */\n", 1)
s = s.replace(A_HOOK, "  document.body.classList.toggle('abc-light', abcLightOn());   /* fix_board_layout_v6 */\n" + A_HOOK, 1)

for need in [MARK, 'function abcLightOn', 'function abcAbmHtml', 'data-abclight', "if(t.dataset.abclight!=null)", 'if(S._abcAbm){']:
    if need not in s:
        sys.exit(f'[fix_board_layout_v6] ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print('[fix_board_layout_v6] Applied.  Backup:', bak)
print('[fix_board_layout_v6] Next: python3 build.py')
