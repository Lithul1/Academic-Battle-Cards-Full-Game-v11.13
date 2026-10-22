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

### Browser tests (Playwright)

For behaviour only a real browser shows -- layout, dragging a slider, which
DOM nodes survive an update -- there are Playwright tests in `tests/e2e/`:

```bash
npx playwright install chromium   # once
npm run test:e2e                  # builds the stub, then runs tests/e2e in Chromium
```

A test that fails once and passes on its automatic retry is reported as
**flaky**, not failed. Its trace and screenshot stay in `test-results/` until
the next run — open the trace with the `npx playwright show-trace …` command
the run prints. The same test turning up flaky again means a real bug.

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

## Working with Claude

Claude validates game logic on the stub build and never needs `assets.json` (~14 MB).
With this folder connected in the Claude desktop app, Claude reads the repo directly,
tests on a scratch copy, and hands back small `fix_*.py` scripts plus the exact
terminal commands to run. You review, run, commit and push (GitHub Desktop).
Your local `python3 build.py` remains the check on final asset integrity.

## Deploy (GitHub Pages)

`dist/academic_battle_cards.html` is the deployable. Point Pages at wherever you
serve it (e.g. copy to `docs/index.html` on a release, or build in an Action).
The release build in `dist/` is committed so Pages (and `play.html`) can serve
straight from the repo; only the throwaway `dist/stub.html` is git-ignored.

## Provenance

`build.py` is deterministic: the same `src` + `assets.json` always give the same
file. It prints the output's sha256 -- paste that line into the release commit
message to record exactly what shipped.

<!-- fix_readme applied -->
