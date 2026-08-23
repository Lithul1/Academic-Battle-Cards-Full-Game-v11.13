/* Issue 4 -- computed hand fan. Run: node tests/fan.test.js */
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
  const D = win.ABC_DEBUG;
  if (!D) { console.log('FATAL: no ABC_DEBUG'); process.exit(1); }
  const doc = win.document;
  const css = Array.from(doc.querySelectorAll('style')).map(s => s.textContent).join('\n');

  // ---- the old system is gone, not supplemented ----
  ok('no hardcoded translateX ladder survives',
     !/\.hand \.hc:nth-child\(\d\)\{transform:translateX/.test(css));
  ok('index ladder covers 24 cards',
     (css.match(/\.hand \.hc:nth-child\(\d+\)\{--i:/g) || []).length === 24);
  ok('fan is declared outside any @media',
     /^\.hand\{[^}]*--tuck-frac/m.test(css.replace(/\r/g, '')),
     'the .hand block with --tuck-frac must be at top level');

  // ---- the count reaches the DOM ----
  try {
    D.freeze();
    D.newGame({}, D.defaultDeck('hamlet'), D.defaultDeck('gatsby'));
  } catch (e) { R.push('  --   could not boot: ' + e.message); }

  const S = D.S;
  [3, 7, 14].forEach(n => {
    try { D.drawN('you', 20); } catch (e) {}
    S.you.hand = S.you.hand.slice(0, n);
    D.render();
    const hand = doc.querySelector('.hand');
    ok('--n is ' + n + ' with ' + n + ' cards in hand',
       hand && hand.style.getPropertyValue('--n') === String(n),
       hand ? 'got ' + hand.style.getPropertyValue('--n') : 'no .hand');
    ok('all ' + n + ' cards rendered',
       hand && hand.querySelectorAll('.hc').length === n,
       hand ? 'got ' + hand.querySelectorAll('.hc').length : '');
  });

  // an empty hand must not emit --n:0 and break the divide
  S.you.hand = [];
  D.render();
  const empty = doc.querySelector('.hand');
  ok('empty hand still renders without throwing', !!empty);
  ok('empty hand shows the placeholder',
     empty && /No cards/.test(empty.innerHTML));

  // ---- blast radius: the shared .hc box ----
  ok('card modal keeps its !important insulation',
     /\.hand-view \.hc\{[^}]*height:auto!important/.test(css),
     'modal must override height, or 4:5 will squash it');
  ok('modal overrides width with !important',
     /\.hand-view \.hc\{[^}]*width:min\([^)]*\)!important/.test(css));
  ok('modal neutralises the fan transform',
     /\.hand-view \.hc\{[^}]*transform:none!important/.test(css));

  // the modal reuses handCard, so it must still produce a card
  try {
    // the repeated drawN(20) above can drain deck+discard, so seed the hand
    // directly rather than relying on a draw succeeding
    if (!S.you.hand.length) S.you.hand = [{ cat:'abc', type:'BLOCK', power:2,
      q:'Test question', opts:['a','b','c','d'], ans:0, cid:'t1' }];
    S._handView = 0;
    D.render();
    const hv = doc.querySelector('.hand-view .hc');
    ok('card detail modal still renders a card', !!hv);
    S._handView = null; D.render();
  } catch (e) { ok('card detail modal still renders a card', false, e.message); }

  // pack overlay uses bare .hc; the sizing rules are scoped to .hand .hc
  ok('sizing is scoped to .hand, not bare .hc',
     !/^body\[data-screen="play"\] \.hc\{[^}]*var\(--card-w\)/m.test(css));

  // ---- shape ----
  ok('aspect ratio is 4:5', /--card-ar:0\.8/.test(css));
  ok('overlap is a fraction of card width, not fixed px',
     /--tuck-frac:0\.09/.test(css) && /var\(--card-w\) \* var\(--tuck-frac\)/.test(css));
  ok('question gains line room at the narrower width',
     /\.hand \.hc \.hc-q\{-webkit-line-clamp:6\}/.test(css));

  // ---- every breakpoint sets a card height ----
  const heights = css.match(/--card-h:\d+px/g) || [];
  ok('each breakpoint declares a card height', heights.length >= 4,
     'found ' + heights.join(', '));

  console.log(R.join('\n'));
  console.log('\n' + pass + ' passed / ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}, 2500);
