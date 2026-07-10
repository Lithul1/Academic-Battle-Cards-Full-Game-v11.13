#!/usr/bin/env python3
# repair_boss_art.py — fixes boss art (a909 Dyefone, a910 Sandroid, a911 Sinsta-Ram)
# that isn't showing in-game. The old apply_boss_art.py stored a full data: URI, which
# build.py then double-prefixed (data:image/webp;base64,data:image/webp;base64,...),
# producing a broken image. This strips any leading data-URI prefix so the stored value
# is RAW base64 (what build.py expects). Idempotent: safe to run even if already correct.
# Usage from repo root:  python3 repair_boss_art.py  &&  python3 build.py
import json, os, sys, base64
root=os.path.dirname(os.path.abspath(__file__)); AJ=os.path.join(root,"assets","assets.json")
if not os.path.exists(AJ): sys.exit("[repair] assets/assets.json not found - run from the repo root.")
a=json.load(open(AJ))
def raw_only(v):
    i=v.find('base64,'); return v[i+7:] if i!=-1 else v
fixed=[]; missing=[]
for k in ("a909","a910","a911"):
    if k not in a: missing.append(k); continue
    nv=raw_only(a[k])
    # if there is STILL a data: prefix after one strip (double-prefixed), strip again
    nv=raw_only(nv)
    # sanity: WebP magic is 'RIFF'....'WEBP'; decoded head should start with RIFF
    try:
        head=base64.b64decode(nv[:12]+'==')
        ok = head[:4]==b'RIFF'
    except Exception:
        ok=False
    if a[k]!=nv:
        a[k]=nv; fixed.append(k+(' (valid WebP)' if ok else ' (WARNING: not WebP after repair)'))
    else:
        fixed.append(k+' (already raw'+(' + valid WebP)' if ok else ', but not valid WebP - re-apply source)'))
json.dump(a,open(AJ,"w"))
print("[repair] boss art:", fixed)
if missing: print("[repair] NOT in assets.json (need apply_boss_art from source):", missing)
print("[repair] done. Next: python3 build.py")
