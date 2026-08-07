// mechanics.test.js — siphon and riposte, on a frozen board.
const {boot, idle, turn, attack} = require('./harness');

boot().then(async ({D, S, ok, done}) => {
  const A = () => S.you.team[S.you.activeIdx];
  const B = () => S.opp.team[S.opp.activeIdx];
  const charged = n => Array.from({length: n}, () => ({cat: 'abc', type: 'ATTACK', power: 1}));

  /* ---------------- SIPHON: tick, leech, expiry ---------------- */
  A().hp = 80; A().maxHp = 100; B().hp = 50; B().maxHp = 100;
  D.applySiphon(A(), B(), 'opp', {amt: 10, turns: 2, leech: 5});
  const yh0 = A().hp, oh0 = B().hp;

  await turn(D, 'opp');                                   // -> 'you', ticks your team
  ok('drains the victim on its own turn', yh0 - A().hp === 10, `-${yh0 - A().hp} HP`);
  ok('owner leeches half',                B().hp - oh0 === 5, `+${B().hp - oh0} HP`);
  ok('duration ticks down',               !A().status.siphon || A().status.siphon.turns === 1);

  const yh1 = A().hp;
  await turn(D, 'opp');
  ok('second tick lands',        yh1 - A().hp === 10, `-${yh1 - A().hp} HP`);
  ok('expires after 2 turns',    !A().status.siphon);

  const yh2 = A().hp;
  await turn(D, 'opp');
  ok('no drain once expired',    A().hp === yh2);

  /* ---------------- SIPHON: caps ---------------- */
  A().hp = 100; B().hp = 20;
  D.applySiphon(A(), B(), 'opp', {amt: 60, turns: 1, leech: 60});
  await turn(D, 'opp');
  ok('leech capped at 20 a turn', B().hp - 20 <= 20, `owner +${B().hp - 20}`);

  A().hp = 4; B().hp = 50;
  D.applySiphon(A(), B(), 'opp', {amt: 10, turns: 1, leech: 5});
  const ob = B().hp;
  await turn(D, 'opp');
  ok('leech never exceeds damage dealt', B().hp - ob <= 4, `dealt 4, owner +${B().hp - ob}`);

  /* ---------------- RIPOSTE: resource modes ---------------- */
  const setup = (mode, extra = {}) => {
    S.turn = 'you';
    const att = A(), def = B();
    att.hp = 100; def.hp = 100; att.status = {}; def.status = {};
    att._ripostedTurn = null;
    att.atkCharge = charged(4); att.blkCharge = charged(1);
    def.blk = {n: 'Gates', cost: 2, block: 50, label: '50/2', riposte: Object.assign({mode}, extra)};
    def.blkCharge = charged(2);
    return {att, def};
  };

  let {att} = setup('charge');
  S.you.hand = [{cat: 'bm', name: 'Truce', kind: 'SUPPORT', effect: 'truce', rarity: 'R'}];
  const n0 = att.atkCharge.length;
  await attack(D, 'you');
  ok('charge mode strips an Attack ABC', att.atkCharge.length < n0);

  ({att} = setup('hand'));
  S.you.hand = [{cat: 'bm', name: 'Truce', kind: 'SUPPORT', effect: 'truce', rarity: 'R'},
                {cat: 'abc', name: 'Q', type: 'ATTACK', power: 2}];
  const bm0 = S.you.hand.filter(c => c.cat === 'bm').length;
  await attack(D, 'you');
  const bm1 = S.you.hand.filter(c => c.cat === 'bm').length;
  ok('hand mode burns a Bookmark', bm1 < bm0, `${bm0} -> ${bm1}`);

  ({att} = setup('hand'));
  S.you.hand = [];
  await attack(D, 'you');
  ok('empty hand falls through safely', true);

  /* ---------------- RIPOSTE: arming ---------------- */
  let r = setup('hp', {dmg: 10});
  const ah0 = r.att.hp;
  await attack(D, 'you');
  ok('fires while the block is charged', ah0 - r.att.hp >= 10, `attacker -${ah0 - r.att.hp}`);

  r = setup('hp', {dmg: 10});
  r.def.blkCharge = charged(1);                      // under the block's cost of 2
  const ah1 = r.att.hp;
  await attack(D, 'you');
  ok('silent when under-charged', r.att.hp === ah1, `attacker -${ah1 - r.att.hp}`);

  r = setup('hp', {dmg: 10});
  await attack(D, 'you');
  const after1 = r.att.hp;
  r.att.atkCharge = charged(4); r.def.blkCharge = charged(2);
  await attack(D, 'you');
  ok('fires only once per attacker per turn', r.att.hp === after1, `2nd attack cost ${after1 - r.att.hp}`);

  done();
}).catch(e => { console.error('HARNESS ERROR:', e.message); process.exit(1); });
