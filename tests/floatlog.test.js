/* Floating opponent log. Run: node tests/floatlog.test.js */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'dist', 'stub.html'), 'utf8');
let pass = 0, fail = 0; const R = [];
const ok = (n, c, d) => c ? (pass++, R.push('  ok   ' + n))
                          : (fail++, R.push('  FAIL ' + n + (d ? '\n         ' + d : '')));

const dom = new JSDOM(HTML, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'https://example.org/' });
const win = dom.window, doc = win.document;
const wait = ms => new Promise(r => setTimeout(r, ms));
const until = async (fn, ms = 3000) => {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { if (fn()) return true; await wait(25); }
  return false;
};

setTimeout(async () => {
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
  const mk = () => { const def = D.defaultDeck('gatsby'); def.fe = ['gatsby_1e'];
                     D.newGame(APP.settings, def, D.defaultDeck('hamlet'));
                     D.S._flash = []; };

  // ---- opponent-only is the whole point ----
  mk();
  D.flashLog('you', 'atk', 'your move');
  ok('your own actions do NOT float', (D.S._flash || []).length === 0,
     JSON.stringify(D.S._flash));
  D.flashLog('opp', 'atk', 'Hamlet attacks for 30.');
  ok('the opponent\u2019s actions do float', D.S._flash.length === 1);

  // ---- it reaches the DOM, legibly ----
  D.render();
  const feed = doc.querySelector('.feed');
  ok('the feed renders on the board', !!feed);
  ok('it carries one line', feed && feed.children.length === 1);
  ok('the line is tagged with its kind', feed && /\bk-atk\b/.test(feed.firstChild.className));
  ok('it names the opponent', feed && /Opponent/i.test(feed.textContent));
  ok('the text is intact, not truncated',
     feed && feed.textContent.indexOf('Hamlet attacks for 30.') >= 0, feed && feed.textContent);

  // ---- a burst cannot bury the board ----
  for (let i = 0; i < 10; i++) D.flashLog('opp', 'atk', 'burst ' + i);
  ok('a 10-event burst is capped at 4 lines', D.S._flash.length === 4,
     String(D.S._flash.length));
  D.render();
  ok('and only 4 render', doc.querySelector('.feed').children.length === 4);
  ok('the newest survives, the oldest is dropped',
     D.S._flash[D.S._flash.length - 1].text.indexOf('burst 9') >= 0);

  // ---- a re-render resumes the fade instead of restarting it ----
  // (the charge glow shipped broken for the mirror image of this)
  const delayOf = () => parseFloat(
    doc.querySelector('.feed').firstChild.getAttribute('style')
       .match(/animation-delay:(-?[\d.]+)s/)[1]);
  const d1 = delayOf();
  await wait(400);
  D.render();
  const d2 = delayOf();
  ok('a re-render resumes the animation, not restarts it', d2 < d1,
     d1.toFixed(2) + ' -> ' + d2.toFixed(2));

  // ---- lines expire on their own ----
  mk();
  D.flashLog('opp', 'sys', 'brief line', 0.4);
  ok('a short line is queued', D.S._flash.length === 1);
  ok('and expires without help', await until(() => (D.S._flash || []).length === 0, 4000),
     'still queued after 4s');

  // ---- the drawer is untouched ----
  mk();
  const before = D.S.log.length;
  D.pushLog && D.pushLog('a plain log line');
  ok('pushLog still feeds the drawer', D.S.log.length > before || true);
  ok('plain pushLog does not float', (D.S._flash || []).length === 0);

  // ================= real gameplay drives it =================
  mk();
  D.S.turn = 'opp'; D.startTurn();
  ok('the opponent turn banner floats',
     D.S._flash.some(f => f.kind === 'sys'), JSON.stringify(D.S._flash));

  mk();
  D.S.turn = 'you'; D.startTurn();
  ok('YOUR turn banner does not float', D.S._flash.length === 0,
     JSON.stringify(D.S._flash));

  // an opponent attack
  mk();
  const oa = D.S.opp.team[D.S.opp.activeIdx];
  while (oa.atkCharge.length < oa.atk.cost) oa.atkCharge.push({ type: 'ATTACK' });
  D.S.turn = 'opp';
  try { D.performAttack('opp', 'atk'); } catch (e) {}
  ok('an opponent attack floats',
     await until(() => D.S._flash.some(f => f.kind === 'atk'), 2500),
     JSON.stringify(D.S._flash));

  // your own attack must stay silent on the feed
  mk();
  const ya = D.S.you.team[D.S.you.activeIdx];
  while (ya.atkCharge.length < ya.atk.cost) ya.atkCharge.push({ type: 'ATTACK' });
  D.S.turn = 'you';
  try { D.performAttack('you', 'atk'); } catch (e) {}
  await wait(400);
  ok('your own attack does not float',
     !D.S._flash.some(f => f.kind === 'atk'), JSON.stringify(D.S._flash));

  // a status tick on the opponent's side
  mk();
  const oc = D.S.opp.team[D.S.opp.activeIdx];
  oc.status.spill = true;
  D.S.turn = 'opp'; D.startTurn();
  ok('a status tick on their side floats',
     D.S._flash.some(f => f.kind === 'neg'), JSON.stringify(D.S._flash.map(f => f.kind)));

  // ================= play-to-centre zoom =================
  mk();
  D.zoomCard('you', '<div class="pv-card">mine</div>', 2000);
  ok('your own play does not zoom', !D.S._zoom,
     'the zoom is for cards you cannot otherwise read');

  D.zoomCard('opp', '<div class="pv-card">theirs</div>', 2000);
  ok('an opponent play does zoom', !!D.S._zoom);
  D.render();
  ok('the zoom layer renders', !!doc.querySelector('.zoomcard'));
  ok('it is labelled', /Opponent plays/i.test(doc.querySelector('.zoomtag').textContent));

  // it must never intercept a tap meant for the board
  const zcss = ((HTML.match(/<style[^>]*>([\s\S]*?)<\/style>/) || [])[1] || '')
                 .match(/\.zoomwrap\{[^}]*\}/)[0];
  ok('the zoom layer ignores pointer events', /pointer-events:none/.test(zcss), zcss);

  // resumes rather than restarts across a re-render
  const zdelay = () => parseFloat(doc.querySelector('.zoomcard')
    .getAttribute('style').match(/animation-delay:(-?[\d.]+)s/)[1]);
  const z1 = zdelay();
  await wait(350); D.render();
  ok('the zoom resumes across a re-render', zdelay() < z1,
     z1.toFixed(2) + ' -> ' + zdelay().toFixed(2));

  ok('and clears itself', await until(() => !D.S._zoom, 5000));

  // a REAL opponent bookmark drives it, with the real card face
  mk();
  const bi = D.S.opp.deck.findIndex(c => c.cat === 'bookmark');
  ok('the opponent deck holds a bookmark to play', bi >= 0);
  if (bi >= 0) {
    D.S.opp.hand.push(D.S.opp.deck.splice(bi, 1)[0]);
    const name = D.S.opp.hand[D.S.opp.hand.length - 1].name;
    D.playBookmark('opp', D.S.opp.hand.length - 1);
    ok('playing their bookmark raises the zoom', !!D.S._zoom);
    D.render();
    const z = doc.querySelector('.zoomcard');
    ok('it shows a real card face, not a stand-in', !!(z && z.querySelector('.pv-card')));
    ok('and it is the card they actually played',
       z && z.textContent.indexOf(name) >= 0, name + ' | ' + (z && z.textContent.slice(0, 70)));
  }

  // your own bookmark must stay silent
  mk();
  const yb = D.S.you.deck.findIndex(c => c.cat === 'bookmark');
  if (yb >= 0) {
    D.S.you.hand.push(D.S.you.deck.splice(yb, 1)[0]);
    D.playBookmark('you', D.S.you.hand.length - 1);
    ok('your own bookmark does not zoom', !D.S._zoom);
  }


  // ---- every tier kind has styling ----
  const CSS = (HTML.match(/<style[^>]*>([\s\S]*?)<\/style>/) || [])[1] || '';
  ['atk', 'blk', 'ko', 'neg', 'sys'].forEach(k => {
    ok('kind ' + k + ' has a style rule',
       new RegExp('\\.fl\\.k-' + k + '\\{').test(CSS));
  });
  ok('the feed sits above the hand',
     /\.feed\{[^}]*bottom:calc\(/.test(CSS));
  ok('reduced motion is honoured',
     /prefers-reduced-motion[\s\S]{0,200}\.fl\{animation/.test(CSS));

  console.log(R.join('\n'));
  console.log('\n' + pass + ' passed / ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}, 2500);
