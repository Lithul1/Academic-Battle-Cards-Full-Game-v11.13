#!/usr/bin/env python3
"""Run every board-redesign test against dist/stub.html (build it first: python3 build.py --stub).
Needs: pip install playwright && python3 -m playwright install chromium
Env:   ABC_STUB=/path/to/build.html   (default: <repo>/dist/stub.html)
       ABC_CHROME=/path/to/chromium   (optional)"""
import subprocess, sys, pathlib
here = pathlib.Path(__file__).parent
tests = ['test_layout_desktop.py','test_tilt.py','test_phone.py','test_lighting_bookmarks.py','test_cardplay.py','test_cardplay_trivia_evolve.py','test_pixel_fx.py','test_pixel_fx2.py','test_pixel_fx3.py','test_pixel_fx4.py','test_pixel_bosses.py','test_pixel_bosses2.py','test_challenges.py','test_print_frames.py','test_print_cards.py','test_menu_book.py','test_menu_pages.py','test_gameplay_perf.py','test_gameplay_perf2.py','test_perf_diag.py','test_safari_perf.py','test_fullscreen_smooth.py','test_dragdrop_cards.py','test_cardface_evolve.py','test_scrim_tome.py','test_scrim_quests.py','test_menu_logo.py','test_scrim_d20.py']
bad = 0
for t in tests:
    print(f'\n===== {t} =====', flush=True)
    r = subprocess.run([sys.executable, str(here / t)])
    bad += (r.returncode != 0)
print(f'\n===== {len(tests)-bad}/{len(tests)} suites passed =====')
sys.exit(1 if bad else 0)
