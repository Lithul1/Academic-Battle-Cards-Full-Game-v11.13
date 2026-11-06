#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_act_passives_2.py -- let Act cards use the last four 1st-Edition-only passives.

fix_act_passives already taught the damage step three Act-card keys
(entryAtkAdd, statusedAtkAdd, inflictAtkAdd). Four keys are still gated to
`.fe`, so a card with act > 1 that declares them does nothing:

    soloBonus        +N while it is the last one standing   (the finisher arc role)
    statusDmgBonus   +N against an afflicted target         (Liquid Dissolution's half)
    benchCostAura    raises the enemy Active's move cost from the bench
    smudgeLock       starts and stays Smudged                (spillLock's twin)

This patch widens the first three from `att.fe` / `c.fe` to "1st Edition OR
Act card", and adds smudgeLock beside the spillLock that evolution already
applies. 1st Edition behaviour is unchanged in every case.

Additive, anchor-verified, refuses to run twice, writes src/game.src.html.bak.
Run from the repo root:  python3 fix_act_passives_2.py
"""
import os, shutil, sys

SRC = "src/game.src.html"
MARK = "/* fix_act_passives_2 */"

EDITS = [
    # (label, anchor, replacement)
    ("soloBonus on Act cards",
     "if(att.fe&&att.passive&&att.passive.soloBonus&&isSoloAlive(A)){",
     "if((att.fe||att.act>1)&&att.passive&&att.passive.soloBonus&&isSoloAlive(A)){ /* fix_act_passives_2 */"),

    ("statusDmgBonus on Act cards",
     "if(att.fe&&att.passive&&att.passive.statusDmgBonus&&STATUS_NEG.some(x=>def.status[x])){",
     "if((att.fe||att.act>1)&&att.passive&&att.passive.statusDmgBonus&&STATUS_NEG.some(x=>def.status[x])){ /* fix_act_passives_2 */"),

    ("benchCostAura from an Act card on the bench",
     "const wiz=P.team.find((c,i)=>i!==P.activeIdx&&c.fe&&c.hp>0&&c.passive&&c.passive.benchCostAura);",
     "const wiz=P.team.find((c,i)=>i!==P.activeIdx&&(c.fe||c.act>1)&&c.hp>0&&c.passive&&c.passive.benchCostAura); /* fix_act_passives_2 */"),

    ("smudgeLock when a character evolves",
     "if(c.passive){ if(c.passive.spillLock){ c.status.spill=true; c.status._spillLock=true; }",
     "if(c.passive){ if(c.passive.spillLock){ c.status.spill=true; c.status._spillLock=true; }"
     " if(c.passive.smudgeLock){ c.status.smudge=true; c.status._smudgeLock=true; } /* fix_act_passives_2 */"),
]

def die(msg):
    sys.exit("[fix_act_passives_2] ABORT: " + msg)

if not os.path.exists(SRC):
    die(SRC + " not found -- run this from the repo root")
src = open(SRC, encoding="utf-8").read()

if MARK in src:
    die("already applied")
if "fix_act_passives" not in src:
    die("run fix_act_passives first -- this patch builds on the Act-passive damage hooks")
if "const STATUS_NEG" not in src:
    die("this does not look like the live game source (no STATUS_NEG)")

for label, anchor, _ in EDITS:
    n = src.count(anchor)
    if n != 1:
        die("anchor for '%s' found %d times (need exactly 1)" % (label, n))

shutil.copyfile(SRC, SRC + ".bak")
for label, anchor, repl in EDITS:
    src = src.replace(anchor, repl, 1)
open(SRC, "w", encoding="utf-8").write(src)

print("[fix_act_passives_2] OK -- %d edits applied" % len(EDITS))
for label, _, _ in EDITS:
    print("    " + label)
print("    1st Edition behaviour unchanged; rebuild with: python3 build.py")
