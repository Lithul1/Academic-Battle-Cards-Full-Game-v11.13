#!/usr/bin/env python3
"""fix_card_play_anim2.py -- Slower, readable card-play animation (needs fix_card_play_anim.py).

Run from the repo root:   python3 fix_card_play_anim2.py
Undo:                     restore src/game.src.html from the .bak this writes.

WHY: the first version flew straight to its target in 0.56s -- correct, but too quick
to read what was played. This version adds a "present" beat, the way digital TCGs
show a played card before it resolves:
   rise   0.30s  the card lifts out of the hand and grows to ~1.35x
   hold   0.40s  it pauses, readable, between the hand and its target
   fly    0.45s  it travels to its target and shrinks into it
   land   0.15s  fades into the target, which flashes gold
   ---------------------------------------------- total ~1.3s
Two or more cards leaving at once now queue one after another (0.5s apart) instead
of overlapping. Everything else is unchanged: purely visual, never blocks a click,
off with Reduce motion.

TUNING: one number -- ABC_FLY_MS (default 1300) near the top of the new block.
Every phase scales with it, so 1000 = brisker, 1600 = slower.
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_card_play_anim2 */'
if not os.path.exists(SRC):
    sys.exit('[fix_card_play_anim2] ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit('[fix_card_play_anim2] Already applied -- nothing to do.')
if '/* fix_card_play_anim */' not in s:
    sys.exit('[fix_card_play_anim2] ERROR: run fix_card_play_anim.py first.')

OLD = """    const sc=Math.max(.35, Math.min(.8, b.h/f.h)), mx=(a.x+b.x)/2, my=Math.min(a.y,b.y)-70;
    if(!wrap.animate){ wrap.remove(); return; }
    const an=wrap.animate([
      {transform:T(a.x,a.y)+' scale(1) rotate(0deg)', opacity:1},
      {transform:T(mx,my)+' scale(1.1) rotate(-6deg)', opacity:1, offset:.4},
      {transform:T(b.x,b.y)+' scale('+sc+') rotate(0deg)', opacity:.95, offset:.85},
      {transform:T(b.x,b.y)+' scale('+(sc*.9)+') rotate(0deg)', opacity:0}
    ], {duration:560, delay:i*70, easing:'cubic-bezier(.3,.7,.25,1)', fill:'both'});
"""
NEW = """    const sc=Math.max(.35, Math.min(.8, b.h/f.h));
    if(!wrap.animate){ wrap.remove(); return; }
    /* fix_card_play_anim2 */ /* rise -> present (hold) -> fly -> land */
    const PS=1.35, sw=st?st.offsetWidth:window.innerWidth, sh=st?st.offsetHeight:window.innerHeight;
    const half=f.w*PS/2+8, halfh=f.h*PS/2+8;
    const px=Math.max(half, Math.min(sw-half, a.x+(b.x-a.x)*.35));
    const py=Math.max(halfh, Math.min(sh-halfh, Math.min(a.y,b.y)-f.h*.25));
    const an=wrap.animate([
      {transform:T(a.x,a.y)+' scale(1) rotate(0deg)', opacity:1, easing:'cubic-bezier(.2,.8,.3,1)'},
      {transform:T(px,py)+' scale('+PS+') rotate(-2deg)', opacity:1, offset:.23},
      {transform:T(px,py-4)+' scale('+PS+') rotate(0deg)', opacity:1, offset:.54, easing:'cubic-bezier(.55,0,.25,1)'},
      {transform:T(b.x,b.y)+' scale('+sc+') rotate(0deg)', opacity:.95, offset:.89},
      {transform:T(b.x,b.y)+' scale('+(sc*.9)+') rotate(0deg)', opacity:0}
    ], {duration:ABC_FLY_MS, delay:i*Math.round(ABC_FLY_MS*.4), fill:'both'});
"""
A_FN = "function abcFlyRun(snap){\n"
for a, l in [(OLD, 'v1 flight keyframes'), (A_FN, 'abcFlyRun head')]:
    n = s.count(a)
    if n != 1:
        sys.exit(f'[fix_card_play_anim2] ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')

s = s.replace(OLD, NEW, 1)
s = s.replace(A_FN, "const ABC_FLY_MS=1300;   /* fix_card_play_anim2 -- card-play animation length (ms); every phase scales with it */\n" + A_FN, 1)
for need in [MARK, 'const ABC_FLY_MS=1300;', 'duration:ABC_FLY_MS']:
    if need not in s:
        sys.exit(f'[fix_card_play_anim2] ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print('[fix_card_play_anim2] Applied.  Backup:', bak)
print('[fix_card_play_anim2] Next: python3 build.py')
