/* Behavioural checks for the 2026-08-23 fix pass (issues 6, 2, 5, 3).
   Run: node tests/fixpass.test.js                                        */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'dist', 'stub.html'), 'utf8');

let pass = 0, fail = 0;
const results = [];
function ok(name, cond, detail) {
  if (cond) { pass++; results.push('  ok   ' + name); }
  else { fail++; results.push('  FAIL ' + name + (detail ? '\n         ' + detail : '')); }
}

const dom = new JSDOM(HTML, {
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  url: 'https://example.org/'
});
const win = dom.window;

setTimeout(() => {
  const D = win.ABC_DEBUG;
  if (!D) { console.log('FATAL: ABC_DEBUG missing — game did not boot'); process.exit(1); }

  // A live battle gives us a real S.opp to hang the modal assertions on.
  // Test functions, not clicking — per the handoff.
  try {
    D.freeze();
    D.newGame({}, D.defaultDeck('hamlet'), D.defaultDeck('gatsby'));
  } catch (e) {
    results.push('  --   could not boot a battle: ' + e.message);
  }

  // ---------------------------------------------------------------- ISSUE 5
  // feImg must resolve a portrait for every First Edition, including the 27
  // that ship img:"" and inherit through base:[deck,char].
  {
    const fes = (win.DATA && win.DATA.firsteds) || [];
    ok('issue5: DATA.firsteds is populated', fes.length > 0, 'got ' + fes.length);

    const emptyImg = fes.filter(f => !f.img);
    ok('issue5: most FEs really do ship img:""', emptyImg.length >= 20,
       'only ' + emptyImg.length + ' had empty img');

    const unresolved = emptyImg
      .map(f => ({ id: f.id, r: D.feImg(f) }))
      .filter(x => !x.r || !x.r.img);
    ok('issue5: feImg resolves a portrait for every empty-img FE',
       unresolved.length === 0,
       'unresolved: ' + unresolved.map(x => x.id).join(', '));

    // The regression itself: reading .img raw would have lost these.
    ok('issue5: raw .img would have failed where feImg succeeds',
       emptyImg.length > 0 && unresolved.length === 0);
  }

  // ------------------------------------------------- ISSUE 5 (expansions)
  // Every expansion portrait must be a usable data: URI, and boosterPool
  // commanders must be wired with a portrait and a base to inherit from.
  {
    const EX = win.EXPANSIONS || {};
    let bare = [], unwired = [];
    Object.keys(EX).forEach(k => {
      const ex = EX[k];
      if (!ex || !ex.battle) return;
      Object.keys(ex.img || {}).forEach(id => {
        const v = ex.img[id];
        if (typeof v === 'string' && v && v.slice(0, 5) !== 'data:') bare.push(k + ':' + id);
      });
      (ex.battle.chars || []).forEach(c => {
        if (c.img && c.img.slice(0, 5) !== 'data:') bare.push(k + ':char:' + c.id);
      });
      ((ex.boosterPool && ex.boosterPool.commanders) || []).forEach(f => {
        const r = D.feImg(f);
        if (!r || !r.img) unwired.push(k + ':' + f.id);
      });
    });
    ok('issue5: no expansion portrait is left without a data: scheme',
       bare.length === 0, bare.slice(0, 8).join(', '));
    ok('issue5: boosterPool commanders resolve a portrait',
       unwired.length === 0, unwired.join(', '));

    // the two sets that were broken must now specifically work
    const sg = EX.sengekokujo, f77 = EX.frankenstein_2077;
    ok('issue5: sengekokujo portraits usable',
       !!(sg && sg.img && String(sg.img.macbeth || '').slice(0, 5) === 'data:'));
    ok('issue5: frankenstein_2077 portraits usable',
       !!(f77 && f77.img && String(f77.img.creature || '').slice(0, 5) === 'data:'));
  }

  // ---------------------------------------------------------------- ISSUE 2
  // The archive card must be the canonical preview, not the old .char token,
  // and must not contain the hp/220 meter that read as "damaged".
  {
    const E = win.EXPANSIONS && win.EXPANSIONS.modern_hamlet;
    ok('issue2: modern_hamlet expansion present', !!E);

    if (E) {
      const html = D.mhCardFull('gertrude');
      ok('issue2: mhCardFull returns markup', !!html && html.length > 50);
      ok('issue2: uses canonical pv-card preview',
         html.indexOf('pv-card pvchar') >= 0, html.slice(0, 120));
      ok('issue2: tagged ed-pv', html.indexOf('ed-pv') >= 0);
      ok('issue2: no fractional HP meter left',
         html.indexOf('pc-hp') < 0 && html.indexOf('<i style="width:') < 0);
      ok('issue2: shows max HP as a figure', /120\s*HP/.test(html), html.slice(0, 400));
      ok('issue2: carries a portrait, not a monogram',
         html.indexOf('<img') >= 0 && html.indexOf('pvmono') < 0);
      // battle.chars carry flavour text the roster stubs omit
      ok('issue2: includes move flavour text',
         html.indexOf('pv-mv-txt') >= 0 && /Torn between two logos|boardroom guard/.test(html),
         'no .t text found');

      // expCardFull is not exported, so drive the real dispatch path:
      // handleScrim('expcard:<key>:<id>') -> showPreview(expCardFull(...)),
      // which writes into #cardPreview. Every collectable expansion character
      // must come back as a real preview carrying a portrait.
      const EX = win.EXPANSIONS || {};
      const doc0 = win.document;
      let broken = [];
      // unlock everything so the ownership gate doesn't short-circuit to a toast
      const allCids = [];
      Object.keys(EX).forEach(k => {
        const ex = EX[k];
        if (ex && ex.battle) ['chars', 'abcs', 'bookmarks', 'commanders'].forEach(kk => {
          (ex.battle[kk] || []).forEach(o => { if (o.cid) allCids.push(o.cid); });
        });
      });
      D.META.editionCards = allCids;

      Object.keys(EX).forEach(k => {
        const ex = EX[k];
        if (!ex || !ex.battle || !ex.battle.chars) return;
        ex.battle.chars.forEach(c => {
          const node = doc0.getElementById('cardPreview');
          if (node) node.innerHTML = '';
          try { D.handleScrim('expcard:' + k + ':' + c.id); }
          catch (e) { broken.push(k + ':' + c.id + ' threw ' + e.message); return; }
          const n = doc0.getElementById('cardPreview');
          const h = n ? n.innerHTML : '';
          if (!h || h.indexOf('pv-card') < 0) broken.push(k + ':' + c.id + ' not a pv-card');
          else if (h.indexOf('<img') < 0) broken.push(k + ':' + c.id + ' no portrait');
          else if (h.indexOf('pc-hp') >= 0) broken.push(k + ':' + c.id + ' still has HP meter');
        });
      });
      ok('issue2: every expansion character renders as a preview with a portrait',
         broken.length === 0, broken.slice(0, 6).join('; '));

      // static: the archive really does delegate now, and the old meter is gone
      ok('issue2: expCardFull delegates to buildCharPreview',
         /function expCardFull[\s\S]{0,600}?buildCharPreview\(edPreviewChar/.test(HTML));
      ok('issue2: hp/220 meter no longer appears in either archive builder',
         HTML.indexOf('Math.round(c.hp/220*100)') < 0);
    }
  }

  // ---------------------------------------------------------------- ISSUE 3
  // The Over-lord must expose move text and a behaviour block, and must keep
  // them after overlordTurn() rebuilds boss.atk.
  {
    // SUPER_BOSS is a const inside the game IIFE, so assert on source, then
    // prove it took effect through the constructed boss below.
    ok('issue3: SUPER_BOSS declares a passive', /SUPER_BOSS = \{[\s\S]{0,1400}?passive:\{/.test(HTML));
    ok('issue3: SUPER_BOSS declares atkText', /SUPER_BOSS = \{[\s\S]{0,2200}?atkText:/.test(HTML));
    ok('issue3: SUPER_BOSS declares blkText', /SUPER_BOSS = \{[\s\S]{0,2600}?blkText:/.test(HTML));
    ok('issue3: SUPER_BOSS declares disorientText', /SUPER_BOSS = \{[\s\S]{0,2600}?disorientText:/.test(HTML));
    // the reassignment in overlordTurn must not drop the text again
    ok('issue3: overlordTurn preserves move text on reassignment',
       /boss\.atk=\{[\s\S]{0,320}?SUPER_BOSS\.atkText/.test(HTML));

    let boss = null;
    try {
      const p = D.scrimOppPlayer({ superboss: true });
      boss = p && p.team && p.team[0];
    } catch (e) {
      results.push('         scrimOppPlayer threw: ' + e.message);
    }
    ok('issue3: superboss constructs', !!boss);
    if (boss) {
      ok('issue3: boss is flagged _overlord', !!boss._overlord);
      ok('issue3: constructed boss has passive text',
         !!(boss.passive && boss.passive.text));
      ok('issue3: constructed boss atk has flavour text',
         !!(boss.atk && boss.atk.t && boss.atk.t.length > 20));
      ok('issue3: constructed boss blk has flavour text',
         !!(boss.blk && boss.blk.t && boss.blk.t.length > 20));

      // benchInfoModal must now render the behaviour block for a non-FE boss
      const S = D.S;
      if (S && S.opp) {
        // graft the boss onto the live opp side so the modal can find it
        const prevTeam = S.opp.team;
        S.opp.team = [boss];
        boss.uid = boss.uid || 'overlord_test';
        D.S._benchView = { side: 'opp', uid: boss.uid };
        let modal = '';
        try { modal = D.benchInfoModalSrc(); } catch (e) { modal = 'THREW ' + e.message; }
        ok('issue3: benchInfoModal renders for the boss',
           modal.indexOf('bench-view') >= 0, modal.slice(0, 160));
        ok('issue3: modal shows the behaviour block',
           modal.indexOf('bv-passive') >= 0 && modal.indexOf('Total Saturation') >= 0,
           'bv-passive missing');
        ok('issue3: behaviour block is labelled Behaviour, not Passive',
           modal.indexOf('Behaviour') >= 0);
        ok('issue3: modal shows attack text',
           modal.indexOf('wall of light') >= 0, 'atk .t not rendered');
        ok('issue3: modal shows block text',
           modal.indexOf('gathers the signal') >= 0, 'blk .t not rendered');
        S.opp.team = prevTeam;
        D.S._benchView = null;
      } else {
        results.push('  --   issue3: no live S.opp to graft onto, modal check skipped');
      }
    }

    // an ordinary FE must still show "Passive", not "Behaviour"
    if (D.makeChar) {
      const fe = (win.DATA.firsteds || []).find(f => f.passive && f.passive.text);
      if (fe) {
        const c = D.makeChar(fe, 1.0);
        const S = D.S;
        if (S && S.opp) {
          const prev = S.opp.team;
          S.opp.team = [c];
          D.S._benchView = { side: 'opp', uid: c.uid };
          let m = '';
          try { m = D.benchInfoModalSrc(); } catch (e) { m = 'THREW ' + e.message; }
          ok('issue3: FE still labelled Passive (no regression)',
             m.indexOf('Passive') >= 0 && m.indexOf('Behaviour') < 0);
          S.opp.team = prev;
          D.S._benchView = null;
        }
      }
    }
  }

  // ---------------------------------------------------------------- ISSUE 6
  // The face-down tile must emit the real card back, not the "A" placeholder.
  {
    const doc = win.document;
    const css = Array.from(doc.querySelectorAll('style')).map(s => s.textContent).join('\n');
    ok('issue6: dm-fd-in is a positioning context',
       /\.dm-fd-in\{[^}]*position:relative/.test(css));
    ok('issue6: face-down card back art is sized to fill',
       /\.hc\.dm-fd \.cb-img\{/.test(css));
    ok('issue6: medallion fallback is scaled for the small tile',
       /\.hc\.dm-fd \.cb-medallion\{/.test(css));

    // source-level: the placeholder span is gone, cardBackHTML() is called
    const srcHtml = HTML;
    ok('issue6: "A" placeholder markup removed',
       srcHtml.indexOf('<div class="dm-fd-in"><span>A</span></div>') < 0);
    ok('issue6: face-down now calls cardBackHTML()',
       srcHtml.indexOf('<div class="dm-fd-in">${cardBackHTML()}</div>') >= 0);
  }

  console.log(results.join('\n'));
  console.log('\n' + pass + ' passed / ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}, 2500);
