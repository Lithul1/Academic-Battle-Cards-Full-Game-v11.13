/* Validate a BUILT single-file HTML.
 *   node tools/validate.js --quick <file>   compile every <script> + boot the Main Menu
 *   node tools/validate.js --full  <file>   + difficulty bg, a battle, and the scrim map
 * Requires: npm i jsdom   (only dependency)
 */
const fs = require('fs');
const path = require('path');
const mode = process.argv.includes('--full') ? 'full' : 'quick';
const file = process.argv.find((a,i)=> i>=2 && !a.startsWith('--')) ||
             path.join(__dirname, '..', 'dist', 'academic_battle_cards.html');
const html = fs.readFileSync(file, 'utf8');
let pass=0, fail=0;
const ok=(c,m)=>{ (c?pass++:fail++); console.log(`  ${c?'PASS':'FAIL'}  ${m}`); };

// 1) every <script> block must compile
const vm = require('vm');
let i=0, bad=0;
for (const m of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)) {
  i++; if(!m[1].trim()) continue;
  try { new vm.Script(m[1], {filename:`block${i}`}); }
  catch(e){ bad++; console.log(`  FAIL  script block ${i}: ${e.message}`); }
}
ok(bad===0, `all ${i} script blocks compile`);

// 2) headless boot
let JSDOM;
try { ({JSDOM} = require('jsdom')); }
catch(e){ console.log('\n  (jsdom not installed: run `npm i jsdom`) — skipped boot checks'); finish(); }

const dom = new JSDOM(html, { runScripts:'dangerously', pretendToBeVisual:true, url:'https://example.org/' });
const { window } = dom;
setTimeout(()=>{
  try {
    const doc=window.document, body=doc.body, D=window.ABC_DEBUG;
    const game=()=>doc.querySelector('#game').innerHTML;
    ok(!!D, 'ABC_DEBUG present (engine booted)');
    ok(body.getAttribute('data-screen')==='menu' && game().length>200, 'Main Menu renders');

    if (mode==='full') {
      D.APP.mode='quick'; D.APP.screen='difficulty'; D.render();
      ok(body.getAttribute('data-menuscreen')==='difficulty', 'quick/custom bg hook (data-menuscreen)');
      D.APP.screen='menu'; D.render();
      D.APP.mode='custom'; D.APP.difficulty='honorroll'; D.APP.youDeck='gatsby'; D.APP.oppDeck='random'; D.APP.customDeck=null;
      let bErr=false; try{ D.startBattle(); }catch(e){ bErr=true; console.log('   battle:',e.message); }
      ok(!bErr && D.APP.screen==='play', 'battle starts');
      let cyc=false; try{ for(let k=0;k<4;k++){ D.doDraw&&D.doDraw('you'); D.endTurn&&D.endTurn(); } }catch(e){ cyc=true; }
      ok(!cyc, 'turn cycle runs');
      D.APP.screen='menu'; D.render();
      let sErr=false; try{ D.scrimOpen(); D.handleScrim('new'); D.handleScrim('kit:gothic'); }catch(e){ sErr=true; console.log('   scrim:',e.message); }
      ok(!sErr && D.SCRIM.view==='map', 'scrimmage map renders');
      ok(game().includes('MAP GUIDE') && (game().match(/class="glg"/g)||[]).length===6, 'notebook legend (6 entries)');
    }
  } catch(e){ fail++; console.log('  FAIL  boot threw:', e.message); }
  finish();
}, mode==='full'?500:300);

function finish(){
  console.log(`\n==== ${mode.toUpperCase()}: ${pass} passed, ${fail} failed ====`);
  process.exit(fail?1:0);
}
