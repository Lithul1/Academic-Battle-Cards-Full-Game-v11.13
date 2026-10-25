#!/usr/bin/env python3
"""fix_table_lighting_v2.py -- Warm table lighting, take two (needs fix_board_layout_v6).

Run from the repo root:   python3 fix_table_lighting_v2.py
Undo:                     restore src/game.src.html from the .bak this writes.

WHAT CHANGES:
  1. OFF by default. Tune > Accessibility > "Warm table lighting" turns it ON
     (remembered per device; localStorage 'abc_light'='on').
  2. Reads as warm lamplight instead of a dim filter:
       * the lamp is a warm amber pool blended with soft-light, which lifts and warms
         the table's midtones instead of greying them;
       * the edge falloff is a faint warm-brown, only toward the desk corners;
       * the film grain is gone (it was the main "dulling" ingredient).
  3. Everything you click stays brighter than the table: the lighting layers now sit
     UNDER every card, button, pile and the hand (previously the vignette sat on top of
     them), and while lighting is on the main buttons, playable hand cards and ready
     moves catch the light with a soft warm glow.
"""
import os, sys, shutil, datetime

SRC = os.path.join('src', 'game.src.html')
MARK = '/* fix_table_lighting_v2 */'
if not os.path.exists(SRC):
    sys.exit('[fix_table_lighting_v2] ERROR: run from the repo root (src/game.src.html not found).')
s = open(SRC, encoding='utf-8').read()
if MARK in s:
    sys.exit('[fix_table_lighting_v2] Already applied -- nothing to do.')
if '/* fix_board_layout_v6 */' not in s:
    sys.exit('[fix_table_lighting_v2] ERROR: run fix_board_layout_v6.py first.')

A_ON  = "function abcLightOn(){ try{ return localStorage.getItem('abc_light')!=='off'; }catch(e){ return true; } }"
A_ROW = "${row('Table lighting (vignette &amp; grain)',"
A_CSS = "</style>\n</head>"
for a, l in [(A_ON, 'abcLightOn (v6)'), (A_ROW, 'Tune lighting label (v6)'), (A_CSS, 'end of <head> styles')]:
    if s.count(a) != 1:
        sys.exit(f'[fix_table_lighting_v2] ERROR: anchor "{l}" found {s.count(a)} times (expected 1). Nothing written.')

L = 'body.abc-arena.abc-light[data-screen="play"]'
CSS = """
/* fix_table_lighting_v2 */
/* lamp: warm amber pool, soft-light blend = warmer + brighter midtones, never greyer */
L .abc-stage::before{z-index:1;mix-blend-mode:soft-light;
  background:radial-gradient(ellipse 52% 48% at 50% 44%,rgba(255,176,84,.75),rgba(255,160,70,.32) 48%,rgba(255,150,60,0) 78%)}
/* falloff: faint warm-brown toward the desk corners only -- and UNDER everything clickable */
L .abc-stage::after{z-index:1;opacity:1;mix-blend-mode:multiply;
  background:radial-gradient(ellipse 80% 78% at 50% 46%,rgba(255,236,200,0) 62%,rgba(150,96,48,.30) 88%,rgba(120,72,34,.45) 100%)!important;
  background-size:auto!important}
body.abc-arena.abc-phone.abc-light[data-screen="play"] .abc-stage::before{
  background:radial-gradient(ellipse 70% 40% at 50% 46%,rgba(255,176,84,.7),rgba(255,160,70,0) 78%)}
/* clickable things catch the light */
L .actions .bigbtn,L .tb-btns button,L .logtoggle{box-shadow:0 0 0 2px rgba(255,214,150,.55),0 0 18px rgba(255,186,90,.55),0 4px 0 #241f1b}
L .hand .hc.playable{box-shadow:0 0 0 2px rgba(255,214,150,.85),0 0 16px rgba(255,186,90,.6)!important}
L .pc-move.atk.ready{box-shadow:0 0 0 3px #E3A92B,0 0 18px rgba(255,186,90,.75)}
L .bench-mini .bm-swap,L .pc-flip{box-shadow:0 0 10px rgba(255,200,110,.7)}
""".replace('\nL ', '\n' + L + ' ').replace(',L ', ',' + L + ' ')

s = s.replace(A_ON, "function abcLightOn(){ try{ return localStorage.getItem('abc_light')==='on'; }catch(e){ return false; } }   /* fix_table_lighting_v2: off unless switched on */", 1)
s = s.replace(A_ROW, "${row('Warm table lighting',", 1)
s = s.replace(A_CSS, CSS + A_CSS, 1)
for need in [MARK, "localStorage.getItem('abc_light')==='on'", "row('Warm table lighting'"]:
    if need not in s:
        sys.exit(f'[fix_table_lighting_v2] ERROR: post-check failed ({need}). Nothing written.')
bak = SRC + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copyfile(SRC, bak)
open(SRC, 'w', encoding='utf-8').write(s)
print('[fix_table_lighting_v2] Applied.  Backup:', bak)
print('[fix_table_lighting_v2] Next: python3 build.py')
