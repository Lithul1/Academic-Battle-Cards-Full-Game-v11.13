/* Lens rewrites part 1 — S1 Structuralism, AR1 Archetypal, D3 Deconstruction.
   Run: node tests/lenses.test.js */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'dist', 'stub.html'), 'utf8');
let pass = 0, fail = 0; const R = [];
const ok = (n, c, d) => c ? (pass++, R.push('  ok   ' + n))
                          : (fail++, R.push('  FAIL ' + n + (d ? '\n         ' + d : '')));

const dom = new JSDOM(HTML, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'https://example.org/' });
const win = dom.window, doc = win.document;

setTimeout(() => {
  const D = win.ABC_DEBUG, APP = D.APP, M = D.META;
  const decks = Object.keys(win.DATA.characters || {});
  M.decks = decks.slice(); M.deckCards = {};
  decks.forEach(k => { M.deckCards[k] = {
    ch: win.DATA.characters[k].map(c => c.id),
    ab: win.DATA.abcs[k].map((_, i) => i),
    bm: win.DATA.bookmarks.map((_, i) => i),
    cr: win.DATA.crits.map((_, i) => i) }; });
  M.commanders = (win.DATA.firsteds || []).map(f => f.id);
  D.freeze(); D.noAI = true;

  const lensOf = id => Object.assign({}, win.DATA.crits.find(c => c.id === id), { fx: id });
  const game = (id) => {
    D.newGame(APP.settings, D.defaultDeck('macbeth'), D.defaultDeck('frankenstein'));
    if (id) D.S.you.crit = lensOf(id);
    return D.S.you.team[D.S.you.activeIdx];
  };
  const anAbc = () => {
    let i = D.S.you.hand.findIndex(c => c.cat === 'abc');
    if (i < 0) { const j = D.S.you.deck.findIndex(c => c.cat === 'abc');
                 D.S.you.hand.push(D.S.you.deck.splice(j, 1)[0]); i = D.S.you.hand.length - 1; }
    return i;
  };
  const attach = (act, power, type) => {
    const i = anAbc();
    D.S.you.hand[i].power = power; D.S.you.hand[i].type = type || 'ATTACK';
    D.S.pending = { card: D.S.you.hand[i], handIdx: i, target: act.uid };
    D.attach('you', i, true, act.uid);
  };

  // ================= S1 Structuralism =================
  let act = game('structuralism');
  act.atkCharge = []; act.blkCharge = [];
  attach(act, 3);
  ok('an ascending charge counts double', act.atkCharge.length === 2,
     'got ' + act.atkCharge.length);
  ok('the bonus charge is synthetic (_wild)',
     act.atkCharge.filter(c => c._wild).length === 1);
  ok('the bonus is tagged as Structuralism\u2019s',
     act.atkCharge.some(c => c._struct));

  const before = act.atkCharge.length;
  attach(act, 1);                                  // deliberately out of order
  ok('a descending charge is ACCEPTED, not refused', act.atkCharge.length > before,
     'the old passive refused this outright');
  ok('and it is not doubled', act.atkCharge.length === before + 1,
     'added ' + (act.atkCharge.length - before));

  // the refusal that caused the stuck modal must be gone entirely
  ok('the refusing guard is gone from the build',
     HTML.indexOf('Structuralism: charge in ascending Power order.') < 0);

  // a _wild bonus must not raise the bar against the next real card
  act.atkCharge = []; act.blkCharge = [];
  attach(act, 2);                                  // -> real 2 + wild 0
  const after2 = act.atkCharge.length;
  attach(act, 2);                                  // equal power: still ascending
  ok('a doubled charge does not block the next equal charge',
     act.atkCharge.length === after2 + 2, 'added ' + (act.atkCharge.length - after2));

  // ================= AR1 Archetypal =================
  act = game('archetypal');
  const living = D.S.you.team.filter(c => c.hp > 0);
  const kinds = [...new Set(living.map(c => c.archetype).filter(Boolean))];
  ok('every living character carries an archetype',
     living.every(c => !!c.archetype), JSON.stringify(living.map(c => c.archetype)));
  ok('the roster spans several archetypes', kinds.length >= 2, JSON.stringify(kinds));

  // drive a real attack and read the damage bonus out of the log
  act.atkCharge = [];
  while (act.atkCharge.length < act.atk.cost) act.atkCharge.push({ type: 'ATTACK', power: 1 });
  D.S.turn = 'you';
  D.performAttack('you', 'atk');
  const line = (D.S.log || []).find(l => /Archetypal Lens/.test(l));
  ok('Archetypal adds damage on attack', !!line, (D.S.log || []).slice(0, 3).join(' | '));
  ok('the bonus is 10 per distinct living archetype',
     !!line && line.indexOf('+' + (kinds.length * 10)) >= 0,
     line + ' (expected +' + kinds.length * 10 + ')');

  // and it must do nothing without the lens
  act = game(null);
  act.atkCharge = [];
  while (act.atkCharge.length < act.atk.cost) act.atkCharge.push({ type: 'ATTACK', power: 1 });
  D.S.turn = 'you';
  D.performAttack('you', 'atk');
  ok('no Archetypal bonus without the lens',
     !(D.S.log || []).some(l => /Archetypal Lens/.test(l)));

  // First Strike must not be referenced as a live mechanic
  ok('First Strike is not silently expected anywhere',
     HTML.indexOf('firstStrike') < 0);

  // ================= D3 Deconstruction =================
  act = game('deconstruct');
  act.atkCharge = []; act.blkCharge = [];
  const need = act.atk.cost;
  for (let i = 0; i < need; i++) act.blkCharge.push({ cat: 'abc', type: 'BLOCK', power: 1 });
  ok('the Active has only BLOCK charges', act.atkCharge.length === 0);
  ok('it is not Exposed yet', !act.status.exposed);
  D.S.turn = 'you';
  D.performAttack('you', 'atk');
  ok('blocks can pay for an attack', act.blkCharge.length < need,
     'blk left ' + act.blkCharge.length + ' of ' + need);
  ok('and the price is Exposed on YOUR Active', act.status.exposed === true);

  // Exposed is a negative status -- the whole point of the correction
  const CSS = HTML;
  ok('Exposed is a negative status, not a gift',
     /exposed:\{n:'Exposed'[^}]*tone:'neg'/.test(CSS));
  ok('Margin Notes is positive, so it was the wrong price',
     /const POS=\['highlight','laminate','hardcover','marginNotes'/.test(CSS));
  ok('D3 does not use Margin Notes as its cost',
     HTML.indexOf("status.marginNotes=true") < 0 ||
     HTML.indexOf('binary collapses') < 0 ? true :
     HTML.slice(HTML.indexOf('binary collapses') - 700,
                HTML.indexOf('binary collapses')).indexOf('marginNotes') < 0);

  // without the lens, blocks must NOT pay for attacks
  act = game(null);
  act.atkCharge = []; act.blkCharge = [];
  for (let i = 0; i < need; i++) act.blkCharge.push({ cat: 'abc', type: 'BLOCK', power: 1 });
  D.S.turn = 'you';
  const fired = D.performAttack('you', 'atk');
  ok('no cross-payment without the lens', fired === false || act.blkCharge.length === need,
     'blk left ' + act.blkCharge.length);

  console.log(R.join('\n'));
  console.log('\n' + pass + ' passed / ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}, 2500);
