/* Step 4 — the two-column tabbed builder. Run: node tests/builderui.test.js */
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
  const D = win.ABC_DEBUG, APP = D.APP, M = D.META;
  const decks = Object.keys(win.DATA.characters || {});
  M.decks = decks.slice(); M.deckCards = {};
  decks.forEach(k => { M.deckCards[k] = {
    ch: win.DATA.characters[k].map(c => c.id),
    ab: win.DATA.abcs[k].map((_, i) => i),
    bm: win.DATA.bookmarks.map((_, i) => i),
    cr: win.DATA.crits.map((_, i) => i) }; });
  M.commanders = (win.DATA.firsteds || []).map(f => f.id);
  M.editionCards = [];
  Object.keys(win.EXPANSIONS || {}).forEach(k => {
    const e = win.EXPANSIONS[k];
    if (e && e.battle) ['chars','abcs','bookmarks','commanders'].forEach(kk =>
      (e.battle[kk] || []).forEach(o => { if (o.cid) M.editionCards.push(o.cid); }));
  });

  const feFor = k => (win.DATA.firsteds || []).find(f => f.deck === k);
  const doc = () => new JSDOM(D.builderScreen(), {}).window.document;

  const pm = D.defaultDeck('hamlet');
  pm.pm = true; pm.books = ['hamlet', 'macbeth'];
  pm.fe = [feFor('hamlet').id, feFor('macbeth').id];
  const cu = D.defaultDeck('gatsby');
  APP.screen = 'builder'; APP.youDeck = 'gatsby';
  APP.builder = D.makeBuilderState(pm, cu, 'cu');

  // ---------------- the class collision that crushed the builder ----------
  const root = doc().querySelector('.builder');
  ok('builder root does not carry .bdx (the 60px deck-box class)',
     !root.classList.contains('bdx'), root.className);
  ok('builder root carries its own namespace', root.classList.contains('bdk'));

  // ---------------- shell ----------
  let d = doc();
  ok('five tabs render', d.querySelectorAll('.bdk-tab').length === 5,
     String(d.querySelectorAll('.bdk-tab').length));
  ok('both columns render', d.querySelectorAll('.bdk-col').length === 2);
  ok('the active column is marked', d.querySelectorAll('.bdk-col.on').length === 1);
  ok('active column is the Custom one',
     d.querySelector('.bdk-col.on').classList.contains('cu'));

  // ---------------- book row placement ----------
  ok('book row sits inside the folder',
     !!d.querySelector('.bdk-folder .bd-setpick'));
  ok('book row is NOT in the page header',
     !d.querySelector('.bd-top .bd-setpick'));
  ok('all twelve books render',
     d.querySelectorAll('.bdk-folder .bd-setpick .bdx').length === 12);

  APP.builder.tab = 'bm'; d = doc();
  ok('book row hidden on Bookmarks', !d.querySelector('.bd-setpick'));
  APP.builder.tab = 'cr'; d = doc();
  ok('book row hidden on Crit Lenses', !d.querySelector('.bd-setpick'));
  APP.builder.tab = 'ch';

  // ---------------- book row as a filter, never a destroyer ----------
  d = doc();
  ok('a committed deck locks the book row', !!d.querySelector('.bdk-books.locked'));
  const before = { d: cu.d, n: cu.ch.length };
  D.handleBuilder('set:hamlet');
  ok('switching book on a committed deck is refused',
     APP.builder.def.d === before.d && APP.builder.def.ch.length === before.n,
     'became ' + APP.builder.def.d + ' with ' + APP.builder.def.ch.length);

  D.handleBuilder('reset');
  const cleared = APP.builder.def;
  ok('Reset clears the deck',
     D.deckCounts(cleared).total === 0, String(D.deckCounts(cleared).total));
  ok('Reset keeps the book until you choose another', cleared.d === 'gatsby');
  d = doc();
  ok('an empty deck unlocks the book row', !d.querySelector('.bdk-books.locked'));

  D.handleBuilder('set:hamlet');
  ok('an empty deck accepts a new book', APP.builder.def.d === 'hamlet');
  ok('switching book on an empty deck adds no cards',
     D.deckCounts(APP.builder.def).total === 0);

  // Pagemaster books come from its commanders, so the row cannot move them
  APP.builder.active = 'pm';
  const pmBooksBefore = JSON.stringify(D.booksOf(APP.builder.def));
  D.handleBuilder('set:gatsby');
  ok('a Pagemaster deck refuses a book change',
     JSON.stringify(D.booksOf(APP.builder.def)) === pmBooksBefore,
     pmBooksBefore + ' -> ' + JSON.stringify(D.booksOf(APP.builder.def)));
  ok('Reset on Pagemaster keeps the commanders', (() => {
    D.handleBuilder('reset');
    return (APP.builder.def.fe || []).length === 2;
  })(), JSON.stringify(APP.builder.def.fe));

  // ---------------- caps follow the focused column ----------
  APP.builder.pm.def = pm; APP.builder.cu.def = cu;
  APP.builder.active = 'pm';
  ok('Pagemaster column reports its own caps', D.capsFor(APP.builder.def).ch === 12);
  APP.builder.active = 'cu';
  ok('Custom column reports its own caps', D.capsFor(APP.builder.def).ch === 14);

  // ---------------- counters and colours ----------
  d = doc();
  const heads = [...d.querySelectorAll('.bdk-sh span')].map(s => s.textContent);
  ok('per-section counters read n/cap',
     heads.length > 0 && heads.every(h => /^\d+\/\d+$/.test(h)), heads.join(' '));
  ok('column total renders', /\d+\/\d+/.test(d.querySelector('.bdk-total').textContent));
  const kinds = new Set([...d.querySelectorAll('.bdk-it')]
    .map(i => ((i.className.match(/(?:^|\s)(k-\w+)/) || [])[1]) || ''));
  ok('deck entries are coloured by card type',
     ['k-ch','k-fe','k-bm','k-cr'].every(k => kinds.has(k)), [...kinds].join(','));

  // ---------------- legality gates Confirm ----------
  const bad = D.defaultDeck('hamlet');
  bad.pm = true; bad.books = ['hamlet','macbeth'];
  bad.fe = [feFor('hamlet').id, feFor('macbeth').id];
  bad.ch = bad.ch.slice(0, 2);
  APP.builder.pm.def = bad; APP.builder.active = 'pm';
  d = doc();
  const pmCol = d.querySelector('.bdk-col.pm');
  ok('an illegal Pagemaster deck disables Confirm',
     !!pmCol.querySelector('.bdk-confirm[disabled]'));
  ok('the shortfall is named', /need 4|need 12/.test(pmCol.textContent),
     pmCol.querySelector('.pm-bstat').textContent.slice(0, 80));

  // defaultDeck('hamlet') is all Hamlet characters, so it can never meet the
  // 4-per-book minimum. Build to the identity, which spans both books.
  const good = D.defaultDeck('hamlet');
  good.pm = true; good.books = ['hamlet','macbeth'];
  good.fe = [feFor('hamlet').id, feFor('macbeth').id];
  D.bdIdentity(good);
  APP.builder.pm.def = good; d = doc();
  ok('a legal deck enables Confirm',
     !d.querySelector('.bdk-col.pm .bdk-confirm[disabled]'),
     d.querySelector('.bdk-col.pm .pm-bstat').textContent.slice(0, 90));

  // ---------------- attack/block search + power filter ----------
  APP.builder.active = 'cu'; APP.builder.tab = 'ab';
  APP.builder.abPower = 0; APP.builder.abQuery = '';
  D.builderScreen();
  const all = APP.builder._abShown;
  ok('unfiltered pool reports a count', all > 0, String(all));

  APP.builder.abPower = 3; D.builderScreen();
  const p3 = APP.builder._abShown;
  ok('power filter narrows the pool', p3 > 0 && p3 < all, all + ' -> ' + p3);

  APP.builder.abPower = 0; APP.builder.abQuery = 'Gatsby'; D.builderScreen();
  const q = APP.builder._abShown;
  ok('search narrows the pool', q > 0 && q < all, all + ' -> ' + q);

  APP.builder.abQuery = ''; D.builderScreen();
  ok('clearing the search restores the pool', APP.builder._abShown === all);
  ok('the filter bar renders on the Attack/Block tab',
     !!doc().querySelector('.bdk-abflt'));
  APP.builder.tab = 'ch';
  ok('the filter bar is absent on other tabs', !doc().querySelector('.bdk-abflt'));

  // ---------------- deck tools ----------
  APP.builder.cu.def = { d:'macbeth', ch:[], ab:[], bm:[], cr:[], fe:[], ed:{}, edab:[], edbm:{} };
  D.handleBuilder('bdidentity:cu');
  const idc = D.deckCounts(APP.builder.cu.def);
  const comp = D.compFor('macbeth');
  ok('Deck identity builds to this book\u2019s own composition',
     idc.ch === comp.ch && idc.ab === comp.ab,
     'got ch' + idc.ch + '/ab' + idc.ab + ' want ch' + comp.ch + '/ab' + comp.ab);
  ok('Deck identity stays within the total', idc.total <= 62, String(idc.total));

  APP.builder.cu.def.ab = APP.builder.cu.def.ab.slice(0, 5);
  D.handleBuilder('bdfill:cu');
  ok('Fill gaps tops up without exceeding the total',
     D.deckCounts(APP.builder.cu.def).total <= 62,
     String(D.deckCounts(APP.builder.cu.def).total));

  D.handleBuilder('bdrand:cu');
  const rc = D.deckCounts(APP.builder.cu.def);
  ok('Randomize produces a deck within the caps', rc.total <= 62 && rc.ch > 0,
     JSON.stringify(rc));

  // ---------------- removing from a column ----------
  const n0 = APP.builder.cu.def.ch.length;
  D.handleBuilder('bddel:cu;ch;0');
  ok('clicking an entry removes it from that column',
     APP.builder.cu.def.ch.length === n0 - 1);

  // ---- layout: the overlap regression ----
  // The tab strip overflowed the pool and painted over the deck rail because
  // .builder was capped at 860px while the rail took 430 of it. jsdom has no
  // layout engine, so these are arithmetic and CSS assertions rather than
  // measurements: they encode the budget the layout must live within.
  const CSS = (HTML.match(/<style[^>]*>([\s\S]*?)<\/style>/) || [])[1] || '';
  ok('the builder is no longer capped at 860px in two-column mode',
     /\.builder\.bdk\{max-width:min\(/.test(CSS));
  ok('the tab strip wraps, so it cannot overflow onto the rail',
     /\.bdk-tabs\{[^}]*flex-wrap:wrap/.test(CSS));
  ok('the deck rail width is declared', /\.bdk-cols\{flex:0 0 470px/.test(CSS));

  const widest = 1560, rail = 470, pad = 28, gap = 14;
  const pool = widest - pad - rail - gap;
  const cols = min => Math.floor(pool / min);
  ok('the pool fits five tabs on one line', pool >= 5 * 110, 'pool ' + pool + 'px');
  ok('characters land in multiple columns', cols(178) >= 4, cols(178) + ' cols');
  ok('bookmarks land in multiple columns, not one', cols(238) >= 3, cols(238) + ' cols');
  ok('trivia lands in multiple columns', cols(226) >= 3, cols(226) + ' cols');
  ok('the pool scrolls inside itself rather than the page',
     /\.bdk \.bd-sec \.bd-grid[^{]*\{[^}]*max-height/.test(CSS));
  ok('narrow desktops shed rail width before columns',
     /@media \(max-width:1400px\)[\s\S]{0,220}\.bdk-cols\{flex:0 0 420px/.test(CSS));


  // ---- Pagemaster must be reachable FROM the builder ----
  // pmpick had exactly one route in, on the difficulty screen. The builder had
  // none, so the Pagemaster column was a dead panel naming a screen you could
  // not get to from there.
  APP.pmCommanders = []; APP.pmDeck = null;
  APP.screen = 'builder';
  APP.builder = D.makeBuilderState(null, D.defaultDeck('gatsby'), 'cu');
  ok('the Pagemaster column starts unseeded', !APP.builder.pm.def);
  d = doc();
  const pmEmpty = d.querySelector('.bdk-col.pm');
  ok('an unopened column offers a way in', !!pmEmpty.querySelector('.bdk-start'),
     pmEmpty.textContent.trim().slice(0, 60));

  D.handleBuilder('bdfocus:pm');
  ok('clicking the Pagemaster column routes to the commander picker',
     APP.screen === 'pmpick', 'went to ' + APP.screen);
  ok('and puts the app in Pagemaster mode', APP.mode === 'pagemaster');

  APP.pmCommanders = [feFor('hamlet').id, feFor('macbeth').id];
  D.builderFocus('pm');
  ok('with commanders chosen the column seeds', !!APP.builder.pm.def);
  ok('the seeded deck knows it is Pagemaster', APP.builder.pm.def.pm === true);
  ok('it carries both commanders', (APP.builder.pm.def.fe || []).length === 2);
  ok('its books derive from them',
     JSON.stringify(D.booksOf(APP.builder.pm.def)) === JSON.stringify(['hamlet','macbeth']),
     JSON.stringify(D.booksOf(APP.builder.pm.def)));
  ok('the Custom column survived the round trip',
     !!APP.builder.cu.def && APP.builder.cu.def.d === 'gatsby');

  D.handleBuilder('bdidentity:pm');
  ok('a Pagemaster deck can be built to legal from the builder',
     /pm-bstat ok/.test(D.pmBuildStatus(APP.builder.pm.def)),
     D.pmBuildStatus(APP.builder.pm.def).slice(0, 90));

  // ---- the deck-type heading ----
  d = doc();
  ok('the rail carries a deck-type heading', !!d.querySelector('.bdk-colhead'));
  ok('the heading names the choice',
     /select your deck type/i.test(d.querySelector('.bdk-colhead').textContent));
  ok('the two columns sit in a row under it',
     d.querySelectorAll('.bdk-colrow > .bdk-col').length === 2);

  // ---- column counts are declared, not inferred ----
  const CSS2 = (HTML.match(/<style[^>]*>([\s\S]*?)<\/style>/) || [])[1] || '';
  // slice from the comment's opening so the strip below can match it
  const followUp = CSS2.slice(CSS2.lastIndexOf('/* ===== builder step 4 follow-up'));
  const rulesOnly = followUp.replace(/\/\*[\s\S]*?\*\//g, '');
  ok('no auto-fill decides a builder column count',
     rulesOnly.indexOf('auto-fill') < 0);
  ok('trivia is two declared columns',
     /\.bdk \.bd-grid\.ab\{grid-template-columns:repeat\(2,/.test(followUp));
  ok('trivia questions are clamped so the chip stays small',
     /\.bdk \.bd-chip\.ab \.bd-q\{[^}]*line-clamp:2/.test(followUp));


  // ---- crit chips: the inspect button must stay inside the tile ----
  // .bd-nm had no min-width, so a long lens name refused to shrink in the flex
  // row and pushed .bd-pv and .bd-mk past the tile border, out of reach.
  APP.builder.tab = 'cr';
  const critDoc = doc();
  const critChips = [...critDoc.querySelectorAll('.bd-chip.crt')];
  ok('every lens renders a chip', critChips.length === win.DATA.crits.length,
     critChips.length + ' of ' + win.DATA.crits.length);
  ok('unlocked lenses carry an inspect button',
     critChips.some(c => c.querySelector('.bd-pv')));

  const critCss = (HTML.match(/<style[^>]*>([\s\S]*?)<\/style>/) || [])[1] || '';
  ok('the lens name is allowed to shrink',
     /\.bd-chip\.crt \.bd-nm\{[^}]*min-width:0/.test(critCss));
  ok('the lens name is allowed to wrap',
     /\.bd-chip\.crt \.bd-nm\{[^}]*white-space:normal/.test(critCss));
  ok('the inspect button is pinned inside the tile',
     /\.bd-chip\.crt \.bd-pv\{[^}]*position:absolute/.test(critCss));
  ok('the tile reserves padding for the controls',
     /\.bd-chip\.crt\{[^}]*padding-right:30px/.test(critCss));
  // the override must land after the generic rule it corrects
  ok('the crit rules override the generic .bd-nm',
     critCss.lastIndexOf('.bd-chip.crt .bd-nm{') >
     critCss.lastIndexOf('.bd-nm{font-family:var(--cond)'));
  APP.builder.tab = 'ch';


  // ---- the board spread ----
  // Two arenas cross-fading into one another, with nothing above the cards.
  const boardCss = (HTML.match(/<style[^>]*>([\s\S]*?)<\/style>/) || [])[1] || '';
  // slice from the comment's OPENING, or the strip below cannot match it --
  // this has now bitten five guards in this project
  const spread = boardCss.slice(boardCss.indexOf('/* ===== the board as one spread'))
                         .replace(/\/\*[\s\S]*?\*\//g, '');
  ok('the board carries both decks as attributes',
     /<div class="board" data-opp=/.test(HTML));
  ok('each arena is its own layer, not a half-height background',
     /height:62%/.test(spread) && spread.indexOf('100% 50%') < 0);
  ok('the layers use cover, so focal points survive',
     /background-size:auto, cover/.test(spread));
  ok('the opponent layer fades downward',
     /mask-image:linear-gradient\(180deg,#000 0%,#000 58%/.test(spread));
  ok('your layer fades upward',
     /mask-image:linear-gradient\(0deg,#000 0%,#000 58%/.test(spread));
  ok('the sides no longer carry the art',
     /\.board \.side\{[^}]*background-image:none!important/.test(spread));
  ok('cards are raised above the spread',
     /\.board \.side > \*\{position:relative; z-index:1\}/.test(spread));
  ok('NOTHING in the spread sits above the cards',
     !/z-index:[2-9]/.test(spread));
  ok('the ownership tint fades out before the middle',
     /transparent 82%/.test(spread));
  ok('no dashed border divides the two halves',
     !/\.(opp|you)-side\{[^}]*dashed/.test(
       boardCss.slice(boardCss.lastIndexOf('/* ===== no dashed division'))),
     'a dashed rule survives after the fix');
  ok('the ownership hairlines survive the border removal',
     /inset 0 3px 0 color-mix/.test(boardCss) && /inset 0 -3px 0 color-mix/.test(boardCss));
  ok('all twelve decks are wired',
     (spread.match(/\.board\[data-opp="/g) || []).length === 12,
     String((spread.match(/\.board\[data-opp="/g) || []).length));


  // ---------------- no regressions ----------
  const wrong = decks.filter(k => {
    const dd = D.defaultDeck(k);
    const feShort = 2 - (dd.fe || []).length;
    return dd.ch.length + dd.ab.length + dd.bm.length + dd.cr.length + dd.fe.length !== 62 - feShort;
  });
  ok('starter decks still total 62', wrong.length === 0, wrong.join(', '));

  console.log(R.join('\n'));
  console.log('\n' + pass + ' passed / ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}, 2500);
