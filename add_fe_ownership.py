#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_fe_ownership.py — first editions now respect what you actually own.

    python3 add_fe_ownership.py src/game.src.html
    python3 build.py

THE BUG
-------
Characters and ABCs are filtered by ownership in the deck builder:

    deckOwnCh(k, id)   deckOwnAb(k, i)

First editions never were. The builder's commander row is

    const feRow = (DATA.firsteds||[]).map(f => ...)

with no check at all — so every one of the 30 commanders shows for every player,
including the 7 belonging to Sherlock, Othello and Wonderland, which are locked
behind a 350 IP licence.

Today that lets you put a commander in your deck whose book you do not own. The
deck then cannot draw on that book for characters or trivia, so you end up with
a commander and nothing to support it. It is the same shape as the Scrimmage
free-node bug: an ownership rule applied in one place and forgotten in another.

WHAT THIS ADDS
--------------
1. feOwned(id) — modelled exactly on deckOwnCh. Sandbox (Quickplay) sees
   everything; an unlocked deck's commanders are all available; a locked deck's
   commanders appear only once you have bought the licence.
2. the builder's commander row filters through it
3. clampDeck drops commanders you do not own, the way it already drops
   characters and ABCs you do not own

A player with the three locked decks still locked now sees 23 of 30 commanders
rather than all 30.

Safety: verifies every anchor before touching anything, builds in memory, writes
a .bak, refuses to run twice, and checks the asset placeholder count is unchanged.
"""
import sys, os, re, shutil

FE_OWNED = """function feOwned(id){
  if(sbx()) return true;
  var f=(DATA.firsteds||[]).find(function(x){ return x.id===id; });
  if(!f) return false;
  var k=f.deck;
  if(!k) return true;                      /* a commander with no book is always available */
  if(!deckLocked(k)||!deckUnlocked(k)) return !deckLocked(k);
  var d=(META.deckCards||{})[k]||{};
  return (d.fe||[]).indexOf(id)>=0 || (META.decks||[]).indexOf(k)>=0;
}
function feOwnedList(){ return (DATA.firsteds||[]).filter(function(f){ return feOwned(f.id); }); }
"""

EDITS = [
    # 1 — the helper, next to the other ownership checks
    ("insert",
     "function deckOwnCh(k,id){",
     FE_OWNED + "function deckOwnCh(k,id){"),

    # 2 — the builder's commander row respects it
    ("replace",
     "const feRow=(DATA.firsteds||[]).map(f=>{",
     "const feRow=feOwnedList().map(f=>{"),
]


def die(msg):
    print("ABORTED \u2014 file not modified.")
    print("  " + msg)
    sys.exit(1)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "src/game.src.html"
    if not os.path.exists(path):
        die(f"no such file: {path}")

    src = open(path, encoding="utf-8").read()

    if "function feOwned(" in src:
        print("Already applied \u2014 feOwned is present. Nothing to do.")
        return

    for deck in ("romeojuliet", "odyssey"):
        if deck not in src:
            die(f"'{deck}' is missing from this file, so it is not your live source.")

    for n, (tag, old, new) in enumerate(EDITS, 1):
        c = src.count(old)
        if c != 1:
            die(f"edit {n}: anchor found {c} times, expected exactly 1.\n"
                f"  anchor: {old[:70]!r}\n"
                f"  Send Claude your current src/game.src.html.")

    out = src
    for tag, old, new in EDITS:
        out = out.replace(old, new, 1)

    # 3 — clampDeck should drop unowned commanders too, if it handles fe at all
    m = re.search(r"function clampDeck\(def\)\{", out)
    if m:
        i = out.index("{", m.start())
        d = 0
        for k in range(i, len(out)):
            if out[k] == "{":
                d += 1
            elif out[k] == "}":
                d -= 1
                if d == 0:
                    break
        block = out[i:k + 1]
        if "feOwned" not in block:
            drop = ("\n  /* a commander you do not own cannot stay in the deck */\n"
                    "  if(def.fe && def.fe.length){\n"
                    "    var _keep=def.fe.filter(function(id){ return feOwned(id); });\n"
                    "    if(_keep.length!==def.fe.length){ def.fe=_keep; def._repaired=true; }\n"
                    "  }\n")
            out = out[:i + 1] + drop + out[i + 1:]
            print("  + clampDeck now drops unowned commanders")
    else:
        print("  ! clampDeck not found \u2014 skipped that guard (not fatal)")

    before = len(re.findall(r"__ABCASSET_\d+__", src))
    after = len(re.findall(r"__ABCASSET_\d+__", out))
    if before != after:
        die(f"asset placeholder count changed ({before} -> {after}).")
    if len(out) <= len(src):
        die("output is not larger than input.")

    backup = path + ".bak"
    shutil.copy(path, backup)
    open(path, "w", encoding="utf-8").write(out)

    print("Applied \u2014 first-edition ownership.")
    print(f"  backup      : {backup}")
    print(f"  {path}: {len(src):,} -> {len(out):,} bytes (+{len(out)-len(src):,})")
    print(f"  placeholders: {after} (unchanged)")
    print()
    print("  The builder now shows only commanders you own. With Sherlock, Othello")
    print("  and Wonderland locked that is 23 of 30 rather than all 30.")
    print()
    print("  Quickplay is unaffected \u2014 sbx() still returns everything, as it does")
    print("  for characters and ABCs.")
    print()
    print("  Next: python3 build.py")


if __name__ == "__main__":
    main()
