#!/usr/bin/env python3
"""fix_card_play_anim3.py -- Card-play animation reaches EVERY card (needs fix_card_play_anim + anim2).

Run from the repo root:   python3 fix_card_play_anim3.py
Undo:                     restore src/game.src.html from the .bak this writes.

THE BUG: ABCs played through a trivia question (correct or wrong) never showed the
animation. The flight copy was created correctly, but it lived INSIDE the board, and
answering a question repaints the board twice (once in attach(), once more to take the
question panel down). The second repaint rebuilt the board and deleted the flying card
a few milliseconds after it launched. Characters and Bookmarks repaint once, which is
why they worked. Anything else that repaints mid-flight had the same problem.

THE FIX:
  * Flights now live in their own layer on the page (#abcFlyLayer), sized and scaled
    exactly like the board, but outside it -- so repaints can no longer remove them.
  * Act cards (character evolutions) now fly to the character that evolved, Active or
    Backstage, instead of always the Active.
Covered after this patch: ABC charged (after a correct answer), ABC discarded (wrong
answer), free / Cliffnotes attaches, shed cards, Bookmarks, Lenses, characters, and
evolutions.
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_card_play_anim3 */'
if not os.path.exists(SRC):
    sys.exit('[fix_card_play_anim3] ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit('[fix_card_play_anim3] Already applied -- nothing to do.')
for m, n in [('/* fix_card_play_anim */', 'fix_card_play_anim.py'), ('/* fix_card_play_anim2 */', 'fix_card_play_anim2.py')]:
    if m not in s:
        sys.exit(f'[fix_card_play_anim3] ERROR: run {n} first.')

A_HOST = "  const host=st||document.body, k=st?(parseFloat(st.style.getPropertyValue('--abc-k'))||1):1;\n"
A_ACT  = "  if(card.cat==='char' || card.cat==='act') return q('.char.you');\n"
A_CSS  = "</style>\n</head>"
for a, l in [(A_HOST, 'flight host line'), (A_ACT, 'char/act target line'), (A_CSS, 'end of <head> styles')]:
    if s.count(a) != 1:
        sys.exit(f'[fix_card_play_anim3] ERROR: anchor "{l}" found {s.count(a)} times (expected 1). Nothing written.')

NEW_HOST = """  /* fix_card_play_anim3 */ /* flights live in a layer OUTSIDE the board, so a repaint mid-flight cannot delete them */
  let host=document.body, k=1;
  if(st){
    k=parseFloat(st.style.getPropertyValue('--abc-k'))||1;
    host=document.getElementById('abcFlyLayer');
    if(!host){ host=document.createElement('div'); host.id='abcFlyLayer'; document.body.appendChild(host); }
    host.style.width=st.offsetWidth+'px'; host.style.height=st.offsetHeight+'px';
    host.style.transform='translate(-50%,-50%) scale('+k+')';
  }
"""
NEW_ACT = """  if(card.cat==='act'){   /* evolution: the character that evolved, wherever it sits */
    const ev=p.team.find(function(ch){ return (ch._actCards||[]).indexOf(card)>=0; });
    if(ev) return ev===active(p) ? q('.char.you') : (q('.bench-mini[data-charuid="'+ev.uid+'"]') || q('.char.you'));
  }
""" + A_ACT
CSS = """
/* fix_card_play_anim3 */
#abcFlyLayer{position:fixed;left:50%;top:50%;transform-origin:50% 50%;pointer-events:none;z-index:40}
body:not(.abc-arena) #abcFlyLayer{display:none}
"""

s = s.replace(A_HOST, NEW_HOST, 1)
s = s.replace(A_ACT, NEW_ACT, 1)
s = s.replace(A_CSS, CSS + A_CSS, 1)
for need in [MARK, "host.id='abcFlyLayer'", "(ch._actCards||[]).indexOf(card)"]:
    if need not in s:
        sys.exit(f'[fix_card_play_anim3] ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print('[fix_card_play_anim3] Applied.  Backup:', bak)
print('[fix_card_play_anim3] Next: python3 build.py')
