# Academic Battle Cards — split source (v11.13)

The game ships as **one self-contained `.html`**. This repo keeps that file
*split* so day-to-day work never touches the ~14 MB of embedded art:

```
src/game.src.html    the game — markup, CSS, JS engine, card/trivia DATA.
                     ~1 MB, contains ZERO base64. This is the only file you edit.
assets/assets.json   { "a0": "<base64>", ... } every embedded image. ~14 MB. Rarely changes.
manifest.json        record of every asset (id, type, size, sha256, occurrences).
build.py             re-inlines assets -> dist/…​.html   (deterministic, no deps).
play.html            fullscreen wrapper that loads dist/academic_battle_cards.html.
dist/                build output (the file you deploy). stub.html is not committed.

tools/               engine checks: run_tests.sh, validate.js, static card-text checks,
                     battle suites (mechanics, lenses, conditionals, …).
tests/               UI + regression suites (builder, hand fan, Pagemaster, logs, …).
sync/                TSV exports of characters / trivia / first editions.
scripts/             reusable tools: deck + catalog sync, card export, asset merge/shrink,
                     trivia audit, print sheet.
scripts/patches/     one-off apply_*/fix_*/add_* scripts, kept for history. They have
                     already been applied to src; most expect to be run from the repo
                     root against older file layouts, so don't re-run them blindly.
art/                 source portraits and backgrounds (already inlined in assets.json).
```

In `src`, every image is a placeholder like `data:image/png;base64,__ABCASSET_12__`.
`build.py` swaps those for the real payloads. **Guarantee:** with unchanged
`assets.json`, the build is byte-for-byte identical every time, so the art and
the `DATA` block are *structurally* incapable of drifting — that's what lets the
everyday validation stay light.

## Everyday loop (the cheap, safe one)

Development needs **no assets** — images don't affect game logic, so a *stub*
build (every image = a 1×1 pixel, ~750 KB) boots and plays identically:

```bash
# 1. edit src/game.src.html   (base64-free — quick to read + diff)
# 2. stub build — no assets.json required
python3 build.py --stub
# 3. quick check: compiles every script + boots the Main Menu (seconds)
node tools/validate.js --quick dist/stub.html
#    milestones: --full  (adds bg hook + a battle + turn cycle + scrim map)
```

## Tests

Needs Node 18+ and Python 3. Once, from the repo root: `npm install` (jsdom).

```bash
npm test          # same as: bash tools/run_tests.sh
```

This builds the stub, compiles every script block, then runs the static
card-text checks, the battle suites in `tools/`, and every `tests/*.test.js`.
It ends with `ALL GREEN` or lists what failed.

Content counts in the static checks (`ROSTER_MIN`, `TEXTS_MIN`, `COND_MIN`)
are **floors**: adding characters never breaks them, losing one does. Raise
them when you add a deck so they keep guarding the new cards.

To produce the **deployable** (real art inlined), run the real build where
`assets/assets.json` lives — i.e. your local repo checkout:

```bash
python3 build.py                 # -> dist/academic_battle_cards.html
node tools/validate.js --full dist/academic_battle_cards.html
```

## Changing or adding art (no code edits)

1. Add the new blob to `assets/assets.json` under a fresh id (e.g. `"a117"`).
2. Reference it in `src` as `data:image/png;base64,__ABCASSET_117__`.
3. `python3 build.py` && validate. Log it in `manifest.json` if you like.

Never hand-edit the base64 in `src` — that's the whole point of the split.

## Working with Claude (token-saving)

Claude can't hold your GitHub token, so it won't clone or push this **private**
repo — and `assets/assets.json` (4.7 MB) is too big for the project folder.
Neither matters, because **Claude never needs the real assets**:

- Put only the small files into the Claude **project files** (they persist, no
  re-uploading): **`src/game.src.html`, `build.py`, `tools/validate.js`**
  (`manifest.json` optional). `assets/assets.json` stays in your repo only.
- Each session Claude edits `src`, runs **`build.py --stub`** (1×1-pixel images,
  no assets needed), validates the stub, and returns the updated `src` + a
  `git`-ready patch. The 4.7 MB never enters Claude's context.
- You `git push` the patch, then run the **real** `python3 build.py` locally
  (your checkout has `assets.json`) to get the deployable, and refresh `src` in
  the project folder.

So: Claude owns game logic (validated on the stub); your local build owns final
asset integrity (`build.py` errors on any missing/unresolved asset, and the
output sha is printed for a milestone checksum).

*(If you ever make the repo public, Claude can `git pull` it directly each
session and skip the manual `src` hand-off.)*

## Deploy (GitHub Pages)

`dist/academic_battle_cards.html` is the deployable. Point Pages at wherever you
serve it (e.g. copy to `docs/index.html` on a release, or build in an Action).
The release build in `dist/` is committed so Pages (and `play.html`) can serve
straight from the repo; only the throwaway `dist/stub.html` is git-ignored.

## Provenance

`src` + `assets.json` in this commit rebuild **demo_11_13** exactly:
`sha256 = 9965f0747feda783fb6a3504b75d119b4fbaa94062dbe6337df5f367135e9ae2`
