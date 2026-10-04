#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_opponent_zoom.py
Academic Battle Cards -- play-to-center zoom (2026-08-29)

When the OPPONENT plays a card you cannot otherwise read, it rises to the centre
of the board at full size, holds, and fades. This is the mechanism that carries
opponent clarity in TCG Live -- not the log. The log tells you what happened;
the zoom lets you actually read the card.

WHICH MOMENTS
  * a bookmark they play  -- the important one: its effect is invisible
                             otherwise, and it resolves immediately
  * a character they swap in -- you need to see who arrived and what it does

Deliberately NOT zoomed:
  * their attack -- the attacking card is already on screen at full size, and
    the floating log now names the move and the damage
  * their attaches -- several per turn; zooming each would be strobing

REUSES EXISTING RENDERERS. buildBmPreview / buildFePreview / buildCharPreview
already produce the full card face used by the deck builder and the archive, so
the zoom shows exactly the card the player would see if they inspected it. No
second card renderer to drift out of sync.

RENDER-SAFE BY CONSTRUCTION. render() rebuilds the board constantly. A CSS
animation on a live node restarts every time and strands the element on screen
-- that is precisely how the charge glow shipped broken. So the zoom lives in
state (S._zoom) and the markup carries a NEGATIVE animation-delay equal to the
elapsed time, so a re-render resumes mid-flight. Identical to the floating log,
which is already proven.

Non-interactive: pointer-events:none, so it never eats a tap meant for the
board underneath.

Run from the repo root:

    python3 fix_opponent_zoom.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

PATCHES.append((
    "zoom-engine",
    """function flashFeed(){""",
    """/* ---- play-to-centre zoom (fix_opponent_zoom.py) ----
   The opponent's unreadable plays, shown big enough to actually read. */
function zoomCard(side, html, hold){
  if(!S || side !== 'opp') return;      /* your own plays are already in hand */
  if(!html) return;
  S._zoom = { html:html, at:Date.now(), hold:(hold||2600) };
  zoomTick();
}
let _zoomTimer = null;
function zoomTick(){
  if(_zoomTimer) return;
  _zoomTimer = setInterval(function(){
    if(!S || !S._zoom){ clearInterval(_zoomTimer); _zoomTimer=null; return; }
    if(Date.now() - S._zoom.at > S._zoom.hold + 500){
      S._zoom = null; clearInterval(_zoomTimer); _zoomTimer=null;
      try{ render(); }catch(e){}
    }
  }, 200);
}
/* Build the same card face the player would see on inspect, so the zoom can
   never drift from the real card. */
function zoomHtmlFor(card){
  try{
    if(!card) return '';
    if(card.cat==='bookmark' || card.bm || card.rarity){
      const b = (typeof card.i==='number' && DATA.bookmarks[card.i]) ? DATA.bookmarks[card.i] : card;
      return buildBmPreview(b);
    }
    if(card.fe) return buildFePreview(card);
    if(card.cat==='char' || card.atk) return buildCharPreview(card, card.deck||card.d||'');
    if(card.cat==='abc') return buildAbcPreview(card);
  }catch(e){}
  return '';
}
function zoomLayer(){
  if(!S || !S._zoom) return '';
  const el = (Date.now() - S._zoom.at) / 1000;
  const h  = S._zoom.hold / 1000;
  return '<div class="zoomwrap"><div class="zoomcard" style="'
       + 'animation-delay:'+(-el)+'s,'+(h-el)+'s">'
       + '<div class="zoomtag">Opponent plays</div>'
       + S._zoom.html + '</div></div>';
}
function flashFeed(){""",
))

PATCHES.append((
    "zoom-render",
    """  ${flashFeed()}""",
    """  ${zoomLayer()}
  ${flashFeed()}""",
))

# ---- the two moments ------------------------------------------------------
PATCHES.append((
    "zoom-bookmark",
    """  const card=P.hand[idx], isYou=side==='you', act=active(P);""",
    """  const card=P.hand[idx], isYou=side==='you', act=active(P);
  /* the opponent's bookmark resolves at once and is invisible otherwise */
  if(!isYou) zoomCard(side, zoomHtmlFor(card), 2600);""",
))

PATCHES.append((
    "zoom-swap",
    """        if(alt>=0){ try{ doSwitch(p,alt); p.flags.swapped=true; pushLog('Opponent pulls back a crippled character.'); }catch(e){} }""",
    """        if(alt>=0){ try{ doSwitch(p,alt); p.flags.swapped=true; pushLog('Opponent pulls back a crippled character.');
          const _in=active(p); if(_in) zoomCard('opp', zoomHtmlFor(_in), 2200);
          flashLog('opp','sys',`${_in?_in.name:'A character'} steps up.`,2.4); }catch(e){} }""",
))

CSS = r"""
/* ===== play-to-centre zoom (fix_opponent_zoom.py) ===== */
.zoomwrap{position:fixed;inset:0;display:grid;place-items:center;z-index:38;
  pointer-events:none}
.zoomcard{
  animation:zmIn .28s cubic-bezier(.2,.9,.3,1.3) both, zmOut .45s ease-in forwards;
  filter:drop-shadow(0 14px 26px rgba(0,0,0,.55));position:relative;
  transform-origin:center}
.zoomtag{position:absolute;top:-13px;left:50%;transform:translateX(-50%);
  background:var(--ink,#241F1B);color:var(--gold,#E6B85C);
  font-family:var(--cond),sans-serif;font-size:10px;letter-spacing:1.3px;
  text-transform:uppercase;padding:3px 11px;border-radius:20px;
  border:2px solid var(--gold,#E6B85C);white-space:nowrap;z-index:2}
/* the shared preview card is sized for a modal; hold it at a readable size
   without letting it exceed the board */
.zoomcard .pv-card{max-width:min(330px,80vw);max-height:74vh;overflow:hidden}
@keyframes zmIn{from{opacity:0;transform:scale(.62) translateY(26px)}
                to{opacity:1;transform:none}}
@keyframes zmOut{to{opacity:0;transform:scale(.94) translateY(-14px)}}
@media (max-width:760px){
  .zoomcard .pv-card{max-width:min(280px,86vw);max-height:62vh}
}
@media (pointer:coarse) and (orientation:landscape) and (max-height:699px){
  .zoomcard .pv-card{max-width:min(230px,44vw);max-height:80vh}
  .zoomtag{font-size:9px;padding:2px 8px}
}
@media (prefers-reduced-motion: reduce){
  .zoomcard{animation:zmIn .01s both, zmOut .01s forwards}
}
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
    if "function flashFeed(" not in src:
        die("fix_floating_log.py must be applied first.")
    for mark in ["fix_opponent_zoom.py", "function zoomCard(", "zoomLayer()"]:
        if mark in src:
            die("already applied (found %r). Ship a named fix_*.py to revise." % mark)

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-16s found %d times, expected 1" % (label, n))
    if problems:
        die("anchor check failed -- nothing written:\n" + "\n".join(problems))

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before, st_before = src.count("<script"), src.count("<style")

    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)
    tail = out.rindex("</style>")
    out = out[:tail] + CSS + out[tail:]

    exp = "  flashLog, flashFeed,"
    if out.count(exp) != 1:
        die("could not find the debug export anchor.")
    out = out.replace(exp, exp + "\n  zoomCard, zoomLayer, zoomHtmlFor,", 1)

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before or out.count("<style") != st_before:
        die("block counts changed")
    if out == src:
        die("no change produced.")
    if "pointer-events:none" not in out[out.index(".zoomwrap"):out.index(".zoomcard{")]:
        die("the zoom layer must not intercept taps.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    zooms        opponent bookmark (2.6s), opponent swap-in (2.2s)")
    print("    reuses       buildBmPreview / buildCharPreview / buildFePreview")
    print("    render-safe  state-driven, negative animation-delay resume")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
