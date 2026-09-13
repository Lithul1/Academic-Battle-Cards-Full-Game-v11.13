#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_timer_bar.py
Academic Battle Cards -- 2026-09-08

The turn clock becomes a depleting bar.

  was: a numeric countdown chip -- 59s, 58s, 57s...
  now: a bar that drains left to right over the same duration, with the seconds
       still readable inside it

Same timer, same settings, same behaviour -- only the presentation changes.
S._timeLeft and S.settings.turnTimer are untouched, so the difficulty presets
(and the Sic Soc boss's 15s) keep working exactly as they do now.

The bar reads at a glance from across a classroom, which a two-digit number does
not, and it earns its urgency: it warms through amber and then red as it drains,
and pulses under five seconds rather than just changing colour.

The number stays inside the bar. Removing it would cost precision for anyone who
wants it, and a bar alone cannot tell you whether you have eight seconds or two.

IMPLEMENTATION: paintTimer() already updates the chip in place every second
without a full render -- the bar reuses that, setting a width percentage rather
than replacing text. No new timer, no new interval.

Run from the repo root:

    python3 fix_timer_bar.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

# ---- markup: a bar with a fill and the seconds inside it --------------------
PATCHES.append((
    "markup",
    """${S.turn==='you'&&!S.over?`<span id="turnclock" class="turnclock${(S._timeLeft<=5)?' low':''}">\u23f1 ${Math.max(0,(S._timeLeft!=null?S._timeLeft:(S.settings.turnTimer||60)))}s</span>`:''}""",
    """${S.turn==='you'&&!S.over?(function(){
      const _tot=+(S.settings.turnTimer||60)||60;
      const _left=Math.max(0,(S._timeLeft!=null?S._timeLeft:_tot));
      const _pct=Math.max(0,Math.min(100,(_left/_tot)*100));
      const _st=_left<=5?' low':(_left<=Math.max(8,_tot*0.34)?' warn':'');
      return `<div id="turnclock" class="turnbar${_st}" role="timer" aria-label="${_left} seconds left">`
           + `<div id="turnbarfill" class="tb-fill" style="width:${_pct}%"></div>`
           + `<span id="turnbartext" class="tb-text">${_left}s</span></div>`;
    })():''}""",
))

# ---- paint: same tick, width instead of text -------------------------------
PATCHES.append((
    "paint",
    """function paintTimer(){
  const el=document.getElementById('turnclock'); if(!el||!S) return;
  const t=Math.max(0,S._timeLeft|0); el.textContent='\u23f1 '+t+'s'; el.classList.toggle('low', t<=5);
}""",
    """function paintTimer(){
  /* paintTimer runs every second WITHOUT a full render, so it must not rebuild
     the element -- it sets the fill width and the label in place. */
  const el=document.getElementById('turnclock'); if(!el||!S) return;
  const tot=+(S.settings.turnTimer||60)||60;
  const t=Math.max(0,S._timeLeft|0);
  const fill=document.getElementById('turnbarfill');
  const txt=document.getElementById('turnbartext');
  if(fill) fill.style.width=Math.max(0,Math.min(100,(t/tot)*100))+'%';
  if(txt) txt.textContent=t+'s';
  el.setAttribute('aria-label', t+' seconds left');
  el.classList.toggle('low', t<=5);
  el.classList.toggle('warn', t>5 && t<=Math.max(8, tot*0.34));
}""",
))

CSS = r"""
/* ===== turn time bar (fix_timer_bar.py) =====
   Replaces the numeric chip. Reads from across a room, which two digits do not,
   and earns its urgency by warming as it drains rather than only changing
   colour at the end. The seconds stay inside it: a bar alone cannot tell you
   whether you have eight seconds or two. */
.turnbar{
  position:relative; width:clamp(120px,22vw,210px); height:18px;
  border-radius:9px; overflow:hidden;
  background:rgba(0,0,0,.34);
  border:1px solid #6b5a33;
  box-shadow:inset 0 1px 3px rgba(0,0,0,.45);
  flex:0 0 auto;
}
.turnbar .tb-fill{
  position:absolute; left:0; top:0; bottom:0;
  background:linear-gradient(90deg,#7FB77E,#A8CE86);
  transition:width .95s linear, background .5s ease;
  border-radius:9px 0 0 9px;
}
.turnbar.warn .tb-fill{background:linear-gradient(90deg,#D79A3A,#E8C05A)}
.turnbar.low  .tb-fill{background:linear-gradient(90deg,#B5352A,#D2543F)}
.turnbar .tb-text{
  position:absolute; inset:0; display:grid; place-items:center;
  font-family:var(--cond),sans-serif; font-size:11px; letter-spacing:.8px;
  font-weight:800; color:#F6ECD2; text-shadow:0 1px 2px rgba(0,0,0,.85);
  pointer-events:none;
}
/* the last five seconds pulse -- motion, not just a colour change */
@keyframes tbPulse{0%,100%{opacity:1}50%{opacity:.55}}
.turnbar.low{animation:tbPulse .9s ease-in-out infinite}
@media (max-width:760px){
  .turnbar{width:clamp(96px,30vw,150px);height:16px}
  .turnbar .tb-text{font-size:10px}
}
@media (prefers-reduced-motion: reduce){
  .turnbar.low{animation:none}
  .turnbar .tb-fill{transition:none}
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
    if "fix_timer_bar.py" in src or "turn time bar" in src:
        die("already applied. Ship a named fix_*.py to revise.")

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-8s found %d times, expected 1" % (label, n))
    if problems:
        die("anchor check failed -- nothing written:\n" + "\n".join(problems))

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before, st_before = src.count("<script"), src.count("<style")

    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)
    tail = out.rindex("</style>")
    out = out[:tail] + CSS + out[tail:]

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before or out.count("<style") != st_before:
        die("block counts changed")

    # the timer's own state must be untouched -- presentation only
    for need in ("S._timeLeft = +(S.settings.turnTimer||60);",
                 "turnTimerId=setInterval(tickTurnTimer,1000);"):
        if need not in out:
            die("the timer's mechanism changed; this patch is presentation only.")
    if "turnclock" not in out:
        die("paintTimer can no longer find its element.")

    # expose paintTimer: it updates the bar in place every second without a
    # render, which is the half a render-only test cannot reach
    exp = "  atkPoolOf,"
    if out.count(exp) == 1:
        out = out.replace(exp, exp + "\n  paintTimer, startTurnTimer, stopTurnTimer,", 1)

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    the bar drains over S.settings.turnTimer, unchanged")
    print("    green -> amber at a third left -> red and pulsing under 5s")
    print("    seconds stay readable inside the bar")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
