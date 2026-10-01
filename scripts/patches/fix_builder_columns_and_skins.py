#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_builder_columns_and_skins.py
Academic Battle Cards -- builder redesign, Step 3 + the Base/Mod fix (2026-08-24)

Reference: ABC_Builder_Redesign_WiringPlan.md sections 3.3 and 5.5.
Requires fix_builder_mode_state.py (steps 1+2) first.

=================================================== BASE/MOD (plan 5.5) =======
The expansion shelf presented a three-way cycle labelled

    Base only  ->  <Expansion>  ->  All (mixed)

but it was never a filter. Verified against the live build: all three
expansions are PURE RESKINS -- modern_hamlet, frankenstein_2077 and sengekokujo
contain zero characters that are not already in their base deck. A reskin is
the same character id wearing different art, so there is no separate card to
filter and `edFlt` never touched the character pool at all. Its only real
effects were:

    'modern' -> set EVERY eligible character to the reskin
    'base'   -> def.ed = {}          <-- wipes every per-card choice
    'all'    -> nothing whatsoever

So it was a bulk skin setter wearing a filter's clothes, and reaching "All
(mixed)" meant cycling THROUGH 'base', which silently destroyed every per-card
Base/Mod choice on the way past. With per-card toggles as the primary control
(they already exist: 'edbase' / 'edmod'), that is straightforward data loss.

Replaced with two explicit, non-destructive bulk actions -- "All Base" and
"All <Expansion>" -- plus a live count of how many characters are currently
modded. Nothing passes through a destructive intermediate state, and the
per-card toggles remain the granular control. `edFilter` is retained ONLY as
the cosmetic `.flt-*` class on the builder root, no longer as deck state.

========================================================= STEP 3 =============
TWO COLUMNS IN STATE, ONE ON SCREEN.

APP.builder held a single `def`, so the Pagemaster and Custom decks could not
coexist. Now:

    APP.builder = {
      active: 'pm' | 'cu',
      pm: { def, code },
      cu: { def, code },
      ...
    }

`APP.builder.def` and `.code` survive as accessor properties that read and write
the ACTIVE column, so all thirteen existing call sites keep working untouched --
the split is invisible to them. Switching column is one assignment.

Both columns are seeded on entry and neither is ever nulled. Confirm saves the
column it was pressed on and leaves the other intact, per the decision of
2026-08-24.

Run from the repo root:

    python3 fix_builder_columns_and_skins.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

# ============================================== STEP 3: column state ========
PATCHES.append((
    "builder-state-factory",
    """function deckIsPm(def){ return !!(def && def.pm); }""",
    """function deckIsPm(def){ return !!(def && def.pm); }
/* --- builder redesign, step 3 (fix_builder_columns_and_skins.py) -----------
   Two decks live side by side. `def` and `code` are accessors onto the ACTIVE
   column, so every existing call site that says APP.builder.def keeps working
   and the split stays invisible to them. Neither column is ever nulled. */
function makeBuilderState(pmDef, cuDef, active){
  const st = {
    active: (active==='pm') ? 'pm' : 'cu',
    pm: { def: pmDef || null, code: '' },
    cu: { def: cuDef || null, code: '' },
    edFilter: 'all', fanOpen: true
  };
  Object.defineProperty(st, 'def', {
    get(){ const c = st[st.active]; return c ? c.def : null; },
    set(v){ const c = st[st.active]; if(c) c.def = v; },
    enumerable: false, configurable: true
  });
  Object.defineProperty(st, 'code', {
    get(){ const c = st[st.active]; return c ? c.code : ''; },
    set(v){ const c = st[st.active]; if(c) c.code = v; },
    enumerable: false, configurable: true
  });
  return st;
}
/* focus a column, seeding it if it has never been opened */
function builderFocus(side){
  const B = APP.builder; if(!B || (side!=='pm' && side!=='cu')) return;
  if(!B[side].def){
    if(side==='cu'){
      const k=(APP.youDeck && APP.youDeck!=='surprise' && DATA.characters[APP.youDeck])
        ? APP.youDeck : DECK_ORDER[0];
      B.cu.def = APP.customDeck ? clone(APP.customDeck) : defaultDeck(k);
    } else {
      const a=(APP.pmCommanders||[]).slice(0,PM.fe);
      if(a.length<PM.fe){ toast('Choose two commanders first.'); return; }
      const bk=pmBooksOf(a[0],a[1]); if(!bk) return;
      const s=(APP.pmDeck?clone(APP.pmDeck):pmSeedDeck(bk.books,a));
      s.pm=true; s.books=bk.books.slice();
      if(!s.fe || !s.fe.length) s.fe=a;
      B.pm.def=s;
    }
  }
  B.active = side;
}""",
))

# ---- entry points seed a column instead of replacing the whole state -------
PATCHES.append((
    "entry-pagemaster",
    """      const _seed=(APP.pmDeck?clone(APP.pmDeck):pmSeedDeck(bk.books,a));
      /* the deck now OWNS its mode, its books and its commanders */
      _seed.pm=true; _seed.books=bk.books.slice();
      if(!_seed.fe || !_seed.fe.length) _seed.fe=a.slice(0,PM.fe);
      APP.builder={ def:_seed, code:'' };""",
    """      const _seed=(APP.pmDeck?clone(APP.pmDeck):pmSeedDeck(bk.books,a));
      /* the deck now OWNS its mode, its books and its commanders */
      _seed.pm=true; _seed.books=bk.books.slice();
      if(!_seed.fe || !_seed.fe.length) _seed.fe=a.slice(0,PM.fe);
      /* seed the Pagemaster column, keeping any Custom column already open */
      if(APP.builder && APP.builder.cu){ APP.builder.pm.def=_seed; APP.builder.pm.code=''; APP.builder.active='pm'; }
      else { APP.builder=makeBuilderState(_seed, null, 'pm'); }""",
))

PATCHES.append((
    "entry-custom",
    """APP.builder={ def:APP.customDeck?clone(APP.customDeck):defaultDeck(_k), code:'' }; APP.codeMsg=null; APP.screen='""",
    """const _cud=APP.customDeck?clone(APP.customDeck):defaultDeck(_k);
      if(APP.builder && APP.builder.cu){ APP.builder.cu.def=_cud; APP.builder.cu.code=''; APP.builder.active='cu'; }
      else { APP.builder=makeBuilderState(null, _cud, 'cu'); } APP.codeMsg=null; APP.screen='""",
))

# ---- switching columns -----------------------------------------------------
PATCHES.append((
    "column-switch-handler",
    """    else if(d==='bd-mark-custom'){ /* reserved: step 3 */ render(); }""",
    """    else if(d==='bdcol:pm'){ builderFocus('pm'); render(); }
    else if(d==='bdcol:cu'){ builderFocus('cu'); render(); }""",
))

# ---- confirm saves ITS column and leaves the other alone -------------------
PATCHES.append((
    "confirm-scoped-pm",
    """        APP.pmDeck=clone(d2); APP.youDeck=d2.books[0];
        APP.codeMsg={text:'Pagemaster deck ready.',ok:true};""",
    """        APP.pmDeck=clone(d2); APP.youDeck=d2.books[0];
        /* saves this column only; the Custom column keeps whatever it holds */
        if(APP.builder && APP.builder.pm) APP.builder.pm.def=clone(d2);
        APP.codeMsg={text:'Pagemaster deck ready.',ok:true};""",
))

# ============================================== BASE/MOD bulk actions =======
PATCHES.append((
    "edfilter-no-longer-writes-deck",
    """  else if(op==='edfilter'){ APP.builder.edFilter=arg;
    def.ed=def.ed||{};
    if(arg==='modern'){ (DATA.characters[def.d]||[]).forEach(function(ch){ if(edCharFor(def.d,ch.id)) def.ed[ch.id]='modern'; }); }
    else if(arg==='base'){ def.ed={}; }
    B.code=''; }""",
    """  else if(op==='edfilter'){
    /* Cosmetic only now. This used to double as a bulk skin setter, and
       cycling through 'base' to reach 'all' wiped def.ed -- every per-card
       Base/Mod choice, silently. Bulk changes are explicit actions below. */
    APP.builder.edFilter=arg; }
  else if(op==='edall'){
    /* explicit, non-destructive bulk skin actions */
    def.ed=def.ed||{};
    const _bks=booksOf(def)||[def.d];
    if(arg==='mod'){
      _bks.forEach(function(bk){ (DATA.characters[bk]||[]).forEach(function(ch){
        if(edCharFor(bk,ch.id)) def.ed[ch.id]='modern'; }); });
      toast('All eligible characters set to the expansion art.');
    } else {
      def.ed={};
      toast('All characters set to base art.');
    }
    B.code=''; }""",
))

PATCHES.append((
    "edcycle-retired",
    """  else if(op==='edcycle'){ var order=['base','modern','all']; var cur=B.edFilter||'all';
    var nx=order[(order.indexOf(cur)+1)%3]; handleBuilder('edfilter:'+nx); return; }""",
    """  else if(op==='edcycle'){
    /* retired: the old three-way cycle passed through a state that wiped
       def.ed. Kept as an alias so any stale markup degrades to a safe no-op. */
    var order=['base','modern','all'], cur=B.edFilter||'all';
    handleBuilder('edfilter:'+order[(order.indexOf(cur)+1)%3]); return; }""",
))

PATCHES.append((
    "expansion-shelf-buttons",
    """    ? '<button class="ebx '+(flt!=='base'?'on':'')+' flt-'+flt+'" data-bld="edcycle:'+k+'" title="Click to cycle: Base only \\u2192 '+e.name+' \\u2192 All">'
      +'<span class="ebx-im"><img src="'+(e.box||'')+'" alt="'+e.name+'"></span>'
      +'<span class="ebx-bdg">'+lbl+'</span></button>'
      +'<span class="ebx-note"><b>'+e.name+'</b> \\u00b7 '+n+'/'+tot+' collected<br><small>Click the box to cycle: <b>Base only</b> \\u2192 <b>'+e.name+'</b> \\u2192 <b>All</b> (mixed).</small></span>'""",
    """    ? '<button class="ebx on" data-bld="edall:mod" title="Set every eligible character to '+e.name+' art">'
      +'<span class="ebx-im"><img src="'+(e.box||'')+'" alt="'+e.name+'"></span>'
      +'<span class="ebx-bdg">All '+e.name+'</span></button>'
      +'<button class="ebx ebx-sm" data-bld="edall:base" title="Set every character back to base art">'
      +'<span class="ebx-bdg">All Base</span></button>'
      +'<span class="ebx-note"><b>'+e.name+'</b> \\u00b7 '+n+'/'+tot+' collected \\u00b7 '+edModCount()+' in this deck<br><small>These set every character at once. Use the <b>Base / Mod</b> switch on a character to mix them.</small></span>'""",
))

PATCHES.append((
    "edmodcount-helper",
    """function bdExpansionShelf(k,open){ var eds=editionsForDeck(k); if(!eds.length) return '';""",
    """/* how many characters in the working deck currently wear expansion art */
function edModCount(){
  try{
    var d=APP.builder&&APP.builder.def; if(!d||!d.ed) return 0;
    return Object.keys(d.ed).filter(function(id){ return d.ed[id]==='modern'; }).length;
  }catch(e){ return 0; }
}
function bdExpansionShelf(k,open){ var eds=editionsForDeck(k); if(!eds.length) return '';""",
))

# ---- test surface ----------------------------------------------------------
PATCHES.append((
    "debug-exports-step3",
    """  deckIsPm, capsFor, booksOf, feOf, pmBuildStatus, pmPerBook, pmBuildBooks,""",
    """  makeBuilderState, builderFocus, handleBuilder, edModCount, clone,
  deckIsPm, capsFor, booksOf, feOf, pmBuildStatus, pmPerBook, pmBuildBooks,""",
))

ALREADY = [
    "fix_builder_columns_and_skins.py",
    "function makeBuilderState(",
    "op==='edall'",
]


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    if "function deckIsPm(" not in src:
        die("fix_builder_mode_state.py (steps 1+2) must be applied first.")
    for mark in ALREADY:
        if mark in src:
            die("already applied (found %r). Ship a named fix_*.py to revise." % mark)

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-28s found %d times, expected 1" % (label, n))
    if problems:
        die("anchor check failed -- nothing written:\n" + "\n".join(problems))

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before = src.count("<script")

    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before:
        die("script block count changed")

    # the destructive wipe must be gone from the filter path
    if "else if(arg==='base'){ def.ed={}; }" in out:
        die("the def.ed wipe survived in the edfilter handler.")
    if out == src:
        die("no change produced.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    step 3: APP.builder holds pm + cu columns; def/code alias the active one")
    print("    base/mod: bulk actions are explicit; nothing wipes def.ed by accident")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
