#!/usr/bin/env python3
"""Extract inline base64 images out of the source and into the asset bundle.

    python3 merge_assets.py src/game.src.html            # merge, in place
    python3 merge_assets.py src/game.src.html --dry-run  # report only, change nothing

New art arrives inline, as `data:image/webp;base64,<payload>` sitting directly in
the HTML. That keeps the file playable on its own but makes it enormous. This
script moves every inline payload into `assets/assets.json` and leaves a
`__ABCASSET_<N>__` placeholder behind, which is exactly what `build.py` expects:

    src   :  "romeo": "data:image/webp;base64,__ABCASSET_204__"
    bundle:  { "a204": "<payload>" }

Contract, matched to build.py:
  * assets.json maps "a<N>" -> the RAW base64 payload, with no `data:` prefix
  * the placeholder replaces only the payload, never the `data:image/...;base64,`
  * ids already in use are never reassigned or recycled

Safe to run twice. Existing placeholders are left alone, identical images share
one id, and a .bak of both files is written before anything changes.

No third-party dependencies.
"""
import re, json, os, sys, shutil, argparse, hashlib

INLINE = re.compile(r'data:image/(?P<fmt>[a-zA-Z0-9.+-]+);base64,(?P<b64>[A-Za-z0-9+/][A-Za-z0-9+/=]{63,})')
PLACEHOLDER = re.compile(r'__ABCASSET_(\d+)__')

ap = argparse.ArgumentParser()
ap.add_argument("src", nargs="?", default="src/game.src.html")
ap.add_argument("--assets", default=None, help="default: assets/assets.json beside the repo root")
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--start", type=int, default=None, help="first id to allocate (default: max+1)")
a = ap.parse_args()

if not os.path.exists(a.src):
    sys.exit("[merge] ERROR: no such file: %s" % a.src)

root = os.path.dirname(os.path.dirname(os.path.abspath(a.src))) or "."
assets_path = a.assets or os.path.join(root, "assets", "assets.json")

src = open(a.src, encoding="utf-8").read()

# ---------- load the bundle -------------------------------------------------
if os.path.exists(assets_path):
    with open(assets_path, encoding="utf-8") as f:
        assets = json.load(f)
else:
    assets = {}
    print("[merge] note: %s does not exist yet; a new bundle will be created" % assets_path)

def idnum(k):
    return int(k[1:]) if re.fullmatch(r'a\d+', k) else -1

used = {idnum(k) for k in assets} | {int(n) for n in PLACEHOLDER.findall(src)}
used.discard(-1)
next_id = a.start if a.start is not None else (max(used) + 1 if used else 0)

# payload -> id, so the same image merged twice keeps one entry
by_payload = {v: idnum(k) for k, v in assets.items() if idnum(k) >= 0}

# ---------- walk the source -------------------------------------------------
added, reused, seen = [], [], {}

def take(m):
    global next_id
    payload = m.group("b64")
    if payload in by_payload:
        n = by_payload[payload]
        if payload not in seen:
            reused.append((n, m.group("fmt"), len(payload)))
            seen[payload] = n
        return "data:image/%s;base64,__ABCASSET_%d__" % (m.group("fmt"), n)
    while next_id in used:
        next_id += 1
    n = next_id
    used.add(n); by_payload[payload] = n; seen[payload] = n
    assets["a%d" % n] = payload
    added.append((n, m.group("fmt"), len(payload)))
    next_id += 1
    return "data:image/%s;base64,__ABCASSET_%d__" % (m.group("fmt"), n)

out = INLINE.sub(take, src)

# ---------- report ----------------------------------------------------------
def kb(n): return n * 3 / 4 / 1024
print("[merge] source : %s" % a.src)
print("[merge] bundle : %s" % assets_path)
if added:
    print("[merge] extracted %d new image(s):" % len(added))
    for n, fmt, ln in added:
        print("          a%-5d %-5s %7.0f KB" % (n, fmt, kb(ln)))
if reused:
    print("[merge] %d image(s) already in the bundle, reused their ids: %s"
          % (len(reused), ", ".join("a%d" % n for n, _, _ in reused)))
if not added and not reused:
    print("[merge] no inline images found - nothing to do")

# ---------- verify before writing -------------------------------------------
leftover = INLINE.search(out)
if leftover:
    sys.exit("[merge] ERROR: an inline image survived the pass - refusing to write")
missing = {int(n) for n in PLACEHOLDER.findall(out)} - {idnum(k) for k in assets}
if missing:
    sys.exit("[merge] ERROR: source would reference ids not in the bundle: %s" % sorted(missing))

if a.dry_run:
    print("[merge] dry run - nothing written")
    print("[merge] would add %.0f KB to the bundle, remove %.0f KB from the source"
          % (sum(kb(l) for _, _, l in added), (len(src) - len(out)) / 1024))
    sys.exit(0)

if not added and not reused:
    sys.exit(0)

# ---------- write ------------------------------------------------------------
shutil.copyfile(a.src, a.src + ".bak")
if os.path.exists(assets_path):
    shutil.copyfile(assets_path, assets_path + ".bak")
os.makedirs(os.path.dirname(assets_path), exist_ok=True)
with open(assets_path, "w", encoding="utf-8") as f:
    json.dump(assets, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
open(a.src, "w", encoding="utf-8").write(out)

print("[merge] source %,d -> %,d bytes  (-%.0f KB)".replace(",", "") % (len(src), len(out), (len(src) - len(out)) / 1024))
print("[merge] bundle now holds %d assets" % len(assets))
print("[merge] backups: %s.bak, %s.bak" % (a.src, assets_path))
print("[merge] next: python3 build.py")
