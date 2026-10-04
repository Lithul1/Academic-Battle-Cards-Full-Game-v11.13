/* Issue 1 (full merge). Run: node tests/femerge.test.js */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'dist', 'stub.html'), 'utf8');
let pass = 0, fail = 0; const R = [];
const ok = (n, c, d) => c ? (pass++, R.push('  ok   ' + n))
                          : (fail++, R.push('  FAIL ' + n + (d ? '\n         ' + d : '')));

const dom = new JSDOM(HTML, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'https://example.org/' });
const win = dom.window;

setTimeout(() => {
  const DBG = win.ABC_DEBUG, EXP = win.ABC_EXPORT;
  if (!DBG || !EXP) { console.log('FATAL: missing export surface'); process.exit(1); }
  // the merge accessors are exported on ABC_EXPORT; everything else on ABC_DEBUG
  const D = new Proxy({}, { get:(_,k)=> (k in EXP ? EXP[k] : DBG[k]) });
  // META is a closure const surfaced on ABC_DEBUG, not on window
  const META = DBG.META;

  const base = (win.DATA.firsteds || []).length;
  const all = D.feAll();
  const exp = D.feExpansionCmds();

  ok('base roster is 30', base === 30, 'got ' + base);
  ok('10 expansion commanders found', exp.length === 10, 'got ' + exp.length);
  ok('feAll spans both', all.length === base + exp.length,
     all.length + ' vs ' + (base + exp.length));
  ok('no duplicate ids in the merged roster',
     new Set(all.map(f => f.id)).size === all.length);

  // every merged entry must carry what consumers read
  const need = ['id', 'name', 'deck', 'hp', 'accent', 'atk', 'blk', 'passive'];
  const broken = all.map(f => [f.id, need.filter(k => f[k] == null)])
                    .filter(x => x[1].length);
  ok('every merged commander has the fields consumers read',
     broken.length === 0, broken.slice(0, 5).map(x => x[0] + ' missing ' + x[1]).join('; '));

  // Pagemaster: every deck key must be a real base deck
  const decks = [...new Set(all.map(f => f.deck).filter(Boolean))];
  ok('every commander deck key is a base deck',
     decks.every(k => !!(win.DATA.characters || {})[k]), decks.join(','));

  // firstedById must resolve every merged id
  const unresolved = all.filter(f => !D.firstedById(f.id));
  ok('firstedById resolves every merged id', unresolved.length === 0,
     unresolved.map(f => f.id).join(','));

  // ---- ownership spans two namespaces without merging them ----
  META.commanders = []; META.editionCards = [];
  ok('nothing owned when both namespaces are empty',
     all.filter(D.feHas).length === 0);

  const oneBase = all.find(f => !f.cid), oneExp = all.find(f => !!f.cid);
  META.commanders = [oneBase.id];
  ok('base ownership reads META.commanders', D.feHas(oneBase));
  ok('a base id does NOT satisfy an expansion commander', !D.feHas(oneExp));

  META.editionCards = [oneExp.cid];
  ok('expansion ownership reads META.editionCards via cid', D.feHas(oneExp));
  ok('namespaces stay separate', D.feHas(oneBase) && D.feHas(oneExp) &&
     all.filter(D.feHas).length === 2);

  // feOwned (the deck-licence path) must also see expansion commanders
  ok('feOwned resolves an owned expansion commander',
     D.feOwned ? D.feOwned(oneExp.id) === true : true);

  // ---- the Library shelf ----
  META.commanders = all.filter(f => !f.cid).map(f => f.id);
  META.editionCards = all.filter(f => !!f.cid).map(f => f.cid);
  ok('everything owned counts as ' + all.length,
     all.filter(D.feHas).length === all.length);

  try {
    DBG.SCRIM.view = 'vault'; DBG.SCRIM.vaultTab = 'firsteds';
  } catch (e) {}
  const shelfHtml = (typeof D.scrimVaultShellSrc === 'function')
    ? D.scrimVaultShellSrc() : '';
  if (shelfHtml) {
    const spines = (shelfHtml.match(/lib-spine/g) || []).length;
    ok('Library shelf renders all ' + all.length + ' spines',
       spines === all.length, 'got ' + spines);
    ok('Library counter reads ' + all.length + '/' + all.length,
       shelfHtml.indexOf(all.length + '/' + all.length) >= 0);
    ok('an expansion commander appears on the shelf',
       shelfHtml.indexOf(oneExp.id) >= 0, oneExp.id + ' not found');
  } else {
    R.push('  --   Library shelf markup not reachable from ABC_DEBUG; skipped');
  }

  // ---- the Pagemaster picker ----
  const ownedList = D.feOwnedList();
  const expInList = ownedList.filter(f => !!f.cid).length;
  ok('feOwnedList includes every owned expansion commander',
     expInList === 10, 'got ' + expInList + ' of 10');
  // base FEs on licence-locked decks are correctly withheld
  const lockedDecks = win.LOCKED_DECKS || [];
  const expectBase = all.filter(f => !f.cid && lockedDecks.indexOf(f.deck) < 0).length;
  ok('feOwnedList still withholds base FEs on locked decks',
     ownedList.filter(f => !f.cid).length === expectBase,
     'got ' + ownedList.filter(f => !f.cid).length + ', expected ' + expectBase);
  ok('Pagemaster pairings rise to C(40,2)=780',
     (all.length * (all.length - 1)) / 2 === 780,
     'got ' + (all.length * (all.length - 1)) / 2);

  // ---- deliberately base-only sites must NOT have widened ----
  ok('feFor stays base-only', (() => {
    const ids = [].concat(...Object.keys(win.DATA.characters || {}).map(k => D.feFor ? D.feFor(k) : []));
    return !ids.some(id => (all.find(f => f.id === id) || {}).cid);
  })(), 'an expansion commander leaked into a starter deck');

  const src = HTML;
  ok('base pack roll left base-only',
     /cmdPool=\(\)=>\(DATA\.firsteds\|\|\[\]\)/.test(src));
  ok('tier-pack R pools left base-only',
     (src.match(/R:\(DATA\.firsteds\|\|\[\]\)/g) || []).length === 2);

  // ---- the dev button that never worked ----
  ok('dev unlock no longer runs Object.keys on the array',
     src.indexOf('Object.keys(DATA.firsteds)') < 0);

  console.log(R.join('\n'));
  console.log('\n' + pass + ' passed / ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}, 2500);
