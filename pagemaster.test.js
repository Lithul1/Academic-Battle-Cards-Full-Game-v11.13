// pagemaster.test.js — the two-commander format's rules, against the live engine.
const {JSDOM} = require('jsdom'), fs = require('fs');
const w = new JSDOM(fs.readFileSync('/tmp/pm_stub.html','utf8'),
  {runScripts:'dangerously', pretendToBeVisual:true, url:'https://example.org/'}).window;

setTimeout(() => {
  let pass = 0, fail = 0;
  const ok = (t, c, note) => { c ? pass++ : fail++; console.log('  ' + (c ? 'PASS' : 'FAIL') + '  ' + t + (note ? '   ' + note : '')); };
  const PMx = w.ABC_PM, D = w.DATA, C = D.characters, AB = D.abcs, F = D.firsteds;
  const legal = PMx.pagemasterLegal;

  const build = (fe1, fe2) => {
    const bk = PMx.pmBooksOf(fe1, fe2), books = bk.books;
    const def = { d: books[0], books, pm: true, fe: [fe1, fe2], ch: [], ab: [], bm: [], cr: [] };
    if (!bk.mono) books.forEach(k => (C[k]||[]).slice(0, PMx.PM.minChPerBook).forEach(c => def.ch.push(c.id)));
    books.forEach(k => { for (const c of (C[k]||[])) { if (def.ch.length >= PMx.PM.ch) break; if (!def.ch.includes(c.id)) def.ch.push(c.id); } });
    books.forEach(k => { for (let i = 0; i < (AB[k]||[]).length; i++) { if (def.ab.length >= PMx.PM.ab) break; def.ab.push({ d: k, i }); } });
    for (let i = 0; i < PMx.PM.bm; i++) def.bm.push(i);
    for (let i = 0; i < PMx.PM.cr; i++) def.cr.push(i);
    return def;
  };

  let bad = [];
  for (let i = 0; i < F.length; i++) for (let j = i + 1; j < F.length; j++) {
    const e = legal(F[i].id, F[j].id, build(F[i].id, F[j].id));
    if (e.length) bad.push(`${F[i].deck}+${F[j].deck}: ${e[0]}`);
  }
  const pairs = F.length * (F.length - 1) / 2;
  ok('every commander pairing produces a legal deck', bad.length === 0, bad.slice(0,3).join(' | ') || `${pairs} pairings`);

  const a = F.find(f => f.deck === 'hamlet').id, b = F.find(f => f.deck === 'macbeth').id;
  const def = build(a, b);
  ok('a legal hybrid passes clean', legal(a, b, def).length === 0, legal(a,b,def).join('; '));
  ok('same commander twice is rejected', legal(a, a, def).some(e => /different cards/.test(e)));

  const short = JSON.parse(JSON.stringify(def)); short.ch.pop();
  ok('a short deck is rejected', legal(a, b, short).some(e => /characters 11/.test(e)));
  const dupBm = JSON.parse(JSON.stringify(def)); dupBm.bm[1] = dupBm.bm[0];
  ok('duplicate bookmarks are rejected', legal(a, b, dupBm).some(e => /one copy/.test(e)));
  const dupCh = JSON.parse(JSON.stringify(def)); dupCh.ch[1] = dupCh.ch[0];
  ok('duplicate characters are rejected', legal(a, b, dupCh).some(e => /duplicate characters/.test(e)));
  const oneBook = JSON.parse(JSON.stringify(def)); oneBook.ch = C['hamlet'].slice(0, 12).map(c => c.id);
  ok('fewer than 4 from a book is rejected', legal(a, b, oneBook).some(e => /need 4/.test(e)));
  const stray = JSON.parse(JSON.stringify(def)); stray.ab[0] = { d: 'oz', i: 0 };
  ok('a card from a third book is rejected', legal(a, b, stray).some(e => /outside your books/.test(e)));

  const mac = F.filter(f => f.deck === 'macbeth');
  ok('a mono-book deck is legal', legal(mac[0].id, mac[1].id, build(mac[0].id, mac[1].id)).length === 0);

  const rc = PMx.pmReturnCost;
  ok('1st return costs 1 attach', rc({ _pmReturns: 0 }) === 1);
  ok('2nd return costs 2 attaches', rc({ _pmReturns: 1 }) === 2);
  ok('there is no 3rd return', rc({ _pmReturns: 2 }) === null);
  ok('a commander that never fell costs 1', rc({}) === 1);

  const st = { hpScale: 1, benchSize: 2, maxAttaches: 2, maxDiscards: 2 };
  const p = PMx.newPlayer('You', def, st, true);
  ok('the two commanders start on the field', p.team.length === 2, `${p.team.length} on field`);
  ok('both are flagged as commanders', p.team.every(c => c._pmCmd));
  ok('the player is marked as Pagemaster', p._pm === true);
  ok('an Active exists from turn one', p._hasActive === true);
  const chInDeck = p.deck.filter(c => c.cat === 'char').length;
  ok('the 12 characters are in the deck', chInDeck === 12, `${chInDeck}`);
  ok('no commander was shuffled in', p.deck.filter(c => c.cat === 'char' && c.fe).length === 0);
  ok('the deck is 60 cards', p.deck.length === 60, `${p.deck.length}`);

  const plain = PMx.newPlayer('You', { d: 'hamlet', ch: C.hamlet.map(c => c.id), ab: [], bm: [], cr: [], fe: [a] }, st, true);
  ok('ordinary Drawn Mode is unchanged', plain.team.length === 0 && plain.deck.some(c => c.fe));

  /* hybrid characters must resolve across both books */
  const macChar = C.macbeth[0].id;
  ok('a Macbeth character resolves in a Hamlet-keyed deck', !!PMx.edResolveChar(def, macChar), macChar);

  console.log('\n  ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}, 3200);
