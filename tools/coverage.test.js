// coverage.test.js — the checks that catch dead mechanics and half-formatted text.
// Added after a regression test showed the suite passing a broken cond test and a
// stripped status icon.
const {boot} = require('./harness');

const ICON = {tear:'\u{1FAA2}', rip:'\u2702', glue:'\u{1FA79}', spill:'\u{1FADF}',
              burn:'\u{1F525}', smudge:'\u{1FAC6}', highlight:'\u2728',
              hardcover:'\u{1F4D5}', laminate:'\u{1F6E1}', marginnotes:'\u{1F4DD}'};
const NAME = {tear:'Tear', rip:'Rip', glue:'Glue', spill:'Spill', burn:'Burn',
              smudge:'Smudge', highlight:'Highlight', hardcover:'Hardcover',
              laminate:'Laminate', marginnotes:'Margin Notes'};

boot().then(async ({w, D, ok, done}) => {
  const T = w.DATA.characters;
  const every = fn => { const out = [];
    for (const k in T) for (const c of T[k]) for (const s of ['atk','blk']) fn(c[s], c, k, s, out);
    return out; };

  /* 1 — every cond test used in DATA must be implemented by condMatch */
  const impl = new Set();
  const srcOf = D.condMatch.toString();
  for (const m of srcOf.matchAll(/rule\.test\s*===\s*'([a-zA-Z]+)'/g)) impl.add(m[1]);
  const used = new Set();
  every(ab => (ab.cond || []).forEach(r => used.add(r.test)));
  const dead = [...used].filter(t => !impl.has(t));
  ok('every cond test is implemented by condMatch', dead.length === 0,
     dead.length ? `DEAD: ${dead.join(', ')}` : `${used.size} tests, all live`);

  /* 2 — a status named in card text must carry its icon, and vice versa */
  const halfFormatted = every((ab, c, k, s, out) => {
    const t = ab.t || '';
    for (const key in NAME) {
      const named = new RegExp(`\\b${NAME[key]}\\b`).test(t);
      const iconed = t.includes(ICON[key]);
      if (named !== iconed) out.push(`${k}/${c.id}.${s} ${NAME[key]} ${named ? 'named without icon' : 'icon without name'}`);
    }
  });
  ok('status names and icons always appear together', halfFormatted.length === 0,
     halfFormatted.slice(0, 4).join(' | '));

  /* 3 — every status a card inflicts is named in its text */
  const unnamed = every((ab, c, k, s, out) => {
    const inf = ab.inflict; if (!inf || ab.cond) return;
    for (const st of (Array.isArray(inf) ? inf : [inf])) {
      const n = NAME[String(st).toLowerCase()];
      if (n && !new RegExp(n, 'i').test(ab.t || '')) out.push(`${k}/${c.id}.${s}:${st}`);
    }
  });
  ok('every inflicted status is named in the text', unnamed.length === 0, unnamed.slice(0,4).join(', '));

  /* 4 — no conditional points at a character or tag that does not exist */
  const ids = new Set(), tags = new Set();
  for (const k in T) for (const c of T[k]) { ids.add(c.id); (c.tags||[]).forEach(t => tags.add(String(t).toLowerCase())); }
  const ghosts = every((ab, c, k, s, out) => (ab.cond || []).forEach(r => {
    for (const i of (r.ids || (r.id ? [r.id] : []))) if (!ids.has(i)) out.push(`${c.id}.${s} -> ${i}`);
    for (const g of (r.tags || [])) if (!tags.has(String(g).toLowerCase())) out.push(`${c.id}.${s} -> tag ${g}`);
  }));
  ok('no conditional targets a missing character or tag', ghosts.length === 0, ghosts.join(', '));

  /* 5 — every status the engine can apply has a code, a tone and help text */
  const H = w.STATUS_HELP;
  const badHelp = Object.entries(H).filter(([, h]) =>
    !/^[A-Z]{2}$/.test(h.ic || '') || !h.tone || !h.t || !h.fix).map(([k]) => k);
  ok('every status has a 2-letter code, tone and help', badHelp.length === 0, badHelp.join(', '));
  const codes = Object.values(H).map(h => h.ic);
  ok('no duplicate status codes', new Set(codes).size === codes.length);

  done();
}).catch(e => { console.error('HARNESS ERROR:', e.message); process.exit(1); });
