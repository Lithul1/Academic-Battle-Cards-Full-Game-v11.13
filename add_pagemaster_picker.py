#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_pagemaster_picker.py — the Pagemaster menu entry and commander picker.

    python3 add_pagemaster_picker.py src/game.src.html
    python3 build.py

Apply AFTER add_pagemaster_engine.py and add_fe_ownership.py. This script
checks for both and refuses to run without them.

WHAT THIS ADDS
--------------
1. a "Pagemaster" entry on the main menu, below Custom Play
2. pmPickerScreen() — choose two commanders from the ones you own, grouped by
   book, with a readout of what the pair opens up before you commit
3. the router entries and the screen dispatcher line
4. CSS, inserted at top level so it is not stranded inside an @media block

WHAT IT DOES NOT DO YET
-----------------------
Pressing "Build the deck" lands on the ordinary builder. The builder does not
yet filter to your two books, enforce the four-per-book minimum, or cap
bookmarks at one copy — that is the next patch. Until then the picker is
browsable and the flow is walkable, but a Pagemaster deck is not enforceable.

Flow after this patch:
    Menu -> Pagemaster -> Difficulty -> Commander picker -> (builder)

Safety: verifies every anchor before touching anything, builds in memory, writes
a .bak, refuses to run twice, checks the asset placeholder count is unchanged,
and confirms the CSS anchor is not inside an @media block.
"""
import sys, os, re, shutil

CSS = """
/* --- Pagemaster commander picker (must stay outside any @media) --- */
.pm-slots{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px}
.pm-slot{flex:1;min-width:230px;background:var(--cream-hi,#FBF3DD);border:3px dashed var(--ink,#241F1B);
  border-radius:11px;padding:10px;min-height:108px;position:relative;color:var(--ink,#241F1B)}
.pm-slot.filled{border-style:solid;box-shadow:0 4px 0 rgba(40,25,12,.4)}
.pm-slot .lbl{font-family:var(--cond);font-size:10.5px;letter-spacing:1.2px;text-transform:uppercase;color:#8a6a1a}
.pm-slot .empty{display:grid;place-items:center;height:72px;font-size:12.5px;font-style:italic;color:#9a8a6a}
.pm-slot .nm{font-family:var(--disp);font-size:14px;margin:3px 0 1px;line-height:1.15}
.pm-slot .bk{font-family:var(--cond);font-size:10.5px;letter-spacing:.7px;text-transform:uppercase;color:#6b5c42}
.pm-slot .row{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}
.pm-slot .chip{font-family:var(--cond);font-size:10px;letter-spacing:.5px;background:var(--cream,#F2E6C6);
  border:2px solid var(--ink,#241F1B);border-radius:7px;padding:2px 7px}
.pm-slot .x{position:absolute;top:7px;right:7px;width:23px;height:23px;border-radius:50%;
  border:2px solid var(--ink,#241F1B);background:var(--cream,#F2E6C6);cursor:pointer;
  font-family:var(--disp);font-size:11px;display:grid;place-items:center;color:var(--ink,#241F1B)}
.pm-read{background:var(--cream-hi,#FBF3DD);border:2px solid var(--ink,#241F1B);border-radius:9px;
  padding:10px 12px;font-size:12.5px;line-height:1.6;color:var(--ink,#241F1B)}
.pm-read.warn{background:#fdf0e2;border-color:var(--red,#B53A2C)}
.pm-rr{display:flex;gap:8px;flex-wrap:wrap;margin-top:7px}
.pm-rr span{font-family:var(--cond);font-size:11px;letter-spacing:.5px;background:var(--cream,#F2E6C6);
  border:2px solid var(--ink,#241F1B);border-radius:8px;padding:3px 9px}
.pm-bookhead{display:flex;align-items:baseline;gap:9px;margin:13px 0 6px;padding-bottom:3px;
  border-bottom:1px dashed #c9b58a}
.pm-bookhead b{font-family:var(--disp);font-size:14px}
.pm-bookhead small{font-family:var(--cond);font-size:10.5px;letter-spacing:.7px;color:#8a6a1a;text-transform:uppercase}
.pm-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:8px}
.pm-cmd{text-align:left;background:var(--cream-hi,#FBF3DD);border:2.5px solid var(--ink,#241F1B);
  border-left-width:6px;border-radius:9px;padding:8px 9px;cursor:pointer;position:relative;
  box-shadow:0 3px 0 rgba(40,25,12,.4);color:var(--ink,#241F1B)}
.pm-cmd.sel{background:#e8f2e8;border-color:#2f7d5c;box-shadow:0 3px 0 #2f7d5c}
.pm-cmd.dim{opacity:.34}
.pm-cmd .n{font-family:var(--disp);font-size:12.5px;line-height:1.15;margin-bottom:2px}
.pm-cmd .m{display:flex;gap:5px;flex-wrap:wrap;margin-top:4px}
.pm-cmd .m i{font-family:var(--cond);font-size:9.5px;font-style:normal;letter-spacing:.4px;
  background:var(--cream,#F2E6C6);border:1.5px solid var(--ink,#241F1B);border-radius:5px;padding:1px 5px}
.pm-cmd .u{position:absolute;top:6px;right:7px;font-family:var(--cond);font-size:9px;letter-spacing:1px;
  color:#fff;background:#6B4E8A;border-radius:4px;padding:1px 5px}
.pm-cmd .p{font-size:10.5px;color:#5a4a32;margin-top:5px;line-height:1.4;font-style:italic}
"""

SCREEN = r"""
/* ---------------- Pagemaster: choose two commanders ---------------- */
function pmPickerScreen(){
  const pick=(APP.pmCommanders||[]);
  const owned=(typeof feOwnedList==='function')?feOwnedList():(DATA.firsteds||[]);
  const slots=[0,1].map(function(i){
    const f=(DATA.firsteds||[]).find(function(x){ return x.id===pick[i]; });
    if(!f) return '<div class="pm-slot"><div class="lbl">Commander '+(i+1)+'</div><div class="empty">choose below</div></div>';
    return '<div class="pm-slot filled" style="border-color:'+(f.accent||'#241F1B')+'">'
      + '<button class="x" data-do="pm-drop:'+i+'">\u2715</button>'
      + '<div class="lbl">Commander '+(i+1)+'</div>'
      + '<div class="nm">'+f.name+'</div>'
      + '<div class="bk">'+(f.deck?setName(f.deck):'no book')+'</div>'
      + '<div class="row"><span class="chip">'+f.hp+' HP</span>'
      + (f.archetype?'<span class="chip">'+f.archetype+'</span>':'')
      + (f.atk&&f.atk.label?'<span class="chip">'+f.atk.label+'</span>':'')
      + (f.blk&&f.blk.label?'<span class="chip">'+f.blk.label+'</span>':'')
      + '</div></div>';
  }).join('');

  let read='', warn=false, ready=false;
  if(pick.length<2){
    read = pick.length===0
      ? 'Pick your first commander. Two from the same book builds a single-book deck; two from different books builds a hybrid.'
      : 'Now pick a second. A different book opens both pools, and asks for at least '+PM.minChPerBook+' characters from each.';
  } else {
    const bk=pmBooksOf(pick[0],pick[1]);
    let poolCh=0, poolAb=0;
    bk.books.forEach(function(k){ poolCh+=(DATA.characters[k]||[]).length; poolAb+=(DATA.abcs[k]||[]).length; });
    warn = poolAb<=PM.ab;
    ready = true;
    read = '<b>'+bk.books.map(function(k){ return setName(k); }).join(' + ')+'</b> \u2014 '
      + (bk.mono?'a single-book deck':'a hybrid')+'.'
      + '<div class="pm-rr">'
      + '<span>'+PM.ch+' characters from '+poolCh+'</span>'
      + '<span>'+PM.ab+' trivia from '+poolAb+'</span>'
      + '<span>'+PM.bm+' bookmarks, one copy each</span>'
      + '<span>'+PM.cr+' lenses</span>'
      + (bk.mono?'':'<span>min '+PM.minChPerBook+' characters from each book</span>')
      + '</div>'
      + (warn?('<div style="margin-top:8px"><b>Note</b> \u2014 '+poolAb+' trivia cards for a '+PM.ab
              +'-card deck means you will play nearly the whole pool. A second book opens it up.</div>'):'');
  }

  const byBook={};
  owned.forEach(function(f){ (byBook[f.deck||'_']=byBook[f.deck||'_']||[]).push(f); });
  const order=(window.DECK_ORDER||Object.keys(DATA.characters));
  const pool=order.filter(function(k){ return byBook[k]; }).map(function(k){
    const list=byBook[k];
    return '<div class="pm-bookhead"><b>'+setName(k)+'</b><small>'+list.length+' commander'+(list.length>1?'s':'')
      + ' \u00b7 '+(DATA.characters[k]||[]).length+' characters \u00b7 '+(DATA.abcs[k]||[]).length+' trivia</small></div>'
      + '<div class="pm-grid">'+list.map(function(f){
          const on=pick.indexOf(f.id)>=0, full=pick.length>=2 && !on;
          const pt=((f.passive&&f.passive.text)||'');
          return '<button class="pm-cmd'+(on?' sel':'')+(full?' dim':'')+'" data-do="pm-pick:'+f.id+'"'
            + ' style="border-left-color:'+(f.accent||'#241F1B')+'">'
            + (f.tier==='ultra'?'<span class="u">ULTRA</span>':'')
            + '<div class="n">'+f.name+'</div>'
            + '<div class="m"><i>'+f.hp+' HP</i>'+(f.archetype?'<i>'+f.archetype+'</i>':'')
            + (f.atk&&f.atk.label?'<i>'+f.atk.label+'</i>':'')
            + (f.blk&&f.blk.label?'<i>'+f.blk.label+'</i>':'')+'</div>'
            + (pt?'<div class="p">'+((f.passive.name?'<b>'+f.passive.name+'</b> \u2014 ':''))
                 + pt.slice(0,104)+(pt.length>104?'\u2026':'')+'</div>':'')
            + '</button>';
        }).join('')+'</div>';
  }).join('');

  return '<div class="title-screen sub-screen">'
    + '<img class="title-logo sm" src="'+(window.ABC_LOGO||'')+'" alt="Academic Battle Cards">'
    + '<h2 class="sub-h">Pagemaster \u2014 choose two commanders</h2>'
    + '<p class="title-sub">They open on the field, and they decide which books your deck may draw from.</p>'
    + '<div class="rules">'
    + '<div class="pm-slots">'+slots+'</div>'
    + '<div class="pm-read'+(warn?' warn':'')+'">'+read+'</div>'
    + '<div class="sub-actions" style="margin:12px 0 0">'
    + '<button class="bigbtn" data-do="pm-build"'+(ready?'':' disabled')+'>Build the deck \u203a</button>'
    + '<button class="toolbtn" data-do="pm-clear">Clear</button>'
    + '<button class="toolbtn" data-do="pm-random">Surprise me</button>'
    + '</div>'
    + '<h2>Your commanders</h2>'
    + (owned.length?pool:'<p>You do not own any 1st Editions yet. Open packs in the Vault to collect them.</p>')
    + '</div>'
    + '<div class="sub-actions"><button class="toolbtn" data-do="menu">\u2039 Back to menu</button></div>'
    + '</div>';
}
"""

MENU_BTN = ('<button class="menu-btn" data-do="go-pagemaster"><span class="menu-ic">\u265b</span>'
            '<span class="menu-tx"><b>Pagemaster</b><small>Two commanders, one or two books \u2014 build a deck around them</small></span>'
            '<span class="menu-go">\u203a</span></button>')

EDITS = [
    # 1 — the screen builder, above guideScreen
    ("insert", "function guideScreen(){", SCREEN + "function guideScreen(){"),

    # 2 — menu entry, directly after Custom Play
    ("replace",
     '</button>\n      <button class="menu-btn" data-do="go-drawn">',
     '</button>\n      ' + MENU_BTN + '\n      <button class="menu-btn" data-do="go-drawn">'),

    # 3 — screen dispatcher
    ("replace",
     "  if(APP.screen==='custom'){ root.innerHTML=customScreen()+_ov(); return; }",
     "  if(APP.screen==='custom'){ root.innerHTML=customScreen()+_ov(); return; }\n"
     "  if(APP.screen==='pmpick'){ root.innerHTML=pmPickerScreen()+_ov(); return; }"),

    # 4 — difficulty routes into the picker when the mode is Pagemaster
    ("replace",
     "  if(t.dataset.diff){\n    applyDifficultyToSettings(t.dataset.diff);\n"
     "    if(APP.mode==='quick'){ APP.customDeck=null; APP.oppDeck='random'; beginBattle(); }\n"
     "    else { APP.screen='custom'; render(); }\n    return;\n  }",
     "  if(t.dataset.diff){\n    applyDifficultyToSettings(t.dataset.diff);\n"
     "    if(APP.mode==='quick'){ APP.customDeck=null; APP.oppDeck='random'; beginBattle(); }\n"
     "    else if(APP.mode==='pagemaster'){ APP.screen='pmpick'; render(); }\n"
     "    else { APP.screen='custom'; render(); }\n    return;\n  }"),

    # 5 — router: the menu entry and the picker's own buttons
    ("replace",
     "    else if(d==='go-drawn'){ APP.mode='custom'; APP.drawnMode=true; APP.screen='difficulty'; render(); }",
     "    else if(d==='go-pagemaster'){ APP.mode='pagemaster'; APP.drawnMode=true; APP.pmCommanders=APP.pmCommanders||[]; APP.screen='difficulty'; render(); }\n"
     "    else if(d.indexOf('pm-pick:')===0){ const id=d.slice(8); const a=APP.pmCommanders||(APP.pmCommanders=[]);\n"
     "      const at=a.indexOf(id); if(at>=0) a.splice(at,1); else if(a.length<PM.fe) a.push(id); render(); }\n"
     "    else if(d.indexOf('pm-drop:')===0){ (APP.pmCommanders||[]).splice(+d.slice(8),1); render(); }\n"
     "    else if(d==='pm-clear'){ APP.pmCommanders=[]; render(); }\n"
     "    else if(d==='pm-random'){ const o=(typeof feOwnedList==='function'?feOwnedList():(DATA.firsteds||[])).slice();\n"
     "      for(let i=o.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); const t2=o[i]; o[i]=o[j]; o[j]=t2; }\n"
     "      APP.pmCommanders=o.slice(0,PM.fe).map(f=>f.id); render(); }\n"
     "    else if(d==='pm-build'){ const a=APP.pmCommanders||[];\n"
     "      if(a.length<PM.fe){ toast('Choose two commanders first.'); return; }\n"
     "      const bk=pmBooksOf(a[0],a[1]);\n"
     "      APP.youDeck=bk.books[0]; APP.customDeck=null;\n"
     "      toast('Deck building for Pagemaster is the next piece \\u2014 the builder is not filtered yet.');\n"
     "      APP.screen='builder'; render(); }\n"
     "    else if(d==='go-drawn'){ APP.mode='custom'; APP.drawnMode=true; APP.screen='difficulty'; render(); }"),
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

    if "function pmPickerScreen" in src:
        print("Already applied \u2014 the commander picker is present. Nothing to do.")
        return

    if "function pagemasterLegal" not in src:
        die("the Pagemaster engine is not present.\n  Run add_pagemaster_engine.py first.")
    if "function feOwned(" not in src:
        die("first-edition ownership is not present.\n  Run add_fe_ownership.py first.")
    for deck in ("romeojuliet", "odyssey"):
        if deck not in src:
            die(f"'{deck}' is missing \u2014 this is not your live source.")

    for n, (tag, old, new) in enumerate(EDITS, 1):
        c = src.count(old)
        if c != 1:
            die(f"edit {n}: anchor found {c} times, expected 1.\n  anchor: {old[:70]!r}")

    out = src
    for tag, old, new in EDITS:
        out = out.replace(old, new, 1)

    # CSS at top level — verify the anchor is not inside an @media block
    anchor = None
    for cand in ("/* --- discard / retry UI (must stay outside any @media) --- */",
                 "/* --- archetype chip (must stay outside any @media) --- */"):
        if cand in out:
            anchor = cand
            break
    if not anchor:
        die("could not find a known top-level CSS anchor to insert before.")
    at = out.index(anchor)
    prev = out.rfind("@media", 0, at)
    if prev >= 0:
        seg = out[prev:at]
        if seg.count("{") - seg.count("}") > 0:
            die("the CSS anchor sits inside an @media block \u2014 the styles would be stranded.")
    out = out.replace(anchor, CSS + anchor, 1)

    before = len(re.findall(r"__ABCASSET_\d+__", src))
    after = len(re.findall(r"__ABCASSET_\d+__", out))
    if before != after:
        die(f"asset placeholder count changed ({before} -> {after}).")
    if len(out) <= len(src):
        die("output is not larger than input.")

    shutil.copy(path, path + ".bak")
    open(path, "w", encoding="utf-8").write(out)

    print("Applied \u2014 Pagemaster menu entry and commander picker.")
    print(f"  backup      : {path}.bak")
    print(f"  {path}: {len(src):,} -> {len(out):,} bytes (+{len(out)-len(src):,})")
    print(f"  placeholders: {after} (unchanged)")
    print()
    print("  Menu -> Pagemaster -> Difficulty -> Commander picker")
    print()
    print("  'Build the deck' lands on the ORDINARY builder \u2014 it does not yet filter")
    print("  to your two books or enforce the format. That is the next patch, and the")
    print("  screen says so with a toast when you press it.")
    print()
    print("  Next: python3 build.py")


if __name__ == "__main__":
    main()
