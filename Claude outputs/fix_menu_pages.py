#!/usr/bin/env python3
"""fix_menu_pages.py -- the menu sub-screens as pages of the same book (CSS only).

Run from the repo root:   python3 fix_menu_pages.py
                          python3 build.py
Undo:                     restore src/game.src.html from the .bak this writes.
Needs:                    nothing (made to sit with fix_menu_book / fix_menu_book2).

WHAT IT DOES
  Difficulty, Custom Play, Pagemaster picker, House Rules, PreCon Arena setup, Challenges, Quickstart Guide and
  Tutorial each become one page of the book on the dark table: gutter shadow, stacked page edges, a running head
  (e.g. "Chapter IV - PreCon Arena") and a page number matching the contents page; "Back to menu" sits top left.
  Index-card difficulty / deck choices with a "chosen" tag, a ruled House Rules ledger, teal main actions, ink
  paper buttons, guide text straight on the page. The small logo is hidden on inner pages.
  Literary Scrimmage and the Deck Builder are untouched.

PERFORMANCE
  No images and no JS: these screens stop drawing the full-screen background art and the logo, so leaving the menu
  no longer decodes/paints a large image. Only short hover transitions (off with reduced motion).

HOW IT HOOKS IN
  One CSS block before </head>. No markup or behaviour changes.
"""
import os, sys, shutil, datetime
CSS = r"""
/* fix_menu_pages -- the sub-screens as pages of the same book (CSS only, no images) */
body[data-screen="menu"]{background-color:#2b2620}
body[data-screen="menu"]::before{background:#2b2620 radial-gradient(rgba(0,0,0,.22) 1px,transparent 1.4px) 0 0/6px 6px!important}
body[data-screen="menu"]:not([data-menuscreen="menu"]) #game{max-width:none;padding:18px 12px 30px}
/* the page */
body .title-screen.sub-screen{position:relative;max-width:940px;margin:0 auto 14px;padding:58px 46px 52px;text-align:center;color:#241f1b;
  background:radial-gradient(120% 60% at 50% 0%,transparent 60%,rgba(120,90,40,.08)),linear-gradient(90deg,#e6d8b6 0,#f6eedb 7%) #f6eedb;border-radius:2px 10px 10px 2px;
  box-shadow:0 18px 26px rgba(0,0,0,.4),0 3px 0 #e3d6b8,0 6px 0 #d9ccae,0 7px 0 #f3ead4,0 9px 0 #cfc1a1}
body .title-screen.sub-screen::after{content:var(--ss-pg,"");position:absolute;left:0;right:0;bottom:16px;text-align:center;font:italic 13px/1 var(--body);color:#8a7a5c;pointer-events:none}
body .title-screen.sub-screen>*{position:relative;z-index:1}
/* running head (right) + page number (bottom), set per screen */
body .title-screen.sub-screen::before{content:var(--ss-head,"");position:absolute;z-index:1;top:22px;right:46px;font:400 12px/1 var(--cond);letter-spacing:.32em;text-transform:uppercase;color:#8a6a2a}
body[data-menuscreen="difficulty"]{--ss-head:"Before the first page";--ss-pg:"— 3 —"}
body[data-menuscreen="custom"]{--ss-head:"Chapter II · Custom Play";--ss-pg:"— 7 —"}
body[data-menuscreen="pmpick"]{--ss-head:"Chapter III · Pagemaster";--ss-pg:"— 19 —"}
body[data-menuscreen="tune"]{--ss-head:"House Rules";--ss-pg:"— 8 —"}
body[data-menuscreen="arena"]{--ss-head:"Chapter IV · PreCon Arena";--ss-pg:"— 28 —"}
body[data-menuscreen="challenges"]{--ss-head:"Chapter VI · Challenges";--ss-pg:"— 63 —"}
body[data-menuscreen="guide"]{--ss-head:"Chapter IX · Quickstart Guide";--ss-pg:"— 92 —"}
body[data-menuscreen="tutorial"]{--ss-head:"Chapter X · The Tutorial";--ss-pg:"— 99 —"}
/* back to the menu = "‹ Contents" tab, top left */
body .title-screen.sub-screen .sub-actions [data-do="menu"]{position:absolute;top:14px;left:46px;z-index:2}
body .title-screen.sub-screen [data-do="menu"]{font-size:0!important;background:none!important;border:0!important;box-shadow:none!important;padding:6px 0!important;min-height:0;cursor:pointer}
body .title-screen.sub-screen [data-do="menu"]::after{content:"‹ Back to menu";font:600 italic 15px/1 var(--body);letter-spacing:0;text-transform:none;color:#b5402a;border-bottom:1.5px solid transparent;transition:border-color .2s}
body .title-screen.sub-screen [data-do="menu"]:hover::after{border-color:#b5402a}
body .title-screen.sub-screen .sub-actions{position:static}
body .title-screen.sub-screen .sub-actions:has([data-do="menu"]){margin-top:20px}
/* no logo image on inner pages: the running head carries the place, and one image less to decode */
body .sub-screen .title-logo.sm{display:none}
/* type */
body .sub-screen .sub-h{font:400 30px/1.1 var(--disp);color:#241f1b;margin:4px 0 6px;text-shadow:2px 2px 0 rgba(227,169,43,.45)}
body .sub-screen .sub-h~.sub-h{font-size:19px;text-shadow:none;margin-top:18px}
body .sub-screen .sub-h:first-of-type::after{content:"";display:block;width:180px;height:12px;margin:10px auto 0;
  background:linear-gradient(#8a6a2a,#8a6a2a) left 50%/70px 1px no-repeat,linear-gradient(#8a6a2a,#8a6a2a) right 50%/70px 1px no-repeat,
  radial-gradient(circle,#8a6a2a 0 4px,transparent 4.5px) center/12px 12px no-repeat}
body .sub-screen .title-sub{font:italic 400 16px/1.45 var(--body);letter-spacing:0;text-transform:none;color:#5a4a34;max-width:620px;margin:6px auto 18px}
body .sub-screen h2,body .deck-pick-wrap h2{font:400 18px/1.2 var(--disp);color:#241f1b}
/* buttons */
body .sub-screen .bigbtn{background:#1F6A6A;color:#fff;border:2px solid #0f3535;border-radius:10px;box-shadow:4px 4px 0 #0f3535;transition:transform .15s,box-shadow .15s}
body .sub-screen .bigbtn:hover{transform:translate(-2px,-2px);box-shadow:6px 6px 0 #0f3535}
body .sub-screen .bigbtn:active{transform:translate(2px,2px);box-shadow:1px 1px 0 #0f3535}
body .sub-screen .toolbtn{background:#fffaf0;border:2px solid #241f1b;border-radius:8px;box-shadow:3px 3px 0 #241f1b;transition:transform .15s,box-shadow .15s,background .15s}
body .sub-screen .toolbtn:hover{background:#ffe9b0;transform:translate(-1px,-1px);box-shadow:4px 4px 0 #241f1b}
body .sub-screen .toolbtn.on,body .sub-screen .toolbtn[aria-pressed="true"]{background:#241f1b;color:#ffd45e}
/* difficulty + arena deck choices: index cards */
body .sub-screen .diff-grid{gap:16px}
body .sub-screen .diff-card{position:relative;text-align:left;background:#fffaf0 repeating-linear-gradient(180deg,transparent 0 23px,rgba(70,110,170,.16) 23px 24px);
  background-position:0 34px;border:2px solid #241f1b;border-left:6px solid var(--dac,#241f1b);border-radius:6px 10px 10px 6px;box-shadow:4px 4px 0 #241f1b;transition:transform .15s,box-shadow .15s}
body .sub-screen .diff-card:hover{transform:translate(-2px,-2px) rotate(-.4deg);box-shadow:6px 6px 0 #241f1b}
body .sub-screen .diff-card.on{box-shadow:4px 4px 0 #241f1b,0 0 0 3px #E3A92B}
body .sub-screen .diff-card.on::after{content:"✓ chosen";position:absolute;top:-10px;right:12px;background:#b5402a;color:#fff;font:400 11px/1 var(--cond);letter-spacing:.16em;text-transform:uppercase;padding:5px 8px 4px;border-radius:3px;transform:rotate(2deg);box-shadow:2px 2px 0 rgba(0,0,0,.3)}
body .sub-screen .diff-name{font-family:var(--disp)}
/* custom: shelf + opponent chips + code box */
body .deck-pick-wrap{background:none;border:0;box-shadow:none;padding:0}
body .shelf-plank{background:linear-gradient(#7a4c1d,#4a2c10);box-shadow:0 6px 0 #2a1808,0 12px 16px rgba(0,0,0,.35);border-radius:3px}
body .opp-opt{background:#fffaf0;border:1.5px solid #241f1b;border-radius:999px;box-shadow:2px 2px 0 #241f1b;font-family:var(--body);font-weight:600}
body .opp-opt.on{background:#241f1b;color:#ffd45e}
body .sub-screen .code-input{background:transparent;border:0;border-bottom:2px solid #241f1b;border-radius:0;font:16px var(--body)}
body .sub-screen .code-input:focus{outline:none;border-color:#b5402a;background:rgba(227,169,43,.08)}
/* tune: ruled ledger */
body .sub-screen .tune-panel,body .sub-screen .settings{background:transparent;border:0;box-shadow:none;max-width:560px;margin:0 auto}
body .sub-screen .set-row{border-bottom:1px solid rgba(70,110,170,.22);font-family:var(--body);font-weight:600;letter-spacing:0;text-transform:none;font-size:15px}
body .sub-screen .set-row.set-head{font:400 12px/1 var(--cond);letter-spacing:.3em;text-transform:uppercase;color:#b5402a;border-bottom:1.5px solid #8a6a2a;padding-top:16px}
body .sub-screen .set-row input[type=range]{accent-color:#1F6A6A}
/* pagemaster */
body .pm-slot{background:#fffaf0;border-color:#8a6a2a;border-radius:10px}
body .pm-slot.filled{border-color:#241f1b;box-shadow:4px 4px 0 #241f1b}
body .pm-cmd{background:#fffaf0;border-width:2px;box-shadow:3px 3px 0 #241f1b;transition:transform .15s,box-shadow .15s}
body .pm-cmd:hover{transform:translate(-1px,-1px);box-shadow:4px 4px 0 #241f1b}
body .pm-cmd.sel{box-shadow:3px 3px 0 #1F6A6A,0 0 0 2px #1F6A6A}
body .pm-bookhead{border-bottom:1.5px solid #8a6a2a}
/* guide + tutorial: text on the page itself */
body .sub-screen .rules{background:transparent;border:0;box-shadow:none;text-align:left;max-width:680px;margin:0 auto}
body .sub-screen .rules p{font-size:15.5px;line-height:1.6}
body .sub-screen .rules h2:first-child::first-letter{font-size:1.6em;color:#b5402a}
body .sub-screen .gd-tag{font-size:15px;color:#6b5f52}
/* challenges already sit on their own panel: let the page be that panel */
body .sub-screen.chs .chs-p{border:0;box-shadow:none;background:transparent;padding:0;width:100%}
@media (max-width:760px){
  body[data-screen="menu"]:not([data-menuscreen="menu"]) #game{padding:12px 8px 24px}
  body .title-screen.sub-screen{padding:52px 16px 30px;border-radius:10px;background:#f6eedb}
  body .title-screen.sub-screen::before{right:16px;top:20px;font-size:10px;letter-spacing:.2em;max-width:55%;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  body .title-screen.sub-screen .sub-actions [data-do="menu"]{left:16px}
  body .sub-screen .sub-h{font-size:24px}
  body .sub-screen .set-row{flex-wrap:wrap}
  body .sub-screen .tune-panel{width:auto;max-width:100%;box-sizing:border-box;padding-left:0;padding-right:0}
  body .sub-screen .trk-pick{flex-wrap:wrap;justify-content:flex-end;max-width:100%}
}
@media (prefers-reduced-motion:reduce){body .sub-screen *{transition:none!important}}
"""
SRC=os.path.join('src','game.src.html'); MARK='/* fix_menu_pages */'; TAG='[fix_menu_pages]'
if not os.path.exists(SRC): sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s=open(SRC,encoding='utf-8').read()
if MARK in s: sys.exit(f'{TAG} Already applied -- nothing to do.')
A="</style>\n</head>"
n=s.count(A)
if n!=1: sys.exit(f'{TAG} ERROR: anchor "end of <head> styles" found {n} times (expected 1). Nothing written.')
for need,why in [('class="title-screen sub-screen','sub-screen markup'),('data-menuscreen','menu screen attribute')]:
    if need not in s: sys.exit(f'{TAG} ERROR: prerequisite missing ({why}). Nothing written.')
s=s.replace(A,'\n'+MARK+CSS+A,1)
if MARK not in s or '--ss-head' not in s: sys.exit(f'{TAG} ERROR: post-check failed. Nothing written.')
bak=SRC+'.bak_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); shutil.copyfile(SRC,bak)
open(SRC,'w',encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:',bak); print(f'{TAG} Next: python3 build.py')
