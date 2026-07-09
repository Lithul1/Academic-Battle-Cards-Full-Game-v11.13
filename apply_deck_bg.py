#!/usr/bin/env python3
"""Embed per-deck card backgrounds into assets/assets.json.

Deck backgrounds occupy a RESERVED asset-id block (900-910) so they can never
collide with portrait ids, which auto-increment from the low end. The matching
CSS in src/game.src.html references these ids as
    background: ... url("data:image/png;base64,__ABCASSET_<id>__") ...

Usage (from the repo root):
    python3 apply_deck_bg.py            # inject every art file it can find
    python3 apply_deck_bg.py && python3 build.py

Drop each deck's borderless PNG in the repo root or a `deck_bg/` folder. Files
that aren't present yet are skipped with a note, so you can add one deck at a
time. Re-running is safe (idempotent).

Auto-optimize: if Pillow is installed, each image is downsized to a sensible
card resolution and re-compressed before embedding (keeps the final HTML lean).
If Pillow is NOT installed, the file is embedded as-is -- so pre-optimized art
still works with zero dependencies.
"""
import os, sys, json, base64, io

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets", "assets.json")
SRC = os.path.join(ROOT, "src", "game.src.html")

# deck  ->  (reserved asset id 900-910, source PNG filename)
DECKS = {
    "gatsby":       (900, "Gatsby_Card_Background_B.png"),
    "crucible":     (901, "Crucible_Card_Background.png"),   # awaiting art
    "hamlet":       (902, "hamlet_background_a.png"),
    "frankenstein": (903, "Frankenstein_background_b.png"),
    "sherlock":     (904, "Sherlock_background_b.png"),
    "othello":      (905, "Othello_background_a.png"),
    "macbeth":      (906, "macbeth_background_a.png"),
    "wonderland":   (907, "Wonderland_background_a.png"),
    "oz":           (908, "oz_background_b.png"),
}

# folders searched for each PNG (first match wins)
ART_DIRS = [ROOT, os.path.join(ROOT, "deck_bg"), os.path.join(ROOT, "assets", "deck_bg")]

OPTIMIZE = True       # downsize + recompress when Pillow is available
MAX_EDGE = 680        # longest side after downscale
QUANT_COLORS = 256    # palette size for quantization


def find_art(fname):
    for d in ART_DIRS:
        p = os.path.join(d, fname)
        if os.path.isfile(p):
            return p
    return None


def optimize(raw):
    """Return (bytes, note). Falls back to raw bytes if Pillow is unavailable
    or anything goes wrong -- optimization must never break the build."""
    if not OPTIMIZE:
        return raw, "as-is"
    try:
        from PIL import Image
    except Exception:
        return raw, "as-is (Pillow not installed)"
    try:
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        w, h = im.size
        scale = min(1.0, MAX_EDGE / max(w, h))
        if scale < 1.0:
            im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        im = im.quantize(colors=QUANT_COLORS, method=Image.FASTOCTREE,
                         dither=Image.FLOYDSTEINBERG)
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        out = buf.getvalue()
        return (out, "optimized") if len(out) < len(raw) else (raw, "as-is (already small)")
    except Exception as e:
        return raw, f"as-is (optimize failed: {e})"


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
        data, note = optimize(open(path, "rb").read())
        b64 = base64.b64encode(data).decode("ascii")
        key = f"a{aid}"
        prev = assets.get(key)
        assets[key] = b64
        state = "unchanged" if prev == b64 else ("updated" if prev else "added")
        added.append((deck, key, len(b64), state, note, path))
        if src and f"__ABCASSET_{aid}__" not in src:
            print(f"[deck_bg] WARN: src does not reference __ABCASSET_{aid}__ "
                  f"(deck '{deck}'). The CSS wiring may be missing.")

    json.dump(assets, open(ASSETS, "w", encoding="utf-8"), ensure_ascii=False)

    for deck, key, n, state, note, path in added:
        print(f"[deck_bg] {deck:12} -> {key}  ({n:,} b64 chars, {state}, {note})")
    for deck, fname in skipped:
        print(f"[deck_bg] {deck:12} -> skipped (no art file '{fname}' yet)")
    print(f"[deck_bg] assets.json now holds {len(assets)} entries.")


if __name__ == "__main__":
    main()
