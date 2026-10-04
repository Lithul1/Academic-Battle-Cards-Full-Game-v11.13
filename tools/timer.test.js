// timer.test.js — the turn clock keeps pressure on during questions.
//   * it keeps counting (and stays visible) while a question is open
//   * running out mid-question scores the question wrong, then ends the turn
//   * Tune > Timer position: middle (board), top left, top right
// The harness freezes the clock; these tests drive tickTurnTimer by hand.
const {boot, idle} = require('./harness');
boot().then(async ({w, D, ok, done}) => {
  const S = () => D.S, doc = w.document;
  const Q = (q, ans) => ({ q, opts: ['A one', 'B two', 'C three', 'D four'], ans });
  let n = 0;
  const abc = () => Object.assign({ cat: 'abc', type: 'ATTACK', power: 1, cid: 'tt' + (++n) }, Q('Test question?', 2));

  // a clean "your turn, mid-strategize" board with a known card in hand
  async function fresh(timeLeft = 30) {
    await idle(D);
    const s = S();
    s.over = false; s.turn = 'you'; s.phase = 'strategize';
    s.pending = null; s._ip = null; s._af = null; s._actGate = null; s._mg = null;
    s._settings = false; s.viewPile = null; s._bossReveal = null;
    s.settings.turnTimer = 30; s._timeLeft = timeLeft; s.settings.timerPos = 'middle';
    s.you.attachesLeft = 2;
    const card = abc();
    s.you.hand.unshift(card, abc(), abc());   // spare cards, so a retry could be offered
    D.busy = false; D.render();
    return card;
  }
  const inHand = cid => S().you.hand.some(c => c.cid === cid);
  const inDiscard = cid => S().you.discard.some(c => c.cid === cid);
  const lastLog = () => S().log.slice(0, 6).join(' | ');   // the log is newest-first
  const clocks = () => doc.querySelectorAll('#turnclock').length;
  const boardClock = () => !!doc.querySelector('.midline #turnclock');
  const floatClock = pos => !!doc.querySelector('.turnbar-float.pos-' + pos + ' #turnclock');

  // ---------- the clock runs, and shows, during a question ----------
  let card = await fresh(30);
  D.openTrivia(card, 0, null);
  ok('a question is open (and the engine is busy)', D.questionOpen() && D.busy === true);
  D.tickTurnTimer();
  ok('the clock keeps counting during a question', S()._timeLeft === 29, S()._timeLeft + 's');
  ok('Middle: the bar floats over the question overlay', floatClock('top') && !boardClock());
  ok('exactly one turn bar on screen', clocks() === 1, clocks() + '');
  D.answerTrivia(card.ans);                        // tidy up: answer it correctly
  await idle(D);

  // ---------- pauses that are NOT questions still hold ----------
  await fresh(30);
  S()._settings = true; D.tickTurnTimer();
  ok('the settings menu still pauses the clock', S()._timeLeft === 30, S()._timeLeft + 's');
  S()._settings = false; D.busy = true; D.tickTurnTimer();
  ok('a picker / animation (busy, no question) still pauses it', S()._timeLeft === 30, S()._timeLeft + 's');
  D.busy = false;
  // opening Tune mid-question must not become a free pause for looking it up
  card = await fresh(30);
  D.openTrivia(card, 0, null); S()._settings = true; D.tickTurnTimer();
  ok('Tune opened mid-question does not pause it', S()._timeLeft === 29, S()._timeLeft + 's');
  S()._settings = false; D.answerTrivia(card.ans); await idle(D);

  // ---------- time runs out on the card question ----------
  card = await fresh(1);
  let charged = D.active(S().you).atkCharge.length;
  D.openTrivia(card, 0, null);
  D.tickTurnTimer();
  ok('time out: the question is closed', !D.questionOpen());
  ok('time out: the card is discarded, as a wrong answer', !inHand(card.cid) && inDiscard(card.cid));
  ok('time out: nothing was charged', D.active(S().you).atkCharge.length === charged);
  ok('time out: no retry offered', !S()._ip);
  ok('time out: the turn passes to the opponent', S().turn === 'opp', S().turn);
  ok('time out: the log says the answer counted as wrong', /counts as wrong/.test(lastLog()), lastLog());
  ok('time out: engine is not left busy', D.busy === false || S().turn === 'opp');

  // ---------- time runs out on the Iterum Probare retry offer ----------
  card = await fresh(1);
  D.openTrivia(card, 0, null);
  D.answerTrivia((card.ans + 1) % 4);              // wrong -> retry offer
  ok('a wrong answer opens the retry offer', !!S()._ip && D.questionOpen());
  D.tickTurnTimer();
  ok('retry offer timed out: declined, card discarded', !S()._ip && !inHand(card.cid) && inDiscard(card.cid));
  ok('retry offer timed out: turn passes', S().turn === 'opp');

  // ---------- time runs out on the Affective Fallacy bonus question ----------
  await fresh(1);
  let act = D.active(S().you); act.hp = act.maxHp;
  S()._af = Object.assign({ stage: 'ask' }, Q('Bonus?', 1));
  D.render(); D.tickTurnTimer();
  ok('Affective question timed out: scored wrong (Active takes 10)', !S()._af && act.hp === act.maxHp - 10, act.hp + '/' + act.maxHp);
  ok('Affective question timed out: turn passes', S().turn === 'opp');
  await fresh(1);
  act = D.active(S().you); act.hp = act.maxHp;
  S()._af = Object.assign({ stage: 'offer' }, Q('Bonus?', 1));
  D.tickTurnTimer();
  ok('Affective offer timed out: declined, no penalty', !S()._af && act.hp === act.maxHp, act.hp + '/' + act.maxHp);

  // ---------- time runs out on the Act III climax ----------
  await fresh(1);
  act = D.active(S().you); delete act._gateSpent;
  S()._actGate = { cid: 'gate', uid: act.uid, q: Object.assign({ tag: 'plot' }, Q('Climax?', 3)), picked: null };
  D.busy = true; D.render(); D.tickTurnTimer();
  ok('climax timed out: gate closed and spent for the turn', !S()._actGate && act._gateSpent != null);
  ok('climax timed out: turn passes', S().turn === 'opp');

  // ---------- time runs out mid-Marginalia ----------
  await fresh(1);
  const attaches = S().you.attachesLeft;
  S()._mg = { idx: 0, card: abc(), need: 2, step: 0, qs: [Q('One?', 0), Q('Two?', 1)] };
  S().pending = { card: S()._mg.qs[0], handIdx: -1, target: null, _mg: true };
  D.busy = true; D.tickTurnTimer();
  ok('Marginalia timed out: scored wrong (attach spent)', !S()._mg && S().you.attachesLeft === attaches - 1,
     S().you.attachesLeft + ' attaches');

  // ---------- Tune > Timer position ----------
  await fresh(30);
  ok('Middle (default): the bar sits in the board', boardClock() && clocks() === 1);
  S().settings.timerPos = 'topleft'; D.render();
  ok('Top left: one floating bar, top left', floatClock('topleft') && !boardClock() && clocks() === 1);
  S().settings.timerPos = 'topright'; D.render();
  ok('Top right: one floating bar, top right', floatClock('topright') && !boardClock() && clocks() === 1);
  card = abc(); S().you.hand.unshift(card); D.openTrivia(card, 0, null);
  ok('Top right stays top right during a question', floatClock('topright') && clocks() === 1);
  D.answerTrivia(card.ans); await idle(D);
  S().turn = 'opp'; D.render();
  ok("no bar on the opponent's turn", clocks() === 0 && D.turnBarWhere() === null);

  // the option itself, through the real settings panel
  await fresh(30);
  S()._settings = true; D.render();
  const sel = doc.querySelector('select[data-set="timerPos"]');
  ok('settings panel offers Timer position', !!sel && sel.options.length === 3,
     sel ? [...sel.options].map(o => o.value).join(',') : 'missing');
  if (sel) { sel.value = 'topleft'; sel.dispatchEvent(new w.Event('input', { bubbles: true })); }
  ok('choosing Top left updates the game setting', S().settings.timerPos === 'topleft', S().settings.timerPos);
  ok('the default is Middle', D.DEFAULTS.timerPos === 'middle');

  done();
}).catch(e => { console.error('HARNESS ERROR:', e.message); process.exit(1); });
