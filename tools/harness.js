// harness.js — deterministic setup for every ABC engine test.
//
//   const {boot, until, idle, report} = require('./harness');
//   boot().then(async ({w,D,S,ok,done}) => { ...; done(); });
//
// Why this exists: the game runs a 45-second turn clock and schedules AI turns
// asynchronously. Fixed sleeps race both, which produced false failures roughly
// one run in four. boot() freezes the clock and the AI before handing back, and
// idle() waits on the engine's own busy flag instead of guessing at a duration.

const {JSDOM} = require('jsdom');
const fs = require('fs');

const STUB = require('path').join(__dirname, '..', 'dist', 'stub.html');

function until(fn, ms = 15000, label = 'condition') {
  return new Promise((res, rej) => {
    const t0 = Date.now();
    (function poll() {
      let v = false;
      try { v = fn(); } catch (e) { /* not ready yet */ }
      if (v) return res(v);
      if (Date.now() - t0 > ms) return rej(new Error(`timed out waiting for ${label}`));
      setTimeout(poll, 25);
    })();
  });
}

async function boot(opts = {}) {
  const html = fs.readFileSync(opts.file || STUB, 'utf8');
  const dom = new JSDOM(html, {
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    url: 'https://example.org/',
    virtualConsole: opts.quiet === false ? undefined : new (require('jsdom').VirtualConsole)()
  });
  const w = dom.window;

  await until(() => w.ABC_DEBUG, 15000, 'ABC_DEBUG');
  const D = w.ABC_DEBUG;

  // stop the AI before any battle exists, so it can never take a turn mid-test
  D.noAI = true;

  const btn = re => [...w.document.querySelectorAll('button,.btn,[onclick]')]
    .find(x => new RegExp(re, 'i').test(x.textContent || ''));

  await until(() => btn('Quickplay'), 15000, 'menu');
  btn('Quickplay').click();
  await until(() => btn('Normal'), 15000, 'difficulty list');
  btn('Normal').click();
  await until(() => D.S, 20000, 'battle state');

  D.freeze();                       // clock off, AI off, turnTimer 0
  const S = D.S;
  S.settings = S.settings || {};
  S.settings.autoBlock = true;

  await idle(D);

  const results = [];
  const ok = (name, cond, extra = '') =>
    results.push((cond ? '  PASS  ' : '  FAIL  ') + name + (extra ? '   ' + extra : ''));

  const done = () => {
    const failed = results.filter(r => r.includes('FAIL')).length;
    console.log(results.join('\n'));
    console.log(`\n${results.length - failed} passed, ${failed} failed`);
    process.exit(failed ? 1 : 0);
  };

  return {w, D, S, btn, ok, results, done};
}

// wait for the engine to stop working rather than sleeping a fixed amount
async function idle(D, ms = 12000) {
  await until(() => D.busy === false, ms, 'engine idle');
  await new Promise(r => setTimeout(r, 20));   // let a queued microtask settle
}

// run a turn boundary and wait for it to fully resolve
async function turn(D, side) {
  if (side) D.S.turn = side;
  D.endTurn();
  await idle(D);
}

// run an attack and wait for it to fully resolve
async function attack(D, side, kind = 'atk') {
  D.performAttack(side, kind);
  await idle(D);
}

module.exports = {boot, until, idle, turn, attack};
