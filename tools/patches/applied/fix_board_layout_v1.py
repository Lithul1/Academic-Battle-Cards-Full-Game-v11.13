#!/usr/bin/env python3
"""fix_board_layout_v1.py -- Arena board layout, v1 (approved design 2026-10-13).

Run from the repo root:   python3 fix_board_layout_v1.py
Undo:                     restore src/game.src.html from the .bak this writes.

WHAT IT DOES (additive only -- no engine code changes, no existing CSS removed):
  1. CSS block (scoped to body.abc-arena) that lays the existing play-screen
     elements onto one fixed 1280x720 stage: opponent page on top, yours below,
     a phase spine between, desks left/right, hand along the bottom.
     The parts are the ones renderGame already draws -- the wrappers
     (.board/.board-inner/.side/.row/.topbar/.score/.midline) become
     display:contents so their children can sit in the stage grid.
  2. renderGame(): wraps the board markup in <div class="abc-stage"> and adds the
     Inspect panel. Modals and the floating turn bar stay OUTSIDE the stage, so
     they still cover the whole window, unscaled.
  3. fitBoard(): in arena mode, one transform:scale() sizes the whole stage to the
     window (replaces the flex measure/scale loop, which caused the clipping and
     blurry text). Classic mode is untouched and still uses the old path.
  4. Inspect panel: hovering a hand card shows it full-size with its details
     (reuses handCard + handViewInfo). Mouse/trackpad only; touch is unchanged.

WHEN ARENA MODE IS ON: landscape windows of at least ~740x420 (desktop, laptop,
iPad landscape, a Google Sites embed). Portrait and phone-landscape keep the
current layout until the phone stage ships. To force the old board on any device:
  localStorage.setItem('abc_layout','classic')   (remove the key to go back)
"""
import os, re, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_board_layout_v1 */'

if not os.path.exists(SRC):
    sys.exit('[fix_board_layout_v1] ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()

if MARK in s:
    sys.exit('[fix_board_layout_v1] Already applied -- nothing to do.')
if s.count('romeojuliet') < 1:
    sys.exit('[fix_board_layout_v1] ERROR: this does not look like the live source (no romeojuliet).')

def once(anchor, label):
    n = s.count(anchor)
    if n != 1:
        sys.exit(f'[fix_board_layout_v1] ERROR: anchor "{label}" found {n} times (expected 1). Nothing written.')

# ---------------------------------------------------------------- anchors
A_CSS_END   = "\n.gate-foot{ padding:0 16px 16px; display:flex; justify-content:flex-end; }\n</style>"
A_RG_HEAD   = "function renderGame(root){\n  if(!S) return;\n"
A_STAGE_OPEN = "  root.innerHTML=`\n   <div class=\"topbar\">"
A_STAGE_CLOSE = "   <div class=\"log ${S._logopen?'open':''}\">${S.log.map(l=>`<div>${l}</div>`).join('')}</div>\n"
A_FIT_HEAD  = "// Uniformly scale the board so both sides + controls always fit the play area (no overlap, no scroll)\nfunction fitBoard(){\n"
A_DEBUG     = "window.ABC_DEBUG = {\n"

for a, l in [(A_CSS_END, 'end of main <style>'), (A_RG_HEAD, 'renderGame head'),
             (A_STAGE_OPEN, 'renderGame template start'), (A_STAGE_CLOSE, 'renderGame log line'),
             (A_FIT_HEAD, 'fitBoard head'), (A_DEBUG, 'ABC_DEBUG')]:
    once(a, l)

# ---------------------------------------------------------------- CSS
P = 'body.abc-arena[data-screen="play"]'
CSS = r"""
/* fix_board_layout_v1 */
/* ===== ARENA BOARD LAYOUT v1 -- one fixed 1280x720 stage, scaled as a whole =====
   Every rule is scoped to body.abc-arena, so classic mode is unaffected.
   !important is used only where an older viewport media query also uses it. */
.abc-inspect{display:none}
P{background-color:#2b2620;background-image:radial-gradient(rgba(0,0,0,.2) 1px,transparent 1.4px);background-size:6px 6px}
P #game{max-width:none!important;margin:0!important;padding:0!important}
P .abc-stage{
  position:fixed;left:50%;top:50%;width:1280px;height:720px;z-index:5;
  transform:translate(-50%,-50%) scale(var(--abc-k,1));transform-origin:50% 50%;
  display:grid;
  grid-template-columns:16px 208px 16px 190px 420px 190px 16px 208px 16px;
  grid-template-rows:52px 104px 150px 40px 150px 104px 120px;
  overflow:hidden;
  background-color:#2b2620;
  background-image:radial-gradient(rgba(0,0,0,.2) 1px,transparent 1.4px);background-size:6px 6px;
}
/* wrappers dissolve so their children can be placed on the stage grid */
P .board,P .board-inner,P .side,P .row,P .topbar,P .score,P .midline{display:contents!important}
P .side::before,P .side::after,P .board-inner::before,P .board-inner::after,P .brand{display:none!important}

/* ---- the two pages of the book (the existing per-deck arena art) ---- */
P .board::before,P .board::after{
  display:block!important;content:''!important;position:relative!important;inset:auto!important;
  left:auto!important;right:auto!important;top:auto!important;bottom:auto!important;height:auto!important;
  grid-column:4/7;z-index:0;pointer-events:none;
  -webkit-mask-image:none!important;mask-image:none!important;
  background-color:#dcc29b;background-repeat:repeat,no-repeat;background-size:auto,cover;
  border:3px solid #241f1b;
}
P .board::before{grid-row:2/4;border-bottom:0;border-radius:6px 6px 0 0;background-color:#dcc29b;
  box-shadow:0 0 0 3px #e7d8b6,0 0 0 5px #241f1b,inset 0 -26px 30px -18px rgba(36,31,27,.55)}
P .board::after{grid-row:5/7;border-top:0;border-radius:0 0 6px 6px;background-color:#d4d0b4;
  box-shadow:0 0 0 3px #e7d8b6,0 0 0 5px #241f1b,inset 0 26px 30px -18px rgba(36,31,27,.55)}
/* everything that sits on a page is raised above it */
P .bench,P .char,P .piles,P .lenschip,P .side-meta,P .kos,P .phasehud,P .actions,P .tb-btns,P .hand-wrap,P .abc-inspect{position:relative;z-index:2}
P .side[data-arena]>*{z-index:2}

/* ---- spine: phase tracker (+ turn timer when it sits on the board) ---- */
P .phasehud{grid-column:4/7;grid-row:4;display:flex;justify-content:center;align-items:center;gap:4px;
  background:#241f1b;border-top:2px solid #E3A92B;border-bottom:2px solid #E3A92B;margin:0}
P .phasehud .ph{background:none;border:0;box-shadow:none;color:#8a7e6b;font-size:12px;padding:4px 12px}
P .phasehud .ph.on{background:#E3A92B;color:#241f1b;border-radius:999px;box-shadow:none}
P .phasehud .ph-arrow{color:#5a4f40;font-size:14px}
P .turnbar{grid-column:6;grid-row:4;align-self:center;justify-self:end;width:150px;margin-right:12px;z-index:3;position:relative}

/* ---- left desk: plates + Inspect ---- */
P .opp-side .side-meta{grid-column:2;grid-row:1;align-self:end}
P .kos.opp{grid-column:2;grid-row:2;align-self:start;justify-self:start;margin-top:6px}
P .kos.you{grid-column:2;grid-row:6;align-self:end;justify-self:start;margin-bottom:6px}
P .you-side .side-meta{grid-column:2;grid-row:7;align-self:start}
P .side-meta{display:block!important;font-family:var(--disp);font-size:14px!important;letter-spacing:.2px;line-height:1.2;
  text-transform:none;color:#f3e8cd!important;opacity:1!important;text-align:left!important;text-shadow:none!important;padding:0;margin:0!important}
P .kos{font-size:12px;padding:4px 10px}
P .abc-inspect{display:flex;flex-direction:column;gap:6px;grid-column:2;grid-row:3/6;align-self:center;max-height:100%;overflow:hidden;pointer-events:none}
P .abc-inspect .ai-lbl{font-family:var(--cond);font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#E3A92B}
P .abc-inspect .ai-empty{font-family:var(--cond);font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#8a7e6b;
  border:2px dashed #4a4136;border-radius:10px;padding:22px 14px;text-align:center;line-height:1.5}
P .abc-inspect .ai-card{display:block}
P .abc-inspect .hc{position:relative!important;transform:none!important;margin:0!important;
  width:200px!important;min-width:0!important;height:auto!important;min-height:0;max-height:270px;
  padding:9px!important;font-size:12.5px!important;opacity:1!important;filter:none!important;
  box-shadow:0 0 0 3px #E3A92B,5px 5px 0 #000!important;overflow:hidden}
P .abc-inspect .hc-q,P .abc-inspect .hc-text{font-size:12px!important;line-height:1.3;-webkit-line-clamp:9!important}
P .abc-inspect .hc-name{font-size:14px!important}
P .abc-inspect .hc-top,P .abc-inspect .hc-foot{font-size:10px!important}
P .abc-inspect .hv-info{width:200px;gap:5px}
P .abc-inspect .hvi-row{padding:5px 8px}
P .abc-inspect .hvi-row p{font-size:11px;line-height:1.3}

/* ---- Backstage rows ---- */
P .bench{grid-column:4/7;display:flex!important;flex-direction:row!important;justify-content:center;align-items:center;
  gap:14px!important;width:auto!important;flex:none!important;margin:0}
P .opp-side .bench{grid-row:2}
P .you-side .bench{grid-row:6}
P .bench-mini{color:var(--ink);width:66px!important;height:90px!important;padding:3px!important;display:flex;flex-direction:column;
  border-radius:8px!important;border:3px solid #241f1b;box-shadow:3px 3px 0 #241f1b;overflow:visible}
P .bench-mini .bm-init{flex:1;height:auto!important;width:100%!important;border-radius:5px}
P .bench-mini .bm-hp{display:block!important;height:5px;margin:3px 0 2px}
P .bench-mini .bm-name{display:block!important;font-size:9px;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
P .bm-hpc{display:grid!important;position:absolute;top:-8px;right:-8px;width:22px;height:22px;border-radius:50%;
  border:2px solid var(--ink);color:#fff;font-family:var(--disp);font-size:9px;place-items:center;z-index:3}
P .bm-hpc.g{background:#3aa055} P .bm-hpc.y{background:#e0a92b} P .bm-hpc.r{background:#c0392b} P .bm-hpc.k{background:#6b6b6b}
P .bm-stc{display:grid!important;position:absolute;bottom:18px;right:-8px;width:20px;height:20px;border-radius:50%;
  background:#e07b28;border:2px solid var(--ink);color:#fff;font-family:var(--disp);font-size:8px;place-items:center;z-index:3;cursor:pointer}
P .bench-mini.drop-zone::after{content:"";position:absolute;inset:-8px;border-radius:12px}

/* ---- Active cards + move picker beside them ---- */
P .char{grid-column:5;justify-self:center;align-self:center;width:150px!important;flex:none!important;
  padding:5px!important;margin:0!important;border-radius:10px}
P .opp-side .char{grid-row:3}
P .you-side .char{grid-row:5}
P .char .pc-plate{margin-bottom:3px}
P .char .pc-name{font-size:11px!important;padding:1px 4px}
P .char .pc-hp{min-width:46px}
P .char .pc-hp b{font-size:10px!important;padding:1px 4px}
P .char .pc-art{height:84px!important}
P .char .pc-art .mono{font-size:30px}
P .char .pips{margin-bottom:0;min-height:16px}
P .char .pc-moves{position:absolute;left:calc(100% + 14px);top:0;width:188px;margin:0;gap:5px;
  background:#241f1b;border:3px solid #241f1b;border-radius:10px;padding:6px;box-shadow:4px 4px 0 rgba(0,0,0,.35)}
P .char .pc-move{min-height:38px}
P .you-side .char{box-shadow:0 0 0 3px #E3A92B,4px 4px 0 #241f1b}
P .opp-side .char{box-shadow:0 0 0 3px #b5402a,4px 4px 0 #241f1b}
P .char.boss .pc-art{height:84px!important}

/* ---- Lens slot, left of each Active ---- */
P .lenschip{grid-column:4;justify-self:center;align-self:center;width:170px;max-width:170px!important;margin:0;font-size:11px}
P .opp-side .lenschip{grid-row:3}
P .you-side .lenschip{grid-row:5}
P .lenschip.empty{min-height:62px;background:transparent;border:2px dashed rgba(36,31,27,.45);border-left-width:2px;opacity:1}
P .lenschip.empty .lc-none{color:rgba(36,31,27,.7);font-family:var(--cond);letter-spacing:1px;text-transform:uppercase;font-size:10px}

/* ---- right desk: menu, piles (deck left of discard), actions ---- */
P .tb-btns{grid-column:8;grid-row:1;align-self:center;justify-self:start}
P .tb-btns button{min-height:40px}
P .logtoggle{position:static!important;grid-column:8;grid-row:1;align-self:center;justify-self:end;transform:none!important;z-index:3;min-height:40px}
P .log{position:absolute!important;right:16px!important;top:56px!important;width:260px;max-height:300px;z-index:40}
P .piles{grid-column:8;display:flex!important;flex-direction:row!important;flex-wrap:wrap;justify-content:flex-end;
  align-items:flex-end;gap:12px!important;width:auto!important;flex:none!important;margin:0}
P .opp-side .piles{grid-row:2/4;align-self:start;margin-top:16px}
P .you-side .piles{grid-row:5/7;align-self:end;margin-bottom:4px}
P .piles .deckstack{order:1;width:64px!important;height:88px!important}
P .piles .discardpile{order:2;width:64px!important;height:88px!important}
P .piles .abm-zone{order:3;flex-basis:100%}
P .piles>*:not(.deckstack):not(.discardpile):not(.abm-zone){order:4}
P .actions{grid-column:8;grid-row:7;display:flex;flex-direction:column;align-items:stretch;justify-content:center;gap:6px;min-height:0;margin:0}
P .actions .bigbtn{width:100%;font-size:20px;padding:14px 10px;border-width:4px}
P .actions .toolbtn{width:100%}
P .actions .hint{color:#cfc3a8;font-size:10px;text-align:center;line-height:1.3}
P .actions .thinking{text-align:center}

/* ---- hand: fans along the bottom, peeks off the stage edge ---- */
P .hand-wrap{position:relative!important;left:auto!important;right:auto!important;bottom:auto!important;top:auto!important;
  grid-column:3/8;grid-row:7;align-self:start;display:block!important;background:none!important;padding:0!important;z-index:30}
P .hand-label,P .hand-toggle{display:none!important}
P .hand-wrap .hand,P .hand-wrap.open .hand{display:flex!important;max-height:none;overflow:visible!important;
  justify-content:center;align-items:flex-start;padding:8px 0 0!important;background:none;border-top:0;box-shadow:none}
P .hand{--card-h:140px;--fan-step:4deg;--fan-arc:1.6px;--fan-lift:36px;--fan-scale:1.1;--tuck-frac:0.09}
P .hand .hc{width:var(--card-w)!important;min-width:var(--card-w)!important;height:var(--card-h)!important;
  padding:7px!important;font-size:11px!important}
P .hc-q,P .hc-text{font-size:11px;line-height:1.25}
P .hc-name{font-size:12px}
P .hc-top,P .hc-foot{font-size:9px}

/* ---- transient overlays now live inside the stage ---- */
P .feed{position:absolute!important;left:auto!important;right:16px!important;top:330px!important;bottom:auto!important;
  transform:none!important;width:208px!important}
"""

CSS = re.sub(r'(^|(?<=[,\s]))P(?=[ {])', P, CSS, flags=re.M)

# ---------------------------------------------------------------- JS
JS_FUNCS = r"""/* fix_board_layout_v1: Arena layout -- one fixed 1280x720 stage, scaled as a whole */
function abcArenaOn(){
  try{ if(localStorage.getItem('abc_layout')==='classic') return false; }catch(e){}
  const w=window.innerWidth, h=window.innerHeight;
  return w>=h*1.15 && Math.min(w/1280, h/720)>=0.58;     /* landscape and big enough to read */
}
function abcLayoutSync(){ const on=!!(S && abcArenaOn()); document.body.classList.toggle('abc-arena', on); return on; }
/* true = arena handled the fit; false = fall through to the classic fitBoard */
function abcArenaFit(){
  const want=!!(S && APP.screen==='play' && abcArenaOn()), has=document.body.classList.contains('abc-arena');
  if(want!==has){ render(); return true; }               /* crossed the threshold (resize/rotate): rebuild once */
  if(!has) return false;
  const st=document.querySelector('.abc-stage');
  if(st) st.style.setProperty('--abc-k', Math.min(window.innerWidth/1280, window.innerHeight/720).toFixed(4));
  return true;
}
let abcInsp=null;                                         /* the hand card under the pointer */
function abcInspectHtml(){
  const c=abcInsp, i=(c&&S)?S.you.hand.indexOf(c):-1;
  if(i<0) return '<div class="ai-empty">Hover a card in your hand to read it here</div>';
  const nw=c._new; let card='', info='';
  try{ card=handCard(c,i); }catch(e){}
  c._new=nw;                                              /* never steal the hand card's deal-in */
  try{ info=handViewInfo(c)||''; }catch(e){}
  return '<div class="ai-card">'+card+'</div>'+info;
}
function abcInspectPanel(){ return '<div class="abc-inspect" aria-live="polite"><div class="ai-lbl">Inspect</div><div class="ai-body">'+abcInspectHtml()+'</div></div>'; }
document.addEventListener('mouseover', function(e){
  if(!S || !document.body.classList.contains('abc-arena')) return;
  const hc=e.target && e.target.closest && e.target.closest('.hand .hc[data-idx]'); if(!hc) return;
  const c=S.you.hand[+hc.dataset.idx]; if(!c || c===abcInsp) return;
  abcInsp=c; const b=document.querySelector('.abc-inspect .ai-body'); if(b) b.innerHTML=abcInspectHtml();
});
"""

# ---------------------------------------------------------------- apply
s = s.replace(A_CSS_END, A_CSS_END.replace("\n</style>", "\n" + CSS + "</style>"), 1)
s = s.replace(A_RG_HEAD, A_RG_HEAD + "  abcLayoutSync();   /* fix_board_layout_v1 */\n", 1)
s = s.replace(A_STAGE_OPEN, "  root.innerHTML=`<div class=\"abc-stage\">${abcInspectPanel()}\n   <div class=\"topbar\">", 1)
s = s.replace(A_STAGE_CLOSE, A_STAGE_CLOSE + "   </div>\n", 1)
s = s.replace(A_FIT_HEAD, JS_FUNCS + A_FIT_HEAD + "  if(abcArenaFit()) return;   /* fix_board_layout_v1 */\n", 1)
s = s.replace(A_DEBUG, A_DEBUG + "  abcArenaOn, abcArenaFit, abcLayoutSync, abcInspectHtml,   /* fix_board_layout_v1 */\n", 1)

# ---------------------------------------------------------------- verify + write
for need in [MARK, 'class="abc-stage"', 'function abcArenaFit', 'if(abcArenaFit()) return;', 'abcLayoutSync();']:
    if need not in s:
        sys.exit(f'[fix_board_layout_v1] ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print('[fix_board_layout_v1] Applied.')
print('[fix_board_layout_v1] Backup:', bak)
print('[fix_board_layout_v1] Next: python3 build.py   (or  python3 build.py --stub  to test without assets)')
