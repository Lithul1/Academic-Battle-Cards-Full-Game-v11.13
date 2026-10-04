#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_starter_bookmarks.py — a wider, more instructive starter collection.

    python3 fix_starter_bookmarks.py src/game.src.html
    python3 build.py

THE PROBLEM
-----------
STARTER_BM grants 2-3 copies of bookmark indices 0-11 and nothing else:

    { 0:2, 4:2, 5:2, 10:2,  1:3, 2:3, 3:3, 6:3, 7:3, 8:3, 9:3, 11:3 }
    12 distinct, 32 cards

Two consequences.

1. Those twelve are ALL of kind ITEM or SUPPORT. A new player owns no STATUS,
   BOOST, UTILITY or RESET bookmark at all — so they never see a card that
   inflicts a status or grants one, despite the Quickstart guide teaching both
   as core mechanics. They learn the vocabulary from character cards only.

2. Pagemaster is singleton on bookmarks and needs 14 DISTINCT. With twelve, a
   new player cannot build a legal Pagemaster deck at any point before they
   start opening packs.

THE CHANGE
----------
    2 copies each of 16 bookmarks = 32 cards

Same total. Four more distinct cards, all Common, all from kinds the starter
currently lacks:

    [12] Torn Chapter        STATUS   inflict Tear
    [18] Sticky Situation    STATUS   inflict Glue
    [23] Proofread           BOOST    remove a negative status
    [25] Highlight Passage   BOOST    grant Highlight

That gives a new player one card that inflicts, one that cleanses and one that
buffs — the three verbs the game runs on.

THE TRADE
---------
Copies fall from 2-3 to a flat 2. Iron Curtain, Papercut, Defibrillator and five
others go from three copies to two. Starter decks will repeat less and vary more,
which is the intent, but it does change what every new player opens with and what
defaultDeck() produces for anyone who has not bought packs.

Safe to run once. Verifies before writing, keeps a .bak.
"""
import sys, os, re, shutil

OLD = ("STARTER_BM = { 0:2, 4:2, 5:2, 10:2,            // watchlist - capped at 2\n"
       "                     1:3, 2:3, 3:3, 6:3, 7:3, 8:3, 9:3, 11:3 };")

NEW = ("STARTER_BM = {\n"
       "  /* Two copies each of sixteen, rather than 2-3 copies of twelve. Same 32\n"
       "     cards, four more distinct, and the four additions are the first STATUS\n"
       "     and BOOST cards a new player owns \u2014 the old starter was ITEM and\n"
       "     SUPPORT only, so nothing in it inflicted or granted a status. Sixteen\n"
       "     distinct also makes a singleton Pagemaster deck (14) buildable. */\n"
       "  0:2,  1:2,  2:2,  3:2,  4:2,  5:2,  6:2,  7:2,\n"
       "  8:2,  9:2, 10:2, 11:2,\n"
       "  12:2,          // Torn Chapter      \u2014 inflict Tear\n"
       "  18:2,          // Sticky Situation  \u2014 inflict Glue\n"
       "  23:2,          // Proofread         \u2014 remove a negative status\n"
       "  25:2           // Highlight Passage \u2014 grant Highlight\n"
       "};")


def die(msg):
    print("ABORTED \u2014 file not modified.")
    print("  " + msg)
    sys.exit(1)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "src/game.src.html"
    if not os.path.exists(path):
        die(f"no such file: {path}")
    src = open(path, encoding="utf-8").read()

    if "18:2,          // Sticky Situation" in src:
        print("Already applied \u2014 the starter is already sixteen distinct. Nothing to do.")
        return

    n = src.count(OLD)
    if n != 1:
        # try a whitespace-tolerant locate so the error is useful
        m = re.search(r"STARTER_BM\s*=\s*\{[^}]*\}", src)
        found = m.group(0)[:120] if m else "(STARTER_BM not found at all)"
        die(f"the STARTER_BM block was found {n} times, expected 1.\n"
            f"  what is actually there: {found!r}\n"
            "  Send Claude your current src/game.src.html.")

    out = src.replace(OLD, NEW, 1)

    # widen the test surface so this can be verified from outside
    if "ABC_PM = {" in out and "get STARTER_BM()" not in out:
        out = out.replace("window.ABC_PM = { PM, pmOn,",
                          "window.ABC_PM = { defaultDeck, bmOwned, get STARTER_BM(){return STARTER_BM;}, PM, pmOn,", 1)

    # the four additions must actually exist in the bookmark table
    for idx, name in ((12, "Torn Chapter"), (18, "Sticky Situation"),
                      (23, "Proofread"), (25, "Highlight Passage")):
        if name not in src:
            die(f"'{name}' (index {idx}) is not in this build's bookmark table.\n"
                "  The indices would point at different cards. Aborting rather than guessing.")

    before = len(re.findall(r"__ABCASSET_\d+__", src))
    after = len(re.findall(r"__ABCASSET_\d+__", out))
    if before != after:
        die(f"asset placeholder count changed ({before} -> {after}).")

    shutil.copy(path, path + ".bak")
    open(path, "w", encoding="utf-8").write(out)

    print("Applied \u2014 starter widened to sixteen distinct bookmarks.")
    print(f"  backup: {path}.bak")
    print(f"  {path}: {len(src):,} -> {len(out):,} bytes ({len(out)-len(src):+,})")
    print()
    print("  12 distinct / 32 cards  ->  16 distinct / 32 cards")
    print()
    print("  New to the starter, all Common:")
    print("    Torn Chapter        inflict Tear")
    print("    Sticky Situation    inflict Glue")
    print("    Proofread           remove a negative status")
    print("    Highlight Passage   grant Highlight")
    print()
    print("  A new player now owns cards that inflict, cleanse and buff \u2014 the old")
    print("  starter was ITEM and SUPPORT only and did none of the three.")
    print()
    print("  Copies drop from 2-3 to a flat 2, so starter decks repeat less.")
    print()
    print("  Next: python3 build.py")


if __name__ == "__main__":
    main()
