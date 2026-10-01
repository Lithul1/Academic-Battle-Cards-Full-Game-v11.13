#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_pagemaster_engine.py — the Pagemaster format's ENGINE layer.

    python3 add_pagemaster_engine.py src/game.src.html
    python3 build.py

WHAT THIS IS AND IS NOT
-----------------------
This adds the rules. It does NOT add the menu entry, the commander picker, or
the builder filter, so after running it Pagemaster is not yet reachable from the
UI. Nothing existing changes behaviour: every rule here is gated on
APP.mode==='pagemaster' or def.pm, neither of which anything sets yet.

The one exception is a genuine bug fix — see edit 9.

WHAT IT ADDS
------------
1. PM constants, pagemasterLegal(), pmReturnCost(), pmBooksOf(), pmOn()
2. edResolveChar() searches both of a hybrid deck's books, not just def.d
3. newPlayer(): in Pagemaster your two commanders OPEN ON THE FIELD rather than
   being shuffled into the deck; the 12 characters are drawn as usual
4. the player shell carries _pm and _hasActive
5. checkKO(): a fallen commander RETURNS TO HAND and the KO does not count.
   1st return costs 1 attach, 2nd costs 2, the 3rd cannot happen — it dies for
   good and that KO counts
6. attackCostFor(): +2 ABC to strike a Backstage character (Pagemaster only)
7. drawnPlayChar(): replaying a returned commander spends its attach cost
8. a replayed commander remembers how many times it has fallen
9. makeDeck(): accepts {d,i} ABC refs as well as plain indices.
   THIS IS A REAL FIX. The old line was DATA.abcs[def.d][i], so any deck whose
   ab entries name their own book silently lost every ABC. No current deck does
   that, so nothing is broken today — but it would have swallowed all 30 cards
   of the first Pagemaster deck without an error.

Additive except edits 2 and 9, which replace one line each with a superset that
handles the old shape identically.

Safety: verifies every anchor before touching anything, builds in memory, writes
a .bak, refuses to run twice, and checks the asset placeholder count is unchanged.
"""
import sys, os, re, shutil

PM_BLOCK = r"""
/* =========================================================================
   PAGEMASTER — a two-commander format.

   Deck: 2 commanders (1st Editions) + 12 characters + 30 ABC + 14 Bookmarks
         + 4 Critical Lenses = 62, all drawn from your commanders' two books.
   What differs from every other mode:
     - your two commanders START on the field; the 12 characters are drawn
     - a knocked-out commander RETURNS TO HAND and that KO does not count.
       Returning costs attaches, and the third fall is permanent.
     - you may strike a Backstage character for +2 ABC
   ========================================================================= */
const PM = {
  total:62, ch:12, ab:30, bm:14, cr:4, fe:2,
  minChPerBook:4,          // hybrids must field at least this many from each book
  bmCopies:1,              // singleton: one copy of each Bookmark
  returnCost:[1,2],        // 1st return costs 1 attach, 2nd costs 2
  maxReturns:2,            // the 3rd KO is permanent and counts
  benchSurcharge:2         // extra ABC to strike past the front line
};
function pmOn(){ try{ return APP.mode==='pagemaster'; }catch(e){ return false; } }
function pmBooksOf(fe1,fe2){
  const a=firstedById(fe1), b=firstedById(fe2);
  if(!a||!b) return null;
  return { a:a.deck, b:b.deck, mono:a.deck===b.deck,
           books:(a.deck===b.deck?[a.deck]:[a.deck,b.deck]) };
}
function pagemasterLegal(fe1,fe2,def){
  const errs=[], bk=pmBooksOf(fe1,fe2);
  if(!bk) return ['unknown commander'];
  if(fe1===fe2) errs.push('the two commanders must be different cards');
  const books=bk.books;
  if(def.ch.length!==PM.ch) errs.push('characters '+def.ch.length+', need '+PM.ch);
  if(def.ab.length!==PM.ab) errs.push('ABCs '+def.ab.length+', need '+PM.ab);
  if(def.bm.length!==PM.bm) errs.push('bookmarks '+def.bm.length+', need '+PM.bm);
  if(def.cr.length!==PM.cr) errs.push('lenses '+def.cr.length+', need '+PM.cr);
  const legalCh=new Set(books.reduce(function(a,k){
    return a.concat((DATA.characters[k]||[]).map(function(c){return c.id;})); },[]));
  const strayCh=def.ch.filter(function(id){ return !legalCh.has(id); });
  if(strayCh.length) errs.push(strayCh.length+' characters outside your books');
  const strayAb=def.ab.filter(function(r){ return books.indexOf((r&&r.d)||def.d)<0; });
  if(strayAb.length) errs.push(strayAb.length+' ABCs outside your books');
  if(!bk.mono) books.forEach(function(k){
    const ids=new Set((DATA.characters[k]||[]).map(function(c){return c.id;}));
    const n=def.ch.filter(function(id){ return ids.has(id); }).length;
    if(n<PM.minChPerBook) errs.push('only '+n+' characters from '+setName(k)+', need '+PM.minChPerBook);
  });
  const dup=function(arr){ return arr.length!==new Set(arr.map(function(x){ return JSON.stringify(x); })).size; };
  if(dup(def.ch)) errs.push('duplicate characters');
  if(dup(def.ab)) errs.push('duplicate ABCs');
  if(dup(def.cr)) errs.push('duplicate lenses');
  if(dup(def.bm)) errs.push('duplicate bookmarks \u2014 Pagemaster allows one copy of each');
  const total=def.ch.length+def.ab.length+def.bm.length+def.cr.length+PM.fe;
  if(total!==PM.total) errs.push('deck is '+total+', need '+PM.total);
  return errs;
}
/* what this commander's next return costs, or null when it can never come back */
function pmReturnCost(ch){
  const n=(ch&&ch._pmReturns)||0;
  return n>=PM.maxReturns ? null : PM.returnCost[n];
}
"""

EDITS = [
    # 1 — the format block, inserted above edResolveChar
    ("insert", "function edResolveChar(def,id){", PM_BLOCK + "function edResolveChar(def,id){"),

    # 2 — resolve characters across both books
    ("replace",
     "function edResolveChar(def,id){ if(def.ed&&def.ed[id]){ var m=edCharFor(def.d,id); if(m) return edInherit(def.d,m.c); } return DATA.characters[def.d].find(function(c){return c.id===id;}); }",
     "function edResolveChar(def,id){ if(def.ed&&def.ed[id]){ var m=edCharFor(def.d,id); if(m) return edInherit(def.d,m.c); }\n"
     "  var hit=(DATA.characters[def.d]||[]).find(function(c){return c.id===id;});\n"
     "  if(hit) return hit;\n"
     "  /* a Pagemaster deck draws on two books, so a character may not live under def.d */\n"
     "  var books=(def.books||[]);\n"
     "  for(var i=0;i<books.length;i++){\n"
     "    var c=(DATA.characters[books[i]]||[]).find(function(x){return x.id===id;});\n"
     "    if(c) return edInherit(books[i], c);\n"
     "  }\n"
     "  return null; }"),

    # 3 — commanders open on the field
    ("replace",
     "    const chCards=pool.map(d=>mk(d,false));\n"
     "    (def.fe||[]).slice(0,LIMITS.fe).forEach(id=>{ const fd=firstedById(id); if(fd) chCards.push(mk(fd,true)); });\n"
     "    return { name,setKey:def.d,team:[],activeIdx:0,",
     "    const chCards=pool.map(d=>mk(d,false));\n"
     "    /* PAGEMASTER: your two commanders are not shuffled in \u2014 they open on the\n"
     "       field, Active and Backstage. Everything else is drawn. */\n"
     "    const pmTeam=[];\n"
     "    if(def.pm){\n"
     "      (def.fe||[]).slice(0,PM.fe).forEach(id=>{ const fd=firstedById(id);\n"
     "        if(fd){ const c=makeChar(fd,st.hpScale); c._pmCmd=true; c._pmReturns=0; pmTeam.push(c); } });\n"
     "    } else {\n"
     "      (def.fe||[]).slice(0,LIMITS.fe).forEach(id=>{ const fd=firstedById(id); if(fd) chCards.push(mk(fd,true)); });\n"
     "    }\n"
     "    return { name,setKey:def.d,team:pmTeam,activeIdx:0,"),

    # 4 — the shell carries the flags
    ("replace",
     "_hpScale:st.hpScale,_drawn:true };",
     "_hpScale:st.hpScale,_drawn:true,_hasActive:pmTeam.length>0,_pm:!!def.pm };"),

    # 5 — a fallen commander returns to hand
    ("replace",
     "    spawnKO(side, a.name);\n    try{ fxKO(side, a.name); }catch(e){}\n    if(!p.grave.includes(a)) p.grave.push(a);",
     "    /* PAGEMASTER: a fallen commander returns to hand rather than the grave, and\n"
     "       the KO does not count \u2014 you beat the army, not the author. The third\n"
     "       fall is permanent and does count. */\n"
     "    if(p._pm && a._pmCmd && pmReturnCost(a)!==null){\n"
     "      const cost=pmReturnCost(a);\n"
     "      a._pmReturns=(a._pmReturns||0)+1;\n"
     "      const at=p.team.indexOf(a); if(at>=0) p.team.splice(at,1);\n"
     "      if(p.activeIdx>=p.team.length) p.activeIdx=Math.max(0,p.team.length-1);\n"
     "      p.hand.push({ cat:'char', charId:a.id, name:a.name, accent:a.accent||'#444', hp:a.maxHp,\n"
     "                    fe:true, _pmCmd:true, _pmReturns:a._pmReturns, _pmCost:cost,\n"
     "                    _cdef:firstedById(a.id),\n"
     "                    cid:'pm'+a.id+'_'+Math.random().toString(36).slice(2,6) });\n"
     "      try{ fxKO(side, a.name); }catch(e){}\n"
     "      pushLog(a.name+' falls \u2014 but the author returns to your hand (costs '+cost+' attach'+(cost>1?'es':'')+' to replay).');\n"
     "      p._hasActive=p.team.some(c=>c.hp>0);\n"
     "      render(); return;\n"
     "    }\n"
     "    spawnKO(side, a.name);\n    try{ fxKO(side, a.name); }catch(e){}\n    if(!p.grave.includes(a)) p.grave.push(a);"),

    # 6 — Backstage surcharge
    ("replace",
     "function attackCostFor(side,ab){\n  let cost=ab.cost||0;",
     "function attackCostFor(side,ab,tgt){\n  let cost=ab.cost||0;\n"
     "  /* PAGEMASTER: striking a Backstage character costs +2 ABC \u2014 open to every\n"
     "     deck, but it spends a full turn of attaching. */\n"
     "  if(pmOn() && tgt && tgt.bench) cost+=PM.benchSurcharge;"),

    # 7 — replaying a returned commander costs attaches
    ("replace",
     "function drawnPlayChar(idx){\n  if(!S||!S.drawn) return;\n  const p=S.you, card=p.hand[idx];\n  if(!card||card.cat!=='char') return;",
     "function drawnPlayChar(idx){\n  if(!S||!S.drawn) return;\n  const p=S.you, card=p.hand[idx];\n  if(!card||card.cat!=='char') return;\n"
     "  /* a returned Pagemaster commander is not free to replay */\n"
     "  const pmCost=(card._pmCmd?(card._pmCost||0):0);\n"
     "  if(pmCost>0){\n"
     "    if(p.attachesLeft<pmCost){ toast(card.name+' needs '+pmCost+' attach'+(pmCost>1?'es':'')+' to return \u2014 you have '+p.attachesLeft+'.'); return; }\n"
     "    p.attachesLeft-=pmCost;\n"
     "    pushLog(card.name+' returns to the page for '+pmCost+' attach'+(pmCost>1?'es':'')+'.');\n"
     "  }"),

    # 8a — a replayed commander remembers its falls (inline placement)
    ("replace",
     "  const ch=makeChar(card._cdef, p._hpScale||1.0);\n  p.hand.splice(idx,1); p.team.push(ch);\n  if(where==='active')",
     "  const ch=makeChar(card._cdef, p._hpScale||1.0);\n"
     "  if(card._pmCmd){ ch._pmCmd=true; ch._pmReturns=card._pmReturns||0; }\n"
     "  p.hand.splice(idx,1); p.team.push(ch);\n  if(where==='active')"),

    # 8b — and in drawnPlayChar
    ("replace",
     "  const ch=makeChar(card._cdef, p._hpScale||1.0);\n  p.hand.splice(idx,1); p.team.push(ch);\n  if(!liveAct)",
     "  const ch=makeChar(card._cdef, p._hpScale||1.0);\n"
     "  if(card._pmCmd){ ch._pmCmd=true; ch._pmReturns=card._pmReturns||0; }\n"
     "  p.hand.splice(idx,1); p.team.push(ch);\n  if(!liveAct)"),

    # 9 — makeDeck accepts {d,i} refs (real fix)
    ("replace",
     "  def.ab.forEach((i,n)=>{ const a=DATA.abcs[def.d][i]; if(a) deck.push({cat:'abc',...clone(a),cid:'a'+i+'_'+n+Math.random().toString(36).slice(2,5)}); });",
     "  /* an entry is a plain index into def.d, or {d,i} naming its own book \u2014\n"
     "     a Pagemaster deck draws on two. The old line indexed def.d only, so a\n"
     "     {d,i} entry silently produced nothing. */\n"
     "  def.ab.forEach((r,n)=>{\n"
     "    const dk=(r&&typeof r==='object')?r.d:def.d, ix=(r&&typeof r==='object')?r.i:r;\n"
     "    const a=(DATA.abcs[dk]||[])[ix];\n"
     "    if(a) deck.push({cat:'abc',...clone(a),cid:'a'+ix+'_'+n+Math.random().toString(36).slice(2,5)});\n"
     "  });"),
]

TEST_SURFACE = ("\n/* test surface \u2014 read by tools/pagemaster.test.js */\n"
                "try{ window.ABC_PM = { PM, pmOn, pmBooksOf, pagemasterLegal, pmReturnCost,\n"
                "  newPlayer, checkKO, drawnPlayChar, attackCostFor, edResolveChar,\n"
                "  get S(){ return typeof S!=='undefined'?S:null; },\n"
                "  get APP(){ return typeof APP!=='undefined'?APP:null; } }; }catch(e){}\n")


def die(msg):
    print("ABORTED \u2014 file not modified.")
    print("  " + msg)
    sys.exit(1)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "src/game.src.html"
    if not os.path.exists(path):
        die(f"no such file: {path}")

    src = open(path, encoding="utf-8").read()

    if "function pagemasterLegal" in src:
        print("Already applied \u2014 Pagemaster engine is present. Nothing to do.")
        return

    for deck in ("romeojuliet", "odyssey"):
        if deck not in src:
            die(f"'{deck}' is missing from this file, so it is not your live source.\n"
                f"  Patching it would build on a stale base. Find the file with all twelve decks.")

    # every anchor must be present exactly once, BEFORE anything is written
    for n, (tag, old, new) in enumerate(EDITS, 1):
        c = src.count(old)
        if c != 1:
            die(f"edit {n}: anchor found {c} times, expected exactly 1.\n"
                f"  anchor starts: {old[:70]!r}\n"
                f"  Your file has moved on. Send Claude your current src/game.src.html.")

    out = src
    for tag, old, new in EDITS:
        out = out.replace(old, new, 1)

    # the test surface goes right after pmReturnCost
    m = re.search(r"function pmReturnCost\(ch\)\{", out)
    i = out.index("{", m.start())
    d = 0
    for k in range(i, len(out)):
        if out[k] == "{":
            d += 1
        elif out[k] == "}":
            d -= 1
            if d == 0:
                break
    out = out[:k + 1] + TEST_SURFACE + out[k + 1:]

    before = len(re.findall(r"__ABCASSET_\d+__", src))
    after = len(re.findall(r"__ABCASSET_\d+__", out))
    if before != after:
        die(f"asset placeholder count changed ({before} -> {after}).")
    if len(out) <= len(src):
        die("output is not larger than input.")

    backup = path + ".bak"
    shutil.copy(path, backup)
    open(path, "w", encoding="utf-8").write(out)

    print("Applied \u2014 Pagemaster engine layer.")
    print(f"  backup      : {backup}")
    print(f"  {path}: {len(src):,} -> {len(out):,} bytes (+{len(out)-len(src):,})")
    print(f"  placeholders: {after} (unchanged)")
    print()
    print("  Nothing is reachable from the UI yet \u2014 every rule is gated on")
    print("  APP.mode==='pagemaster', which nothing sets. The menu entry, commander")
    print("  picker and builder filter are the next piece.")
    print()
    print("  One real fix rode along: makeDeck() now accepts {d,i} ABC refs. The old")
    print("  line indexed one book only and would have silently dropped all 30 ABCs")
    print("  from the first Pagemaster deck.")
    print()
    print("  Next: python3 build.py")


if __name__ == "__main__":
    main()
