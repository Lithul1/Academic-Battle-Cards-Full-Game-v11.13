#!/usr/bin/env python3
"""Embed per-deck card backgrounds into assets/assets.json.

Deck backgrounds occupy a RESERVED asset-id block (900-910) so they can never
collide with portrait ids, which auto-increment from the low end. The matching
CSS in src/game.src.html references these ids as
    background: ... url("data:image/png;base64,__ABCASSET_<id>__") ...

Usage (from the repo root):
    python3 apply_deck_bg.py            # inject every art file it can find
    python3 apply_deck_bg.py && python3 build.py

Drop each deck's borderless PNG (the inner pattern, no frame) in the repo root
or in a `deck_bg/` folder. Files that aren't present yet are skipped with a
note, so you can add one deck at a time. Re-running is safe (idempotent).
"""
import os, sys, json, base64

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets", "assets.json")
SRC = os.path.join(ROOT, "src", "game.src.html")

# deck  ->  (reserved asset id 900-910, source PNG filename)
DECKS = {
    "gatsby": (900, "Gatsby_Card_Background_B.png"),
    # add future decks here, e.g.:
    # "macbeth":    (901, "Macbeth_Card_Background.png"),
    # "wonderland": (902, "Wonderland_Card_Background.png"),
}

# folders searched for each PNG (first match wins)
ART_DIRS = [ROOT, os.path.join(ROOT, "deck_bg"), os.path.join(ROOT, "assets", "deck_bg")]


def find_art(fname):
    for d in ART_DIRS:
        p = os.path.join(d, fname)
        if os.path.isfile(p):
            return p
    return None


def main():
    if not os.path.isfile(ASSETS):
        sys.exit(f"[deck_bg] ERROR: {ASSETS} not found. Run this from the repo root.")
    assets = json.load(open(ASSETS, encoding="utf-8"))

    src = open(SRC, encoding="utf-8").read() if os.path.isfile(SRC) else ""

    added, skipped = [], []
    for deck, (aid, fname) in sorted(DECKS.items(), key=lambda kv: kv[1][0]):
        path = find_art(fname)
        if not path:
            skipped.append((deck, fname))
            continue
        raw = open(path, "rb").read()
        b64 = base64.b64encode(raw).decode("ascii")
        key = f"a{aid}"
        prev = assets.get(key)
        assets[key] = b64
        state = "updated" if prev and prev != b64 else ("unchanged" if prev == b64 else "added")
        added.append((deck, key, len(b64), state, path))
        if src and f"__ABCASSET_{aid}__" not in src:
            print(f"[deck_bg] WARN: src does not reference __ABCASSET_{aid}__ "
                  f"(deck '{deck}'). The CSS wiring may be missing.")

    json.dump(assets, open(ASSETS, "w", encoding="utf-8"), ensure_ascii=False)

    for deck, key, n, state, path in added:
        print(f"[deck_bg] {deck:12} -> {key}  ({n:,} b64 chars, {state})  <- {os.path.basename(path)}")
    for deck, fname in skipped:
        print(f"[deck_bg] {deck:12} -> skipped (no art file '{fname}' found yet)")
    print(f"[deck_bg] assets.json now holds {len(assets)} entries.")
    if not added:
        print("[deck_bg] Nothing injected. Put the deck PNG(s) in the repo root or deck_bg/.")


if __name__ == "__main__":
    main()
