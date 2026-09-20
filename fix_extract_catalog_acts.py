#!/usr/bin/env python3
"""fix_extract_catalog_acts.py -- keep Act cards and gate questions out of the
regular sync.

extract_catalog.py writes every Characters row and every Trivia_ABC row for a
deck into characters.tsv / trivia.tsv, and sync_decks.py turns those into
DATA.characters / DATA.abcs. Without this patch, Thane of Cawdor would sync in
as a standalone character and the GATE questions as ordinary trivia cards.

After this patch:
  Characters rows with act 2 or 3  -> sync/acts.tsv   (not characters.tsv)
  Trivia_ABC rows with type GATE   -> sync/gate.tsv   (not trivia.tsv)

Additive. Refuses to run twice. Writes extract_catalog.py.bak.
    python3 fix_extract_catalog_acts.py [path/to/extract_catalog.py]
"""
import os, shutil, sys
def die(m): sys.exit("[fix_extract_catalog_acts] ABORT: " + m)
cands = sys.argv[1:] or ["extract_catalog.py", "tools/extract_catalog.py", "scripts/extract_catalog.py"]
path = next((p for p in cands if os.path.exists(p)), None)
if not path: die("extract_catalog.py not found (tried %s) -- pass its path" % ", ".join(cands))
s = open(path, encoding="utf-8").read()
MARK = "# Act cards and gate questions sync separately"
if MARK in s: die("already applied")
ANCHOR = "            rows=[r for r in rows if r.get('deck') in decks]\n"
if s.count(ANCHOR) != 1: die("anchor found %d times (need 1)" % s.count(ANCHOR))
ADD = ANCHOR + """            # Act cards and gate questions sync separately (see fix_extract_catalog_acts.py)
            side=None
            if name=='Characters':
                side=('acts',[r for r in rows if r.get('act','').strip() not in ('','1')])
            elif name=='Trivia_ABC':
                side=('gate',[r for r in rows if r.get('type','').strip().upper()=='GATE'])
            if side is not None:
                held=set(id(r) for r in side[1]); rows=[r for r in rows if id(r) not in held]
                with io.open('sync/%s.tsv'%side[0],'w',encoding='utf-8') as f:
                    f.write('\\t'.join(hdr)+'\\n')
                    for d in side[1]:
                        f.write('\\t'.join(d.get(k,'').replace('\\t',' ').replace('\\n',' ') for k in hdr)+'\\n')
                print("  sync/%-14s %4d rows" % (side[0]+'.tsv', len(side[1])))
"""
shutil.copyfile(path, path + ".bak")
open(path, "w", encoding="utf-8").write(s.replace(ANCHOR, ADD, 1))
print("[fix_extract_catalog_acts] OK -- patched " + path)
