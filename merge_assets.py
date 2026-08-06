#!/usr/bin/env python3
"""Merge a small asset file into assets/assets.json.

    python3 merge_assets.py assets/assets_othello_portraits.json
    python3 merge_assets.py assets/assets_othello_portraits.json --dry-run

Writes a timestamped backup of assets.json before touching anything.
Keys already present are REPLACED; new keys are added.
"""
import json, os, sys, shutil, argparse, datetime

root = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("patch", help="the small json file of new assets")
ap.add_argument("--assets", default=os.path.join(root, "assets/assets.json"))
ap.add_argument("--src",    default=os.path.join(root, "src/game.src.html"))
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()

if not os.path.exists(a.assets):
    sys.exit(f"[merge] ERROR: no assets.json at {a.assets}")
if not os.path.exists(a.patch):
    sys.exit(f"[merge] ERROR: no patch file at {a.patch}")

assets = json.load(open(a.assets))
patch  = json.load(open(a.patch))

bad = [k for k in patch if not (k.startswith("a") and k[1:].isdigit())]
if bad:
    sys.exit(f"[merge] ERROR: keys must look like a93 — got {bad[:5]}")

replaced, added = [], []
for k, v in patch.items():
    (replaced if k in assets else added).append(k)

def kb(s): return len(s) / 1024

print(f"[merge] {a.patch}")
print(f"[merge] {len(patch)} key(s): {len(replaced)} replaced, {len(added)} added")
for k in sorted(patch, key=lambda x: int(x[1:])):
    old = assets.get(k)
    note = f"{kb(old):7.0f} KB -> {kb(patch[k]):7.0f} KB" if old else f"{'new':>10} -> {kb(patch[k]):7.0f} KB"
    print(f"          {k:6} {note}")

# sanity: does the source actually reference these ids?
if os.path.exists(a.src):
    import re
    used = set(re.findall(r"__ABCASSET_(\d+)__", open(a.src, encoding="utf-8").read()))
    orphan = [k for k in patch if k[1:] not in used]
    if orphan:
        print(f"[merge] WARNING: not referenced by src, will never render: {orphan}")

if a.dry_run:
    print("[merge] dry run — nothing written")
    sys.exit(0)

stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
backup = f"{a.assets}.{stamp}.bak"
shutil.copy(a.assets, backup)

assets.update(patch)
json.dump(assets, open(a.assets, "w"), indent=0)

print(f"[merge] backup  {backup}")
print(f"[merge] written {a.assets}  ({len(assets)} keys total)")
print("[merge] now run: python3 build.py")
