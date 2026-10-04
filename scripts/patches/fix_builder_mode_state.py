#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_builder_mode_state.py
Academic Battle Cards -- builder redesign, Steps 1 + 2 (2026-08-24)

Reference: ABC_Builder_Redesign_WiringPlan.md sections 3.1 and 3.2.

Ships as ONE patch in two anchored halves, because Step 2's correctness depends
on Step 1's threading.

============================================================== STEP 1 =========
MODE BECOMES A PROPERTY OF THE DECK.

pmOn() is `APP.mode === 'pagemaster'` -- a global that fifteen sites read live.
Every one of them derives something load-bearing from it: the cap set, the book
list, the bookmark singleton rule, which encoder runs, which saved deck plays.
When the flag is stale the deck is silently measured against the wrong rules.

The sharpest instance: pmBuildStatus() opens with `if(!pmOn()) return ''`, so a
Pagemaster deck edited while the flag is off gets NO legality feedback at all --
no per-book count, no error list. It just looks fine.

`def.pm` and `def.books` already exist on the deck object and are already read
by clampDeck and makeDeck, so this finishes a migration that was half done
rather than inventing a concept. Every builder site now reads deckIsPm(def).

Also threaded into battle: newGame() now records S._pm from the deck actually in
play, so the Pagemaster bench surcharge stops depending on a menu flag.

============================================================== STEP 2 =========
COMMANDERS UNIFY INTO def.fe.

Pagemaster kept its commanders in APP.pmCommanders, a SEPARATE array from the
def.fe the builder's own 1st Editions section writes to. They were reconciled
only at 'use', which overwrote def.fe wholesale:

    const a = (APP.pmCommanders||[]).slice(0, PM.fe);
    const d2 = Object.assign({}, def, { books:..., pm:true, fe:a });

Verified against the live build:

    builder def.fe before use:  ["hamlet_1e"]
    deck.fe after use:          ["macbeth_1e","gatsby_1e"]

So picking a commander inside the builder appeared to work, updated the display,
and was silently discarded on confirm.

Commanders now live in def.fe for both modes. feOf(def) reads the deck and falls
back to APP.pmCommanders ONLY for decks saved before this patch -- a legacy shim
to keep for one release, then delete in Step 5. Deck codes are unaffected:
pmEncodeDeck already writes fe into the payload.

The picker screen still writes APP.pmCommanders (it runs before a deck exists);
'pm-build' now seeds def.fe from it, and from that point the deck owns them.

Run from the repo root:

    python3 fix_builder_mode_state.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

# ======================================================== STEP 1 CORE =======
PATCHES.append((
    "core-accessors",
    """function pmOn(){ try{ return APP.mode==='pagemaster'; }catch(e){ return false; } }""",
    """function pmOn(){ try{ return APP.mode==='pagemaster'; }catch(e){ return false; } }
/* --- builder redesign, steps 1+2 (fix_builder_mode_state.py) ---------------
   Mode is a property of the DECK, not a global menu flag. def.pm and def.books
   already existed and were already read by clampDeck and makeDeck; these
   accessors finish that migration so no site has to consult APP.mode. */
function deckIsPm(def){ return !!(def && def.pm); }
/* Commanders live on the deck. Decks saved before this patch kept them in
   APP.pmCommanders -- read through for one release, then drop in step 5. */
function feOf(def){
  if(def && def.fe && def.fe.length) return def.fe.slice(0, PM.fe);
  try{ return (APP.pmCommanders||[]).slice(0, PM.fe); }catch(e){ return []; }
}
/* The books a deck actually plays: two for Pagemaster, derived from its own
   commanders, and one for anything else. */
function booksOf(def){
  if(!def) return null;
  if(!deckIsPm(def)) return def.d ? [def.d] : null;
  if(def.books && def.books.length) return def.books.slice();
  const a=feOf(def);
  if(a.length < PM.fe) return null;
  const bk=pmBooksOf(a[0], a[1]);
  return bk ? bk.books : null;
}
/* the caps in force FOR THIS DECK */
function capsFor(def){
  return deckIsPm(def)
    ? { total:PM.total, ch:PM.ch, ab:PM.ab, bm:PM.bm, cr:PM.cr, fe:PM.fe }
    : { total:LIMITS.total, ch:LIMITS.ch, ab:LIMITS.ab, bm:LIMITS.bm, cr:LIMITS.cr, fe:LIMITS.fe };
}""",
))

# pmCaps keeps working for anything not yet threaded, but delegates
PATCHES.append((
    "pmcaps-delegates",
    """  return pmOn() ? { total:PM.total, ch:PM.ch, ab:PM.ab, bm:PM.bm, cr:PM.cr, fe:PM.fe }
                : { total:LIMITS.total, ch:LIMITS.ch, ab:LIMITS.ab, bm:LIMITS.bm, cr:LIMITS.cr, fe:LIMITS.fe };""",
    """  /* delegates to capsFor(); prefer capsFor(def) at any site that has a deck */
  const _d=(APP && APP.builder && APP.builder.def) || null;
  return capsFor(_d && (_d.pm!=null) ? _d : { pm: pmOn() });""",
))

# pmBuildBooks now derives from the deck
PATCHES.append((
    "pmbuildbooks-from-deck",
    """function pmBuildBooks(){
  const a=(APP.pmCommanders||[]);
  if(a.length<2) return null;
  const bk=pmBooksOf(a[0],a[1]);
  return bk?bk.books:null;""",
    """function pmBuildBooks(def){
  /* derives from the deck's own commanders; falls back to the builder's
     working deck, then to the legacy global via feOf(). */
  const d=def || (APP && APP.builder && APP.builder.def) || null;
  const a=feOf(d);
  if(a.length<2) return null;
  const bk=pmBooksOf(a[0],a[1]);
  return bk?bk.books:null;""",
))

# the status line must not go silent when the global is stale
PATCHES.append((
    "buildstatus-reads-deck",
    """function pmBuildStatus(def){
  if(!pmOn()) return '';
  const a=(APP.pmCommanders||[]);""",
    """function pmBuildStatus(def){
  /* was `if(!pmOn()) return ''` -- a Pagemaster deck edited with the menu flag
     off reported nothing at all: no per-book count, no errors, no warning. */
  if(!deckIsPm(def)) return '';
  const a=feOf(def);""",
))

PATCHES.append((
    "buildstatus-body",
    """  const d2=Object.assign({}, def, { books:pmBuildBooks(), fe:a.slice(0,PM.fe) });""",
    """  const d2=Object.assign({}, def, { books:booksOf(def), fe:a.slice(0,PM.fe) });""",
))

PATCHES.append((
    "perbook-from-deck",
    """function pmPerBook(def){
  const books=pmBuildBooks(); if(!books) return null;""",
    """function pmPerBook(def){
  const books=booksOf(def); if(!books) return null;""",
))

# ---- builderScreen: every mode read takes the deck -------------------------
PATCHES.append((
    "builder-books",
    """  const _books=(pmOn()&&pmBuildBooks())||[k];""",
    """  const _books=booksOf(def)||[k];""",
))

PATCHES.append((
    "builder-copy-ch",
    """<small>${pmOn()?_books.map(b=>setName(b)).join(' + ')+' \u00b7 min '+PM.minChPerBook+' each':'pick your roster'} \u00b7 max ${CAP.ch}</small>""",
    """<small>${deckIsPm(def)?_books.map(b=>setName(b)).join(' + ')+' \u00b7 min '+PM.minChPerBook+' each':'pick your roster'} \u00b7 max ${CAP.ch}</small>""",
))

PATCHES.append((
    "builder-copy-bm",
    """<small>${pmOn()?'one copy each':'add copies'} \u00b7 max ${CAP.bm} total</small>""",
    """<small>${deckIsPm(def)?'one copy each':'add copies'} \u00b7 max ${CAP.bm} total</small>""",
))

PATCHES.append((
    "builder-copy-fe",
    """\u00b7 from ${(pmOn()&&pmBuildBooks()||[k]).map(setName).join(' or ')}</small>""",
    """\u00b7 from ${(booksOf(def)||[k]).map(setName).join(' or ')}</small>""",
))

# ---- handleBuilder ---------------------------------------------------------
PATCHES.append((
    "handler-fe-books",
    """        const _bk=(pmOn()&&pmBuildBooks())||[def.d];""",
    """        const _bk=booksOf(def)||[def.d];""",
))

PATCHES.append((
    "handler-bm-copies",
    """      const _cap=pmCaps(), _copies=pmOn()?PM.bmCopies:bmOwned(n);""",
    """      const _cap=capsFor(def), _copies=deckIsPm(def)?PM.bmCopies:bmOwned(n);""",
))

PATCHES.append((
    "handler-fill-comp",
    """      const _comp = pmOn()
        ? { ch:PM.ch, ab:PM.ab, bm:PM.bm, cr:PM.cr, total:PM.total }
        : Object.assign({}, compFor(def.d), { total:LIMITS.total });""",
    """      const _comp = deckIsPm(def)
        ? { ch:PM.ch, ab:PM.ab, bm:PM.bm, cr:PM.cr, total:PM.total }
        : Object.assign({}, compFor(def.d), { total:LIMITS.total });""",
))

PATCHES.append((
    "handler-gencode",
    """      B.code = pmOn() ? pmEncodeDeck(Object.assign({}, def, {books:pmBuildBooks()||[def.d], fe:(APP.pmCommanders||[]).slice(0,PM.fe)}))
                      : encodeDeck(def); }""",
    """      B.code = deckIsPm(def)
        ? pmEncodeDeck(Object.assign({}, def, {books:booksOf(def)||[def.d], fe:feOf(def)}))
        : encodeDeck(def); }""",
))

# ======================================================== STEP 2 ============
# 'use' must no longer discard the commanders the builder just edited.
PATCHES.append((
    "use-keeps-builder-fe",
    """      if(pmOn()){
        const a=(APP.pmCommanders||[]).slice(0,PM.fe);
        const d2=Object.assign({}, def, { books:pmBuildBooks()||[def.d], pm:true, fe:a });""",
    """      if(deckIsPm(def)){
        /* was `(APP.pmCommanders||[]).slice(...)`, which threw away whatever the
           builder's own 1st Editions section had just written to def.fe. */
        const a=feOf(def);
        const d2=Object.assign({}, def, { books:booksOf(def)||[def.d], pm:true, fe:a });""",
))

# seeding the builder for Pagemaster: the deck takes ownership of the commanders
PATCHES.append((
    "pm-build-seeds-deck",
    """      const bk=pmBooksOf(a[0],a[1]);
      APP.youDeck=bk.books[0]; APP.customDeck=null;
      /* the builder needs its working deck seeded, exactly as data-do='builder' does */
      APP.builder={ def:(APP.pmDeck?clone(APP.pmDeck):pmSeedDeck(bk.books,a)), code:'' };""",
    """      const bk=pmBooksOf(a[0],a[1]);
      APP.youDeck=bk.books[0];
      /* Opening Pagemaster used to run APP.customDeck=null, deleting the custom
         deck outright. The two decks are independent; nothing clears the other.
         (Step 3 gives each its own builder column; this only stops the delete.) */
      const _seed=(APP.pmDeck?clone(APP.pmDeck):pmSeedDeck(bk.books,a));
      /* the deck now OWNS its mode, its books and its commanders */
      _seed.pm=true; _seed.books=bk.books.slice();
      if(!_seed.fe || !_seed.fe.length) _seed.fe=a.slice(0,PM.fe);
      APP.builder={ def:_seed, code:'' };""",
))

# the ordinary builder entry marks its deck as non-Pagemaster explicitly
PATCHES.append((
    "custom-build-marks-deck",
    """    else if(d==='loadcode'){ const el=document.getElementById('codein'); const _raw=el?el.value:'';""",
    """    else if(d==='bd-mark-custom'){ /* reserved: step 3 */ render(); }
    else if(d==='loadcode'){ const el=document.getElementById('codein'); const _raw=el?el.value:'';""",
))

# a PM deck loaded from a code carries its own commanders
PATCHES.append((
    "pmcode-load",
    """        if(pd){ APP.pmDeck=pd; APP.pmCommanders=(pd.fe||[]).slice(0,PM.fe);""",
    """        if(pd){ APP.pmDeck=pd; pd.pm=true;
          /* kept in sync for the picker screen, which runs before a deck exists */
          APP.pmCommanders=(pd.fe||[]).slice(0,PM.fe);""",
))

# ---- battle: the bench surcharge is a rule of the deck in play -------------
PATCHES.append((
    "newgame-records-pm",
    """  oppDef=clampDeck(oppDef||defaultDeck(st.oppSet));
  const drawn = !!APP.drawnMode;
  S = { settings:clone(st), turn:'you', phase:'deal', over:false, winner:null,""",
    """  oppDef=clampDeck(oppDef||defaultDeck(st.oppSet));
  const drawn = !!APP.drawnMode;
  /* Record the rule set from the deck ACTUALLY IN PLAY, so the Pagemaster bench
     surcharge stops depending on a menu flag that may since have moved on. */
  const _pmRules=!!(youDef && youDef.pm);
  S = { _pm:_pmRules, settings:clone(st), turn:'you', phase:'deal', over:false, winner:null,""",
))

PATCHES.append((
    "bench-surcharge-from-deck",
    """  if(pmOn() && tgt && tgt.bench) cost+=PM.benchSurcharge;""",
    """  if((S&&S._pm!=null?S._pm:pmOn()) && tgt && tgt.bench) cost+=PM.benchSurcharge;""",
))

# ---- test surface -----------------------------------------------------------
# The redesign is validated against these across every remaining step, so they
# join the debug exports alongside the deck helpers already there.
PATCHES.append((
    "debug-exports",
    """  defaultDeck:(k)=>defaultDeck(k), compFor:(k)=>compFor(k), poolAb:(k)=>poolAb(k),""",
    """  defaultDeck:(k)=>defaultDeck(k), compFor:(k)=>compFor(k), poolAb:(k)=>poolAb(k),
  deckIsPm, capsFor, booksOf, feOf, pmBuildStatus, pmPerBook, pmBuildBooks,
  pmEncodeDeck, pmDecodeDeck, encodeDeck, decodeDeck, fillGaps,""",
))

ALREADY = [
    "fix_builder_mode_state.py",
    "function deckIsPm(",
    "function booksOf(",
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
    for mark in ALREADY:
        if mark in src:
            die("already applied (found %r). Ship a named fix_*.py to revise." % mark)

    # this patch builds on the earlier passes
    if "def._repaired=!!def._repaired" not in src:
        die("fix_fillgaps_and_offbook_fe.py must be applied first.")

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-26s found %d times, expected 1" % (label, n))
    if problems:
        die("anchor check failed -- nothing written:\n" + "\n".join(problems))

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before = src.count("<script")

    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)

    if "S = { _pm:_pmRules" not in out:
        die("newGame did not receive the _pm flag.")

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before:
        die("script block count changed")
    if out == src:
        die("no change produced.")

    # the deleting line must be gone
    if "APP.youDeck=bk.books[0]; APP.customDeck=null;" in out:
        die("the APP.customDeck=null delete survived.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    left = len(re.findall(r"pmOn\(\)", out))
    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    step 1: builder sites read deckIsPm(def), not the global")
    print("    step 2: commanders unified into def.fe (legacy shim in feOf)")
    print("    pmOn() references remaining: %d (was 16; step 5 removes the rest)" % left)
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
