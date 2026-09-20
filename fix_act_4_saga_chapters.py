#!/usr/bin/env python3
"""fix_act_4_saga_chapters.py -- Three-Act Evolution, part 4 of 4.

"Act" now means a character's evolution stage, so Saga bookmarks count in
Chapters instead: the active-bookmark chip ("Ch. II / 3", abbreviated to fit),
the two Saga log lines, and the rules text (matching the catalog's "Chapter I") of Serialized Novel, Three-Act Structure and
Deus Ex Machina. Display text only -- _stage, stages and sagaAct are
untouched. Refuses to run twice. Writes a .bak. Run from the repo root.
"""
import os, re, shutil, sys
SRC = "src/game.src.html"
def die(m): sys.exit("[fix_act_4_saga_chapters] ABORT: " + m)
if not os.path.exists(SRC): die(SRC + " not found -- run from the repo root")
s = open(SRC, encoding="utf-8").read()
if "c._tag==='saga'?('Ch. '+roman(c._stage||0)" in s: die("already applied")

EDITS = [
    ("chip", "c._tag==='saga'?('Act '+roman(c._stage||0)", "c._tag==='saga'?('Ch. '+roman(c._stage||0)"),
    ("tick log", "\\u2014 Act ${roman(c._stage)}.`", "\\u2014 Chapter ${roman(c._stage)}.`"),
    ("open log", "\u2014 Act I begins at the start of your next turn.`", "\u2014 Chapter I begins at the start of your next turn.`"),
]
for label, a, r in EDITS:
    n = s.count(a)
    if n != 1: die("anchor for '%s' found %d times (need 1)" % (label, n))

CARDS = ["{ id:'serialnovel',", "{ id:'threeact',", "{ id:'deusex',"]
lines = s.split("\n"); hits = []
for i, ln in enumerate(lines):
    if any(ln.lstrip().startswith(c) for c in CARDS) and "saga:true" in ln: hits.append(i)
if len(hits) != 3: die("expected 3 Saga card lines, found %d" % len(hits))

shutil.copyfile(SRC, SRC + ".bak")
for label, a, r in EDITS: s = s.replace(a, r, 1)
lines = s.split("\n"); n_txt = 0
for i in hits:
    new = re.sub(r"(text:[\"'])(.*?)([\"'], effect:'saga')",
                 lambda m: m.group(1) + re.sub(r"\bAct (I{1,3})\b", r"Chapter \1", m.group(2)) + m.group(3), lines[i])
    if new != lines[i]: n_txt += 1
    lines[i] = new
if n_txt != 3: die("rewrote %d Saga texts (expected 3) -- restore from .bak" % n_txt)
open(SRC, "w", encoding="utf-8").write("\n".join(lines))
print("[fix_act_4_saga_chapters] OK -- chip, 2 log lines, 3 Saga texts")
