#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_hand_fan.py
Academic Battle Cards -- issue 4, 2026-08-23

The hand fan was defined only inside
    @media (max-width:760px), (pointer:coarse) and (max-width:1400px)
so a desktop matched neither branch and fell back to .hand{overflow-x:auto} --
a flat horizontal scroll strip. The fan also hardcoded :nth-child(1..7), so it
stopped fanning past seven cards on every device.

This replaces both hardcoded ladders with ONE computed fan that applies at every
width. Card index comes from a static :nth-child ladder (24 deep); the only
value JS supplies is --n on the .hand container. Rotation, arc and overlap all
derive from

    --off = --i - (--n - 1) / 2

so the fan is correct at any hand size instead of stopping at seven.

Card shape: .hc was 152x150, essentially square, which is why a fanned hand read
as a row of tiles. Cards are now driven by a height plus a 4:5 aspect ratio, so
shape and fan are independent and the overlap is a FRACTION OF CARD WIDTH rather
than a fixed pixel figure -- an 11px tuck that suits a 152px card is far too
aggressive on a 120px one.

Blast radius: every rule added is scoped to `.hand .hc`. The card detail modal
(.hand-view .hc) overrides width, height, max-height and transform with
!important and is unaffected; the pack overlay and deck builder use bare .hc,
which is left untouched.

Run from the repo root:

    python3 fix_hand_fan.py

Writes src/game.src.html.bak before touching anything. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

LADDER = "\n".join(".hand .hc:nth-child(%d){--i:%d}" % (i + 1, i) for i in range(24))
ZLAYER = "\n".join(".hand .hc:nth-child(%d){z-index:%d}" % (i + 1, i + 1) for i in range(10))

PATCHES = []

# --------------------------------------------------------------- A1: base ---
# The desktop fallback becomes the fan itself.
PATCHES.append((
    "fan-container",
    """.hand{display:flex;gap:8px;justify-content:center;align-items:flex-end;overflow-x:auto;padding:6px 4px 2px;scrollbar-width:thin}""",
    """/* ---------- computed hand fan (fix_hand_fan.py) ----------
   Applies at every width. --n is set on this element by render(); --i comes
   from the nth-child ladder below. Everything else derives from those two, so
   the fan stays correct at any hand size. */
.hand{
  --card-h:150px;      /* card height; overridden per breakpoint below      */
  --card-ar:0.8;       /* width / height -- 4:5, so it reads as a card      */
  --fan-step:4deg;     /* rotation per card away from centre                */
  --fan-arc:1.5px;     /* how far the outer cards drop                      */
  --fan-lift:24px;     /* hover lift                                        */
  --fan-scale:1.14;    /* hover scale                                       */
  --tuck-frac:0.09;    /* overlap per card past 5, as a fraction of width   */
  --card-w:calc(var(--card-h) * var(--card-ar));
  display:flex;justify-content:center;align-items:flex-end;
  gap:0;overflow:visible;padding:14px 4px 4px;
}
""" + LADDER + """
body[data-screen="play"] .hand .hc{
  --mid:calc((var(--n,1) - 1) / 2);
  --off:calc(var(--i,0) - var(--mid));
  flex:none;
  width:var(--card-w);min-width:var(--card-w);height:var(--card-h);
  transform-origin:bottom center;
  transition:transform .16s ease, box-shadow .16s ease;
  transform:translateY(calc(var(--off) * var(--off) * var(--fan-arc)))
            rotate(calc(var(--off) * var(--fan-step)));
  margin-left:calc(-1 * clamp(0px,
      (var(--n,1) - 5) * var(--card-w) * var(--tuck-frac),
      var(--card-w) * 0.72));
}
body[data-screen="play"] .hand .hc:first-child{margin-left:0}
""" + ZLAYER + """
.hand .hc:nth-child(n+11){z-index:11}
body[data-screen="play"] .hand .hc:hover,
body[data-screen="play"] .hand .hc:active,
body[data-screen="play"] .hand .hc.sel{
  transform:translateY(calc(var(--fan-lift) * -1)) scale(var(--fan-scale)) rotate(0deg);
  z-index:60;box-shadow:0 12px 24px rgba(0,0,0,.55);
}
/* a 4:5 card is narrower than the old square, so the question needs the room */
body[data-screen="play"] .hand .hc .hc-q{-webkit-line-clamp:6}""",
))

# ------------------------------------------------- A3 + A2: phone / coarse ---
PATCHES.append((
    "fan-mobile-block",
    """  body[data-screen="play"] .hand .hc{
    width:50px!important;min-width:50px!important;height:66px!important;padding:3px!important;font-size:7px;
    transform-origin:bottom center;transition:transform .16s ease,box-shadow .16s ease;flex:none;
  }
  body[data-screen="play"] .hand .hc:nth-child(1){transform:translateX(10px) rotate(-8deg)}
  body[data-screen="play"] .hand .hc:nth-child(2){transform:translateX(5px) rotate(-4deg)}
  body[data-screen="play"] .hand .hc:nth-child(4){transform:translateX(-5px) rotate(4deg)}
  body[data-screen="play"] .hand .hc:nth-child(5){transform:translateX(-10px) rotate(8deg)}
  body[data-screen="play"] .hand .hc:nth-child(6){transform:translateX(-15px) rotate(12deg)}
  body[data-screen="play"] .hand .hc:nth-child(7){transform:translateX(-20px) rotate(16deg)}
  body[data-screen="play"] .hand .hc:hover,
  body[data-screen="play"] .hand .hc:active,
  body[data-screen="play"] .hand .hc.sel{transform:translateY(-20px) scale(1.25) rotate(0deg)!important;z-index:40;
    box-shadow:0 10px 20px rgba(0,0,0,.55)}""",
    """  /* phone: shorter card, steeper fan, harder tuck. Shape and hover come from
     the shared computed rules -- only the tuning changes here. */
  /* phone typography only. Card height and fan tuning are set by the later
     block sharing this media query, which wins the cascade. */
  body[data-screen="play"] .hand .hc{padding:3px!important;font-size:7px}""",
))

# ------------------------------------------------------- A4: tablet coarse ---
PATCHES.append((
    "fan-tablet-block",
    """  body[data-screen="play"] .hand .hc{
    width:96px!important;min-width:96px!important;height:126px!important;padding:7px!important;font-size:11px!important;
  }
  body[data-screen="play"] .hand .hc:nth-child(1){transform:translateX(8px) rotate(-6deg)}
  body[data-screen="play"] .hand .hc:nth-child(2){transform:translateX(4px) rotate(-3deg)}
  body[data-screen="play"] .hand .hc:nth-child(4){transform:translateX(-4px) rotate(3deg)}
  body[data-screen="play"] .hand .hc:nth-child(5){transform:translateX(-8px) rotate(6deg)}
  body[data-screen="play"] .hand .hc:nth-child(6){transform:translateX(-12px) rotate(9deg)}
  body[data-screen="play"] .hand .hc:nth-child(7){transform:translateX(-16px) rotate(12deg)}
  body[data-screen="play"] .hand .hc:hover,
  body[data-screen="play"] .hand .hc:active,
  body[data-screen="play"] .hand .hc.sel{transform:translateY(-26px) scale(1.16) rotate(0deg)!important}""",
    """  /* tablet: bigger card, gentler fan, easy to grab */
  body[data-screen="play"] .hand{
    --card-h:132px;--fan-step:5deg;--fan-arc:1.9px;
    --fan-lift:26px;--fan-scale:1.16;--tuck-frac:0.10;
  }
  body[data-screen="play"] .hand .hc{padding:7px!important;font-size:11px!important}""",
))

# ------------------------------------------------- A5: iPad landscape block ---
# This one already used a near-5:7 card (106x150). Folded into the same system
# so there is exactly one place that decides card shape.
PATCHES.append((
    "fan-ipad-landscape",
    """  body[data-screen="play"] .hand .hc{
    flex:0 0 106px!important;              /* flex-basis governs a flex item, not width */
    width:106px!important;min-width:106px!important;max-width:106px!important;
    height:150px!important;max-height:150px!important;
  }
  body[data-screen="play"] .hand .hc .hc-q{-webkit-line-clamp:4}""",
    """  body[data-screen="play"] .hand{
    --card-h:150px;--fan-step:4.5deg;--fan-arc:1.7px;
    --fan-lift:26px;--fan-scale:1.16;--tuck-frac:0.09;
  }
  body[data-screen="play"] .hand .hc .hc-q{-webkit-line-clamp:5}""",
))

# ------------------------------------------------------------ A7: the count ---
# The single value the CSS cannot derive on its own.
PATCHES.append((
    "fan-count-on-container",
    """     <div class="hand">${you.hand.map((c,i)=>handCard(c,i)).join('')||'<span class="empty">No cards</span>'}</div></div>""",
    """     <div class="hand" style="--n:${you.hand.length}">${you.hand.map((c,i)=>handCard(c,i)).join('')||'<span class="empty">No cards</span>'}</div></div>""",
))

# ------------------------------------------- A6: the LATER phone override ---
# A second block with the SAME media query as the first appears further down and
# therefore wins the cascade: it resizes the card to 58x74 and re-declares the
# ladder. The earlier block's 50x66 was already dead code. Tuning is set here,
# after the earlier block, so this is the one that decides the phone card.
PATCHES.append((
    "fan-mobile-later-block",
    """  body[data-screen="play"] .hand .hc{width:58px!important;min-width:58px!important;height:74px!important}
  body[data-screen="play"] .hand .hc:nth-child(1){transform:translateX(6px) rotate(-6deg)}
  body[data-screen="play"] .hand .hc:nth-child(2){transform:translateX(3px) rotate(-3deg)}
  body[data-screen="play"] .hand .hc:nth-child(4){transform:translateX(-3px) rotate(3deg)}
  body[data-screen="play"] .hand .hc:nth-child(5){transform:translateX(-6px) rotate(6deg)}
  body[data-screen="play"] .hand .hc:nth-child(6){transform:translateX(-9px) rotate(9deg)}
  body[data-screen="play"] .hand .hc:nth-child(7){transform:translateX(-12px) rotate(12deg)}""",
    """  /* bigger, easier-to-hit cards + less overlap. This block shares its media
     query with the earlier phone block and wins the cascade, so the card
     height is settled here. 74px tall at 4:5 gives a 59px card -- the same
     fingertip target as the 58px it replaces. */
  body[data-screen="play"] .hand{
    --card-h:74px;--fan-step:6deg;--fan-arc:2.1px;
    --fan-lift:20px;--fan-scale:1.35;--tuck-frac:0.11;
  }""",
))

ALREADY = ["computed hand fan (fix_hand_fan.py)", "--tuck-frac", 'style="--n:$']


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("this file is missing romeojuliet/odyssey -- it is the stale "
            "snapshot, not the live build.")

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
    sc_after = out.count("<script")
    if sc_after != sc_before:
        die("script block count changed (%d -> %d)" % (sc_before, sc_after))

    # the old ladders must be gone, not merely supplemented
    if re.search(r'\.hand \.hc:nth-child\(\d\)\{transform:translateX', out):
        die("a hardcoded nth-child ladder survived -- refusing to leave two "
            "fan systems in place.")

    if out == src:
        die("no change produced.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_after)
    print("    script blocks %d (unchanged)" % sc_after)
    print("    card shape    4:5, height 70 / 132 / 150 by breakpoint")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
