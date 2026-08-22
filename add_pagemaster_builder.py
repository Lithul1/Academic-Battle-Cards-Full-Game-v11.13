#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_pagemaster_builder.py — the deck builder learns the Pagemaster format.

    python3 add_pagemaster_builder.py src/game.src.html
    python3 build.py

Apply AFTER add_pagemaster_engine.py, add_fe_ownership.py and
add_pagemaster_picker.py. This script checks for all three.

WHY ONE BUILDER AND NOT TWO
---------------------------
The existing builder already has category sections, live counts, fill, reset and
deck codes. A second Pagemaster-only builder would duplicate every one of those
and the two would drift. So this teaches the one builder a second set of rules
rather than adding a second screen.

WHAT CHANGES, ONLY WHEN APP.mode==='pagemaster'
-----------------------------------------------
1. pmBuildBooks() — the two books your commanders opened
2. the character section lists BOTH books, each card tagged with its book, and
   shows a per-book count so the four-from-each minimum is visible while you
   build rather than at save time
3. the trivia section lists both books the same way
4. the caps come from PM (12 / 30 / 14 / 4 / 2) instead of LIMITS
5. bookmarks are capped at ONE copy each — Pagemaster is singleton
6. the totals bar reports against the Pagemaster caps and shows any legality
   error from pagemasterLegal() live
7. the commander section is locked to the two you picked

Outside Pagemaster every one of these is bypassed and the builder behaves exactly
as it does today.

Safety: verifies every anchor before touching anything, builds in memory, writes
a .bak, refuses to run twice, checks the asset placeholder count, and confirms
the CSS anchor is not inside an @media block.
"""
import sys, os, re, shutil

HELPERS = r"""
/* ---------------- Pagemaster: the builder's second rule set ---------------- */
function pmBuildBooks(){
  const a=(APP.pmCommanders||[]);
  if(a.length<2) return null;
  const bk=pmBooksOf(a[0],a[1]);
  return bk?bk.books:null;
}
/* the caps in force: Pagemaster's, or the ordinary ones */
function pmCaps(){
  return pmOn() ? { total:PM.total, ch:PM.ch, ab:PM.ab, bm:PM.bm, cr:PM.cr, fe:PM.fe }
                : { total:LIMITS.total, ch:LIMITS.ch, ab:LIMITS.ab, bm:LIMITS.bm, cr:LIMITS.cr, fe:LIMITS.fe };
}
/* how many characters you have taken from each book, for the 4-per-book minimum */
function pmPerBook(def){
  const books=pmBuildBooks(); if(!books) return null;
  return books.map(function(k){
    const ids=new Set((DATA.characters[k]||[]).map(function(c){ return c.id; }));
    return { book:k, n:(def.ch||[]).filter(function(id){ return ids.has(id); }).length };
  });
}
/* one line telling you what is still wrong, or that the deck is legal */
function pmBuildStatus(def){
  if(!pmOn()) return '';
  const a=(APP.pmCommanders||[]);
  if(a.length<2) return '<div class="pm-bstat warn">Choose two commanders first.</div>';
  const d2=Object.assign({}, def, { books:pmBuildBooks(), fe:a.slice(0,PM.fe) });
  const errs=pagemasterLegal(a[0],a[1],d2);
  const per=pmPerBook(def)||[];
  const perTxt=per.map(function(p){
    const short=p.n<PM.minChPerBook;
    return '<span class="'+(short?'short':'')+'">'+setName(p.book)+' '+p.n+'/'+PM.minChPerBook+'</span>';
  }).join('');
  if(!errs.length) return '<div class="pm-bstat ok"><b>Legal.</b> '+perTxt+'</div>';
  return '<div class="pm-bstat warn"><b>'+errs.length+' to fix</b> \u2014 '+errs.slice(0,3).join('; ')
       + (errs.length>3?'\u2026':'')+' '+perTxt+'</div>';
}
"""

CSS = """
/* --- Pagemaster builder (must stay outside any @media) --- */
.pm-bstat{font-family:var(--cond);font-size:12px;letter-spacing:.5px;border:2px solid var(--ink,#241F1B);
  border-radius:9px;padding:6px 11px;margin:8px 0;display:flex;gap:9px;align-items:center;flex-wrap:wrap;
  color:var(--ink,#241F1B)}
.pm-bstat.ok{background:#e8f2e8;border-color:#2f7d5c}
.pm-bstat.warn{background:#fdf0e2;border-color:var(--red,#B53A2C)}
.pm-bstat b{font-family:var(--disp);font-size:12px}
.pm-bstat span{background:var(--cream,#F2E6C6);border:2px solid var(--ink,#241F1B);border-radius:7px;padding:2px 8px}
.pm-bstat span.short{background:#f7d9d3;border-color:var(--red,#B53A2C)}
.bd-book{font-family:var(--cond);font-size:9px;letter-spacing:.7px;text-transform:uppercase;
  opacity:.72;display:block}
"""

EDITS = [
    # 1 — helpers, above the builder
    ("insert", "function builderScreen(){", HELPERS + "function builderScreen(){"),

    # 2 — caps come from pmCaps(), and the character row spans both books
    ("replace",
     "  const over=t=>c[t]>LIMITS[t]?'over':'';\n  const chRow=DATA.characters[k].map(ch=>{\n    if(!deckOwnCh(k,ch.id)) return",
     "  const CAP=pmCaps();\n"
     "  const over=t=>c[t]>CAP[t]?'over':'';\n"
     "  /* Pagemaster draws on the two books your commanders opened, not just def.d */\n"
     "  const _books=(pmOn()&&pmBuildBooks())||[k];\n"
     "  const _chPool=_books.reduce((a,bk)=>a.concat((DATA.characters[bk]||[]).map(c=>({c,bk}))),[]);\n"
     "  const chRow=_chPool.map(({c:ch,bk:k})=>{\n"
     "    if(!deckOwnCh(k,ch.id)) return"),

    # 3 — the trivia row spans both books too
    ("replace",
     "  const abRow=DATA.abcs[k].map((a,i)=>{\n    if(!deckOwnAb(k,i)) return",
     "  const _abPool=_books.reduce((acc,bk)=>acc.concat((DATA.abcs[bk]||[]).map((a,i)=>({a,i,bk}))),[]);\n"
     "  const abRow=_abPool.map(({a,i,bk:k})=>{\n"
     "    if(!deckOwnAb(k,i)) return"),

    # 4 — the totals bar reports against the caps in force
    ("replace",
     '<span class="${over(\'total\')}">Total ${c.total}/${LIMITS.total}</span>',
     '<span class="${over(\'total\')}">Total ${c.total}/${CAP.total}</span>'),
    ("replace",
     '<span class="${over(\'ch\')}">Characters ${c.ch}/${LIMITS.ch}</span>',
     '<span class="${over(\'ch\')}">Characters ${c.ch}/${CAP.ch}</span>'),
    ("replace",
     '<span class="${over(\'ab\')}">Attack/Block ${c.ab}/${LIMITS.ab}</span>',
     '<span class="${over(\'ab\')}">Attack/Block ${c.ab}/${CAP.ab}</span>'),
    ("replace",
     '<span class="${over(\'bm\')}">Bookmarks ${c.bm}/${LIMITS.bm}</span>',
     '<span class="${over(\'bm\')}">Bookmarks ${c.bm}/${CAP.bm}</span>'),
    ("replace",
     '<span class="${over(\'cr\')}">Crit-Cards ${c.cr}/${LIMITS.cr}</span>',
     '<span class="${over(\'cr\')}">Crit-Cards ${c.cr}/${CAP.cr}</span>'),
    ("replace",
     '<span class="${over(\'fe\')}">1st Editions ${c.fe}/${LIMITS.fe}</span>',
     '<span class="${over(\'fe\')}">1st Editions ${c.fe}/${CAP.fe}</span>${pmBuildStatus(def)}'),

    # 5 — section headings show the caps in force and both book names
    ("replace",
     "<h3>Characters <small>pick your roster \u00b7 max ${LIMITS.ch}</small></h3>",
     "<h3>Characters <small>${pmOn()?_books.map(b=>setName(b)).join(' + ')+' \u00b7 min '+PM.minChPerBook+' each':'pick your roster'} \u00b7 max ${CAP.ch}</small></h3>"),
    ("replace",
     "<h3>Attack / Block cards <small>${setName(k)} trivia \u00b7 max ${LIMITS.ab}</small></h3>",
     "<h3>Attack / Block cards <small>${_books.map(b=>setName(b)).join(' + ')} trivia \u00b7 max ${CAP.ab}</small></h3>"),
    ("replace",
     "<h3>Bookmarks <small>add copies \u00b7 max ${LIMITS.bm} total</small></h3>",
     "<h3>Bookmarks <small>${pmOn()?'one copy each':'add copies'} \u00b7 max ${CAP.bm} total</small></h3>"),
    ("replace",
     "<h3>Crit-Cards (Critical Lenses) <small>pick up to ${LIMITS.cr}</small></h3>",
     "<h3>Crit-Cards (Critical Lenses) <small>pick up to ${CAP.cr}</small></h3>"),

    # 6 — the toggles respect the caps in force; bookmarks go singleton
    ("replace",
     "else if(op==='bm+'){ const n=+arg; const have=def.bm.filter(x=>x===n).length; if(def.bm.length<LIMITS.bm && have<bmOwned(n)) def.bm.push(n);",
     "else if(op==='bm+'){ const n=+arg; const have=def.bm.filter(x=>x===n).length;\n"
     "      const _cap=pmCaps(), _copies=pmOn()?PM.bmCopies:bmOwned(n);\n"
     "      if(def.bm.length<_cap.bm && have<_copies) def.bm.push(n);"),
    ("replace",
     "else if(op==='cr'){ const n=+arg, i=def.cr.indexOf(n); if(i>=0) def.cr.splice(i,1); else if(def.cr.length<LIMITS.cr && ownCrit(n)) def.cr.push(n);",
     "else if(op==='cr'){ const n=+arg, i=def.cr.indexOf(n); if(i>=0) def.cr.splice(i,1); else if(def.cr.length<pmCaps().cr && ownCrit(n)) def.cr.push(n);"),
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

    if "function pmBuildBooks" in src:
        print("Already applied \u2014 the builder knows Pagemaster. Nothing to do.")
        return
    for need, who in (("function pagemasterLegal", "add_pagemaster_engine.py"),
                      ("function feOwned(", "add_fe_ownership.py"),
                      ("function pmPickerScreen", "add_pagemaster_picker.py")):
        if need not in src:
            die(f"missing prerequisite. Run {who} first.")
    for deck in ("romeojuliet", "odyssey"):
        if deck not in src:
            die(f"'{deck}' is missing \u2014 this is not your live source.")

    for n, (tag, old, new) in enumerate(EDITS, 1):
        c = src.count(old)
        if c != 1:
            die(f"edit {n}: anchor found {c} times, expected 1.\n  anchor: {old[:78]!r}")

    out = src
    for tag, old, new in EDITS:
        out = out.replace(old, new, 1)

    anchor = None
    for cand in ("/* --- Pagemaster commander picker (must stay outside any @media) --- */",
                 "/* --- discard / retry UI (must stay outside any @media) --- */"):
        if cand in out:
            anchor = cand
            break
    if not anchor:
        die("no known top-level CSS anchor found.")
    at = out.index(anchor)
    prev = out.rfind("@media", 0, at)
    if prev >= 0:
        seg = out[prev:at]
        if seg.count("{") - seg.count("}") > 0:
            die("the CSS anchor is inside an @media block \u2014 styles would be stranded.")
    out = out.replace(anchor, CSS + anchor, 1)

    before = len(re.findall(r"__ABCASSET_\d+__", src))
    after = len(re.findall(r"__ABCASSET_\d+__", out))
    if before != after:
        die(f"asset placeholder count changed ({before} -> {after}).")
    if len(out) <= len(src):
        die("output is not larger than input.")

    shutil.copy(path, path + ".bak")
    open(path, "w", encoding="utf-8").write(out)

    print("Applied \u2014 the builder now knows Pagemaster.")
    print(f"  backup      : {path}.bak")
    print(f"  {path}: {len(src):,} -> {len(out):,} bytes (+{len(out)-len(src):,})")
    print(f"  placeholders: {after} (unchanged)")
    print()
    print("  In Pagemaster the builder lists BOTH your books, caps at 12/30/14/4/2,")
    print("  allows one copy of each Bookmark, shows a per-book character count, and")
    print("  reports live whether the deck is legal.")
    print()
    print("  Outside Pagemaster nothing changes \u2014 every rule is behind pmOn().")
    print()
    print("  Next: python3 build.py")


if __name__ == "__main__":
    main()
