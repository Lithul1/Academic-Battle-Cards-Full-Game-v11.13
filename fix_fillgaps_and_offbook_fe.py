#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_fillgaps_and_offbook_fe.py
Academic Battle Cards -- 2026-08-24

TWO INDEPENDENT FIXES, both found while prototyping the builder redesign.

-------------------------------------------------------------------- FIX 1 --
Fill Gaps could build an illegal deck.

fillGaps(def, comp) tops each section up to comp, falling back to LIMITS when
no comp is passed. The per-section LIMITS do not sum to the deck total:

    ch 14 + ab 36 + bm 20 + cr 4 + fe 2  =  76        LIMITS.total = 62

defaultDeck() is safe because it passes compFor(k), and every DECK_COMP entry
sums to 60 (+2 first editions = 62). But the builder's Fill Gaps button calls
fillGaps(def) with NO comp, so it filled to 76 -- fourteen cards over. clampDeck
then slices each section to its own cap and never checks the total, so nothing
downstream caught it.

Fixed at the call site (pass the deck's own composition: PM caps for a
Pagemaster deck, compFor(def.d) otherwise) AND defensively inside fillGaps,
which now refuses to push past the total. The internal guard cannot affect
defaultDeck: every composition sums to 60, so the ceiling is never reached.

-------------------------------------------------------------------- FIX 2 --
A Custom deck could carry a commander from a book it does not play.

clampDeck filters def.ch and def.ab to the deck's book(s) but checked def.fe
only for existence and ownership, never for book. So a Custom Gatsby deck could
anchor on the Macbeth commander -- a card whose deck synergies cannot fire,
because no Macbeth character is in the deck.

NOTE: this was DELIBERATE. The builder's own copy read "not locked to their
decks in Custom Play". Trevor reversed that decision on 2026-08-24. Consequences
worth knowing:

  * Existing saved Custom decks holding an off-book commander will have it
    stripped on load, and def._repaired is set so the player is told.
  * Shared deck codes containing one will load one commander short.
  * Pagemaster is unaffected: its books are DERIVED from its two commanders, so
    a commander is always in-book by construction.

Fixed in three places: clampDeck (the data-level repair), the builder's 'fe'
handler (refuses the pick, with a reason), and the section copy that advertised
the old rule.

Run from the repo root:

    python3 fix_fillgaps_and_offbook_fe.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

# ============================================================== FIX 1 =======
PATCHES.append((
    "fillgaps-total-guard",
    """function fillGaps(def, comp){
  const k=def.d;
  // comp is the deck's own composition; fall back to the builder ceiling
  const C = comp || { ch:LIMITS.ch, ab:LIMITS.ab, bm:LIMITS.bm, cr:LIMITS.cr };""",
    """function fillGaps(def, comp){
  const k=def.d;
  // comp is the deck's own composition; fall back to the builder ceiling
  const C = comp || { ch:LIMITS.ch, ab:LIMITS.ab, bm:LIMITS.bm, cr:LIMITS.cr };
  /* The per-section ceilings do not sum to the deck total (14+36+20+4+2 = 76
     against a total of 62), so filling every section to its own cap overfills
     by fourteen. Nothing downstream catches it: clampDeck slices per section
     and never checks the total. Bound every top-up by the remaining total.
     This cannot affect defaultDeck -- every DECK_COMP sums to 60. */
  const _totCap = (C.total || LIMITS.total || 62);
  const _room = () => _totCap - ((def.ch||[]).length + (def.ab||[]).length
                    + (def.bm||[]).length + (def.cr||[]).length + (def.fe||[]).length);""",
))

# each top-up loop gains the total bound
PATCHES.append((
    "fillgaps-ch-bound",
    """  while(def.ch.length<C.ch){ const miss=allCh.filter(id=>!def.ch.includes(id)); if(!miss.length) break; def.ch.push(miss[rnd(miss.length)]); }""",
    """  while(def.ch.length<C.ch && _room()>0){ const miss=allCh.filter(id=>!def.ch.includes(id)); if(!miss.length) break; def.ch.push(miss[rnd(miss.length)]); }""",
))
PATCHES.append((
    "fillgaps-ab-bound",
    """  while(def.ab.length<C.ab){ const miss=allAb.filter(i=>!def.ab.includes(i)); if(!miss.length) break; def.ab.push(miss[rnd(miss.length)]); }""",
    """  while(def.ab.length<C.ab && _room()>0){ const miss=allAb.filter(i=>!def.ab.includes(i)); if(!miss.length) break; def.ab.push(miss[rnd(miss.length)]); }""",
))
PATCHES.append((
    "fillgaps-cr-bound",
    """  while(def.cr.length<C.cr){ const miss=allCr.filter(i=>!def.cr.includes(i)); if(!miss.length) break; def.cr.push(miss[rnd(miss.length)]); }""",
    """  while(def.cr.length<C.cr && _room()>0){ const miss=allCr.filter(i=>!def.cr.includes(i)); if(!miss.length) break; def.cr.push(miss[rnd(miss.length)]); }""",
))
PATCHES.append((
    "fillgaps-bm-bound",
    """  while(def.bm.length<C.bm){""",
    """  while(def.bm.length<C.bm && _room()>0){""",
))

# the builder's button must pass a composition that actually sums to the total
PATCHES.append((
    "fill-callsite-comp",
    """  else if(op==='fill'){ fillGaps(def); clampDeck(def); B.code=''; toast('Filled gaps with random cards.'); }""",
    """  else if(op==='fill'){
      /* Pass the deck's OWN composition. Called bare, fillGaps fell back to the
         per-section LIMITS, which sum to 76 against a 62-card deck. Pagemaster
         caps already sum to 62 exactly; compFor() sums to 60 plus commanders. */
      const _comp = pmOn()
        ? { ch:PM.ch, ab:PM.ab, bm:PM.bm, cr:PM.cr, total:PM.total }
        : Object.assign({}, compFor(def.d), { total:LIMITS.total });
      fillGaps(def, _comp); clampDeck(def); B.code=''; toast('Filled gaps with random cards.'); }""",
))

# ============================================================== FIX 2 =======
PATCHES.append((
    "clampdeck-fe-book",
    """  def.fe=(def.fe||[]).filter(id=>firstedById(id)).filter((id,i,a)=>a.indexOf(id)===i).slice(0,LIMITS.fe);""",
    """  /* A commander must belong to a book this deck actually plays. ch and ab were
     already filtered to _bks; fe was not, so a Custom Gatsby deck could anchor
     on the Macbeth commander and none of its synergies could ever fire.
     Pagemaster is unaffected -- its books are derived from its commanders, so
     they are in-book by construction. */
  const _feWas=(def.fe||[]).length;
  def.fe=(def.fe||[]).filter(id=>firstedById(id))
    .filter(function(id){ const f=firstedById(id); return !f.deck || _bks.indexOf(f.deck)>=0; })
    .filter((id,i,a)=>a.indexOf(id)===i).slice(0,LIMITS.fe);
  if(def.fe.length<_feWas) def._repaired=true;""",
))

PATCHES.append((
    "builder-fe-handler",
    """  else if(op==='fe'){ if(!def.fe)def.fe=[]; const i=def.fe.indexOf(arg); if(i>=0) def.fe.splice(i,1); else if(def.fe.length<LIMITS.fe) def.fe.push(arg); B.code=''; }""",
    """  else if(op==='fe'){ if(!def.fe)def.fe=[]; const i=def.fe.indexOf(arg);
      if(i>=0){ def.fe.splice(i,1); }
      else if(def.fe.length<LIMITS.fe){
        /* refuse a commander from a book this deck does not play */
        const _f=firstedById(arg);
        const _bk=(pmOn()&&pmBuildBooks())||[def.d];
        if(_f && _f.deck && _bk.indexOf(_f.deck)<0){
          toast(_f.name+' belongs to '+setName(_f.deck)+' \\u2014 this deck plays '+_bk.map(setName).join(' + ')+'.');
        } else { def.fe.push(arg); }
      }
      B.code=''; }""",
))

PATCHES.append((
    "builder-fe-copy",
    """    <div class="bd-sec"><h3>1st Editions <small>Commander-style deck anchors \u00b7 pick up to ${LIMITS.fe} \u00b7 not locked to their decks in Custom Play</small></h3><div class="bd-grid ch">${feRow}</div></div>""",
    """    <div class="bd-sec"><h3>1st Editions <small>Commander-style deck anchors \u00b7 pick up to ${LIMITS.fe} \u00b7 from ${(pmOn()&&pmBuildBooks()||[k]).map(setName).join(' or ')}</small></h3><div class="bd-grid ch">${feRow}</div></div>""",
))

# ---------------------------------------------------------------------------
# Pre-existing bug found while testing FIX 2: this line ASSIGNS _repaired rather
# than OR-ing into it, so it silently overwrote the flag set moments earlier by
# the commander-ownership strip at the top of clampDeck. A deck that lost a
# commander it no longer owned was therefore repaired without ever telling the
# player. FIX 2's book strip would have been swallowed the same way.
PATCHES.append((
    "repaired-flag-clobber",
    """  def._repaired=(def.ch.length<_was.ch)||(def.ab.length<_was.ab)||(def.cr.length<_was.cr)||(def.bm.length<_was.bm);""",
    """  def._repaired=!!def._repaired||(def.ch.length<_was.ch)||(def.ab.length<_was.ab)||(def.cr.length<_was.cr)||(def.bm.length<_was.bm);""",
))

ALREADY = ["fillgaps-total-guard", "_totCap", "belongs to \'+setName(_f.deck)",
           "def._repaired=!!def._repaired"]


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

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-22s found %d times, expected 1" % (label, n))
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
    if out == src:
        die("no change produced.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    fix 1: Fill Gaps bounded by the deck total (was filling to 76/62)")
    print("    fix 2: commanders confined to the books their deck plays")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
