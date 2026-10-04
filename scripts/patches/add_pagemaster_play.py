#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_pagemaster_play.py — deck codes, the LIMITS fix, and taking a Pagemaster
deck into a match. This completes the format.

    python3 add_pagemaster_play.py src/game.src.html
    python3 build.py

Apply AFTER the engine, ownership, picker and builder patches. All four are
checked for.

WHAT THIS ADDS
--------------
1. LIMITS.ch raised 12 -> 14.
   MY BUG, from the deck-composition work earlier. Three starters ship more
   than 12 characters (gatsby 13, hamlet 13, oz 14) but the builder ceiling
   stayed at 12, so those decks displayed "Characters 13/12" in red in a
   builder they had never been edited in. Raising the ceiling to 14 covers
   every shipped composition. MINIMA.ch stays at 8.

2. Pagemaster deck codes, prefixed ABC-PM- rather than ABC-.
   encodeDeck() now emits the prefix and carries `books` and `pm` when the deck
   is a Pagemaster deck; decodeDeck() understands both. An ABC-PM- code pasted
   into the ordinary builder is refused with a clear message rather than
   silently producing a broken deck, and old ABC- codes are untouched.

3. APP.pmDeck — Pagemaster gets its OWN saved deck slot, so building one does
   not overwrite your Custom deck.

4. "Use this deck" in Pagemaster saves to pmDeck, refuses an illegal deck with
   the reason, and sends you into a match rather than back to the menu.

Safety: verifies every anchor first, builds in memory, writes a .bak, refuses to
run twice, and checks the asset placeholder count.
"""
import sys, os, re, shutil

CODE_FNS = r"""
/* ---- Pagemaster deck codes: ABC-PM- so they cannot be confused with ABC- ---- */
function pmEncodeDeck(def){
  try{
    const j=JSON.stringify({ d:def.d, books:def.books||[], pm:true,
      ch:def.ch, ab:def.ab, bm:def.bm, cr:def.cr, fe:def.fe||[] });
    return 'ABC-PM-'+window.btoa(unescape(encodeURIComponent(j))).replace(/=+$/,'');
  }catch(e){ return ''; }
}
function pmDecodeDeck(code){
  try{
    let s=(code||'').trim();
    if(!s.indexOf('ABC-PM-')===0 && s.indexOf('ABC-PM-')!==0) return null;
    s=s.slice(7).replace(/\s+/g,'');
    while(s.length%4) s+='=';
    const o=JSON.parse(decodeURIComponent(escape(window.atob(s))));
    if(!o||!o.pm||!o.books||!o.books.length) return null;
    if(!o.books.every(function(k){ return DATA.characters[k]; })) return null;
    return { d:o.d||o.books[0], books:o.books, pm:true,
             ch:o.ch||[], ab:o.ab||[], bm:o.bm||[], cr:o.cr||[], fe:o.fe||[],
             ed:{}, edab:[], edbm:{} };
  }catch(e){ return null; }
}
function isPmCode(code){ return String(code||'').trim().indexOf('ABC-PM-')===0; }
"""

EDITS = [
    # 1 — the ceiling covers every shipped composition
    ("replace",
     "const LIMITS={ ch:12, ab:36, bm:20, cr:4, fe:2, total:62 };   // builder CEILING per category",
     "const LIMITS={ ch:14, ab:36, bm:20, cr:4, fe:2, total:62 };   // builder CEILING per category\n"
     "/* ch is 14, not 12: gatsby and hamlet ship 13 characters and oz ships 14, so a\n"
     "   ceiling of 12 flagged three untouched starter decks as over-cap. */"),

    # 2 — the code helpers, next to the originals
    ("insert", "function encodeDeck(def){", CODE_FNS + "function encodeDeck(def){"),

    # 3 — generating a code respects the format
    ("replace",
     "else if(op==='gencode'){ clampDeck(def); B.code=encodeDeck(def); }",
     "else if(op==='gencode'){ clampDeck(def);\n"
     "      B.code = pmOn() ? pmEncodeDeck(Object.assign({}, def, {books:pmBuildBooks()||[def.d], fe:(APP.pmCommanders||[]).slice(0,PM.fe)}))\n"
     "                      : encodeDeck(def); }"),

    # 4 — loading a code understands both kinds and refuses a mismatch
    ("replace",
     "else if(d==='loadcode'){ const el=document.getElementById('codein'); const def=decodeDeck(el?el.value:'');",
     "else if(d==='loadcode'){ const el=document.getElementById('codein'); const _raw=el?el.value:'';\n"
     "      if(isPmCode(_raw) && !pmOn()){\n"
     "        APP.codeMsg={text:'That is a Pagemaster code \\u2014 open Pagemaster to use it.',ok:false}; render(); return; }\n"
     "      if(!isPmCode(_raw) && pmOn()){\n"
     "        APP.codeMsg={text:'That is an ordinary deck code \\u2014 Pagemaster needs an ABC-PM- code.',ok:false}; render(); return; }\n"
     "      if(isPmCode(_raw)){\n"
     "        const pd=pmDecodeDeck(_raw);\n"
     "        if(pd){ APP.pmDeck=pd; APP.pmCommanders=(pd.fe||[]).slice(0,PM.fe);\n"
     "          APP.builder={ def:clone(pd), code:'' };\n"
     "          APP.codeMsg={text:'Pagemaster deck loaded \\u2713 ('+deckCounts(pd).total+' cards)',ok:true}; }\n"
     "        else { APP.codeMsg={text:'That Pagemaster code did not work \\u2014 check it and try again.',ok:false}; }\n"
     "        render(); return; }\n"
     "      const def=decodeDeck(_raw);"),

    # 5 — "Use this deck" in Pagemaster saves to its own slot and starts a match
    ("replace",
     "else if(op==='use'){ clampDeck(def); if(def._repaired) toast('Some cards in this deck aren\\u2019t unlocked yet \\u2014 swapped for cards you own.'); APP.customDeck=clone(def); APP.youDeck=def.d;",
     "else if(op==='use'){ clampDeck(def);\n"
     "      if(pmOn()){\n"
     "        const a=(APP.pmCommanders||[]).slice(0,PM.fe);\n"
     "        const d2=Object.assign({}, def, { books:pmBuildBooks()||[def.d], pm:true, fe:a });\n"
     "        const errs=pagemasterLegal(a[0],a[1],d2);\n"
     "        if(errs.length){ toast('Not legal yet \\u2014 '+errs[0]); return; }\n"
     "        APP.pmDeck=clone(d2); APP.youDeck=d2.books[0];\n"
     "        APP.codeMsg={text:'Pagemaster deck ready.',ok:true};\n"
     "        APP.screen='custom'; render(); return;\n"
     "      }\n"
     "      if(def._repaired) toast('Some cards in this deck aren\\u2019t unlocked yet \\u2014 swapped for cards you own.'); APP.customDeck=clone(def); APP.youDeck=def.d;"),

    # 6 — the match plays the Pagemaster deck when the mode is on
    ("replace",
     "function deckForPlay(){\n  if(APP.customDeck) return clone(APP.customDeck);",
     "function deckForPlay(){\n"
     "  /* Pagemaster plays its own saved deck, kept separate from the Custom one */\n"
     "  if(pmOn() && APP.pmDeck) return clone(APP.pmDeck);\n"
     "  if(APP.customDeck) return clone(APP.customDeck);"),

    # 7 — extend the test surface so the flow can be verified end to end
    ("replace",
     "try{ window.ABC_PM = { PM, pmOn, pmBooksOf, pagemasterLegal, pmReturnCost,",
     "try{ window.ABC_PM = { PM, pmOn, pmBooksOf, pagemasterLegal, pmReturnCost,\n"
     "  deckForPlay, pmEncodeDeck, pmDecodeDeck, isPmCode, pmCaps, pmBuildBooks,"),
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

    if "function pmEncodeDeck" in src:
        print("Already applied \u2014 Pagemaster codes are present. Nothing to do.")
        return
    for need, who in (("function pagemasterLegal", "add_pagemaster_engine.py"),
                      ("function feOwned(", "add_fe_ownership.py"),
                      ("function pmPickerScreen", "add_pagemaster_picker.py"),
                      ("function pmBuildBooks", "add_pagemaster_builder.py")):
        if need not in src:
            die(f"missing prerequisite. Run {who} first.")

    for n, (tag, old, new) in enumerate(EDITS, 1):
        c = src.count(old)
        if c != 1:
            die(f"edit {n}: anchor found {c} times, expected 1.\n  anchor: {old[:78]!r}")

    out = src
    for tag, old, new in EDITS:
        out = out.replace(old, new, 1)

    before = len(re.findall(r"__ABCASSET_\d+__", src))
    after = len(re.findall(r"__ABCASSET_\d+__", out))
    if before != after:
        die(f"asset placeholder count changed ({before} -> {after}).")
    if len(out) <= len(src):
        die("output is not larger than input.")

    shutil.copy(path, path + ".bak")
    open(path, "w", encoding="utf-8").write(out)

    print("Applied \u2014 Pagemaster codes, own deck slot, and the LIMITS fix.")
    print(f"  backup      : {path}.bak")
    print(f"  {path}: {len(src):,} -> {len(out):,} bytes (+{len(out)-len(src):,})")
    print(f"  placeholders: {after} (unchanged)")
    print()
    print("  LIMITS.ch 12 -> 14. Gatsby and Hamlet ship 13 characters and Oz ships 14,")
    print("  so those three starters were displaying as over-cap in an untouched builder.")
    print()
    print("  Pagemaster decks now save to APP.pmDeck, separate from your Custom deck,")
    print("  and export as ABC-PM- codes. Pasting one into the wrong builder is refused")
    print("  with a message rather than silently mangling the deck.")
    print()
    print("  Next: python3 build.py")


if __name__ == "__main__":
    main()
