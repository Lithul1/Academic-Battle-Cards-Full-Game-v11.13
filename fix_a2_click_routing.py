#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_a2_click_routing.py
Academic Battle Cards -- 2026-09-06

REPORTED: the Affective Fallacy "Read further" prompt appears, but neither
button does anything and the panel cannot be dismissed.

CAUSE, and it is mine. The board's click handler resolves its target through an
explicit allow-list of attributes:

    const t = e.target.closest('[data-do],[data-idx],[data-act],[data-ans],
      [data-def],[data-pick],[data-deck],[data-opp],[data-diff],[data-pile],
      [data-bld],[data-audio],[data-benchinfo],[data-scrim],[data-ippick],
      [data-mgpick]');

fix_lens_affective_a2.py added the handling for `data-af` and `data-afans`
INSIDE that function, but never added the attributes to the selector. So
clicking "Read further" produced `t = null` (or an unrelated ancestor), the
branch was never reached, and nothing happened -- while S._af stayed set, so the
panel stayed up with no way to close it.

The handler code was correct. The click simply never arrived.

This is the third time this session a change has been made in one of two places
that must agree -- after the charge glow's selectors and the D3 button gate. The
allow-list is the failure mode: adding a branch to the handler is not enough,
the attribute must also be admitted, and nothing enforces that.

The patch adds both attributes, and adds a guard asserting that every data-
attribute the handler branches on is present in the selector -- so the next
person to add a branch is told immediately rather than shipping a dead button.

Run from the repo root:

    python3 fix_a2_click_routing.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

OLD = ("const t=e.target.closest('[data-do],[data-idx],[data-act],[data-ans],"
       "[data-def],[data-pick],[data-deck],[data-opp],[data-diff],[data-pile],"
       "[data-bld],[data-audio],[data-benchinfo],[data-scrim],[data-ippick],"
       "[data-mgpick]');")

NEW = ("/* The selector is an allow-list: a branch below is unreachable unless its\n"
       "   attribute appears here. data-af / data-afans were added to the handler\n"
       "   without being added here, so the Affective Fallacy buttons were dead. */\n"
       "  const t=e.target.closest('[data-do],[data-idx],[data-act],[data-ans],"
       "[data-def],[data-pick],[data-deck],[data-opp],[data-diff],[data-pile],"
       "[data-bld],[data-audio],[data-benchinfo],[data-scrim],[data-ippick],"
       "[data-mgpick],[data-af],[data-afans]');")


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    if "fix_a2_click_routing.py" in src or "[data-afans]');" in src:
        die("already applied. Ship a named fix_*.py to revise.")
    if "function afOffer(" not in src:
        die("fix_lens_affective_a2.py must be applied first.")

    if src.count(OLD) != 1:
        die("could not find the click selector exactly once.")

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    out = src.replace(OLD, NEW, 1)

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != src.count("<script"):
        die("script block count changed")
    if out == src:
        die("no change produced.")

    # Every attribute the handler branches on must be admitted by the selector.
    # This is the check that would have caught the bug when it was introduced.
    i = out.index("const t=e.target.closest('[data-do]")
    sel_end = out.index("');", i)
    selector = out[i:sel_end]
    body = out[sel_end:out.index("\n}", sel_end)]
    branched = set(re.findall(r"t\.dataset\.([A-Za-z0-9_]+)", body))

    def kebab(name):
        return "data-" + re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), name)

    missing = sorted(a for a in branched if ("[" + kebab(a) + "]") not in selector)
    if missing:
        for a in missing:
            sys.stderr.write("  handler branches on t.dataset.%s but the selector "
                             "does not admit %s\n" % (a, kebab(a)))
        die("%d dead branch(es) in the click handler." % len(missing))

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  click routing fixed")
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    admitted     data-af, data-afans")
    print("    verified     every t.dataset.* branch is reachable (%d checked)"
          % len(branched))
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
