#!/usr/bin/env python3
"""
sync_catalog.py — push the card catalog (.xlsx export of the Google Sheet)
into src/game.src.html.  Replaces the retired inject_cards.py.

SCOPE (v1)
  * Characters sheet  -> DATA.characters[deck]   (base cards only; rows with an
                                                  `act` value are Act cards and
                                                  are reported, not written)
  * 1st Editions +
    Special Editions  -> DATA.firsteds            (passive name/text only — the
                                                  passive's engine flags are kept)
  * Bookmarks         -> REPORT ONLY.  Decks store Bookmarks by array index, and
                         the game's list no longer matches catalog order, so
                         writing here could silently swap cards in saved decks.

WHAT IT CHANGES
  Only cards whose catalog-owned fields differ from the source.  Fields the
  catalog doesn't own (img, imgpos, hpos, fe, tier, base, deck, passive flags,
  anything a patch added) are carried over untouched.  A rewritten card keeps
  its own quote style (old decks use '...', newer decks use "...").

USAGE (from the repo root)
  python3 tools/sync_catalog.py --catalog "Academic_Battle_Cards_Catalog.xlsx"            # dry run
  python3 tools/sync_catalog.py --catalog "Academic_Battle_Cards_Catalog.xlsx" --apply    # write
  optional:  --decks gatsby,romeojuliet   limit to these decks
             --src path/to/game.src.html  (default src/game.src.html)

Dry run prints every change.  --apply writes src/game.src.html.bak first and
re-checks the result.  Running it again after --apply reports "0 cards changed".
Requires: python3 3.8+ (standard library only — no node, no pip installs).
"""
import argparse, datetime, json, os, re, shutil, sys, zipfile
import xml.etree.ElementTree as ET

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}

# ---------------------------------------------------------------- xlsx reader
DATE_FMT_IDS = set(range(14, 23)) | {45, 46, 47}

def _col_idx(ref):
    col = re.match(r'[A-Z]+', ref).group(0)
    n = 0
    for ch in col: n = n * 26 + (ord(ch) - 64)
    return n - 1

def _is_date_code(code):
    code = re.sub(r'"[^"]*"|\[[^\]]*\]', '', code or '').lower()
    return bool(re.search(r'[dmy]', code)) and 'general' not in code

def read_xlsx(path):
    """Return {sheet_name: [row lists]} with the two known catalog repairs:
       whole floats -> int, date-formatted cells -> 'M/D' (e.g. a 10/2 label)."""
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
            shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['m'])))
    date_styles = set()
    if 'xl/styles.xml' in z.namelist():
        st = ET.fromstring(z.read('xl/styles.xml'))
        custom = {int(f.get('numFmtId')): f.get('formatCode')
                  for f in st.findall('m:numFmts/m:numFmt', NS)}
        for i, xf in enumerate(st.findall('m:cellXfs/m:xf', NS)):
            fid = int(xf.get('numFmtId', 0))
            if fid in DATE_FMT_IDS or (fid in custom and _is_date_code(custom[fid])):
                date_styles.add(i)
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = {r.get('Id'): r.get('Target')
            for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')).findall('rel:Relationship', NS)}
    out = {}
    for sh in wb.findall('m:sheets/m:sheet', NS):
        target = rels[sh.get('{%s}id' % NS['r'])].lstrip('/')
        if not target.startswith('xl/'): target = 'xl/' + target
        rows = []
        for row in ET.fromstring(z.read(target)).iter('{%s}row' % NS['m']):
            vals = {}
            for c in row.findall('m:c', NS):
                t, s = c.get('t'), int(c.get('s', 0))
                v = c.find('m:v', NS)
                if t == 's':
                    val = shared[int(v.text)] if v is not None else ''
                elif t == 'inlineStr':
                    val = ''.join(x.text or '' for x in c.iter('{%s}t' % NS['m']))
                elif t in ('str', 'e'):
                    val = v.text if v is not None else ''
                elif t == 'b':
                    val = bool(int(v.text)) if v is not None else ''
                else:
                    if v is None: val = ''
                    else:
                        num = float(v.text)
                        if s in date_styles:   # repair: 10/2 stored as a date
                            d = datetime.date(1899, 12, 30) + datetime.timedelta(days=int(num))
                            val = '%d/%d' % (d.month, d.day)
                        else:
                            val = int(num) if num.is_integer() else num
                vals[_col_idx(c.get('r'))] = val
            if vals:
                rows.append([vals.get(i, '') for i in range(max(vals) + 1)])
        out[sh.get('name')] = rows
    return out

def table(sheets, name):
    rows = sheets.get(name) or []
    if not rows: return []
    hdr = [str(h).strip() if h is not None else '' for h in rows[0]]
    res = []
    for r in rows[1:]:
        d = {hdr[i]: (r[i] if i < len(r) else '') for i in range(len(hdr)) if hdr[i]}
        if any(v not in ('', None) for v in d.values()): res.append(d)
    return res

# ------------------------------------------------------- catalog -> card dict
WARN = []

def blank(v): return v is None or (isinstance(v, str) and v.strip() == '')

def num(v):
    if blank(v): return None
    if isinstance(v, (int, float)): return int(v) if float(v).is_integer() else v
    s = str(v).strip()
    m = re.match(r'^-?\d+(\.\d+)?', s)          # '20+' -> 20 (a label typed into a number column)
    if not m: return None
    if m.group(0) != s: WARN.append('number column held "%s" — read as %s' % (s, m.group(0)))
    f = float(m.group(0)); return int(f) if f.is_integer() else f

def js_json(v, where):
    if blank(v): return {}
    try:
        d = json.loads(str(v))
    except Exception as e:
        raise SystemExit('Bad JSON in %s: %s\n  %s' % (where, e, v))
    if not isinstance(d, dict): raise SystemExit('JSON in %s is not an object' % where)
    return d

def ability(row, p, val_key, where):
    a = {'n': str(row[p + '_name']).strip(), 't': str(row[p + '_text']).strip()}
    c = num(row[p + '_cost'])
    if c is not None: a['cost'] = c
    v = num(row[p + ('_dmg' if p == 'atk' else '_block')])
    if v is not None: a[val_key] = v
    for k, x in js_json(row[p + '_extra_json'], where + ' ' + p + '_extra_json').items():
        a[k] = x
    # catalog convention: a growing move keeps its starting value in the dmg/block
    # column; the engine reads `base`, so carry it across when the JSON omits it
    if (a.get('dmgType') == 'perTurn' or a.get('blockType') == 'perTurn') and 'base' not in a and v is not None:
        a['base'] = v
        WARN.append('%s %s: perTurn had no "base" in its JSON — used %s from the %s column'
                    % (where, p, v, 'dmg' if p == 'atk' else 'block'))
    lab = row[p + '_label']
    if not blank(lab): a['label'] = str(lab).strip()
    return a

def char_from_row(r):
    where = '%s/%s' % (r['deck'], r['id'])
    d = {'id': str(r['id']).strip(), 'name': str(r['name']).strip(), 'hp': num(r['hp']),
         'archetype': str(r['archetype']).strip(), 'accent': str(r['accent']).strip()}
    if not blank(r.get('tags')):
        d['tags'] = [t.strip() for t in str(r['tags']).split(',') if t.strip()]
    d['atk'] = ability(r, 'atk', 'dmg', where)
    d['blk'] = ability(r, 'blk', 'block', where)
    return d

def fe_from_row(r):
    where = '1E/%s' % r['id']
    d = {'id': str(r['id']).strip(), 'name': str(r['name']).strip(), 'hp': num(r['hp']),
         'archetype': str(r['archetype']).strip(), 'accent': str(r['accent']).strip(),
         'passive': {'name': str(r['passive_name']).strip(), 'text': str(r['passive_text']).strip()}}
    d['atk'] = ability(r, 'atk', 'dmg', where)
    d['blk'] = ability(r, 'blk', 'block', where)
    return d

CHAR_OWNED = ['name', 'hp', 'archetype', 'accent', 'tags', 'atk', 'blk']
FE_OWNED = ['name', 'hp', 'archetype', 'accent', 'atk', 'blk']   # + passive.name/text

# -------------------------------------------------------- JS source locating
def match_close(s, i):
    """s[i] is '{' or '['; return index just past its matching close,
       skipping strings, template literals and comments."""
    pairs = {'{': '}', '[': ']', '(': ')'}
    stack, j, n = [], i, len(s)
    while j < n:
        ch = s[j]
        if ch in '\'"`':
            q = ch; j += 1
            while j < n and s[j] != q:
                j += 2 if s[j] == '\\' else 1
        elif s.startswith('//', j):
            j = s.find('\n', j); j = n if j < 0 else j; continue
        elif s.startswith('/*', j):
            j = s.find('*/', j) + 2; continue
        elif ch in pairs:
            stack.append(pairs[ch])
        elif ch in '}])':
            if not stack or stack.pop() != ch: raise ValueError('bracket mismatch at %d' % j)
            if not stack: return j + 1
        j += 1
    raise ValueError('unclosed bracket from %d' % i)

def region(s, start_pat, frm=0):
    m = re.compile(start_pat, re.M).search(s, frm)
    if not m: return None
    open_at = s.index(m.group(0)[-1], m.end() - 1)
    return (open_at, match_close(s, open_at))

def find_literal(s, lo, hi, cid):
    m = re.compile(r'\{\s*["\']?id["\']?\s*:\s*(["\'])%s\1' % re.escape(cid)).search(s, lo, hi)
    if not m: return None
    return (m.start(), match_close(s, m.start()), m.group(1))

# ------------------------------------------------------------ JS read/write
class _JS:
    """Minimal reader for the JS object literals in DATA (no node needed):
       {bare:1, 'q':"s", arr:[1,2,], nested:{...}}, true/false/null, // and /* */ comments."""
    ESC = {'n': '\n', 't': '\t', 'r': '\r', 'b': '\b', 'f': '\f', 'v': '\v', '0': '\0'}
    def __init__(self, t): self.t, self.i = t, 0
    def ws(self):
        t = self.t
        while self.i < len(t):
            if t[self.i] in ' \t\r\n': self.i += 1
            elif t.startswith('//', self.i): j = t.find('\n', self.i); self.i = len(t) if j < 0 else j
            elif t.startswith('/*', self.i): self.i = t.index('*/', self.i) + 2
            else: break
    def val(self):
        self.ws(); c = self.t[self.i]
        if c == '{': return self.obj()
        if c == '[': return self.arr()
        if c in '\'"': return self.string()
        m = re.compile(r'-?\d+(\.\d+)?([eE][-+]?\d+)?').match(self.t, self.i)
        if m:
            self.i = m.end(); f = float(m.group(0))
            return int(f) if f.is_integer() and 'e' not in m.group(0).lower() and '.' not in m.group(0) else f
        for w, v in (('true', True), ('false', False), ('null', None), ('undefined', None)):
            if self.t.startswith(w, self.i): self.i += len(w); return v
        raise ValueError('unexpected %r at %d: %s' % (c, self.i, self.t[self.i:self.i + 40]))
    def string(self):
        q = self.t[self.i]; self.i += 1; out = []
        while True:
            c = self.t[self.i]
            if c == q: self.i += 1; break
            if c == '\\':
                n = self.t[self.i + 1]
                if n == 'u':
                    out.append(chr(int(self.t[self.i + 2:self.i + 6], 16))); self.i += 6; continue
                if n == 'x':
                    out.append(chr(int(self.t[self.i + 2:self.i + 4], 16))); self.i += 4; continue
                if n == '\n': self.i += 2; continue
                out.append(self.ESC.get(n, n)); self.i += 2; continue
            out.append(c); self.i += 1
        # join UTF-16 surrogate pairs written as \ud83e\udea2
        return ''.join(out).encode('utf-16', 'surrogatepass').decode('utf-16')
    def key(self):
        self.ws()
        if self.t[self.i] in '\'"': return self.string()
        m = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*').match(self.t, self.i)
        if not m: raise ValueError('bad key at %d: %s' % (self.i, self.t[self.i:self.i + 40]))
        self.i = m.end(); return m.group(0)
    def obj(self):
        self.i += 1; d = {}
        while True:
            self.ws()
            if self.t[self.i] == '}': self.i += 1; return d
            k = self.key(); self.ws()
            if self.t[self.i] != ':': raise ValueError('expected : at %d' % self.i)
            self.i += 1; d[k] = self.val(); self.ws()
            if self.t[self.i] == ',': self.i += 1
    def arr(self):
        self.i += 1; a = []
        while True:
            self.ws()
            if self.t[self.i] == ']': self.i += 1; return a
            a.append(self.val()); self.ws()
            if self.t[self.i] == ',': self.i += 1

def js_eval(literals):
    """Read JS object literals with the built-in reader above."""
    out = []
    for x in literals:
        try:
            r = _JS(x); v = r.val(); r.ws()
            if r.i != len(x): raise ValueError('trailing text at %d' % r.i)
            out.append(v)
        except Exception as e:
            raise SystemExit('Could not read a card literal (%s):\n%s' % (e, x[:300]))
    return out

IDENT = re.compile(r'^[A-Za-z_$][A-Za-z0-9_$]*$')

def ser(v, q):
    if isinstance(v, bool): return 'true' if v else 'false'
    if v is None: return 'null'
    if isinstance(v, (int, float)): return str(int(v)) if float(v).is_integer() else repr(v)
    if isinstance(v, str):
        return q + v.replace('\\', '\\\\').replace(q, '\\' + q).replace('\n', '\\n') + q
    if isinstance(v, list): return '[' + ', '.join(ser(x, q) for x in v) + ']'
    if isinstance(v, dict):
        return '{' + ', '.join((k if IDENT.match(k) else ser(k, q)) + ':' + ser(x, q) for k, x in v.items()) + '}'
    raise TypeError(type(v))

def render_card(obj, q, indent='      '):
    """One line of scalar top-level keys, then one line per object/array of objects."""
    head, body = [], []
    for k, v in obj.items():
        (body if isinstance(v, dict) else head).append((k, v))
    key = lambda k: k if IDENT.match(k) else ser(k, q)
    out = indent + '{ ' + ', '.join(key(k) + ':' + ser(v, q) for k, v in head)
    for k, v in body:
        out += ',\n' + indent + '  ' + key(k) + ':' + ser(v, q)
    return out.lstrip() + ' }'

def merged(existing, canon, owned, fe=False):
    out = {}
    for k, v in existing.items():          # keep original key order
        if k in owned:
            if k in canon: out[k] = canon[k]
        elif fe and k == 'passive' and isinstance(v, dict):
            p = dict(v); p['name'] = canon['passive']['name']; p['text'] = canon['passive']['text']; out[k] = p
        else:
            out[k] = v
    for k in owned:                         # owned keys the source lacked
        if k in canon and k not in out:
            # place before atk so the card reads naturally
            items = list(out.items()); pos = next((i for i, (kk, _) in enumerate(items) if kk == 'atk'), len(items))
            items.insert(pos, (k, canon[k])); out = dict(items)
    return out

def diff_fields(old, new, owned, fe=False):
    keys = list(owned) + (['passive'] if fe else [])
    ch = []
    for k in keys:
        a, b = old.get(k), new.get(k)
        if fe and k == 'passive':
            a = {x: (a or {}).get(x) for x in ('name', 'text')}; b = {x: (b or {}).get(x) for x in ('name', 'text')}
        if a != b:
            if isinstance(a, dict) and isinstance(b, dict):
                for kk in list(dict.fromkeys(list(a) + list(b))):
                    if a.get(kk) != b.get(kk): ch.append(('%s.%s' % (k, kk), a.get(kk), b.get(kk)))
            else:
                ch.append((k, a, b))
    return ch

def short(v, n=70):
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    return s if len(s) <= n else s[:n - 1] + '…'

# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--catalog', required=True)
    ap.add_argument('--src', default='src/game.src.html')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--decks', default='')
    a = ap.parse_args()
    if not os.path.exists(a.src): raise SystemExit('Source not found: %s (run from the repo root)' % a.src)
    s = open(a.src, encoding='utf8').read()
    if 'romeojuliet' not in s: raise SystemExit('This does not look like the live src/game.src.html.')
    decks = set(x.strip() for x in a.decks.split(',') if x.strip())
    sheets = read_xlsx(a.catalog)
    for need in ('Characters', '1st Editions'):
        if need not in sheets: raise SystemExit('Catalog is missing the "%s" sheet.' % need)

    chars = table(sheets, 'Characters')
    base_rows = [r for r in chars if blank(r.get('act'))]
    act_rows = [r for r in chars if not blank(r.get('act'))]
    fe_rows = [r for r in table(sheets, '1st Editions') + table(sheets, 'Special Editions')
               if not blank(r.get('deck')) and re.match(r'^[A-Za-z0-9_]+$', str(r.get('id', '')).strip())]

    ids = [str(r['id']).strip() for r in base_rows]
    dup = sorted(set(i for i in ids if ids.count(i) > 1))
    if dup: raise SystemExit('Duplicate character ids in the catalog: ' + ', '.join(dup))

    dstart = s.find('const DATA = {')
    if dstart < 0: raise SystemExit('Anchor "const DATA = {" not found.')
    dend = match_close(s, s.index('{', dstart))
    chars_reg = region(s[:dend], r'^  characters: \{', dstart)
    fe_reg = region(s[:dend], r'^  firsteds: \[', dstart)
    if not chars_reg or not fe_reg: raise SystemExit('Could not find DATA.characters / DATA.firsteds.')

    jobs, notes = [], []        # jobs: (lo, hi, q, canon, owned, fe, label)
    for r in base_rows:
        dk = str(r['deck']).strip()
        if decks and dk not in decks: continue
        reg = region(s[:chars_reg[1]], r'^    %s: \[' % re.escape(dk), chars_reg[0])
        if not reg: notes.append('deck "%s" is not in the game — %s skipped' % (dk, r['id'])); continue
        lit = find_literal(s, reg[0], reg[1], str(r['id']).strip())
        if not lit: notes.append('NEW character %s/%s is not in the game — not added (new cards need art + deck limits)' % (dk, r['id'])); continue
        jobs.append((lit[0], lit[1], lit[2], char_from_row(r), CHAR_OWNED, False, '%s/%s' % (dk, r['id'])))
    for r in fe_rows:
        dk = str(r['deck']).strip()
        if decks and dk not in decks: continue
        lit = find_literal(s, fe_reg[0], fe_reg[1], str(r['id']).strip())
        if not lit: notes.append('1E %s is not in the game — not added' % r['id']); continue
        jobs.append((lit[0], lit[1], lit[2], fe_from_row(r), FE_OWNED, True, '1E %s' % r['id']))

    olds = js_eval([s[lo:hi] for lo, hi, *_ in jobs])
    edits, report = [], []
    for (lo, hi, q, canon, owned, fe, label), old in zip(jobs, olds):
        new = merged(old, canon, owned, fe)
        ch = diff_fields(old, new, owned, fe)
        if not ch: continue
        report.append((label, ch))
        edits.append((lo, hi, render_card(new, q), new))

    acts = sorted(set('%s/%s' % (r['deck'], r['id']) for r in act_rows if not decks or r['deck'] in decks))
    print('== sync_catalog: %d card(s) differ from the catalog ==' % len(report))
    for label, ch in report:
        print('\n' + label)
        for f, o, n in ch: print('   %-22s %s  ->  %s' % (f, short(o), short(n)))
    if WARN:
        print('\n-- catalog warnings --'); [print('   ' + w) for w in dict.fromkeys(WARN)]
    if notes:
        print('\n-- not written --'); [print('   ' + n) for n in notes]
    if acts:
        print('\n-- Act cards (%d) are handled by the Act-card patch, not this tool --' % len(acts))
    bm_report(sheets, s)

    if not a.apply:
        print('\nDry run only. Re-run with --apply to write %s.' % a.src); return
    if not edits:
        print('\nNothing to write.'); return
    back = js_eval([e[2] for e in edits])          # rendered text must read back exactly
    for e, b in zip(edits, back):
        if b != json.loads(json.dumps(e[3])): raise SystemExit('Round-trip mismatch writing a card — nothing written.')
    for lo, hi, txt, _ in sorted(edits, key=lambda e: e[0], reverse=True):
        s = s[:lo] + txt + s[hi:]
    shutil.copy2(a.src, a.src + '.bak')
    open(a.src, 'w', encoding='utf8').write(s)
    print('\nWrote %s (%d cards). Backup: %s.bak' % (a.src, len(edits), a.src))

def bm_report(sheets, s):
    rows = table(sheets, 'Bookmarks')
    if not rows: return
    i = s.find('\n  bookmarks: [')
    if i < 0: return
    j = match_close(s, s.index('[', i))
    have = set(re.findall(r'\{\s*["\']?id["\']?\s*:\s*["\']([^"\']+)', s[i:j]))
    missing = [str(r['id']) for r in rows if str(r['id']) not in have]
    if missing:
        print('\n-- Bookmarks in the catalog but not in the game (report only, %d) --' % len(missing))
        print('   ' + ', '.join(missing))

if __name__ == '__main__':
    main()
