#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trivia_audit.py — Trivia Standard Format conformance and bias audit.

    python3 trivia_audit.py <file> [--deck=KEY] [--sheet=NAME] [--list]

<file> may be a .tsv/.csv, or the catalog .xlsx itself - the workbook is read
with the standard library, so nothing needs installing. With an .xlsx it finds
the Trivia_ABC sheet on its own.

    python3 trivia_audit.py Academic_Battle_Cards_Catalog.xlsx
    python3 trivia_audit.py Academic_Battle_Cards_Catalog.xlsx --deck=gatsby
    python3 trivia_audit.py Academic_Battle_Cards_Catalog.xlsx --list

Works on the 12-column Trivia Standard Format and on the legacy 10-column
Trivia_ABC export (act/pool checks are skipped when those columns are absent).

Exit code 0 = every FAIL-level check passed. 1 = at least one FAIL.
WARN never changes the exit code; it flags things worth a look.
"""
import sys, csv, io, os, re, zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

THRESH = dict(
    min_per_pool        = 50,
    curve               = {1:.40, 2:.30, 3:.20, 4:.10},
    curve_tol           = .07,   # +/- 7 points per band
    slot_tol_overall    = .06,   # +/- 6 points from 25%
    cell_slack          = 1,     # a cell may exceed its even share by this many
    cell_min_n          = 8,     # below this a cell is too small to judge
    max_run             = 3,
    longest_max         = .40,   # "pick the longest" must not beat this
    mean_len_gap_max    = 2.0,   # chars, correct vs distractor
    giveaway_chars      = 8,
    giveaway_max        = 0,
    type_tol            = .10,
)

R = {'fail':[], 'warn':[], 'ok':[]}
def rec(level, label, detail): R[level].append((label, detail))
def check(cond, label, detail, level='fail'):
    rec('ok' if cond else level, label, detail)
    return cond

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

def _col(ref):
    m = re.match(r'([A-Z]+)', ref or '')
    if not m: return 0
    n = 0
    for ch in m.group(1): n = n*26 + (ord(ch)-64)
    return n-1

def xlsx_sheets(path):
    """[(name, zip-path)] using only the standard library."""
    with zipfile.ZipFile(path) as z:
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        tgt = {r.get('Id'): r.get('Target') for r in rels}
        out = []
        for sh in wb.iter(NS+'sheet'):
            t = tgt.get(sh.get(REL+'id'), '')
            if t.startswith('/xl/'): t = t[1:]
            elif not t.startswith('xl/'): t = 'xl/' + t.lstrip('/')
            out.append((sh.get('name'), t))
        return out

def xlsx_rows(path, sheet_name):
    with zipfile.ZipFile(path) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            for si in ET.fromstring(z.read('xl/sharedStrings.xml')).iter(NS+'si'):
                shared.append(''.join(t.text or '' for t in si.iter(NS+'t')))
        target = dict(xlsx_sheets(path)).get(sheet_name)
        if not target: return None
        grid = []
        for row in ET.fromstring(z.read(target)).iter(NS+'row'):
            cells = {}
            for c in row.iter(NS+'c'):
                i = _col(c.get('r'))
                if c.get('t') == 'inlineStr':
                    v = ''.join(t.text or '' for t in c.iter(NS+'t'))
                else:
                    ve = c.find(NS+'v')
                    v = ve.text if ve is not None and ve.text is not None else ''
                    if c.get('t') == 's' and v.isdigit(): v = shared[int(v)]
                cells[i] = (v or '').strip()
            grid.append([cells.get(i, '') for i in range(max(cells)+1)] if cells else [])
        return grid

def _from_grid(grid):
    """Find the header row, then read the rows under it."""
    hdr_i = None
    for i, r in enumerate(grid[:40]):
        low = [c.strip().lower() for c in r]
        if 'question' in low and any(c.startswith('correct_option') for c in low):
            hdr_i = i; break
    if hdr_i is None: return None
    hdr = [c.strip() for c in grid[hdr_i]]
    rows = []
    for r in grid[hdr_i+1:]:
        if not any(c.strip() for c in r): continue
        r = list(r) + ['']*(len(hdr)-len(r))
        rows.append({hdr[j]: r[j] for j in range(len(hdr)) if hdr[j]})
    return rows

def load(path, sheet=None):
    if not os.path.exists(path):
        near = [f for f in os.listdir('.') if f.lower().endswith(('.xlsx','.tsv','.csv'))]
        sys.exit("Can't find %r.\n  In this folder: %s\n  Point it at the catalog directly:\n"
                 "    python3 trivia_audit.py Academic_Battle_Cards_Catalog.xlsx"
                 % (path, ", ".join(sorted(near)) or "(no .xlsx/.tsv/.csv here)"))
    if path.lower().endswith(('.xlsx','.xlsm')):
        names = [n for n,_ in xlsx_sheets(path)]
        if sheet is None:
            cands = [n for n in names if 'trivia' in n.lower()]
            if not cands:
                sys.exit("No trivia sheet in %s.\n  Sheets: %s\n  Pass one with --sheet=NAME"
                         % (path, ", ".join(names)))
            sheet = cands[0]
        elif sheet not in names:
            sys.exit("No sheet %r.\n  Sheets: %s" % (sheet, ", ".join(names)))
        grid = xlsx_rows(path, sheet)
        rows = _from_grid(grid) if grid else None
        if not rows:
            sys.exit("Sheet %r has no header row with 'question' and 'correct_option'." % sheet)
        print("  reading sheet %r from %s" % (sheet, os.path.basename(path)))
    else:
        with io.open(path, encoding='utf-8-sig') as f:
            sample = f.read(4096); f.seek(0)
            delim = '\t' if sample.count('\t') >= sample.count(',') else ','
            rows = list(csv.DictReader(f, delimiter=delim))
    if not rows: sys.exit("empty file")
    keymap = {}
    for k in rows[0]:
        lk = k.strip().lower()
        if lk.startswith('correct_option'): keymap['key'] = k
        elif lk.startswith('correct_text'):  keymap['ans'] = k
        elif lk in ('deck','type','power','question','act','pool'): keymap[lk] = k
        elif lk.startswith('option_'):       keymap[lk] = k
    for need in ('key','ans','type','power','question'):
        if need not in keymap: sys.exit("missing column: %s" % need)
    return rows, keymap

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args: sys.exit(__doc__)
    path = args[0]
    deck = sheet = None
    for a in sys.argv[1:]:
        if a.startswith('--deck'):  deck  = a.split('=',1)[-1]
        if a.startswith('--sheet'): sheet = a.split('=',1)[-1]
    if '--list' in sys.argv:
        if path.lower().endswith(('.xlsx','.xlsm')):
            print("Sheets in %s:" % os.path.basename(path))
            for nm,_ in xlsx_sheets(path): print("   " + nm)
        rows, K = load(path, sheet)
        if 'deck' in K:
            print("\nDecks in this sheet:")
            for d,k in Counter(r[K['deck']] for r in rows).most_common():
                print("   %-16s %d questions" % (d,k))
        return 0
    rows, K = load(path, sheet)
    if deck and 'deck' not in K: sys.exit("--deck given but the sheet has no deck column")
    if deck and deck not in set(r[K['deck']] for r in rows):
        sys.exit("No deck %r. Available: %s" % (deck, ", ".join(sorted(set(r[K['deck']] for r in rows)))))
    if deck and 'deck' in K:
        rows = [r for r in rows if r[K['deck']] == deck]
    n = len(rows)
    OPT = [K['option_%d'%i] for i in (1,2,3,4)]
    has_pool = 'pool' in K
    has_act  = 'act'  in K

    for r in rows:
        r['_p'] = int(r[K['power']]); r['_k'] = int(r[K['key']])
        r['_a'] = r[K['ans']]; r['_o'] = [r[c] for c in OPT]

    print("=" * 66)
    print("TRIVIA AUDIT  %s   n=%d%s" % (path.split('/')[-1], n, "  deck=%s"%deck if deck else ""))
    print("=" * 66)

    # ---------- 1. integrity ----------
    bad_key = [r for r in rows if r['_o'][r['_k']-1] != r['_a']]
    check(not bad_key, "answer key points at the correct option", "%d mismatches" % len(bad_key))
    dup = [r for r in rows if len(set(r['_o'])) != 4]
    check(not dup, "four distinct options", "%d rows with duplicates" % len(dup))
    ws = [r for r in rows if any(c in v for v in [r[K['question']]]+r['_o'] for c in '\t\r\n')]
    check(not ws, "no tabs or newlines in any cell", "%d rows" % len(ws))
    lq = [r for r in rows if any(v.startswith('"') for v in r['_o'])]
    check(not lq, "no leading straight quote (Excel paste safety)", "%d rows" % len(lq))
    bp = [r for r in rows if r['_p'] not in (1,2,3,4)]
    check(not bp, "power is 1-4", "%d rows out of range" % len(bp))

    # ---------- 2. pools ----------
    pools = defaultdict(list)
    for r in rows: pools[r[K['pool']] if has_pool else 'all'].append(r)
    if has_pool:
        for p, sub in sorted(pools.items()):
            check(len(sub) >= THRESH['min_per_pool'],
                  "pool '%s' has >= %d questions" % (p, THRESH['min_per_pool']),
                  "%d" % len(sub))
    else:
        rec('warn', "no 'pool' column", "legacy format - pool checks skipped")

    # ---------- 3. power curve, per pool ----------
    for p, sub in sorted(pools.items()):
        c = Counter(r['_p'] for r in sub)
        off = []
        for pw, want in THRESH['curve'].items():
            got = c[pw]/len(sub)
            if abs(got-want) > THRESH['curve_tol']: off.append("p%d %.0f%% (want %.0f%%)"%(pw,100*got,100*want))
        check(not off, "pool '%s' follows the 40/30/20/10 curve" % p, "; ".join(off) or "on target")

    # a booster pool must not be more powerful than the starter pool
    if has_pool and 'starter' in pools and 'booster' in pools:
        ms = sum(r['_p'] for r in pools['starter'])/len(pools['starter'])
        mb = sum(r['_p'] for r in pools['booster'])/len(pools['booster'])
        check(mb <= ms + 0.15, "booster adds breadth, not power",
              "mean power starter %.2f vs booster %.2f" % (ms, mb))

    # ---------- 4. answer slot ----------
    c = Counter(r['_k'] for r in rows)
    worst = max(abs(c[k]/n - .25) for k in (1,2,3,4))
    check(worst <= THRESH['slot_tol_overall'], "answer slot ~25% overall",
          " ".join("%d:%.0f%%"%(k,100*c[k]/n) for k in (1,2,3,4)))

    cells = defaultdict(list)
    for r in rows: cells[(r[K['pool']] if has_pool else 'all', r['_p'])].append(r)
    # Judged on counts, not percentages: in a 10-row cell one slot holding 4 is
    # ordinary, and a float comparison on 0.15 is a coin toss at the boundary.
    import math
    skew = []
    for (p, pw), sub in sorted(cells.items()):
        if len(sub) < THRESH['cell_min_n']: continue
        cc = Counter(r['_k'] for r in sub)
        cap = math.ceil(len(sub)/4.0) + THRESH['cell_slack']
        if max(cc.values()) > cap:
            skew.append("%s p%d %s (cap %d of %d)" % (p, pw,
                " ".join("%d:%d"%(k,cc[k]) for k in (1,2,3,4)), cap, len(sub)))
    check(not skew, "answer slot ~25% inside every pool x power cell",
          "; ".join(skew) or "all cells within tolerance")

    run = best = 1; bk = None
    for i in range(1, n):
        if rows[i]['_k'] == rows[i-1]['_k']:
            run += 1
            if run > best: best, bk = run, rows[i]['_k']
        else: run = 1
    check(best <= THRESH['max_run'], "no more than %d consecutive rows share a slot" % THRESH['max_run'],
          "longest run %d%s" % (best, " (slot %s)"%bk if bk else ""))

    # ---------- 5. THE LENGTH TELL ----------
    L  = lambda r: len(r['_a'])
    mx = lambda r: max(len(o) for o in r['_o'])
    mn = lambda r: min(len(o) for o in r['_o'])
    wr = lambda r: [o for o in r['_o'] if o != r['_a']]
    longest  = sum(1 for r in rows if L(r) == mx(r)) / n
    shortest = sum(1 for r in rows if L(r) == mn(r)) / n
    ac = sum(L(r) for r in rows)/n
    aw = sum(len(o) for r in rows for o in wr(r)) / (3*n)
    give = [r for r in rows if L(r) - max(len(o) for o in wr(r)) >= THRESH['giveaway_chars']]

    print("\n  LENGTH TELL")
    print("    pick-the-longest  %5.0f%%   (chance 25%%, ceiling %.0f%%)" % (100*longest, 100*THRESH['longest_max']))
    print("    pick-the-shortest %5.0f%%" % (100*shortest))
    print("    mean length  correct %.1f ch  vs  distractor %.1f ch" % (ac, aw))
    print("    %d-char giveaways  %d\n" % (THRESH['giveaway_chars'], len(give)))

    check(longest <= THRESH['longest_max'], "picking the longest option does not beat chance",
          "%.0f%% (ceiling %.0f%%)" % (100*longest, 100*THRESH['longest_max']))
    check(abs(ac-aw) <= THRESH['mean_len_gap_max'], "correct and distractor lengths match",
          "%.1f vs %.1f ch (gap %.1f, max %.1f)" % (ac, aw, abs(ac-aw), THRESH['mean_len_gap_max']))
    check(len(give) <= THRESH['giveaway_max'], "no answer is %d+ chars longer than every distractor" % THRESH['giveaway_chars'],
          "%d rows" % len(give))
    if abs(shortest-.25) > .15:
        rec('warn', "shortest-option rate is skewed", "%.0f%% (chance 25%%)" % (100*shortest))

    # ---------- 6. type balance ----------
    for p, sub in sorted(pools.items()):
        t = Counter(r[K['type']].upper() for r in sub)
        share = t['ATTACK']/len(sub)
        check(abs(share-.5) <= THRESH['type_tol'], "pool '%s' ATTACK/BLOCK is even" % p,
              "ATTACK %d / BLOCK %d (%.0f%%)" % (t['ATTACK'], t['BLOCK'], 100*share))
        off = []
        for pw in (1,2,3,4):
            band = [r for r in sub if r['_p']==pw]
            if len(band) < 6: continue
            tt = Counter(r[K['type']].upper() for r in band)
            if abs(tt['ATTACK']/len(band)-.5) > .25:
                off.append("p%d %d/%d" % (pw, tt['ATTACK'], tt['BLOCK']))
        if off: rec('warn', "pool '%s' type skew within a power band" % p, "; ".join(off))

    # ---------- 7. coverage ----------
    if has_act:
        acts = Counter(r[K['act']] for r in rows)
        thin = [a for a,k in acts.items() if k < 4]
        print("  COVERAGE  " + "  ".join("%s:%d" % (a,k) for a,k in acts.most_common()))
        if thin: rec('warn', "thin coverage", "acts with <4 questions: %s" % ", ".join(thin))
    else:
        rec('warn', "no 'act' column", "legacy format - coverage checks skipped")

    # ---------- report ----------
    print("\n" + "-"*66)
    for label, detail in R['ok']:   print("  PASS  %-52s %s" % (label, detail))
    for label, detail in R['warn']: print("  WARN  %-52s %s" % (label, detail))
    for label, detail in R['fail']: print("  FAIL  %-52s %s" % (label, detail))
    print("-"*66)
    print("  %d passed, %d warnings, %d failed" % (len(R['ok']), len(R['warn']), len(R['fail'])))
    return 1 if R['fail'] else 0

if __name__ == '__main__':
    sys.exit(main())
