#!/usr/bin/env python3
"""fix_repo_docs.py -- README/build.py doc refresh + retire superseded asset bundles.

Run once from the repo root:   python3 fix_repo_docs.py

  1. README.md   - rewrites "Working with Claude" (stale 4.7 MB figures, old
                   hand-off flow), documents assets/_superseded/, and replaces
                   the demo_11_13 provenance sha with the current build's.
  2. build.py    - docstring only ("4.7MB bundle" -> "~14 MB bundle"). Build
                   output is unchanged.
  3. assets/     - moves the 8 assets_*.json side bundles into
                   assets/_superseded/ (git-ignored, kept on disk). Each one is
                   verified first: every key must already exist in assets.json
                   (newer WebP payload) or every blob must match one there.
                   Nothing is deleted; git history keeps the originals.

Idempotent: refuses to run twice. Writes .bak copies of every edited file.
"""
import os, sys, json, glob, shutil, re

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
MARK = "<!-- fix_repo_docs applied -->"

def die(msg): sys.exit(f"[fix_repo_docs] ABORT: {msg}")

for p in ("README.md", "build.py", "assets/assets.json", "src/game.src.html", ".gitignore"):
    if not os.path.exists(p): die(f"missing {p} -- run from the repo root")

readme = open("README.md", encoding="utf-8").read()
if MARK in readme: die("already applied (marker found in README.md)")

# ---------- README anchors ----------
A_ART  = "art/                 source portraits and backgrounds (already inlined in assets.json).\n"
A_WC0  = "## Working with Claude (token-saving)\n"
A_WC1  = "## Deploy (GitHub Pages)\n"
A_PROV = "`src` + `assets.json` in this commit rebuild **demo_11_13** exactly:\n`sha256 = 9965f0747feda783fb6a3504b75d119b4fbaa94062dbe6337df5f367135e9ae2`\n"
for name, a in (("art line", A_ART), ("Working with Claude", A_WC0), ("Deploy", A_WC1), ("Provenance", A_PROV)):
    if readme.count(a) != 1: die(f"README anchor not found exactly once: {name}")

NEW_ART = A_ART + ("assets/_superseded/  older side bundles (assets_*.json) whose payloads were merged into\n"
                   "                     assets.json and re-encoded as WebP. Git-ignored; safe to delete.\n")

NEW_WC = """## Working with Claude

Claude never needs the real assets -- game logic is validated on the stub build.
Two ways to hand it the code:

- **Connected folder (Cowork):** connect this repo folder in the Claude desktop
  app. Claude reads `src/`, runs `npm test` on a scratch copy, and drops
  `fix_*.py` patch scripts in the repo root for you to run. It does not commit
  or push -- you do that in GitHub Desktop.
- **Project files:** if the folder isn't connected, keep the small files in the
  Claude project (`src/game.src.html`, `build.py`, `tools/validate.js`,
  optionally `manifest.json`). `assets/assets.json` (~14 MB) stays in the repo.

Either way: Claude owns game logic (validated on the stub); your local
`python3 build.py` owns final asset integrity -- it errors on any
missing/unresolved asset and prints the output sha for a milestone checksum.

"""

NEW_PROV = ("As of commit `705edae` (2026-10-04), `src` + `assets.json` rebuild\n"
            "`dist/academic_battle_cards.html` exactly (16,171,137 bytes):\n"
            "`sha256 = 7ee74378da910002db665c7cec43df782e92f961bc04e2d15be9439425c1bce6`\n\n"
            "Any change to `src` or `assets.json` changes this -- update it on a release.\n")

i0, i1 = readme.index(A_WC0), readme.index(A_WC1)
if i1 < i0: die("README sections out of order")
new_readme = readme[:i0] + NEW_WC + readme[i1:]
new_readme = new_readme.replace(A_ART, NEW_ART).replace(A_PROV, NEW_PROV)
new_readme = new_readme.rstrip("\n") + "\n\n" + MARK + "\n"

# ---------- build.py anchor ----------
build = open("build.py", encoding="utf-8").read()
A_B = "when the 4.7MB bundle isn't on hand."
if build.count(A_B) != 1: die("build.py docstring anchor not found")
new_build = build.replace(A_B, "when the ~14 MB bundle isn't on hand.")

# ---------- asset bundles: verify all before moving any ----------
main = json.load(open("assets/assets.json"))
vals = set(main.values())
src_ids = {"a" + x for x in re.findall(r"__ABCASSET_(\d+)__", open("src/game.src.html", encoding="utf-8").read())}
if src_ids - set(main): die(f"src references ids missing from assets.json: {sorted(src_ids - set(main))[:5]}")
side = sorted(glob.glob("assets/assets_*.json"))
for f in side:
    d = json.load(open(f))
    if not isinstance(d, dict) or not d: die(f"{f}: unexpected format")
    keys_ok  = all(k in main for k in d)
    blobs_ok = all(isinstance(v, str) and v in vals for v in d.values())
    if not (keys_ok or blobs_ok): die(f"{f}: has content not in assets.json -- not moving anything")
print(f"[fix_repo_docs] verified {len(side)} side bundle(s) are superseded by assets.json")

# ---------- write ----------
for p, txt in (("README.md", new_readme), ("build.py", new_build)):
    shutil.copy2(p, p + ".bak")
    open(p, "w", encoding="utf-8").write(txt)
    print(f"[fix_repo_docs] updated {p}  (backup: {p}.bak)")

gi = open(".gitignore", encoding="utf-8").read()
if "assets/_superseded/" not in gi:
    shutil.copy2(".gitignore", ".gitignore.bak")
    open(".gitignore", "a", encoding="utf-8").write(
        ("" if gi.endswith("\n") else "\n") +
        "\n# asset bundles already merged into assets/assets.json (see README)\nassets/_superseded/\n")
    print("[fix_repo_docs] .gitignore: added assets/_superseded/")

if side:
    os.makedirs("assets/_superseded", exist_ok=True)
    for f in side:
        dst = os.path.join("assets/_superseded", os.path.basename(f))
        if os.path.exists(dst): die(f"{dst} already exists")
        os.rename(f, dst)
        print(f"[fix_repo_docs] moved {f} -> {dst}")

print("[fix_repo_docs] done. Commit in GitHub Desktop (README, build.py, .gitignore, 8 assets_*.json removals).")
