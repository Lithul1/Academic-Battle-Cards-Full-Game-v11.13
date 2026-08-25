#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_builder_ui.py
Academic Battle Cards -- builder redesign, Step 4 (2026-08-24)

Reference: ABC_Builder_Redesign_WiringPlan.md section 3.4.
Requires fix_builder_columns_and_skins.py (step 3) first.

Replaces the single-column stacked-sections builder with the two-column tabbed
layout from builder_prototype.html, on top of the column state shipped in
step 3.

WHAT IS AND IS NOT REWRITTEN
  * The chip builders -- chRow, abRow, bmRow, crRow, feRow -- are LEFT ALONE.
    They are large, correct, and already handle ownership, reskins, previews and
    expansion cards. Only the shell around them changes.
  * builderScreen()'s return block becomes a shell: folder tabs, a pool panel
    showing one tab at a time, and the two deck columns.
  * The deck columns are new markup: until now the builder had no list of what
    was actually in the deck, only counters.

NEW BEHAVIOUR
  * Five tabs: Characters / 1st Editions / Attack-Block / Bookmarks / Crit Lenses
  * Both decks on screen; clicking a column header focuses it. The pool, the
    caps and the legality line all follow the focused column.
  * Per-section counters and a per-column total.
  * Attack/Block search box and a power filter (Any / x1-x4).
  * Deck identity (from DECK_COMP), Fill gaps, Randomize -- per column.
  * Confirm saves that column only.
  * Colour by card type: bookmark gold, crit orange, attack red, block blue,
    1st edition purple, characters tan with a heavy border.

Run from the repo root:

    python3 fix_builder_ui.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

# --------------------------------------------------------------------------
NEW_FUNCS = r"""
/* ===== builder redesign, step 4 (fix_builder_ui.py) =======================
   The shell only. chRow/abRow/bmRow/crRow/feRow are untouched and still
   produce every chip; these functions decide which of them is on screen and
   draw the two deck columns beside them. */
const BD_TABS = [['ch','Characters'],['fe','1st Editions'],['ab','Attack/Block'],
                 ['bm','Bookmarks'],['cr','Crit Lenses']];

function bdTab(){ return (APP.builder && APP.builder.tab) || 'ch'; }
/* has this deck been built into at all? once it has, its book is committed and
   only Reset releases it. */
function bdHasCards(def){
  if(!def) return false;
  return !!((def.ch||[]).length || (def.ab||[]).length || (def.fe||[]).length
         || (def.bm||[]).length || (def.cr||[]).length);
}

function bdTabsHTML(){
  const t = bdTab();
  return '<div class="bdk-tabs">' + BD_TABS.map(function(x){
    return '<button class="bdk-tab'+(t===x[0]?' on':'')+'" data-bld="bdtab:'+x[0]+'">'+x[1]+'</button>';
  }).join('') + '</div>';
}

/* the Attack/Block filter bar -- only meaningful on that tab */
function bdAbFilter(shown, total){
  if(bdTab()!=='ab') return '';
  const B=APP.builder, q=(B.abQuery||''), pw=(B.abPower||0);
  const seg=[0,1,2,3,4].map(function(p){
    return '<b class="'+(pw===p?'on':'')+'" data-bld="abpw:'+p+'">'+(p?'\u00d7'+p:'Any')+'</b>';
  }).join('');
  return '<div class="bdk-abflt">'
    + '<input id="bd-abq" class="bdk-q" placeholder="Search questions\u2026" value="'
    + String(q).replace(/"/g,'&quot;') + '">'
    + '<div class="bdk-pw">'+seg+'</div>'
    + '<span class="bdk-cnt">'+shown+' of '+total+'</span></div>';
}

/* one entry in a deck column */
function bdItem(side, kind, idx, label, cls){
  return '<div class="bdk-it '+cls+'" data-bld="bddel:'+side+';'+kind+';'+idx+'" title="Remove">'
       + label + '<span class="bdk-x">\u2715</span></div>';
}
function bdNameOf(def, kind, v){
  try{
    if(kind==='ch'){
      const bks=booksOf(def)||[def.d];
      for(let i=0;i<bks.length;i++){
        const c=(DATA.characters[bks[i]]||[]).find(function(x){return x.id===v;});
        if(c){ const m=(def.ed&&def.ed[v]==='modern')?edCharFor(bks[i],v):null;
               return m?m.c.name:c.name; }
      }
      return v;
    }
    if(kind==='fe'){ const f=firstedById(v); return f?f.name:v; }
    if(kind==='cr'){ const c=DATA.crits[+v]; return c?c.name:('Lens '+v); }
    if(kind==='bm'){ const b=DATA.bookmarks[+v]; return b?b.name:('Bookmark '+v); }
    if(kind==='ab'){
      const bk=(v&&typeof v==='object')?v.d:def.d, i=(v&&typeof v==='object')?v.i:+v;
      const a=(DATA.abcs[bk]||[])[i];
      if(!a) return 'Card '+i;
      return (a.type==='ATTACK'?'ATK':'BLK')+' \u2014 '+String(a.q||'').slice(0,30)+'\u2026';
    }
  }catch(e){}
  return String(v);
}

/* a deck column: sections, counters, legality, tools, confirm */
function bdColumn(side){
  const B=APP.builder, col=B[side], def=col&&col.def;
  const on=(B.active===side);
  const title=(side==='pm')?'Pagemaster Deck Build':'Custom Deck Build';
  if(!def){
    return '<div class="bdk-col '+side+(on?' on':'')+'">'
      + '<h3 data-bld="bdfocus:'+side+'">'+title+'</h3>'
      + '<div class="bdk-empty">'+(side==='pm'
          ? 'Choose two commanders in Pagemaster to open this deck.'
          : 'Open the Custom builder to start this deck.')+'</div></div>';
  }
  const C=capsFor(def), c=deckCounts(def);
  const bks=booksOf(def)||[def.d];
  const KIND={ch:'ch',fe:'fe',ab:'ab',bm:'bm',cr:'cr'};
  const CLS={ch:'k-ch',fe:'k-fe',bm:'k-bm',cr:'k-cr'};
  let secs='';
  BD_TABS.forEach(function(x){
    const kind=KIND[x[0]], list=(def[kind]||[]);
    if(!list.length) return;
    const over=(c[kind]>C[kind]);
    secs += '<div class="bdk-sh'+(over?' over':'')+'">'+x[1]
          + '<span>'+c[kind]+'/'+C[kind]+'</span></div>';
    secs += list.map(function(v,i){
      let cls=CLS[kind]||'';
      if(kind==='ab'){
        const bk=(v&&typeof v==='object')?v.d:def.d, ix=(v&&typeof v==='object')?v.i:+v;
        const a=(DATA.abcs[bk]||[])[ix];
        cls=(a&&a.type==='ATTACK')?'k-atk':'k-blk';
      }
      return bdItem(side, kind, i, bdNameOf(def,kind,v), cls);
    }).join('');
  });
  if(!secs) secs='<div class="bdk-empty">Empty \u2014 click cards to add.</div>';
  const overT=(c.total>C.total);
  const status=deckIsPm(def) ? pmBuildStatus(def)
    : ('<div class="pm-bstat '+(c.total>C.total||!c.ch?'warn':'ok')+'">'
       + (c.total>C.total ? '<b>Over by '+(c.total-C.total)+'</b>'
          : (!c.ch ? '<b>Add at least one character</b>' : '<b>Legal.</b> '+c.total+'/'+C.total))
       + '</div>');
  const bad=/warn/.test(status);
  return '<div class="bdk-col '+side+(on?' on':'')+'">'
    + '<h3 data-bld="bdfocus:'+side+'">'+title+'</h3>'
    + '<div class="bdk-books">'+bks.map(setName).join(' + ')+'</div>'
    + '<div class="bdk-total'+(overT?' over':'')+'">Total <b>'+c.total+'/'+C.total+'</b></div>'
    + '<div class="bdk-items">'+secs+'</div>'
    + status
    + '<div class="bdk-tools">'
      + '<button data-bld="bdidentity:'+side+'" title="Build to this book\u2019s deck identity">Deck identity</button>'
      + '<button data-bld="bdfill:'+side+'" title="Top up to the caps with cards you own">Fill gaps</button>'
      + '<button data-bld="bdrand:'+side+'" title="A complete legal deck from cards you own">Randomize</button>'
    + '</div>'
    + '<button class="bdk-confirm" data-bld="bduse:'+side+'"'+(bad?' disabled':'')+'>Confirm?</button>'
    + '</div>';
}

/* build to the deck's own DECK_COMP identity, then leave it legal */
function bdIdentity(def){
  const bks=booksOf(def)||[def.d];
  const C=capsFor(def);
  const cs=bks.map(compFor);
  const avg=function(f){ return Math.round(cs.reduce(function(a,x){return a+x[f];},0)/cs.length); };
  const want={ ch:Math.min(avg('ch'),C.ch), ab:Math.min(avg('ab'),C.ab),
               bm:Math.min(avg('bm'),C.bm), cr:Math.min(avg('cr'),C.cr) };
  /* Averaging two books and then clamping to the tighter Pagemaster caps can
     land under the total -- hamlet+macbeth averages to 58 against a required
     62. Pagemaster wants the deck exactly full, so spend the shortfall where
     there is still headroom: bookmarks, then trivia, then bodies. */
  const _budget=C.total-(def.fe||[]).length;
  let _short=_budget-(want.ch+want.ab+want.bm+want.cr);
  ['bm','ab','ch'].forEach(function(f){
    if(_short<=0) return;
    const room=C[f]-want[f];
    const add=Math.min(room,_short);
    want[f]+=add; _short-=add;
  });
  const keepFe=(def.fe||[]).slice();
  def.ch=[]; def.ab=[]; def.bm=[]; def.cr=[];
  const perCh=Math.max(1,Math.ceil(want.ch/bks.length));
  bks.forEach(function(bk){ poolCh(bk).slice(0,perCh).forEach(function(id){
    if(def.ch.length<want.ch) def.ch.push(id); }); });
  /* trivia is authored in reading order, so a plain slice takes every ATTACK
     before it reaches a BLOCK -- abStarter already balances both types */
  const perAb=Math.max(1,Math.ceil(want.ab/bks.length));
  bks.forEach(function(bk){
    const got=abStarter(bk, perAb);
    got.forEach(function(i){ if(def.ab.length<want.ab)
      def.ab.push(bks.length>1?{d:bk,i:i}:i); });
  });
  def.cr=poolCr().slice(0,want.cr);
  def.fe=keepFe;
  fillGaps(def, Object.assign({}, want, { total:C.total }));
  clampDeck(def);
  return def;
}
"""

# --------------------------------------------------------------------------
NEW_RETURN = r"""  const _tabNow=bdTab();
  const _rows={ ch:chRow, fe:feRow, ab:abRow, bm:bmRow, cr:crRow };
  const _label={ ch:'Characters', fe:'1st Editions', ab:'Attack / Block cards',
                 bm:'Bookmarks', cr:'Crit-Cards (Critical Lenses)' };
  const _sub={
    ch: deckIsPm(def)?_books.map(b=>setName(b)).join(' + ')+' · min '+PM.minChPerBook+' each':'pick your roster',
    fe: 'Commander-style deck anchors · from '+(booksOf(def)||[k]).map(setName).join(' or '),
    ab: _books.map(b=>setName(b)).join(' + ')+' trivia',
    bm: deckIsPm(def)?'one copy each':'add copies',
    cr: 'pick up to '+CAP.cr
  };
  const _grid={ ch:'ch', fe:'ch', ab:'ab', bm:'bm', cr:'ch' };
  const _body=_rows[_tabNow]||'';
  return `<div class="builder bdk ${edFlt!=='all'?'flt-'+edFlt:''}">
    <div class="bd-top">
      <button class="toolbtn" data-do="title">‹ Back</button>
      <h1>Deck Builder</h1>
    </div>
    <div class="bdk-wrap">
      <div class="bdk-pool">
        ${bdTabsHTML()}
        <div class="bdk-folder">
          ${(_tabNow==='ch'||_tabNow==='ab'||_tabNow==='fe') ? `<div class="bd-setpick bdk-books${bdHasCards(def)?' locked':''}" title="${bdHasCards(def)?'This deck is '+setName(k)+' \u2014 Reset to start a different book':'Pick the book to build from'}">
            ${DECK_ORDER.map(dk=>bdDeckBox(dk,k===dk)).join('')}
          </div>` : ''}
          ${_tabNow==='ch'||_tabNow==='ab' ? bdExpansionShelf(k, APP.builder.fanOpen!==false) : ''}
          ${bdAbFilter(APP.builder._abShown||0, APP.builder._abTotal||0)}
          <div class="bd-sec"><h3>${_label[_tabNow]} <small>${_sub[_tabNow]}</small></h3>
            <div class="${_tabNow==='bm'?'bd-bmgrid':'bd-grid '+_grid[_tabNow]}">${_body}</div></div>
        </div>
      </div>
      <div class="bdk-cols">
        ${bdColumn('pm')}
        ${bdColumn('cu')}
      </div>
    </div>
    <div class="bd-actions">
      <button class="toolbtn" data-bld="reset">Reset to full deck</button>
      <button class="toolbtn" data-bld="gencode">⛓ Generate code</button>
    </div>
    <div id="bd-codebox" class="bd-codebox" style="display:${APP.builder.code?'flex':'none'}">
      <input class="code-input" id="bd-codeout" readonly value="${APP.builder.code||''}">
      <button class="toolbtn" data-bld="copycode">Copy</button>
    </div>
  </div>`;
}
"""

CSS = r"""
/* ===== builder redesign, step 4 ===== */
.bdk .bd-top{padding:0 10px 8px}
.bdk-wrap{display:flex;gap:14px;align-items:flex-start;padding:0 10px 10px}
.bdk-pool{flex:1 1 auto;min-width:0}
.bdk-cols{flex:0 0 430px;display:flex;gap:10px}
@media (max-width:1100px){ .bdk-wrap{flex-direction:column} .bdk-cols{flex:none;width:100%} }
.bdk-tabs{display:flex;gap:4px;padding-left:6px}
.bdk-tab{background:var(--cream-hi,#FBF3DD);border:2.5px solid var(--ink,#241F1B);border-bottom:none;
  border-radius:9px 9px 0 0;padding:7px 15px;cursor:pointer;font-family:var(--cond);font-size:14px;
  letter-spacing:1.1px;text-transform:uppercase;color:#9b4a3c;opacity:.6;position:relative;top:3px}
.bdk-tab.on{opacity:1;top:0;color:#C0392B;background:var(--cream,#F2E6C6)}
.bdk-folder{background:var(--cream,#F2E6C6);border:2.5px solid var(--ink,#241F1B);
  border-radius:0 12px 12px 12px;padding:8px}
.bdk-books{padding:2px 2px 10px!important;margin-bottom:9px;
  border-bottom:1.5px dashed rgba(0,0,0,.22);justify-content:flex-start}
.bdk-books .bdx{width:52px}
/* once a deck is committed to a book the others dim: the row still shows the
   whole shelf, but clicking elsewhere cannot take the deck away from you */
.bdk-books.locked .bdx:not(.sel){opacity:.32;filter:grayscale(.55)}
.bdk-books.locked .bdx:not(.sel):hover{opacity:.5}
.bdk-abflt{display:flex;gap:8px;align-items:center;padding:2px 2px 8px;margin-bottom:8px;
  border-bottom:1.5px dashed rgba(0,0,0,.22)}
.bdk-q{flex:1;min-width:0;font-family:var(--body,Georgia),serif;font-size:12.5px;padding:6px 9px;
  border:2px solid var(--ink,#241F1B);border-radius:7px;background:#fffdf5}
.bdk-pw{display:flex;border:2px solid var(--ink,#241F1B);border-radius:7px;overflow:hidden}
.bdk-pw b{font-family:var(--cond);font-size:11px;padding:5px 9px;cursor:pointer;font-weight:normal;
  background:var(--cream-hi,#FBF3DD);border-right:1px solid rgba(0,0,0,.18)}
.bdk-pw b:last-child{border-right:none}
.bdk-pw b.on{background:var(--ink,#241F1B);color:var(--cream,#F2E6C6);font-weight:bold}
.bdk-cnt{font-family:var(--cond);font-size:10.5px;color:#6b5b45;white-space:nowrap}

.bdk-col{flex:1;min-width:0;background:var(--cream,#F2E6C6);border:3px solid var(--ink,#241F1B);
  border-radius:10px;padding-bottom:8px;opacity:.55;transition:opacity .14s}
.bdk-col.on{opacity:1;box-shadow:0 0 0 3px var(--gold,#E6B85C)}
.bdk-col h3{margin:0;padding:8px 6px;text-align:center;font-family:var(--cond);font-size:13.5px;
  letter-spacing:1px;text-transform:uppercase;cursor:pointer;border-bottom:2px solid var(--ink,#241F1B);
  background:var(--cream-hi,#FBF3DD)}
.bdk-col.on h3{background:var(--gold,#E6B85C)}
.bdk-col.pm h3{color:#1E3A5F} .bdk-col.cu h3{color:#5B4B8A}
.bdk-col.on.pm h3,.bdk-col.on.cu h3{color:var(--ink,#241F1B)}
.bdk-books,.bdk-total{font-family:var(--cond);font-size:10px;text-align:center;padding:4px 6px 2px;color:#4a3f31}
.bdk-total{border-top:1px dotted rgba(0,0,0,.2)}
.bdk-total.over{color:#B03A30;font-weight:bold}
.bdk-items{max-height:50vh;overflow-y:auto;padding:4px 6px}
.bdk-sh{font-family:var(--cond);font-size:9px;letter-spacing:1.1px;text-transform:uppercase;
  color:#6b5b45;margin:7px 0 3px;border-bottom:1px dotted rgba(0,0,0,.25);padding-bottom:2px}
.bdk-sh span{float:right;font-weight:bold}
.bdk-sh.over span{color:#B03A30}
.bdk-it{border:2px solid var(--ink,#241F1B);border-radius:6px;padding:4px 7px;margin-bottom:4px;
  font-family:var(--cond);font-size:10.5px;font-weight:bold;cursor:pointer;position:relative;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:20px}
.bdk-it .bdk-x{position:absolute;right:5px;top:3px;opacity:.45}
.bdk-it:hover .bdk-x{opacity:1}
/* colour by card type */
.bdk-it.k-ch{background:#DFD2AC}
.bdk-it.k-fe{background:#7E5AA8;color:#fff}
.bdk-it.k-bm{background:#E8B54B}
.bdk-it.k-cr{background:#D9743A;color:#fff}
.bdk-it.k-atk{background:#C8443C;color:#fff}
.bdk-it.k-blk{background:#4A90C2;color:#fff}
.bdk-empty{padding:14px;font-family:var(--cond);font-size:10px;opacity:.55;text-align:center}
.bdk-tools{display:flex;gap:4px;padding:6px 6px 0}
.bdk-tools button{flex:1;font-family:var(--cond);font-size:9px;padding:5px 2px;cursor:pointer;
  border:1.5px solid var(--ink,#241F1B);border-radius:5px;background:var(--cream-hi,#FBF3DD);line-height:1.15}
.bdk-tools button:hover{background:var(--gold,#E6B85C)}
.bdk-confirm{display:block;width:calc(100% - 12px);margin:8px 6px 0;padding:7px;
  border:2.5px solid var(--ink,#241F1B);border-radius:6px;background:#E4E0EE;cursor:pointer;
  font-family:var(--cond);font-size:14px;letter-spacing:1px}
.bdk-confirm[disabled]{opacity:.4;cursor:not-allowed}
.bdx .ebx-sm{padding:4px 10px;min-width:0}
"""

HANDLERS = r"""  else if(op==='bdset'){ /* alias, kept for clarity in markup */ handleBuilder('set:'+arg); return; }
  else if(op==='bdtab'){ APP.builder.tab=arg; APP.builder.code=''; }
  else if(op==='bdfocus'){ builderFocus(arg); }
  else if(op==='abpw'){ APP.builder.abPower=+arg; }
  else if(op==='abq'){ APP.builder.abQuery=(arg===undefined?'':cmd.slice(4)); }
  else if(op==='bddel'){
      const p=arg.split(';'), side=p[0], kind=p[1], ix=+p[2];
      const d=(APP.builder[side]||{}).def;
      if(d && d[kind]) d[kind].splice(ix,1);
      if(side==='cu' && kind==='fe') APP.builder.cu.code='';
      B.code=''; }
  else if(op==='bdidentity'){ builderFocus(arg);
      const d=APP.builder[arg]&&APP.builder[arg].def; if(d){ bdIdentity(d); B.code=''; toast('Built to the deck identity.'); } }
  else if(op==='bdfill'){ builderFocus(arg);
      const d=APP.builder[arg]&&APP.builder[arg].def;
      if(d){ const _c=deckIsPm(d)?{ch:PM.ch,ab:PM.ab,bm:PM.bm,cr:PM.cr,total:PM.total}
                                 :Object.assign({},compFor(d.d),{total:LIMITS.total});
             fillGaps(d,_c); clampDeck(d); B.code=''; toast('Filled gaps with cards you own.'); } }
  else if(op==='bdrand'){ builderFocus(arg);
      const d=APP.builder[arg]&&APP.builder[arg].def;
      if(d){
        if(!deckIsPm(d)){
          const pool=feOwnedList().filter(function(f){ return f.deck===d.d; });
          d.fe=pool.slice(0,LIMITS.fe).map(function(f){ return f.id; });
        }
        bdIdentity(d); B.code=''; toast('Randomized from cards you own.'); } }
  else if(op==='bduse'){ builderFocus(arg); handleBuilder('use'); return; }
"""


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    if "function makeBuilderState(" not in src:
        die("fix_builder_columns_and_skins.py (step 3) must be applied first.")
    for mark in ["fix_builder_ui.py", "function bdColumn(", "bdk-wrap"]:
        if mark in src:
            die("already applied (found %r). Ship a named fix_*.py to revise." % mark)

    # ---- the return block, extracted exactly -----------------------------
    i = src.index("function builderScreen(){")
    j = src.index('  return `<div class="builder ', i)
    k = src.index("\n}\n", j)
    old_return = src[j:k + 3]
    if src.count(old_return) != 1:
        die("builderScreen return block is not unique.")

    anchors = [
        ("new-funcs", "function builderScreen(){", NEW_FUNCS + "\nfunction builderScreen(){"),
        ("return-block", old_return, NEW_RETURN),
        ("handlers", "  else if(op==='bdtab-reserved'){}\n", None),  # placeholder, replaced below
    ]

    out = src
    out = out.replace(anchors[0][1], anchors[0][2], 1)
    out = out.replace(old_return, NEW_RETURN, 1)

    # handlers go in ahead of the first existing builder op
    hook = "  else if(op==='edcycle'){"
    if out.count(hook) != 1:
        die("could not find the handler insertion point exactly once.")
    out = out.replace(hook, HANDLERS + hook, 1)

      # option 2: the book row browses, it never replaces the deck. Committing
    # happens on the first card; Reset is the only way back out.
    set_old = ("  if(op==='set'){ if(!deckUnlocked(arg)){ toast(setName(arg)+' is locked \\u2014 buy a Deck License in the Vault.'); return; }\n"
               "    if(def.d===arg){ B.fanOpen=(B.fanOpen===false); } else { B.def=defaultDeck(arg); B.code=''; B.edFilter='all'; B.fanOpen=true; } }")
    if out.count(set_old) != 1:
        die("could not find the 'set' handler exactly once.")
    set_new = ("  if(op==='set'){ if(!deckUnlocked(arg)){ toast(setName(arg)+' is locked \\u2014 buy a Deck License in the Vault.'); return; }\n"
               "    if(def.d===arg){ B.fanOpen=(B.fanOpen===false); }\n"
               "    else if(deckIsPm(def)){ toast('A Pagemaster deck plays the two books its commanders opened.'); }\n"
               "    else if(bdHasCards(def)){ toast('This deck is '+setName(def.d)+'. Use Reset to start a different book.'); }\n"
               "    else { /* the deck is empty, so switching book costs nothing */\n"
               "      def.d=arg; B.code=''; B.edFilter='all'; B.fanOpen=true; } }")
    out = out.replace(set_old, set_new, 1)

    reset_old = "  else if(op==='reset'){ B.def=defaultDeck(def.d); B.code=''; }"
    if out.count(reset_old) != 1:
        die("could not find the 'reset' handler exactly once.")
    reset_new = ("  else if(op==='reset'){\n"
                 "    /* Reset now CLEARS. That is what releases the book row: a committed\n"
                 "       deck refuses a book change, so there has to be a way back out.\n"
                 "       Use Deck identity to get a starter list again. */\n"
                 "    const _pm=deckIsPm(def);\n"
                 "    const _n={ d:def.d, ch:[], ab:[], bm:[], cr:[], fe:_pm?(def.fe||[]).slice():[],\n"
                 "               ed:{}, edab:[], edbm:{} };\n"
                 "    if(_pm){ _n.pm=true; _n.books=(def.books||[]).slice(); }\n"
                 "    B.def=_n; B.code='';\n"
                 "    toast(_pm?'Deck cleared \\u2014 commanders kept.':'Deck cleared \\u2014 pick a book to start again.'); }")
    out = out.replace(reset_old, reset_new, 1)

    # the button says what it now does
    out = out.replace('data-bld="reset">Reset to full deck<', 'data-bld="reset">Reset (clear deck)<', 1)

    # the Attack/Block search and power filter must actually filter the pool.
    # _abPool is the one line that feeds abRow, so the filter goes there and
    # abRow itself stays untouched.
    pool_old = "  const _abPool=_books.reduce((acc,bk)=>acc.concat((DATA.abcs[bk]||[]).map((a,i)=>({a,i,bk}))),[]);"
    if out.count(pool_old) != 1:
        die("could not find the _abPool line exactly once.")
    pool_new = (
        "  const _abAll=_books.reduce((acc,bk)=>acc.concat((DATA.abcs[bk]||[]).map((a,i)=>({a,i,bk}))),[]);\n"
        "  /* search + power filter feed abRow; abRow itself is unchanged */\n"
        "  const _abQ=String((APP.builder.abQuery)||'').trim().toLowerCase();\n"
        "  const _abP=+(APP.builder.abPower||0);\n"
        "  const _abPool=_abAll.filter(function(o){\n"
        "    if(_abP && (o.a.power||0)!==_abP) return false;\n"
        "    if(_abQ && String(o.a.q||'').toLowerCase().indexOf(_abQ)<0) return false;\n"
        "    return true; });\n"
        "  APP.builder._abShown=_abPool.length; APP.builder._abTotal=_abAll.length;"
    )
    out = out.replace(pool_old, pool_new, 1)

    # keep focus in the search box across the re-render
    ren_old = "  else if(op==='abq'){ APP.builder.abQuery=(arg===undefined?'':cmd.slice(4)); }"
    if out.count(ren_old) == 1:
        out = out.replace(ren_old,
            "  else if(op==='abq'){ APP.builder.abQuery=(arg===undefined?'':cmd.slice(4));\n"
            "      render();\n"
            "      try{ const _e=document.getElementById('bd-abq');\n"
            "           if(_e){ _e.focus(); _e.setSelectionRange(_e.value.length,_e.value.length); } }catch(e){}\n"
            "      return; }", 1)

    # expose the new helpers for tests and preview capture
    exp = "  makeBuilderState, builderFocus, handleBuilder, edModCount, clone,"
    if out.count(exp) != 1:
        die("could not find the debug export anchor.")
    out = out.replace(exp, exp + "\n  builderScreen, bdIdentity, bdColumn, bdTab, deckCounts,", 1)

  # css goes at the end of the last style block
    css_hook = "\n/* ===== builder redesign, step 4 ====="
    tail = out.rindex("</style>")
    out = out[:tail] + CSS + out[tail:]

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != src.count("<script"):
        die("script block count changed")
    if out.count("<style") != src.count("<style"):
        die("style block count changed")
    if out == src:
        die("no change produced.")

    # .bdx already exists as the 60px deck-picker box. Any future namespace must
    # not collide with a class the game already styles.
    import re as _re
    if _re.search(r'class="builder\s+bdx[\s"]', out):
        die("the builder root carries .bdx, which is the 60px deck-picker box "
            "class -- the whole builder would be crushed to 60px wide.")
    for _cls in ("bdk-wrap", "bdk-pool", "bdk-col", "bdk-tab"):
        if _re.search(r'(^|[\s,}])\.' + _cls + r'\s*[{,]', src, _re.M):
            die("class .%s already exists in the game -- pick another namespace." % _cls)

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  step 4 applied")
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    tabs + two columns + counters + ab search/power filter")
    print("    chip builders (chRow/abRow/bmRow/crRow/feRow) untouched")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
