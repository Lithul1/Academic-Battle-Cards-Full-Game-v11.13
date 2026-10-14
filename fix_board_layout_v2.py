#!/usr/bin/env python3
"""fix_board_layout_v2.py -- Arena board, readability pass (needs fix_board_layout_v1).

Run from the repo root:   python3 fix_board_layout_v2.py
Undo:                     restore src/game.src.html from the .bak this writes.

WHAT CHANGES (arena layout only, except item 4):
  1. Inspect is the one reading zone. The 'i' on an Active, tapping a Backstage
     card, and the Lens arrow now open their details IN the Inspect column instead
     of a tall pop-up. Hovering a hand card still previews it; move off the hand and
     the pinned details come back. Close / Offstage / Fulfil thesis work from there.
  2. Lens sits compact on the board (portrait, name, thesis button) -- no more tall
     text column running over the spine.
  3. Clipping and size: wider Active (168px) so names and HP fit, move names wrap to
     two clean lines instead of being cut, nothing on the stage below 10px.
     The KO tally moves onto the spine (left end) as a scoreboard, which frees the
     whole left column for Inspect.
  4. Backstage name labels skip "The / A / An" and use a surname for titled names
     ("The Lion" -> LION, "Professor Moriarty" -> MORIARTY). This is the one change
     that also shows in the classic layout.
  5. Right desk re-spaced: deck stacks clear the Tune/Menu row, and the action
     buttons have their own space below your piles.
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_board_layout_v2 */'
if not os.path.exists(SRC):
    sys.exit('[fix_board_layout_v2] ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit('[fix_board_layout_v2] Already applied -- nothing to do.')
if '/* fix_board_layout_v1 */' not in s:
    sys.exit('[fix_board_layout_v2] ERROR: run fix_board_layout_v1.py first.')

A_CSS_END  = "</style>\n</head>"
A_MODAL    = "   ${S._benchView?benchInfoModal():''}\n"
A_BMNAME   = "<span class=\"bm-name\">${c.name.split(' ')[0]}</span>"
A_INSP     = "function abcInspectHtml(){\n"
A_FIT      = "// Uniformly scale the board so both sides + controls always fit the play area (no overlap, no scroll)\nfunction fitBoard(){\n"
for a, l in [(A_CSS_END, 'end of <head> styles'), (A_MODAL, 'bench modal slot'), (A_BMNAME, 'bench name label'),
             (A_INSP, 'abcInspectHtml (v1)'), (A_FIT, 'fitBoard head')]:
    n = s.count(a)
    if n != 1:
        sys.exit(f'[fix_board_layout_v2] ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')

P = 'body.abc-arena[data-screen="play"]'
CSS = """
/* fix_board_layout_v2 */
/* ---- Inspect: the one reading zone (hand preview, character dossier, lens) ---- */
P .abc-inspect{pointer-events:auto;overflow-y:auto;overflow-x:hidden;scrollbar-width:thin;scrollbar-color:#5a4f40 transparent;padding-right:2px}
P .abc-inspect .ai-card,P .abc-inspect .ai-card *{pointer-events:none}
P .abc-inspect{grid-row:2/7;margin:8px 0}
P .abc-inspect:has(.ai-dossier),P .abc-inspect:has(.ai-lens){align-self:stretch}
/* KO tally moves to the spine as a scoreboard; frees the left desk for Inspect */
P .kos{grid-column:4/6;grid-row:4;align-self:center;justify-self:start;margin:0;z-index:3;font-size:12px!important;padding:3px 10px}
P .kos.opp{grid-column:4/6;grid-row:4;align-self:center;justify-self:start;margin:0 0 0 14px}
P .kos.you{grid-column:4/6;grid-row:4;align-self:center;justify-self:start;margin:0 0 0 104px}
P .opp-side .side-meta{grid-row:1;align-self:center}
P .you-side .side-meta{grid-row:7;align-self:center}
P .ai-dossier .bench-view{width:auto!important;max-height:none!important;overflow:visible!important;margin:0;
  padding:8px!important;border-radius:12px;display:flex;flex-direction:column;gap:6px;box-shadow:0 0 0 3px #E3A92B,5px 5px 0 #000}
P .ai-dossier .pc-plate{margin:0}
P .ai-dossier .pc-name{font-size:13px!important;white-space:normal;line-height:1.1}
P .ai-dossier .pc-hp b{font-size:11px!important}
P .ai-dossier .bv-art{height:104px!important;border-radius:8px;overflow:hidden}
P .ai-dossier .bv-art img{width:100%;height:100%;object-fit:cover}
P .ai-dossier .arch{margin:0}
P .ai-dossier .bv-passive,P .ai-dossier .bv-move{padding:6px 8px;border-radius:8px}
P .ai-dossier .bv-ph,P .ai-dossier .bv-h b{font-size:12px;line-height:1.15}
P .ai-dossier p{font-size:11.5px;line-height:1.35;margin:3px 0 0}
P .ai-dossier .bv-chg{font-size:11px}
P .ai-dossier .bigbtn{font-size:13px;padding:8px 10px;width:100%}
P .ai-dossier .pcb-close{align-self:center;min-height:36px;padding:4px 16px}
P .ai-lens .lenschip{width:auto!important;max-width:none!important;flex-direction:column;align-items:stretch;gap:6px;padding:9px}
P .ai-lens .lenschip .lc-port{width:100%;height:96px;flex-basis:auto}
P .ai-lens .lenschip .lc-port img{width:100%;height:100%;object-fit:cover}
P .ai-lens .lenschip .lc-nm{font-size:14px;white-space:normal}
P .ai-lens .lenschip .lc-pf,P .ai-lens .lenschip .lc-th{display:block!important;font-size:11.5px;line-height:1.35}
P .ai-lens .lenschip .lc-toggle{position:absolute;top:6px;right:6px}

/* ---- Lens on the board: always compact ---- */
P .lenschip{flex-direction:row;align-items:center;padding:5px 7px;gap:7px;min-height:58px}
P .lenschip .lc-pf,P .lenschip .lc-th{display:none!important}
P .lenschip .lc-port{width:40px;height:40px;flex:0 0 40px}
P .lenschip .lc-body{min-width:0;display:flex;flex-direction:column;gap:4px}
P .lenschip .lc-nm{font-size:12px;line-height:1.1;white-space:normal}
P .lenschip .lc-thesis{font-size:10px;padding:3px 7px;margin:0}

/* ---- Active cards: room for names and HP; move names wrap, never cut ---- */
P .char{width:168px!important}
P .char .pc-art{height:84px!important}
P .char .pc-name{font-size:12px!important}
P .char .pc-hp{min-width:56px}
P .char .pc-hp b{font-size:11px!important}
P .char .pc-moves{width:196px;left:calc(100% + 12px)}
P .char .pc-move{min-height:44px;align-items:center}
P .char .pc-mn{white-space:normal!important;overflow:hidden;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;
  font-size:12.5px;line-height:1.1;text-overflow:clip}
P .char .pc-mc{font-size:10px}

/* ---- minimum sizes ---- */
P .bench-mini .bm-name{font-size:10px!important;letter-spacing:.4px}
P .actions .hint{font-size:11px!important}

/* ---- right desk spacing ---- */
P .opp-side .piles{grid-row:2/4;align-self:start;margin-top:34px}
P .you-side .piles{grid-row:5;align-self:start;margin:6px 0 0}
P .actions{grid-row:6/8;justify-content:flex-end;padding-bottom:14px}
P .actions .bigbtn{font-size:17px;line-height:1.15;padding:12px 10px}
""".replace('\nP ', '\n' + P + ' ').replace(',P ', ',' + P + ' ')

JS = r"""/* fix_board_layout_v2: details open in the Inspect column (arena layout) */
function abcShortName(n){
  let w=String(n||'').trim().split(/\s+/);
  if(w.length>1 && /^(the|a|an)$/i.test(w[0])) w=w.slice(1);
  const full=w.join(' ');
  if(full.length<=9) return full;
  if(w.length>1 && /^(professor|inspector|doctor|dr\.?|mr\.?|mrs\.?|miss|lady|lord|king|queen|prince|princess|sir|friar|father|general|captain|aunt|uncle|count|duke|old)$/i.test(w[0])) return w[w.length-1];
  return w[0];
}
function abcPinnedHtml(){
  if(!S) return '';
  if(S._benchView){
    const h=String(benchInfoModal()||'').replace(/^\s*<div class="modal-bg">/,'').replace(/<\/div>\s*$/,'');
    if(h) return '<div class="ai-dossier">'+h+'</div>';
  }
  for(const side of ['you','opp']){ const P=S[side]; if(P && P._lensOpen && P.crit) return '<div class="ai-lens">'+critChip(P,side)+'</div>'; }
  return '';
}
function abcInspectPaint(){ const b=document.querySelector('.abc-inspect .ai-body'); if(b) b.innerHTML=abcInspectHtml(); }
/* one pinned subject at a time: opening a dossier closes an open lens, and vice versa */
document.addEventListener('click', function(e){
  if(!S || !document.body.classList.contains('abc-arena')) return;
  const t=e.target && e.target.closest && e.target.closest('[data-benchinfo],[data-do^="lens:"]'); if(!t) return;
  abcInsp=null;
  if(t.dataset.benchinfo){ S.you._lensOpen=false; S.opp._lensOpen=false; }
  else { S._benchView=null; const other=t.dataset.do==='lens:you'?S.opp:S.you; other._lensOpen=false; }
}, true);
/* leaving the hand drops the hover preview and brings the pinned details back */
document.addEventListener('mouseout', function(e){
  if(!abcInsp || !document.body.classList.contains('abc-arena')) return;
  const from=e.target && e.target.closest && e.target.closest('.hand'); if(!from) return;
  if(e.relatedTarget && from.contains(e.relatedTarget)) return;
  abcInsp=null; abcInspectPaint();
});
"""

s = s.replace(A_CSS_END, CSS + A_CSS_END, 1)
s = s.replace(A_MODAL, "   ${(S._benchView&&!document.body.classList.contains('abc-arena'))?benchInfoModal():''}   " + "\n", 1)
s = s.replace(A_BMNAME, "<span class=\"bm-name\">${abcShortName(c.name)}</span>", 1)
s = s.replace(A_INSP, A_INSP + "  if(!abcInsp){ const pin=abcPinnedHtml(); if(pin) return pin; }   /* fix_board_layout_v2 */\n", 1)
s = s.replace(A_FIT, JS + A_FIT, 1)

for need in [MARK, 'function abcPinnedHtml', 'abcShortName(c.name)', "classList.contains('abc-arena'))?benchInfoModal()"]:
    if need not in s:
        sys.exit(f'[fix_board_layout_v2] ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print('[fix_board_layout_v2] Applied.  Backup:', bak)
print('[fix_board_layout_v2] Next: python3 build.py')
