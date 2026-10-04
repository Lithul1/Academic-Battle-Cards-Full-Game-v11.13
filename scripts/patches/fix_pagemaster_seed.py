#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_pagemaster_seed.py — repairs a build that got the FIRST version of
add_pagemaster_picker.py.

    python3 fix_pagemaster_seed.py src/game.src.html
    python3 build.py

WHY YOU NEED THIS
-----------------
I shipped add_pagemaster_picker.py, then updated it, and the updated script
refuses to run on a file that already has the old one ("Already applied"). So if
you applied the first version you are missing two things:

1. the "deck building is the next piece" toast is still there and is now WRONG —
   the builder does know Pagemaster, as of add_pagemaster_builder.py
2. pm-build never seeds APP.builder, so pressing "Build the deck" crashes the
   builder on `undefined.def`. You may not have hit this if the toast made you
   stop, but it is there.

This patch adds pmSeedDeck(), seeds APP.builder on pm-build, and removes the
stale toast. If your build already has the corrected picker it will say so and
do nothing.

Safe to run on either version. Verifies before writing, keeps a .bak.
"""
import sys, os, re, shutil

SEED_FN = """/* an empty Pagemaster deck, correctly shaped, for the builder to fill */
function pmSeedDeck(books, cmds){
  return { d:books[0], books:books.slice(), pm:true,
           ch:[], ab:[], bm:[], cr:[], fe:(cmds||[]).slice(0,PM.fe), ed:{}, edab:[], edbm:{} };
}
"""

OLD_BUILD = ("      APP.youDeck=bk.books[0]; APP.customDeck=null;\n"
             "      toast('Deck building for Pagemaster is the next piece "
             "\\u2014 the builder is not filtered yet.');\n"
             "      APP.screen='builder'; render(); }")
NEW_BUILD = ("      APP.youDeck=bk.books[0]; APP.customDeck=null;\n"
             "      /* the builder needs its working deck seeded, exactly as data-do='builder' does */\n"
             "      APP.builder={ def:(APP.pmDeck?clone(APP.pmDeck):pmSeedDeck(bk.books,a)), code:'' };\n"
             "      APP.codeMsg=null; APP.screen='builder'; render(); }")


def die(msg):
    print("ABORTED \u2014 file not modified.")
    print("  " + msg)
    sys.exit(1)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "src/game.src.html"
    if not os.path.exists(path):
        die(f"no such file: {path}")
    src = open(path, encoding="utf-8").read()

    if "function pmPickerScreen" not in src:
        die("the Pagemaster picker is not in this file.\n"
            "  Run add_pagemaster_picker.py (the current version) instead.")

    already = "function pmSeedDeck" in src and OLD_BUILD not in src
    if already:
        print("Nothing to do \u2014 this build already has the corrected picker.")
        return

    n = src.count(OLD_BUILD)
    if n != 1:
        die(f"the old pm-build block was found {n} times, expected 1.\n"
            "  Your file differs from what this expects. Send Claude your src/game.src.html.")

    out = src.replace(OLD_BUILD, NEW_BUILD, 1)

    if "function pmSeedDeck" not in out:
        anchor = "/* ---------------- Pagemaster: choose two commanders ---------------- */"
        if anchor not in out:
            die("could not find the picker block to insert pmSeedDeck before.")
        out = out.replace(anchor, SEED_FN + anchor, 1)

    if "the builder is not filtered yet" in out:
        die("the stale toast is still present after patching \u2014 refusing to write.")

    before = len(re.findall(r"__ABCASSET_\d+__", src))
    after = len(re.findall(r"__ABCASSET_\d+__", out))
    if before != after:
        die(f"asset placeholder count changed ({before} -> {after}).")

    shutil.copy(path, path + ".bak")
    open(path, "w", encoding="utf-8").write(out)

    print("Applied \u2014 picker seeding repaired.")
    print(f"  backup      : {path}.bak")
    print(f"  {path}: {len(src):,} -> {len(out):,} bytes ({len(out)-len(src):+,})")
    print()
    print("  \u2022 the stale 'not filtered yet' toast is gone \u2014 the builder does know")
    print("    Pagemaster now")
    print("  \u2022 'Build the deck' seeds APP.builder, so it will no longer crash")
    print()
    print("  Next: python3 build.py")


if __name__ == "__main__":
    main()
