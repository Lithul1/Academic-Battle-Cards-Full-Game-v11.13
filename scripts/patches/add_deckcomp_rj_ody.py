#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_deckcomp_rj_ody.py — give Romeo & Juliet and The Odyssey their own starter
compositions, so they stop falling through to compFor()'s generic default.

    python3 add_deckcomp_rj_ody.py src/game.src.html
    python3 build.py

Additive only: two lines inserted into DECK_COMP, nothing removed or replaced.
Writes a .bak first, refuses to run twice, and aborts without touching the file
if anything looks wrong.

Why these numbers
-----------------
Romeo & Juliet  12 / 33 / 11 / 4   — lowest average HP in the game (91), two
    Martyrs, and the two lowest HP totals belong to Romeo and Mercutio. Already
    the closest thing to a glass-cannon deck, so it gets aggressive tempo:
    0.55 ABC/turn, a cost-3 move in 5.5 turns.

The Odyssey     14 / 27 / 15 / 4   — widest roster in the game (17 characters),
    highest average HP (101), two Mentors and two Forces of Nature. Endurance
    and depth rather than speed: 0.45 ABC/turn, a body every 4.3 turns.

Both total 62 with fe:2. Both sit inside the agreed ranges
(ch 8-14, ab 24-36, bm 10-20, cr 2-4). Both pools can supply them comfortably —
106 and 107 ABCs available against a 33 and 27 need.
"""
import sys, os, re, shutil

NEW_LINES = (
    "  romeojuliet:  { ch:12, ab:33, bm:11, cr:4 },   // fast and fatal, fragile bodies\n"
    "  odyssey:      { ch:14, ab:27, bm:15, cr:4 },   // attrition, the widest roster\n"
)

# the line we insert directly after — the last existing entry
ANCHOR = "  othello:      { ch:12, ab:26, bm:18, cr:4 },   // control, slowest to threaten\n"


def die(msg):
    print("ABORTED — file not modified.")
    print("  " + msg)
    sys.exit(1)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "src/game.src.html"
    if not os.path.exists(path):
        die(f"no such file: {path}\n  Run this from the repo root, or pass the path to your game.src.html.")

    src = open(path, encoding="utf-8").read()

    # --- already applied? ---
    if "romeojuliet:  { ch:" in src or "odyssey:      { ch:" in src:
        print("Already applied — Romeo & Juliet and Odyssey already have compositions.")
        print("Nothing to do.")
        return

    # --- sanity: is this the right file, and is it current? ---
    if "const DECK_COMP" not in src:
        die("DECK_COMP not found.\n"
            "  This file predates the per-deck composition work. Send Claude your current\n"
            "  src/game.src.html rather than applying this to an older copy.")

    for deck in ("romeojuliet", "odyssey"):
        if f"'{deck}'" not in src and f'"{deck}"' not in src:
            die(f"'{deck}' does not appear anywhere in this file.\n"
                f"  That deck is missing, so this is not your live source. Do not patch it —\n"
                f"  find the file that has all twelve decks in DECK_ORDER.")

    n = src.count(ANCHOR)
    if n != 1:
        die(f"the othello line was found {n} times, expected exactly 1.\n"
            "  DECK_COMP is not in the shape this patch expects. Send Claude your file.")

    out = src.replace(ANCHOR, ANCHOR + NEW_LINES, 1)

    # --- additive only ---
    if len(out) <= len(src):
        die("the result is not larger than the input, which should be impossible here.")
    before_assets = len(re.findall(r"__ABCASSET_\d+__", src))
    after_assets = len(re.findall(r"__ABCASSET_\d+__", out))
    if before_assets != after_assets:
        die(f"asset placeholder count changed ({before_assets} -> {after_assets}).")

    # --- braces still balanced inside DECK_COMP ---
    m = re.search(r"const DECK_COMP\s*=\s*\{", out)
    i = out.index("{", m.start())
    depth = 0
    for j in range(i, len(out)):
        if out[j] == "{":
            depth += 1
        elif out[j] == "}":
            depth -= 1
            if depth == 0:
                break
    block = out[i:j + 1]
    entries = re.findall(r"(\w+):\s*\{ ch:(\d+), ab:(\d+), bm:(\d+), cr:(\d+) \}", block)
    if len(entries) != 12:
        die(f"expected 12 deck entries after patching, found {len(entries)}.")

    bad = [(k, int(a) + int(b) + int(c) + int(d) + 2) for k, a, b, c, d in entries
           if int(a) + int(b) + int(c) + int(d) + 2 != 62]
    if bad:
        die("a composition does not total 62: " + ", ".join(f"{k}={t}" for k, t in bad))

    backup = path + ".bak"
    shutil.copy(path, backup)
    open(path, "w", encoding="utf-8").write(out)

    print("Applied.")
    print(f"  backup written : {backup}")
    print(f"  {path}: {len(src):,} -> {len(out):,} bytes (+{len(out)-len(src)})")
    print()
    print("  romeojuliet   12 / 33 / 11 / 4   0.55 ABC/turn   cost-3 in 5.5 turns")
    print("  odyssey       14 / 27 / 15 / 4   0.45 ABC/turn   a body every 4.3 turns")
    print()
    print(f"  all 12 decks now have a composition, every one totalling 62.")
    print("  Next: python3 build.py")


if __name__ == "__main__":
    main()
