/* Opponent messages must never be shown to the player.
   Run: node tests/sidetoast.test.js

   The reported symptom was "with 4 attack ABCs the game is telling me i have
   zero" -- the message was about the OPPONENT's card. The real defect was that
   toast() has no notion of sides while the engine functions that raise it run
   for both players, so every new failure branch was a fresh leak.

   These assertions are written against BEHAVIOUR (drive the path, read the
   toast node) rather than against source text, so they still hold if the
   implementation changes. */
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
  D.freeze();

  // read and clear the shared #toast node
  const grab = () => {
    const t = doc.getElementById('toast');
    const v = t ? t.textContent.trim() : '';
    if (t) t.textContent = '';
    return v;
  };
  const game = (opp) => D.newGame(APP.settings, D.defaultDeck('gatsby'),
                                  D.defaultDeck(opp || 'macbeth'));

  // ---- the helper itself ----
  ok('sideToast exists', typeof D.sideToast === 'function');
  grab();
  D.sideToast('opp', 'should never appear');
  ok('sideToast is silent for the opponent', grab() === '');
  D.sideToast('you', 'should appear');
  ok('sideToast still speaks to the player', grab() === 'should appear');

  // ---- the exact reported bug ----
  game();
  const oa = () => D.S.opp.team[D.S.opp.activeIdx];
  oa().atkCharge = [];
  grab();
  D.performAttack('opp', 'atk');
  ok('an opponent who cannot pay says nothing to you', grab() === '',
     'this is the reported "have 0" message');

  // and your own charged attack is untouched by the fix
  game();
  const ya = D.S.you.team[D.S.you.activeIdx];
  while (ya.atkCharge.length < ya.atk.cost) ya.atkCharge.push({ type: 'ATTACK' });
  grab();
  const okAtk = D.performAttack('you', 'atk');
  ok('your own fully charged attack still fires', okAtk !== false, String(okAtk));

  // your own UNDER-charged attack must still tell you
  game();
  D.S.you.team[D.S.you.activeIdx].atkCharge = [];
  grab();
  D.performAttack('you', 'atk');
  const mine = grab();
  ok('your own shortfall is still reported to you', /ATTACK ABCs/.test(mine), mine);

  // ---- the other confirmed leaks ----
  game();
  const o2 = oa();
  while (o2.atkCharge.length < o2.atk.cost) o2.atkCharge.push({ type: 'ATTACK' });
  D.S.you.team.forEach(c => c.hp = 0);
  grab();
  D.performAttack('opp', 'atk');
  ok('"No target" does not leak from the opponent', grab() === '');

  // ---- the sweep that found Defibrillator: every real bookmark, every deck ----
  const leaks = {};
  let plays = 0;
  decks.forEach(dk => {
    game(dk);
    const bms = D.S.opp.deck.filter(c => c.cat === 'bookmark');
    bms.forEach(card => {
      game(dk);
      D.S.opp.hand.push(card);
      grab();
      try { D.playBookmark('opp', D.S.opp.hand.length - 1); plays++; } catch (e) {}
      const t = grab();
      if (t) leaks[t] = (leaks[t] || 0) + 1;
    });
  });
  // one pass per deck rather than the 40 randomised passes used during
  // diagnosis; 12 decks x ~14 bookmarks is enough to cover every card
  ok('a broad sweep of opponent bookmark plays ran', plays > 100, plays + ' plays');
  ok('no opponent bookmark leaks a toast', Object.keys(leaks).length === 0,
     Object.keys(leaks).map(k => k.slice(0, 50)).join(' | '));

  // ---- the information is preserved, not merely silenced ----
  game();
  oa().atkCharge = [];
  const before = D.S.log.length;
  D.performAttack('opp', 'atk');
  ok('the opponent\u2019s failure still reaches the log', D.S.log.length > before);
  ok('and the log line names the opponent',
     /Opponent/i.test(D.S.log[0] || ''), String(D.S.log[0]).slice(0, 70));

  // ---- structural: no unguarded toast left in the two engine functions ----
  // This is the assertion that stops the trap being re-armed by the next
  // failure branch someone adds.
  const src = HTML;
  ['performAttack', 'playBookmark'].forEach(fn => {
    const i = src.indexOf('function ' + fn + '(');
    const j = src.indexOf('\nfunction ', i + 10);
    const body = src.slice(i, j);
    const bad = body.split('\n').filter(l =>
      /(?<!side)toast\(/.test(l) && l.indexOf('sideToast(') < 0
      && l.indexOf("side==='you'") < 0 && l.indexOf('isYou') < 0);
    ok(fn + ' raises no unguarded toast', bad.length === 0,
       bad.map(b => b.trim().slice(0, 80)).join(' || '));
  });

  console.log(R.join('\n'));
  console.log('\n' + pass + ' passed / ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}, 2500);
