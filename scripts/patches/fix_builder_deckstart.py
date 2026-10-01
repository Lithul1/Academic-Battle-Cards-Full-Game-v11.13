#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_builder_deckstart.py
Academic Battle Cards -- builder redesign, step 4 follow-up (2026-08-25)

Requires fix_builder_ui_layout.py.

------------------------------------------------ 1. PAGEMASTER WAS UNREACHABLE
The Pagemaster commander picker (`APP.screen='pmpick'`) has exactly one route
into it, at the difficulty screen:

    else if(APP.mode==='pagemaster'){ APP.screen='pmpick'; render(); }

There is no route from the Deck Builder. So the Pagemaster column could only
ever show "Choose two commanders in Pagemaster to open this deck" -- and
clicking it did nothing but toast the same sentence. A Pagemaster deck simply
could not be started from the builder, which is what Trevor hit.

Clicking the Pagemaster column now takes you to the picker, and `pm-build`
already returns to the builder with that column seeded and focused, so the loop
closes.

--------------------------------------------------- 2. "SELECT YOUR DECK TYPE"
The two columns sat flush with the top of the pool, which read as "here are two
decks" rather than "choose which ruleset you are building in". They now sit
below a heading aligned with the tab strip:

    Select your deck type to start

and each column is a click target with an explicit call to action while empty.

-------------------------------------------------- 3. TRIVIA IN TWO COLUMNS
The trivia grid was `repeat(auto-fill,minmax(226px,1fr))` and still rendered a
single column in Trevor's build. Rather than keep guessing at what auto-fill
resolves to across zoom levels and device pixel ratios, the column count is now
DECLARED per breakpoint. Deterministic beats clever here: every layout surprise
in this redesign so far has come from a rule that resolved differently than I
expected.

The trivia chips are also compacted -- tighter padding, a two-line clamp on the
question, a thinner accent bar -- so two sit side by side as small rectangles
rather than two tall slabs.

Run from the repo root:

    python3 fix_builder_deckstart.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

CSS = r"""
/* ===== builder step 4 follow-up (fix_builder_deckstart.py) =====
   Column counts are DECLARED, not inferred. auto-fill resolved to a single
   column in the field despite the arithmetic saying otherwise, and every
   layout surprise here has come from a rule resolving differently than
   expected. Explicit counts cannot drift. */
.bdk .bd-grid.ab{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
.bdk .bd-grid.ch{grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}
.bdk .bd-bmgrid{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}

/* compact trivia: a small rectangle, not a slab */
.bdk .bd-chip.ab{padding:6px 8px;gap:3px;border-top-width:4px;min-height:0}
.bdk .bd-chip.ab .bd-q{font-size:12px;line-height:1.25;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.bdk .bd-chip.ab .bd-ty{font-size:9.5px}
.bdk .bd-chip.ab .bd-pv{width:16px;height:16px;font-size:10px}

/* ---- the deck rail sits under its own heading, aligned with the tabs ---- */
.bdk-colhead{display:flex;align-items:center;justify-content:center;
  height:34px;margin-bottom:3px;padding:0 8px;
  font-family:var(--cond);font-size:12.5px;letter-spacing:1.1px;
  text-transform:uppercase;color:#6b5b45;text-align:center;line-height:1.15}
.bdk-cols{flex-direction:column}
.bdk-colrow{display:flex;gap:10px;align-items:flex-start}
.bdk-colrow>.bdk-col{flex:1;min-width:0}
/* an unopened column is a call to action, not a dead panel */
.bdk-col .bdk-start{display:block;width:calc(100% - 12px);margin:10px 6px;
  padding:9px 7px;border:2.5px dashed var(--ink,#241F1B);border-radius:7px;
  background:var(--cream-hi,#FBF3DD);cursor:pointer;font-family:var(--cond);
  font-size:12px;letter-spacing:.8px;text-transform:uppercase;line-height:1.3}
.bdk-col .bdk-start:hover{background:var(--gold,#E6B85C)}
.bdk-col:not(.on) h3{cursor:pointer}

@media (max-width:1400px){
  .bdk .bd-grid.ch{grid-template-columns:repeat(3,minmax(0,1fr))}
  .bdk .bd-bmgrid{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:1100px){
  .bdk-colhead{height:auto;margin-bottom:6px}
}
@media (max-width:760px){
  .bdk .bd-grid.ab{grid-template-columns:1fr}
  .bdk .bd-grid.ch{grid-template-columns:repeat(2,minmax(0,1fr))}
  .bdk .bd-bmgrid{grid-template-columns:1fr}
  .bdk-colrow{flex-direction:column}
}
"""

PATCHES = []

# ---- the rail gains a heading and a row wrapper --------------------------
PATCHES.append((
    "cols-heading",
    """      <div class="bdk-cols">
        ${bdColumn('pm')}
        ${bdColumn('cu')}
      </div>""",
    """      <div class="bdk-cols">
        <div class="bdk-colhead">Select your deck type to start</div>
        <div class="bdk-colrow">
          ${bdColumn('pm')}
          ${bdColumn('cu')}
        </div>
      </div>""",
))

# ---- an unopened column offers a way in ----------------------------------
PATCHES.append((
    "empty-column-cta",
    """  if(!def){
    return '<div class="bdk-col '+side+(on?' on':'')+'">'
      + '<h3 data-bld="bdfocus:'+side+'">'+title+'</h3>'
      + '<div class="bdk-empty">'+(side==='pm'
          ? 'Choose two commanders in Pagemaster to open this deck.'
          : 'Open the Custom builder to start this deck.')+'</div></div>';
  }""",
    """  if(!def){
    /* This used to be a dead panel: the Pagemaster picker has no route from the
       builder, so the message named a screen you could not get to from here. */
    return '<div class="bdk-col '+side+(on?' on':'')+'">'
      + '<h3 data-bld="bdfocus:'+side+'">'+title+'</h3>'
      + '<div class="bdk-empty">'+(side==='pm'
          ? 'Two commanders, two books, singleton bookmarks.'
          : 'One book, your own roster.')+'</div>'
      + '<button class="bdk-start" data-bld="bdfocus:'+side+'">'
      + (side==='pm' ? 'Choose two commanders \\u203a' : 'Start a Custom deck \\u203a')
      + '</button></div>';
  }""",
))

# ---- clicking the Pagemaster column routes to the picker -----------------
PATCHES.append((
    "focus-routes-to-picker",
    """    } else {
      const a=(APP.pmCommanders||[]).slice(0,PM.fe);
      if(a.length<PM.fe){ toast('Choose two commanders first.'); return; }""",
    """    } else {
      const a=(APP.pmCommanders||[]).slice(0,PM.fe);
      if(a.length<PM.fe){
        /* the picker is the only place commanders can be chosen, and the
           builder had no route into it. pm-build brings you back here with
           this column seeded and focused. */
        APP.mode='pagemaster'; APP.screen='pmpick'; render(); return;
      }""",
))

ALREADY = ["fix_builder_deckstart.py", "bdk-colhead", "Select your deck type"]


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    if ".builder.bdk{max-width" not in src:
        die("fix_builder_ui_layout.py must be applied first.")
    for mark in ALREADY:
        if mark in src:
            die("already applied (found %r). Ship a named fix_*.py to revise." % mark)

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-24s found %d times, expected 1" % (label, n))
    if problems:
        die("anchor check failed -- nothing written:\n" + "\n".join(problems))

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before = src.count("<script")
    st_before = src.count("<style")

    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)

    tail = out.rindex("</style>")
    out = out[:tail] + CSS + out[tail:]

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before or out.count("<style") != st_before:
        die("block counts changed")
    if out == src:
        die("no change produced.")

    # no auto-fill left deciding the builder's column count. Scope the check to
    # the CSS block itself -- the document past </style> legitimately contains
    # the string in other contexts.
    blk = out[out.rindex("/* ===== builder step 4 follow-up"):out.rindex("</style>")]
    blk_rules = re.sub(r"/\*[\s\S]*?\*/", "", blk)   # prose mentions it; rules must not
    if "auto-fill" in blk_rules:
        die("an auto-fill rule survived in the follow-up block.")
    for _sel in (".bdk .bd-grid.ab{", ".bdk .bd-grid.ch{", ".bdk .bd-bmgrid{"):
        if _sel not in blk:
            die("missing a declared column rule for %s" % _sel)

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    trivia       2 declared columns, compact chips (2-line clamp)")
    print("    characters   4 columns; bookmarks 3")
    print("    rail         'Select your deck type to start' heading + CTA buttons")
    print("    pagemaster   the column now routes to the commander picker")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
