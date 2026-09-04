#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_lens_card_text.py
Academic Battle Cards -- lens card text (2026-09-04)

The five rewritten lenses were still printing their OLD passives on the card.
Players were reading rules the engine no longer runs -- and in Archetypal's case,
a rule the engine never ran.

Text only. No behaviour changes; each new line describes what the code shipped in
fix_lens_rewrites_1.py, fix_lens_formalism_f1.py and fix_lens_affective_a2.py
actually does.

  Formalism      symbols are stripped from ENEMY moves only, not everyone's
                 -- and the old line advertised First Strike, which the engine
                 has never had
  Affective      the automatic wrong-answer damage is gone; the risk is now an
                 optional second question
  Structuralism  the ascending order is optional and rewarded, not enforced
  Archetypal     First Strike replaced with the archetype count the code reads
  Deconstruction keyword inversion replaced with cross-payment priced in Exposed

Wording is kept to the register the other twelve lenses use: an em-dashed clause
naming the concept, then the rule in plain terms.

Run from the repo root:

    python3 fix_lens_card_text.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

# (label, old, new)
PATCHES = [
    ("formalism",
     r"""passive:'Strip the context \u2014 all special symbols (Pierce, Negate, Cap, First Strike, Sacrifice) are ignored.',""",
     r"""passive:'Strip the context \u2014 special symbols (Pierce, Negate, Cap, Sacrifice) are ignored on ENEMY moves. Yours still work.',"""),

    ("affective",
     r"""passive:'Critical anxiety \u2014 any wrong trivia answer deals 10 damage to that player\u2019s Active.',""",
     r"""passive:'Read further \u2014 after a correct answer you may take a second question, drawn at random from your book. Correct: heal your Active 20 and draw a card. Wrong: your Active takes 10.',"""),

    ("structuralism",
     r"""passive:'Rigid order \u2014 you may only charge ABC cards in ascending Power order (1\u21924).',""",
     r"""passive:'Rigid order \u2014 charging in ascending Power order is optional, and every charge that keeps the sequence counts double.',"""),

    ("archetypal",
     r"""passive:'Hero / Villain characters gain First Strike when fully charged.',""",
     r"""passive:'The monomyth \u2014 your Active gains +10 attack for each distinct archetype among your living characters.',"""),

    ("deconstruct",
     r"""passive:'Binary inversion \u2014 Negate now doubles incoming damage, and Pierce can be blocked.',""",
     r"""passive:'Binary inversion \u2014 your blocks may pay for attacks and your attacks for blocks. Each mismatched payment leaves your own Active Exposed.',"""),
]


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    if "fix_lens_card_text.py" in src or "The monomyth" in src:
        die("already applied. Ship a named fix_*.py to revise.")
    # the behaviour must exist before the card claims it
    for need, why in (("function afOffer(", "A2"),
                      ("function symbolsOff(actor)", "F1"),
                      ("_structDouble", "S1"),
                      ("Archetypal Lens: +", "AR1")):
        if need not in src:
            die("%s is not applied -- the card text would describe behaviour "
                "the build does not have." % why)

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-16s found %d times, expected 1" % (label, n))
    if problems:
        die("anchor check failed -- nothing written:\n" + "\n".join(problems))

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != src.count("<script"):
        die("script block count changed")
    if out == src:
        die("no change produced.")

    # No CARD may still promise First Strike. Check card data only -- code
    # comments legitimately discuss it, and a guard tripping on its own
    # explanation has already cost this project four false aborts.
    bad = []
    for m in re.finditer(r"First Strike", out):
        a = out.rfind("\n", 0, m.start()) + 1
        line = out[a:out.find("\n", m.start())]
        stripped = re.sub(r"/\*[\s\S]*?\*/", "", line)
        if re.search(r"(passive|thesis|reward|text|t)\s*:", stripped) and "First Strike" in stripped:
            bad.append(line.strip()[:110])
    if bad:
        for b in bad:
            sys.stderr.write("  card still promises First Strike: %s\n" % b)
        die("a card names a mechanic the engine has never implemented.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d lens texts updated" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    no card promises First Strike any more")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
