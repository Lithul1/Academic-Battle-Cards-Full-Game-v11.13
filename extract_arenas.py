#!/usr/bin/env python3
"""Pull just the nine arena images out of assets/assets.json.

Writes assets_arenas.json (a few hundred KB) containing only the backgrounds,
so the whole multi-megabyte asset bundle does not have to be moved around.

    python3 extract_arenas.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, "assets", "assets.json")
OUT  = os.path.join(ROOT, "assets_arenas.json")

# --arena-* placeholders, read out of src/game.src.html
WANTED = {
    "a1015": "gatsby",   "a1016": "hamlet", "a1017": "frankenstein",
    "a1018": "sherlock", "a1019": "wonderland", "a1020": "oz",
    "a1021": "city",     "a1022": "forest", "a1023": "castle",
}

if not os.path.exists(SRC):
    sys.exit("cannot find %s -- run this from the repo root." % SRC)

assets = json.load(open(SRC, encoding="utf-8"))
out, missing = {}, []
for key, name in WANTED.items():
    if key in assets:
        out[name] = assets[key]
    else:
        missing.append("%s (%s)" % (key, name))

json.dump(out, open(OUT, "w", encoding="utf-8"))
size = os.path.getsize(OUT)
print("wrote %s  (%.1f MB, %d of %d arenas)" % (OUT, size / 1e6, len(out), len(WANTED)))
if missing:
    print("missing:", ", ".join(missing))
