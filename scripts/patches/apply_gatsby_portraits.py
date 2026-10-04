#!/usr/bin/env python3
"""Embed the updated Gatsby character portraits into assets/assets.json.

Six of the seven update existing portrait asset ids in place (no dead weight);
Tom takes a fresh id (a163) since he wasn't in the override map before. The
matching wiring lives in src/game.src.html (window.CHAR_IMG_NEW / CHAR_IMGPOS_NEW).

Usage (from the repo root):
    python3 apply_gatsby_portraits.py && python3 build.py

Drop the seven *_portrait.jpg files in the repo root (or a portraits/ folder).
The JPEGs are already optimized, so they're embedded as-is. Re-running is safe.
"""
import os, sys, json, base64

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets", "assets.json")

# character -> (asset id, source jpg)
PORTRAITS = {
    # 7 updated in place
    "daisy":  (15,  "daisy_portrait.jpg"),
    "gatsby": (16,  "gatsby_portrait.jpg"),
    "myrtle": (17,  "myrtle_portrait.jpg"),
    "nick":   (18,  "nick_portrait.jpg"),
    "george": (19,  "george_portrait.jpg"),
    "jordan": (20,  "jordan_portrait.jpg"),
    "tom":    (163, "tom_portrait.jpg"),
    # 8 new cards
    "james_gatz":      (164, "james_gatz_portrait.jpg"),
    "meyer_wolfsheim": (165, "meyer_wolfsheim_portrait.jpg"),
    "owl_eyes":        (166, "owl_eyes_portrait.jpg"),
    "klipspringer":    (167, "klipspringer_portrait.jpg"),
    "dan_cody":        (168, "dan_cody_portrait.jpg"),
    "catherine":       (169, "catherine_portrait.jpg"),
    "henry_gatz":      (170, "henry_gatz_portrait.jpg"),
    "pammy_buchanan":  (171, "pammy_buchanan_portrait.jpg"),
}
ART_DIRS = [ROOT, os.path.join(ROOT, "portraits"), os.path.join(ROOT, "gatsby_portraits")]


def find(fname):
    for d in ART_DIRS:
        p = os.path.join(d, fname)
        if os.path.isfile(p):
            return p
    return None


def main():
    if not os.path.isfile(ASSETS):
        sys.exit(f"[portraits] ERROR: {ASSETS} not found. Run from the repo root.")
    assets = json.load(open(ASSETS, encoding="utf-8"))
    done, missing = [], []
    for cid, (aid, fname) in sorted(PORTRAITS.items(), key=lambda kv: kv[1][0]):
        path = find(fname)
        if not path:
            missing.append((cid, fname)); continue
        b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")
        key = f"a{aid}"
        state = "updated" if key in assets else "added"
        assets[key] = b64
        done.append((cid, key, len(b64), state))
    json.dump(assets, open(ASSETS, "w", encoding="utf-8"), ensure_ascii=False)
    for cid, key, n, state in done:
        print(f"[portraits] {cid:8} -> {key}  ({n:,} b64 chars, {state})")
    for cid, fname in missing:
        print(f"[portraits] {cid:8} -> MISSING art file '{fname}'")
    if missing:
        sys.exit(f"[portraits] {len(missing)} file(s) not found -- put the *_portrait.jpg files in the repo root.")
    print(f"[portraits] assets.json now holds {len(assets)} entries.")


if __name__ == "__main__":
    main()
