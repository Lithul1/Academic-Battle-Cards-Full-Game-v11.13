#!/usr/bin/env python3
"""
build_catalog.py — build the Card Catalog + Deck Builder (dist/catalog.html).

WHAT IT READS (nothing is retyped)
  catalog.xlsx               the Google Sheet export (same file sync_catalog.py uses)
                             Characters, 1st Editions, Special Editions, Trivia_ABC
                             (needs the `id` column), Bookmarks, Crit_Lenses,
                             ABC_precon_decklists
  src/game.src.html          deck-size rules (PM, LIMITS), book names (setName,
                             DECK_ORDER) and the expansion list (window.EXPANSIONS),
                             so the catalog and the game can never disagree
  src/catalog.src.html       the catalog app
  catalog/content.json       hand-written text: archetype roles, stories, best uses,
                             book blurbs, "How to Read a Card"
  art/scans/<card id>.webp   Dextrous scans, named by card id (.webp/.png/.jpg).
                             480 x 672 WebP is the recommended size.
  art/back_print.webp        card back (full colour)
  art/back_emblem.webp       emblem used on the light, ink-saving back

USAGE (repo root)
  python3 tools/build_catalog.py                    # -> dist/catalog.html
  python3 tools/build_catalog.py --catalog other.xlsx --out somewhere.html

Standard library only (python3 3.8+). Reads the xlsx with the reader in
tools/sync_catalog.py. Refuses to build if a precon references a card that
does not exist or is not a legal 62.
"""
import argparse, base64, hashlib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from sync_catalog import read_xlsx, table  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--catalog', default=os.path.join(ROOT, 'catalog.xlsx'))
ap.add_argument('--game',    default=os.path.join(ROOT, 'src/game.src.html'))
ap.add_argument('--src',     default=os.path.join(ROOT, 'src/catalog.src.html'))
ap.add_argument('--content', default=os.path.join(ROOT, 'catalog/content.json'))
ap.add_argument('--scans',   default=os.path.join(ROOT, 'art/scans'))
ap.add_argument('--out',     default=os.path.join(ROOT, 'dist/catalog.html'))
a = ap.parse_args()

def die(msg): sys.exit('[catalog] ERROR: ' + msg)
def warn(msg): print('[catalog] note: ' + msg)
def blank(v): return v is None or (isinstance(v, str) and v.strip() == '')
def s(v): return '' if blank(v) else str(v).strip()
def n(v):
    if blank(v): return None
    try:
        f = float(v); return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return s(v)

for p in (a.catalog, a.game, a.src):
    if not os.path.exists(p): die('missing ' + os.path.relpath(p, ROOT))

# ------------------------------------------------------------ rules from game
game = open(a.game, encoding='utf-8').read()
def obj_nums(pat, name):
    m = re.search(pat, game, re.S)
    if not m: die('could not find %s in src/game.src.html' % name)
    return {k: int(v) for k, v in re.findall(r'(\w+)\s*:\s*(\d+)\b', m.group(1))}
PM = obj_nums(r'const PM\s*=\s*\{(.*?)\};', 'PM')
LIM = obj_nums(r'const LIMITS\s*=\s*\{(.*?)\};', 'LIMITS')
for k in ('total', 'ch', 'ab', 'bm', 'cr', 'fe'):
    if k not in PM or k not in LIM: die('PM/LIMITS is missing "%s"' % k)
RULES = {'pm': PM, 'classic': LIM}

m = re.search(r"const DECK_ORDER\s*=\s*\[(.*?)\]", game)
if not m: die('could not find DECK_ORDER')
BOOKS = re.findall(r"'(\w+)'", m.group(1))
m = re.search(r"const setName\s*=.*", game)
NAMES = dict(re.findall(r"k==='(\w+)'\?'([^']+)'", m.group(0) if m else ''))
EXP = []
for eid, body in re.findall(r'window\.EXPANSIONS\.(\w+)\s*=\s*\{(.{0,400})', game):
    nm = re.search(r'"?name"?\s*:\s*"([^"]+)"', body); bs = re.search(r'"?base"?\s*:\s*"([^"]+)"', body)
    if nm and bs: EXP.append({'id': eid, 'n': nm.group(1), 'b': bs.group(1)})

# ------------------------------------------------------------ cards from sheet
sh = read_xlsx(a.catalog)
def tab(name):
    if name not in sh: die('catalog.xlsx has no "%s" tab' % name)
    return table(sh, name)

def move(r, p, val):
    return [s(r.get(p + '_name')), s(r.get(p + '_text')), n(r.get(p + '_cost')), s(r.get(p + '_label'))]

cards, skipped = [], set()
for r in tab('Characters'):
    if blank(r.get('id')): continue
    if s(r.get('deck')) not in BOOKS: skipped.add(s(r.get('deck'))); continue
    base = s(r.get('base')).split(',')[-1].strip() or s(r.get('id'))
    cards.append({'id': s(r['id']), 't': 'ch', 'b': s(r['deck']), 'n': s(r['name']), 'hp': n(r.get('hp')),
                  'ar': s(r.get('archetype')), 'act': n(r.get('act')) or 1, 'ef': s(r.get('evolves_from')) or None,
                  'base': base, 'res': s(r.get('resolution')) or None,
                  'a': move(r, 'atk', 'dmg'), 'k': move(r, 'blk', 'block'),
                  'p': [s(r['passive_name']), s(r.get('passive_text'))] if not blank(r.get('passive_name')) else None})
for t in ('1st Editions', 'Special Editions'):
    for r in tab(t):
        if blank(r.get('id')) or s(r.get('deck')) not in BOOKS: continue
        cards.append({'id': s(r['id']), 't': 'fe', 'b': s(r['deck']), 'n': s(r['name']), 'hp': n(r.get('hp')),
                      'ar': s(r.get('archetype')), 'tier': s(r.get('tier')),
                      'base': s(r.get('base')).split(',')[-1].strip(),
                      'a': move(r, 'atk', 'dmg'), 'k': move(r, 'blk', 'block'),
                      'p': [s(r['passive_name']), s(r.get('passive_text'))] if not blank(r.get('passive_name')) else None})
trivia_rows = tab('Trivia_ABC')
if trivia_rows and 'id' not in trivia_rows[0]: die('Trivia_ABC needs an "id" column (see claude/ABC_catalog_deckbuilder_plan.md)')
no_id = 0
for r in trivia_rows:
    if s(r.get('deck')) not in BOOKS: continue
    if blank(r.get('id')): no_id += 1; continue
    cards.append({'id': s(r['id']), 't': 'ab', 'b': s(r['deck']), 'n': s(r.get('question')), 'kind': s(r.get('type')).upper(),
                  'pw': n(r.get('power')), 'o': [s(r.get('option_%d' % i)) for i in range(1, 5)],
                  'c': n(r.get('correct_option (1-4)')), 'pool': s(r.get('pool (starter/booster)')) or None,
                  'act': s(r.get('act/chapter')) or None})
if no_id: warn('%d trivia rows have no id and were left out' % no_id)
for r in tab('Bookmarks'):
    if blank(r.get('id')): continue
    cards.append({'id': s(r['id']), 't': 'bm', 'n': s(r.get('name')), 'kind': s(r.get('kind')),
                  'r': s(r.get('rarity (C/U/R/E/L)')), 'x': s(r.get('text'))})
for r in tab('Crit_Lenses'):
    if blank(r.get('id')): continue
    cards.append({'id': s(r['id']), 't': 'cr', 'n': s(r.get('name')), 'ps': s(r.get('passive')),
                  'th': s(r.get('thesis')), 'rw': s(r.get('reward'))})

keys = {}
for c in cards:
    k = c['t'] + ':' + c['id']
    if k in keys: die('duplicate %s id "%s"' % (c['t'], c['id']))
    keys[k] = c
if skipped: warn('skipped non-book decks: ' + ', '.join(sorted(skipped)))

# ------------------------------------------------------------ precons
qidx = {}
for c in cards:
    if c['t'] == 'ab': qidx.setdefault((c['b'], re.sub(r'\s+', ' ', c['n']).strip()), c['id'])
SEC = {'Commander': 'fe', 'Character': 'ch', 'Trivia': 'ab', 'Bookmark': 'bm', 'Crit Lens': 'cr'}
pre, order, errs = {}, [], []
for r in tab('ABC_precon_decklists'):
    lab, sec, key = s(r.get('deck')), s(r.get('section')), s(r.get('id_or_question'))
    if not lab or not sec: continue
    if sec not in SEC: errs.append('%s: unknown section "%s"' % (lab, sec)); continue
    if lab not in pre:
        pre[lab] = {'name': re.sub(r'\s*precon\s*$', '', lab, flags=re.I).strip(), 'fe': [], 'ch': [], 'ab': [], 'bm': [], 'cr': []}
        order.append(lab)
    t = SEC[sec]
    if t == 'ab':
        if ('ab:' + key) in keys: pre[lab]['ab'].append(key); continue      # trivia listed by id
        hit = [v for (b, q), v in qidx.items() if q == re.sub(r'\s+', ' ', key).strip()]
        if not hit: errs.append('%s: trivia not found: %s' % (lab, key[:70])); continue
        pre[lab]['ab'].append(hit[0])
    else:
        if (t + ':' + key) not in keys: errs.append('%s: %s "%s" is not in the catalog' % (lab, sec, key)); continue
        pre[lab][t].append(key)
precons = []
for lab in order:
    p = pre[lab]
    books = sorted({keys['ch:' + i]['b'] for i in p['ch']} | {keys['fe:' + i]['b'] for i in p['fe']},
                   key=lambda b: BOOKS.index(b))
    p['b'] = books[0] if books else 'gatsby'
    p['books'] = books[:2]
    cnt = tuple(len(p[t]) for t in ('fe', 'ch', 'ab', 'bm', 'cr'))
    want = (PM['fe'], PM['ch'], PM['ab'], PM['bm'], PM['cr'])
    if cnt != want: errs.append('%s: %d+%d+%d+%d+%d, precons must be %d+%d+%d+%d+%d' % ((lab,) + cnt + want))
    precons.append(p)
if errs: die('precon problems, nothing written:\n  ' + '\n  '.join(errs))

# ------------------------------------------------------------ content + scans
content = {}
if os.path.exists(a.content):
    content = json.load(open(a.content, encoding='utf-8'))
    for cid, x in (content.get('cards') or {}).items():
        c = keys.get('ch:' + cid)
        if not c: warn('content.json card "%s" is not in the Characters tab' % cid); continue
        norm = lambda v: re.sub(r'\W', '', v or '').lower()
        diffs = [f for f, a1, b1 in (('name', x.get('name'), c['n']), ('attack', x.get('atkName'), c['a'][0]),
                                     ('block', x.get('blkName'), c['k'][0]),
                                     ('passive', (x.get('passive') or {}).get('name'), (c['p'] or [''])[0]))
                 if a1 and norm(a1) != norm(b1)]
        if diffs: warn('No. %s %s: printed card and sheet differ on %s' % (x.get('no'), c['n'], ', '.join(diffs)))

MIME = {'.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
def data_uri(path):
    return 'data:%s;base64,%s' % (MIME[os.path.splitext(path)[1].lower()], base64.b64encode(open(path, 'rb').read()).decode())
scans, unknown = {}, []
if os.path.isdir(a.scans):
    for f in sorted(os.listdir(a.scans)):
        stem, ext = os.path.splitext(f)
        if ext.lower() not in MIME: continue
        hits = [t + ':' + stem for t in ('ch', 'fe', 'bm', 'cr', 'ab') if (t + ':' + stem) in keys]
        if not hits: unknown.append(f); continue
        scans[hits[0]] = data_uri(os.path.join(a.scans, f))
if unknown: warn('scans with no matching card id: ' + ', '.join(unknown))
back = {}
for k, f in (('full', 'art/back_print.webp'), ('emblem', 'art/back_emblem.webp')):
    if os.path.exists(os.path.join(ROOT, f)): back[k] = data_uri(os.path.join(ROOT, f))
    else: warn('%s missing — printing uses the plain placeholder back' % f)

# ------------------------------------------------------------ assemble
data = {'rules': RULES, 'books': [{'id': b, 'n': NAMES.get(b, b)} for b in BOOKS],
        'cards': cards, 'precons': precons, 'exp': EXP, 'content': content}
src = open(a.src, encoding='utf-8').read()
for ph in ('/*@ABC_DATA@*/', '/*@ABC_SCANS@*/'):
    if src.count(ph) != 1: die('src/catalog.src.html must contain %s exactly once' % ph)
js = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
out = src.replace('/*@ABC_DATA@*/', 'window.ABC_DATA=' + js(data) + ';') \
         .replace('/*@ABC_SCANS@*/', 'window.ABC_SCANS=' + js(scans) + ';window.ABC_BACK=' + js(back) + ';')
os.makedirs(os.path.dirname(a.out), exist_ok=True)
open(a.out, 'w', encoding='utf-8').write(out)
cnt = {}
for c in cards: cnt[c['t']] = cnt.get(c['t'], 0) + 1
print('[catalog] %s' % os.path.relpath(a.out, ROOT))
print('[catalog] %d characters, %d commanders, %d trivia, %d bookmarks, %d lenses · %d precons · %d scans · %d expansions'
      % (cnt.get('ch', 0), cnt.get('fe', 0), cnt.get('ab', 0), cnt.get('bm', 0), cnt.get('cr', 0), len(precons), len(scans), len(EXP)))
print('[catalog] %s bytes  sha256=%s' % (format(len(out), ','), hashlib.sha256(out.encode()).hexdigest()))
