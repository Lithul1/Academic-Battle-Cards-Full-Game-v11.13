# -*- coding: utf-8 -*-
"""Sync romeojuliet + odyssey into game.src.html.

Additive everywhere except six registry points that must learn the new keys.
Run:  python3 sync_decks.py [--dry-run]
"""
import io, re, csv, json, sys

DRY = '--dry-run' in sys.argv
P = 'game.src.html'
h = io.open(P, encoding='utf-8').read()
orig = len(h)
report = []

def esc(s): return (s or '').replace('\\', '\\\\').replace('"', '\\"')
def extra(js, sep=', '):
    if not (js or '').strip(): return ''
    inner = json.dumps(json.loads(js), ensure_ascii=False)[1:-1]
    return (sep + inner) if inner else ''

def char_js(c):
    s = '{ id:"%s", name:"%s", hp:%d, "archetype":"%s", accent:"%s", img:""' % (
        c['id'], esc(c['name']), int(c['hp']), c['archetype'], c['accent'])
    tags = [t.strip() for t in (c.get('tags') or '').split(',') if t.strip()]
    if tags: s += ', tags:' + json.dumps(tags, ensure_ascii=False)
    s += ',\n        atk:{n:"%s", t:"%s", cost:%d' % (esc(c['atk_name']), esc(c['atk_text']), int(c['atk_cost']))
    if str(c['atk_dmg']).strip(): s += ', dmg:%d' % int(c['atk_dmg'])
    s += extra(c.get('atk_extra_json'))
    s += ', label:"%s"},\n        blk:{n:"%s", t:"%s", cost:%d' % (
        c['atk_label'], esc(c['blk_name']), esc(c['blk_text']), int(c['blk_cost']))
    if str(c['blk_block']).strip(): s += ', block:%d' % int(c['blk_block'])
    s += extra(c.get('blk_extra_json'))
    return s + ', label:"%s"} }' % c['blk_label']

def fe_js(f):
    pid = re.sub(r'[^a-z0-9]', '', f['passive_name'].lower())[:18]
    s = ('{ id:"%s", name:"%s", deck:"%s", hp:%d, archetype:\'%s\', accent:"%s", img:"", fe:true, tier:"%s", base:%s,'
         % (f['id'], esc(f['name']), f['deck'], int(f['hp']), f['archetype'], f['accent'],
            f.get('tier') or 'standard',
            json.dumps([x.strip() for x in f['base'].split(',')], ensure_ascii=False)))
    s += '\n        passive:{id:"%s",name:"%s",text:"%s"},' % (pid, esc(f['passive_name']), esc(f['passive_text']))
    s += '\n        atk:{n:"%s",t:"%s",cost:%d' % (esc(f['atk_name']), esc(f['atk_text']), int(f['atk_cost']))
    if str(f['atk_dmg']).strip(): s += ',dmg:%d' % int(f['atk_dmg'])
    s += extra(f.get('atk_extra_json'), ',')
    s += ',label:"%s"},\n        blk:{n:"%s",t:"%s",cost:%d' % (
        f['atk_label'], esc(f['blk_name']), esc(f['blk_text']), int(f['blk_cost']))
    if str(f['blk_block']).strip(): s += ',block:%d' % int(f['blk_block'])
    s += extra(f.get('blk_extra_json'), ',')
    return s + ',label:"%s"} }' % f['blk_label']

CH = list(csv.DictReader(io.open('sync/characters.tsv', encoding='utf-8'), delimiter='\t'))
FE = list(csv.DictReader(io.open('sync/firsteds.tsv', encoding='utf-8'), delimiter='\t'))
TR = list(csv.DictReader(io.open('sync/trivia.tsv', encoding='utf-8'), delimiter='\t'))
DECKS = ['romeojuliet', 'odyssey']

# ---------------------------------------------------------------- 1 characters
anchor = '\n    ]\n  },\n\n  // -------- ABC ACTION CARDS (trivia)'
assert h.count(anchor) == 1, 'characters close anchor'
blocks = ''
for d in DECKS:
    rows = [c for c in CH if c['deck'] == d]
    assert rows, d
    blocks += ',\n    %s: [\n      ' % d + ',\n      '.join(char_js(c) for c in rows) + '\n    ]'
    report.append('characters.%-12s %3d' % (d, len(rows)))
h = h.replace(anchor, '\n    ]' + blocks + '\n  },\n\n  // -------- ABC ACTION CARDS (trivia)', 1)

# ---------------------------------------------------------------- 2 first editions
m = re.search(r'\n  \]\n\};\nif \(typeof window', h)
assert m, 'firsteds close anchor'
# the array may or may not already end in a trailing comma; a second one would
# create an elision (an undefined hole), so decide from what is actually there
before = h[:m.start()].rstrip()
lead = '\n      ' if before.endswith(',') else ',\n      '
h = h[:m.start()] + lead + ',\n      '.join(fe_js(f) for f in FE) + h[m.start():]
report.append('firsteds            +%3d' % len(FE))

# ---------------------------------------------------------------- 3 trivia
abc_close = '\n    ]\n  },\n\n  // -------- CRIT CARDS'
assert h.count(abc_close) == 1, 'abcs close anchor'
tblocks = ''
for d in DECKS:
    rows = [t for t in TR if t['deck'] == d]
    assert rows, d
    lines = []
    for t in rows:
        opts = [t['option_%d' % i] for i in (1, 2, 3, 4)]
        ans = int(t['correct_option (1-4)']) - 1
        assert opts[ans] == t['correct_text (read-only)'], 'key mismatch: ' + t['question'][:44]
        lines.append("_abc('%s',%s,%s,%s,%d)" % (
            'A' if t['type'].upper() == 'ATTACK' else 'B', t['power'],
            json.dumps(t['question'], ensure_ascii=False),
            json.dumps(opts, ensure_ascii=False), ans))
    tblocks += ',\n    %s: [\n      ' % d + ',\n      '.join(lines) + '\n    ]'
    report.append('abcs.%-18s %3d' % (d, len(rows)))
h = h.replace(abc_close, '\n    ]' + tblocks + '\n  },\n\n  // -------- CRIT CARDS', 1)

# ---------------------------------------------------------------- 4 DECK_ORDER
old = "const DECK_ORDER = ['gatsby','crucible','hamlet','frankenstein','sherlock','othello','oz','macbeth','wonderland','tewwg'];"
assert h.count(old) == 1, 'DECK_ORDER'
h = h.replace(old, old[:-2] + ",'romeojuliet','odyssey'];", 1)
report.append('DECK_ORDER          +  2')

# ---------------------------------------------------------------- 5 setName
old = "k==='tewwg'?'Their Eyes Were Watching God':k;"
assert h.count(old) == 1, 'setName'
h = h.replace(old, "k==='tewwg'?'Their Eyes Were Watching God':k==='romeojuliet'?'Romeo and Juliet':k==='odyssey'?'The Odyssey':k;", 1)
report.append('setName             +  2')

# ---------------------------------------------------------------- 6 The Stacks
old = 'const STACKS_LORE = [\n'
assert h.count(old) == 1, 'STACKS_LORE'
lore = (
 '  {id:"romeojuliet",t:"Romeo and Juliet",a:"William Shakespeare",y:"c.1595",ac:"#a3202f",type:"Deck",'
 'b:"Two houses in Verona have hated each other so long that nobody remembers why. Their children meet, marry in secret, '
 'and are dead within four days. Shakespeare\'s tragedy of haste, of the feud that outlives its cause, and of the message that arrives too late."},\n'
 '  {id:"odyssey",t:"The Odyssey",a:"Homer",y:"c.700 BC",ac:"#1f5e7a",type:"Deck",'
 'b:"Ten years at Troy, and ten more getting home. Odysseus outlasts monsters, gods and his own crew to reach an Ithaca '
 'full of men eating his house. The founding epic of the long way round, and of cunning as the virtue that survives."},\n')
h = h.replace(old, old + lore, 1)
report.append('STACKS_LORE         +  2')

# ---------------------------------------------------------------- write
print('[sync] DRY RUN' if DRY else '[sync] applying')
for r in report: print('   ' + r)
print('[sync] %d -> %d bytes  (+%.0f KB)' % (orig, len(h), (len(h) - orig) / 1024))
if not DRY:
    io.open(P, 'w', encoding='utf-8').write(h)
    print('[sync] written')
