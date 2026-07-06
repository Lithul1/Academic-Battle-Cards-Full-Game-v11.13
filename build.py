#!/usr/bin/env python3
"""Assemble the single-file HTML from the split source.

  python3 build.py                 # real build (needs assets/assets.json)
  python3 build.py --stub          # tiny stub build (NO assets needed): every
                                   # image becomes a 1x1 pixel. Boots + plays
                                   # identically — use this to develop/validate
                                   # when the 4.7MB bundle isn't on hand.

Deterministic, no third-party deps.
"""
import re, json, hashlib, argparse, os, sys

root = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--src",    default=os.path.join(root, "src/game.src.html"))
ap.add_argument("--assets", default=os.path.join(root, "assets/assets.json"))
ap.add_argument("--out",    default=None)
ap.add_argument("--stub",   action="store_true",
                help="replace every asset with a 1x1 pixel; no assets.json needed")
a = ap.parse_args()

STUB = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABpfZFQAAAAABJRU5ErkJggg=="
src = open(a.src, encoding="utf-8").read()

if a.stub:
    out = re.sub(r'__ABCASSET_\d+__', STUB, src)
    default_out = os.path.join(root, "dist/stub.html")
else:
    assets = json.load(open(a.assets))
    missing = set(re.findall(r'__ABCASSET_(\d+)__', src)) - {k[1:] for k in assets}
    if missing:
        sys.exit(f"[build] ERROR: src references asset ids not in bundle: {sorted(missing)}")
    out = re.sub(r'__ABCASSET_(\d+)__', lambda m: assets[f"a{m.group(1)}"], src)
    default_out = os.path.join(root, "dist/academic_battle_cards.html")

leftover = re.findall(r'__ABCASSET_\d+__', out)
if leftover:
    sys.exit(f"[build] ERROR: {len(leftover)} placeholder(s) left unresolved")

out_path = a.out or default_out
os.makedirs(os.path.dirname(out_path), exist_ok=True)
open(out_path, "w", encoding="utf-8").write(out)
kind = "STUB" if a.stub else "FULL"
print(f"[build:{kind}] {out_path}")
print(f"[build:{kind}] {len(out):,} bytes  sha256={hashlib.sha256(out.encode()).hexdigest()}")
