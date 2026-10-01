#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_fe_full_merge.py
Academic Battle Cards -- issue 1 (full merge), 2026-08-23

DATA.firsteds is a static, base-only array of 30. Expansion commanders live in
EXPANSIONS[k].battle.commanders and EXPANSIONS[k].boosterPool.commanders.
firstedById() already falls through to them, but the twenty LIST call sites did
not, so expansion commanders were invisible to the Library, the Pagemaster
picker, Scrimmage, and the completion metric.

Approach, per the handoff's pattern-A rule: grep the class first, then fix it in
one place. Two new accessors carry the merge --

    feAll()   base firsteds ++ every expansion commander
    feHas(f)  ownership, spanning BOTH namespaces:
              expansion commanders are owned via edHas(f.cid) / META.editionCards
              base first editions via META.commanders

The two ownership namespaces are deliberately NOT unified. They mean different
things and are saved separately; the accessor spans them, it does not merge
them. This is the pattern-C trap the handoff warns about, so each call site
keeps exactly the ownership policy it had before -- only the POOL widens.

Pagemaster needs no change. Every expansion commander already carries a BASE
deck key (hamlet / frankenstein / macbeth), so they map onto existing book pools
and pagemasterLegal is unaffected. Pairings rise from C(30,2)=435 to C(40,2)=780
and remain buildable by construction, since the set of books is unchanged.

DELIBERATELY LEFT BASE-ONLY (confirmed with Trevor 2026-08-23):
  * feFor(k)                    -- starter decks stay starter decks
  * scrimRollPack cmdPool/rollCmd, and the tier-pack R pools
                                -- expansion commanders come from expansion
                                   portfolios; putting them in base packs would
                                   make them obtainable through two paths with
                                   two ownership namespaces

Also fixes a dev-menu bug found on the way: the "All 1st editions" button ran
Object.keys() on an ARRAY, writing ["0","1","2"...] into META.editionCards --
indices, and into the wrong namespace besides. It has never worked.

Run from the repo root:

    python3 fix_fe_full_merge.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

# ------------------------------------------------------------- the core ----
PATCHES.append((
    "merge-accessors",
    """function feFor(k){ return (DATA.firsteds||[]).filter(f=>f.deck===k).map(f=>f.id).slice(0,LIMITS.fe); }""",
    """/* feFor stays BASE-ONLY on purpose: it seeds starter decks, and a starter deck
   should not open with an expansion commander. */
function feFor(k){ return (DATA.firsteds||[]).filter(f=>f.deck===k).map(f=>f.id).slice(0,LIMITS.fe); }
/* ---- the First Edition roster, base + expansions (fix_fe_full_merge.py) ----
   Every expansion commander carries a BASE deck key, so everything downstream
   -- Pagemaster books, deck pools, set names -- works unchanged. */
function feExpansionCmds(){
  var out=[], E=window.EXPANSIONS||{};
  for(var k in E){ var ed=E[k]; if(!ed) continue;
    ((ed.battle&&ed.battle.commanders)||[]).forEach(function(c){ out.push(c); });
    ((ed.boosterPool&&ed.boosterPool.commanders)||[]).forEach(function(c){ out.push(c); });
  }
  return out;
}
function feAll(){ return (DATA.firsteds||[]).concat(feExpansionCmds()); }
/* Ownership spans two namespaces that mean different things and are saved
   separately: expansion cards live in META.editionCards keyed by cid, base
   first editions in META.commanders keyed by id. This reads both; it does not
   merge them. */
function feHas(f){
  if(!f) return false;
  if(sbx()) return true;
  if(f.cid) return edHas(f.cid);
  return (META.commanders||[]).indexOf(f.id)>=0;
}""",
))

# --------------------------------------------------- Pagemaster slot lookup ---
PATCHES.append((
    "pm-slot-lookup",
    """    const f=(DATA.firsteds||[]).find(function(x){ return x.id===pick[i]; });""",
    """    /* firstedById already spans expansions; the raw array lookup did not, so a
       chosen expansion commander rendered as an empty slot. */
    const f=firstedById(pick[i]);""",
))

# ------------------------------------------------------------ ownership ----
PATCHES.append((
    "fe-owned-expansion",
    """  var f=(DATA.firsteds||[]).find(function(x){ return x.id===id; });
  if(!f) return false;""",
    """  var f=(DATA.firsteds||[]).find(function(x){ return x.id===id; });
  if(!f){
    /* an expansion commander: owned through the edition namespace instead */
    var x=firstedById(id);
    return !!(x && x.cid && edHas(x.cid));
  }""",
))

PATCHES.append((
    "fe-owned-list",
    """function feOwnedList(){ return (DATA.firsteds||[]).filter(function(f){ return feOwned(f.id); }); }""",
    """function feOwnedList(){ return feAll().filter(function(f){ return feOwned(f.id); }); }""",
))

# ------------------------------------------------------------- Scrimmage ----
# Both of these were ALREADY ownership-blind. Widening the pool preserves that
# behaviour exactly rather than quietly introducing a filter on one path only.
PATCHES.append((
    "scrim-fe-rewards",
    """  const all=(DATA.firsteds||[]).filter(f=>f.tier!=='ultra').map(f=>f.id);""",
    """  /* pool widened to include expansion commanders; ownership policy unchanged
     (this path has always been ownership-blind, as has the Book Fair swap). */
  const all=feAll().filter(f=>f.tier!=='ultra').map(f=>f.id);""",
))

PATCHES.append((
    "scrim-swap",
    """    case 'swap': { const feids=(DATA.firsteds||[]).map(f=>f.id).filter(id=>!SCRIM.team.some(t=>t.fe&&t.id===id));""",
    """    case 'swap': { const feids=feAll().map(f=>f.id).filter(id=>!SCRIM.team.some(t=>t.fe&&t.id===id));""",
))

# ------------------------------------------- team-member card resolution ----
PATCHES.append((
    "team-resolve-a",
    """    if(t.fe){ c=(DATA.firsteds||[]).find(function(f){return f.id===t.id;}); }""",
    """    if(t.fe){ c=firstedById(t.id); }""",
))

PATCHES.append((
    "team-resolve-b",
    """      if(t.fe) c=(DATA.firsteds||[]).find(function(f){return f.id===t.id;});""",
    """      if(t.fe) c=firstedById(t.id);""",
))

# ------------------------------------------------------ completion metric ----
PATCHES.append((
    "catalog-metric",
    """  const catalog=Math.round((((META.commanders||[]).length+(META.perks||[]).length)/((DATA.firsteds||[]).length+Object.keys(SCRIM_PERKS).length))*100);""",
    """  const _feAll=feAll(), _feGot=_feAll.filter(feHas).length;
  const catalog=Math.round(((_feGot+(META.perks||[]).length)/(_feAll.length+Object.keys(SCRIM_PERKS).length))*100);""",
))

# ------------------------------------------------------------- the Library ---
PATCHES.append((
    "library-shelf",
    """  const owned=(META.commanders||[]).length, total=(DATA.firsteds||[]).length;
  const shelf=(DATA.firsteds||[]).map((f,i)=>{const got=(META.commanders||[]).indexOf(f.id)>=0;""",
    """  const _all=feAll();
  const owned=_all.filter(feHas).length, total=_all.length;
  const shelf=_all.map((f,i)=>{const got=feHas(f);""",
))

# ------------------------------------------------------------- dev + debug ---
PATCHES.append((
    "dev-unlock-firsteds",
    """    case 'firsteds':{ const ids=(typeof DATA!=='undefined'&&DATA.firsteds)?Object.keys(DATA.firsteds):[];
                     META.editionCards=ids.slice(); devLog(ids.length+' first editions granted'); break; }""",
    """    case 'firsteds':{
      /* was Object.keys() on an ARRAY -- it granted ["0","1","2"...] into the
         edition namespace, so it never worked. Grant both namespaces properly. */
      const _all=(typeof feAll==='function')?feAll():[];
      const baseIds=_all.filter(function(f){return !f.cid;}).map(function(f){return f.id;});
      const edCids=_all.filter(function(f){return !!f.cid;}).map(function(f){return f.cid;});
      const seen={}; (META.commanders||[]).concat(baseIds).forEach(function(x){seen[x]=1;});
      META.commanders=Object.keys(seen);
      const seenEd={}; (META.editionCards||[]).concat(edCids).forEach(function(x){seenEd[x]=1;});
      META.editionCards=Object.keys(seenEd);
      devLog(_all.length+' first editions granted ('+baseIds.length+' base, '+edCids.length+' expansion)'); break; }""",
))

PATCHES.append((
    "debug-felist",
    """  feList:()=>(DATA.firsteds||[]).map(f=>({id:f.id,name:f.name})),""",
    """  feList:()=>feAll().map(f=>({id:f.id,name:f.name,cid:f.cid||null,deck:f.deck||null})),
  feAll, feHas, feExpansionCmds, feOwnedList,""",
))

ALREADY = ["fix_fe_full_merge.py", "function feAll()", "function feHas("]


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
            problems.append("  %-24s found %d times, expected 1" % (label, n))
    if problems:
        die("anchor check failed -- nothing written:\n" + "\n".join(problems))

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before = src.count("<script")

    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)

    ph_after = len(re.findall(r"__ABCASSET_\d+__", out))
    if ph_after != ph_before:
        die("placeholder count changed (%d -> %d)" % (ph_before, ph_after))
    if out.count("<script") != sc_before:
        die("script block count changed")

    # the deliberately base-only sites must NOT have been widened
    if "feAll().filter(f=>f.tier!=='ultra').map(f=>f.id).filter(id=>(META.commanders" in out:
        die("pack roll was widened -- it must stay base-only.")
    if out == src:
        die("no change produced.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_after)
    print("    base-only kept: feFor, scrimRollPack, tier-pack R pools")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
