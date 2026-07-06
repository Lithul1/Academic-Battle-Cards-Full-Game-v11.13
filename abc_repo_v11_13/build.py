#!/usr/bin/env python3
"""Assemble the shippable single-file HTML from the split source.
   Usage: python3 build.py [--src src/game.src.html] [--assets assets/assets.json]
                           [--out dist/academic_battle_cards.html]
No third-party deps. Deterministic: same inputs -> byte-identical output.
"""
import re, json, hashlib, argparse, os, sys

root = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--src",    default=os.path.join(root, "src/game.src.html"))
ap.add_argument("--assets", default=os.path.join(root, "assets/assets.json"))
ap.add_argument("--out",    default=os.path.join(root, "dist/academic_battle_cards.html"))
a = ap.parse_args()

src = open(a.src, encoding="utf-8").read()
assets = json.load(open(a.assets))

missing = set(re.findall(r'__ABCASSET_(\d+)__', src)) - {k[1:] for k in assets}
if missing:
    sys.exit(f"[build] ERROR: src references asset ids not in bundle: {sorted(missing)}")

out = re.sub(r'__ABCASSET_(\d+)__', lambda m: assets[f"a{m.group(1)}"], src)

leftover = re.findall(r'__ABCASSET_\d+__', out)
if leftover:
    sys.exit(f"[build] ERROR: {len(leftover)} placeholder(s) left unresolved")

os.makedirs(os.path.dirname(a.out), exist_ok=True)
open(a.out, "w", encoding="utf-8").write(out)
print(f"[build] {a.out}")
print(f"[build] {len(out):,} bytes  sha256={hashlib.sha256(out.encode()).hexdigest()}")
