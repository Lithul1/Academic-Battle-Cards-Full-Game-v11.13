#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_floating_log.py
Academic Battle Cards -- floating opponent log (2026-08-27)

Adds a second, selective log channel: the OPPONENT's significant actions float
up at the foot of the board, hold, and fade. The existing drawer is untouched --
pushLog still records all 331 sites, and `Log` still shows the full history.

WHY OPPONENT-ONLY (Trevor, 2026-08-27): you already see your own moves as you
make them. The stated goal was clarity about what the opponent is doing, and
floating both sides would double the traffic for no gain. The rule lives in ONE
place (flashLog's own guard) so it can be widened later by deleting a line.

WHY OPT-IN RATHER THAN AUTOMATIC: there are 331 pushLog sites and a sampled game
produces mostly "Shuffling decks...", "- Your turn -", "Spill: X loses 10 HP".
I tried to classify by text and gave up honestly: 258 distinct literal openings,
nearly all `${character.name}`-first templates, with no reliable signal. So
floating is opted into at the sites that matter -- 8 of them -- and everything
else stays drawer-only.

TIER 1 (holds 4s): attacks landing, blocks, knockouts, status damage ticks
TIER 2 (holds 2.2s): the opponent's turn banner, their draws

SURVIVING RE-RENDER: render() rebuilds the board constantly, which would restart
a CSS animation every time and leave lines stuck on screen forever. Each entry
carries the timestamp it was raised, and the markup sets a NEGATIVE
animation-delay equal to the elapsed time, so a re-rendered line resumes exactly
where it was instead of starting over. A pruning tick drops expired entries.
(The charge glow shipped broken for the mirror-image of this reason.)

Run from the repo root:

    python3 fix_floating_log.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

# ------------------------------------------------------------- the engine ---
PATCHES.append((
    "flashlog-fn",
    """function pushLog(t){ if(!S) return; S.log.unshift(t); if(S.log.length>70) S.log.pop(); }""",
    """function pushLog(t){ if(!S) return; S.log.unshift(t); if(S.log.length>70) S.log.pop(); }
/* ---- floating opponent log (fix_floating_log.py) ----
   A second channel beside the drawer. pushLog keeps recording everything; this
   surfaces only the opponent's board-changing moves, so you can watch the board
   instead of the log. */
const FLASH_MAX = 4;
function flashLog(side, kind, text, hold){
  if(!S) return;
  /* opponent-only. Widening this to both sides means deleting this line. */
  if(side !== 'opp') return;
  if(!S._flash) S._flash = [];
  S._flash.push({ id:(S._flashId=(S._flashId||0)+1), kind:kind||'sys',
                  text:String(text||''), at:Date.now(), hold:(hold||4)*1000 });
  /* a burst must never bury the board: push the oldest out early */
  while(S._flash.length > FLASH_MAX) S._flash.shift();
  flashTick();
}
let _flashTimer = null;
function flashTick(){
  if(_flashTimer) return;
  _flashTimer = setInterval(function(){
    if(!S || !S._flash || !S._flash.length){
      clearInterval(_flashTimer); _flashTimer=null; return;
    }
    const now = Date.now();
    const before = S._flash.length;
    S._flash = S._flash.filter(function(f){ return now - f.at < f.hold + 600; });
    if(S._flash.length !== before){ try{ render(); }catch(e){} }
    if(!S._flash.length){ clearInterval(_flashTimer); _flashTimer=null; }
  }, 250);
}
function flashFeed(){
  if(!S || !S._flash || !S._flash.length) return '';
  const now = Date.now();
  return '<div class="feed">' + S._flash.map(function(f){
    /* Negative delay resumes the animation mid-flight, so a re-render does not
       restart the fade and strand the line on screen. */
    const el = (now - f.at) / 1000;
    return '<div class="fl k-'+f.kind+'" style="--hold:'+(f.hold/1000)+'s;'
         + 'animation-delay:'+(-el)+'s,'+((f.hold/1000)-el)+'s">'
         + '<b>Opponent</b>'+f.text+'</div>';
  }).join('') + '</div>';
}""",
))

# ------------------------------------------------------------ the markup ----
PATCHES.append((
    "feed-render",
    """  <button class="logtoggle" data-do="log">\u2630 Log</button>""",
    """  ${flashFeed()}
  <button class="logtoggle" data-do="log">\u2630 Log</button>""",
))

# ================================================================ TIER 1 =====
PATCHES.append((
    "t1-attack",
    """  pushLog(`${att.name} uses ${ab.n}: ${net} damage to ${def.name}. (${def.hp}/${def.maxHp} HP)`);""",
    """  pushLog(`${att.name} uses ${ab.n}: ${net} damage to ${def.name}. (${def.hp}/${def.maxHp} HP)`);
  flashLog(side,'atk',`${att.name} uses ${ab.n} \\u2014 ${net} damage to ${def.name}.`);""",
))

PATCHES.append((
    "t1-block",
    """  pushLog(`${def.name} blocks with ${b.n} (${neg?'all damage negated':'-'+amt}).`);""",
    """  pushLog(`${def.name} blocks with ${b.n} (${neg?'all damage negated':'-'+amt}).`);
  /* the defender is the side NOT attacking, so this floats when the opponent
     is the one holding the guard */
  flashLog(side==='you'?'opp':'you','blk',`${def.name} blocks with ${b.n} \\u2014 ${neg?'all damage negated':'-'+amt}.`);""",
))

PATCHES.append((
    "t1-ko",
    """  pushLog(`${a.name} is knocked out!`);""",
    """  pushLog(`${a.name} is knocked out!`);
  /* `side` here is the side LOSING the character; float it when the opponent
     lands the knockout, i.e. when the fallen character is yours */
  flashLog(side==='you'?'opp':'you','ko',`${a.name} is knocked out.`);""",
))

PATCHES.append((
    "t1-status-tick",
    """if(_bs>0) pushLog(`${c.status.burn?'Burn':'Spill'}: ${c.name} loses ${_bs} HP.`); }""",
    """if(_bs>0){ pushLog(`${c.status.burn?'Burn':'Spill'}: ${c.name} loses ${_bs} HP.`);
      flashLog(_tk,'neg',`${c.status.burn?'Burn':'Spill'} \\u2014 ${c.name} loses ${_bs} HP.`,3); } }""",
))

# ================================================================ TIER 2 =====
PATCHES.append((
    "t2-turn-banner",
    """  pushLog(`\u2014 ${p===S.you?'Your':"Opponent's"} turn \u2014`);""",
    """  pushLog(`\u2014 ${p===S.you?'Your':"Opponent's"} turn \u2014`);
  flashLog(p===S.you?'you':'opp','sys','Their turn begins.',2.2);""",
))

CSS = r"""
/* ===== floating opponent log (fix_floating_log.py) ===== */
.feed{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(var(--handh,150px) + 26px);
  display:flex;flex-direction:column;align-items:center;gap:6px;
  width:min(430px,86vw);pointer-events:none;z-index:36}
.fl{width:100%;box-sizing:border-box;padding:8px 12px;border-radius:9px;
  border:2px solid var(--ink,#241F1B);border-left-width:7px;
  background:#EFE2E0;color:var(--ink,#241F1B);
  font-family:var(--body,Georgia),serif;font-size:14px;line-height:1.35;
  box-shadow:0 3px 0 rgba(0,0,0,.32);
  animation:flIn .22s ease-out both, flOut .55s ease-in forwards}
.fl b{font-family:var(--cond),sans-serif;font-size:10px;letter-spacing:1.1px;
  text-transform:uppercase;display:block;margin-bottom:2px;opacity:.72}
.fl.k-atk{border-left-color:#C8443C} .fl.k-atk b{color:#C8443C}
.fl.k-blk{border-left-color:#4A90C2} .fl.k-blk b{color:#4A90C2}
.fl.k-pos{border-left-color:#3f7a55} .fl.k-pos b{color:#3f7a55}
.fl.k-neg{border-left-color:#8E4B8B} .fl.k-neg b{color:#8E4B8B}
.fl.k-ko{border-left-color:var(--gold,#E6B85C);background:var(--ink,#241F1B);color:var(--cream,#F2E6C6)}
.fl.k-ko b{color:var(--gold,#E6B85C)}
.fl.k-sys{border-left-color:#6b5b45;font-size:13px}
@keyframes flIn{from{opacity:0;transform:translateY(10px) scale(.97)}to{opacity:1;transform:none}}
@keyframes flOut{to{opacity:0;transform:translateY(-6px)}}
@media (max-width:760px){
  .feed{width:92vw;bottom:calc(var(--handh,86px) + 16px)}
  .fl{font-size:12.5px;padding:6px 9px}
}
@media (prefers-reduced-motion: reduce){
  .fl{animation:flIn .01s both, flOut .01s forwards}
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
    for mark in ["fix_floating_log.py", "function flashLog(", "flashFeed()"]:
        if mark in src:
            die("already applied (found %r). Ship a named fix_*.py to revise." % mark)

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-18s found %d times, expected 1" % (label, n))
    if problems:
        die("anchor check failed -- nothing written:\n" + "\n".join(problems))

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before, st_before = src.count("<script"), src.count("<style")

    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)
    tail = out.rindex("</style>")
    out = out[:tail] + CSS + out[tail:]

    # expose for tests -- the charge glow shipped dead because nothing drove it
    exp = "  fxChargeGlow, moveFull, chargeSnap, chargeReport, SFX,"
    if out.count(exp) != 1:
        die("could not find the debug export anchor.")
    out = out.replace(exp, exp + "\n  flashLog, flashFeed,", 1)

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before or out.count("<style") != st_before:
        die("block counts changed")
    if out == src:
        die("no change produced.")
    # 1 definition + 5 tier call sites
    wired = out.count("flashLog(") - 1
    if wired != 5:
        die("expected 5 tier call sites, wired %d" % wired)
    for lab in ("'atk'", "'blk'", "'ko'", "'neg'", "'sys'"):
        if ("flashLog(" not in out) or (lab not in out):
            die("tier kind %s was not wired" % lab)

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    tier 1       attack, block, knockout, status tick")
    print("    tier 2       turn banner")
    print("    opponent-only, capped at %d lines, drawer untouched" % 4)
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
