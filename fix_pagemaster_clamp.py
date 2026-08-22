#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_pagemaster_clamp.py — three defects that stop a legal Pagemaster deck being used.

    python3 fix_pagemaster_clamp.py src/game.src.html
    python3 build.py

THE SYMPTOM
-----------
The status bar reads "Legal. Hamlet 7/4 Macbeth 5/4", but pressing "Use this
deck" says "Not legal yet - characters 7, need 12", and the totals show
"Total 64/62" and "Attack/Block 32/30" in red.

THE CAUSES — all three are mine, from the Pagemaster builder patch.

1. clampDeck() filters characters against ONE book:
       def.ch.filter(id => DATA.characters[k].some(c => c.id === id))
   where k is def.d. For a Hamlet+Macbeth deck that silently DELETES every
   Macbeth character. clampDeck runs first in the "use" handler, so twelve
   characters became seven before the legality check ever saw them.

2. clampDeck() bounds-checks ABCs as plain indices:
       def.ab.filter(i => i >= 0 && i < DATA.abcs[k].length)
   A Pagemaster ab entry is {d,i}, not a number, so this test is meaningless.
   Same class of bug as makeDeck() had.

3. The character and trivia toggles cap against LIMITS (14 and 36) rather than
   the Pagemaster caps (12 and 30). That is the 32/30 and the 64/62 — the
   builder let you go past the format's own limits.

THE FIX
-------
clampDeck becomes book-aware: when a deck carries `books`, characters and ABCs
are checked against all of them, and {d,i} refs are validated against the book
they name. The two toggles use pmCaps() like the bookmark and lens toggles
already do.

Ordinary decks are unaffected: with no `books` field the behaviour is identical
to today.

Safe to run once. Verifies before writing, keeps a .bak.
"""
import sys, os, re, shutil

OLD_CLAMP = ("const k=def.d;\n"
             "  def.ch=(def.ch||[]).filter(id=>DATA.characters[k].some(c=>c.id===id)).slice(0,LIMITS.ch);\n"
             "  def.ab=(def.ab||[]).filter(i=>i>=0&&i<DATA.abcs[k].length).slice(0,LIMITS.ab);")

NEW_CLAMP = (
    "const k=def.d;\n"
    "  /* A Pagemaster deck draws on two books, so validate against all of them.\n"
    "     Filtering to def.d alone deleted every character from the second book. */\n"
    "  const _bks=(def.books&&def.books.length)?def.books:[k];\n"
    "  const _CAP=(typeof pmCaps==='function'&&def.pm)?pmCaps():LIMITS;\n"
    "  const _chOk=new Set(_bks.reduce(function(a,b){\n"
    "    return a.concat((DATA.characters[b]||[]).map(function(c){ return c.id; })); },[]));\n"
    "  def.ch=(def.ch||[]).filter(id=>_chOk.has(id)).slice(0,_CAP.ch);\n"
    "  /* an ab entry is a plain index into def.d, or {d,i} naming its own book */\n"
    "  def.ab=(def.ab||[]).filter(function(r){\n"
    "    if(r&&typeof r==='object') return _bks.indexOf(r.d)>=0 && r.i>=0 && r.i<((DATA.abcs[r.d]||[]).length);\n"
    "    return r>=0 && r<((DATA.abcs[k]||[]).length);\n"
    "  }).slice(0,_CAP.ab);")

EDITS = [
    ("replace", OLD_CLAMP, NEW_CLAMP),

    # the bookmark and lens clamps should honour the format's caps too
    ("replace",
     "  def.bm=(def.bm||[]).filter(i=>i>=0&&i<DATA.bookmarks.length).slice(0,LIMITS.bm);\n"
     "  def.cr=(def.cr||[]).filter(i=>i>=0&&i<DATA.crits.length).slice(0,LIMITS.cr);",
     "  def.bm=(def.bm||[]).filter(i=>i>=0&&i<DATA.bookmarks.length).slice(0,_CAP.bm);\n"
     "  def.cr=(def.cr||[]).filter(i=>i>=0&&i<DATA.crits.length).slice(0,_CAP.cr);"),

    # the character toggle respects the format cap
    ("replace",
     "op==='ch'){ const i=def.ch.indexOf(arg); if(i>=0) def.ch.splice(i,1); else if(def.ch.length<LIMITS.ch) def.ch.push(arg);",
     "op==='ch'){ const i=def.ch.indexOf(arg); if(i>=0) def.ch.splice(i,1); else if(def.ch.length<pmCaps().ch) def.ch.push(arg);"),

    # and the trivia toggle
    ("replace",
     "op==='ab'){ const n=+arg, i=def.ab.indexOf(n); if(i>=0) def.ab.splice(i,1); else if(def.ab.length<LIMITS.ab) def.ab.push(n);",
     "op==='ab'){ const n=+arg, i=def.ab.indexOf(n); if(i>=0) def.ab.splice(i,1); else if(def.ab.length<pmCaps().ab) def.ab.push(n);"),

    # the ownership-repair pass has the SAME single-book bug, plus it backfills
    # bookmarks with duplicates, which Pagemaster forbids
    ("replace",
     "  def.ch=(def.ch||[]).filter(id=>deckOwnCh(k,id));\n"
     "  def.ab=(def.ab||[]).filter(i=>deckOwnAb(k,i));",
     "  def.ch=(def.ch||[]).filter(id=>_bks.some(b=>deckOwnCh(b,id)));\n"
     "  def.ab=(def.ab||[]).filter(function(r){\n"
     "    if(r&&typeof r==='object') return deckOwnAb(r.d,r.i);\n"
     "    return deckOwnAb(k,r); });"),

    ("replace",
     "    (function(){ const pool=poolCh(k).filter(id=>!def.ch.includes(id));\n"
     "      while(def.ch.length<capTo(_was.ch,LIMITS.ch) && pool.length) def.ch.push(pool.splice(rnd(pool.length),1)[0]); })();",
     "    (function(){ const pool=_bks.reduce((a,b)=>a.concat(poolCh(b)),[]).filter(id=>!def.ch.includes(id));\n"
     "      while(def.ch.length<capTo(_was.ch,_CAP.ch) && pool.length) def.ch.push(pool.splice(rnd(pool.length),1)[0]); })();"),

    ("replace",
     "    (function(){ const pool=poolAb(k).filter(i=>!def.ab.includes(i));\n"
     "      while(def.ab.length<capTo(_was.ab,LIMITS.ab) && pool.length) def.ab.push(pool.splice(rnd(pool.length),1)[0]); })();",
     "    (function(){ const has=new Set(def.ab.map(r=>JSON.stringify(r)));\n"
     "      const pool=(def.books&&def.books.length)\n"
     "        ? _bks.reduce((a,b)=>a.concat(poolAb(b).map(i=>({d:b,i}))),[]).filter(r=>!has.has(JSON.stringify(r)))\n"
     "        : poolAb(k).filter(i=>!def.ab.includes(i));\n"
     "      while(def.ab.length<capTo(_was.ab,_CAP.ab) && pool.length) def.ab.push(pool.splice(rnd(pool.length),1)[0]); })();"),

    # Pagemaster is singleton: never backfill a duplicate bookmark
    ("replace",
     "        const avail=slots.filter(i=>(u[i]||0)<bmOwned(i));",
     "        const _cp=(typeof pmCaps==='function'&&def.pm)?PM.bmCopies:null;\n"
     "        const avail=slots.filter(i=>(u[i]||0)<(_cp!==null?_cp:bmOwned(i)));"),
    ("replace",
     "      while(def.bm.length<capTo(_was.bm,LIMITS.bm)){",
     "      while(def.bm.length<capTo(_was.bm,_CAP.bm)){"),

    # expose clampDeck so the fix can be verified
    ("replace",
     "try{ window.ABC_PM = { PM, pmOn, pmBooksOf, pagemasterLegal, pmReturnCost,",
     "try{ window.ABC_PM = { PM, pmOn, pmBooksOf, pagemasterLegal, pmReturnCost, clampDeck,"),
]


def die(msg):
    print("ABORTED \u2014 file not modified.")
    print("  " + msg)
    sys.exit(1)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "src/game.src.html"
    if not os.path.exists(path):
        die(f"no such file: {path}")
    src = open(path, encoding="utf-8").read()

    if "_chOk" in src:
        print("Already applied \u2014 clampDeck is book-aware. Nothing to do.")
        return
    if "function pmCaps" not in src:
        die("the Pagemaster builder patch is not present.\n  Run add_pagemaster_builder.py first.")

    for n, (tag, old, new) in enumerate(EDITS, 1):
        c = src.count(old)
        if c != 1:
            die(f"edit {n}: anchor found {c} times, expected 1.\n  anchor: {old[:76]!r}")

    out = src
    for tag, old, new in EDITS:
        out = out.replace(old, new, 1)

    before = len(re.findall(r"__ABCASSET_\d+__", src))
    after = len(re.findall(r"__ABCASSET_\d+__", out))
    if before != after:
        die(f"asset placeholder count changed ({before} -> {after}).")

    shutil.copy(path, path + ".bak")
    open(path, "w", encoding="utf-8").write(out)

    print("Applied \u2014 clampDeck is book-aware and the builder respects the format caps.")
    print(f"  backup      : {path}.bak")
    print(f"  {path}: {len(src):,} -> {len(out):,} bytes ({len(out)-len(src):+,})")
    print()
    print("  \u2022 characters from your SECOND book are no longer deleted on save")
    print("  \u2022 {d,i} trivia refs are validated against the book they name")
    print("  \u2022 the character and trivia toggles stop at 12 and 30 in Pagemaster")
    print()
    print("  Ordinary decks are unchanged \u2014 with no `books` field the behaviour is")
    print("  identical to before.")
    print()
    print("  If your current deck is over (64/62), press Reset or remove the extras;")
    print("  the caps will now hold you at the right numbers.")
    print()
    print("  Next: python3 build.py")


if __name__ == "__main__":
    main()
