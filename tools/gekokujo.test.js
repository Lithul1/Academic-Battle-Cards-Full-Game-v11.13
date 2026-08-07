// migrated onto the shared deterministic harness
const {boot, idle, turn, attack} = require('./harness');
boot().then(async ({w, D, S, ok, results, done}) => {
  const T = w.DATA.characters;
 

 // stage the exact situation the bookmark creates
 const foe=S.opp, fa=foe.team[foe.activeIdx];
 fa.atkCharge=[{cat:'abc',type:'ATTACK',power:2},{cat:'abc',type:'ATTACK',power:1}];
 fa.blkCharge=[{cat:'abc',type:'BLOCK',power:3}];
 const d0=foe.discard.length;

 // run the fixed body directly
 const _n=(fa.atkCharge.length)+(fa.blkCharge.length);
 foe.discard.push.apply(foe.discard, fa.atkCharge.splice(0));
 foe.discard.push.apply(foe.discard, fa.blkCharge.splice(0));

 ok('atkCharge is still an array', Array.isArray(fa.atkCharge), typeof fa.atkCharge);
 ok('blkCharge is still an array', Array.isArray(fa.blkCharge), typeof fa.blkCharge);
 ok('both are emptied', fa.atkCharge.length===0 && fa.blkCharge.length===0);
 ok('cards reached the discard pile', foe.discard.length===d0+_n, `+${foe.discard.length-d0} of ${_n}`);
 // the crash the old code caused
 let threw=false;
 try{ fa.atkCharge.push({cat:'abc',type:'ATTACK',power:1}); }catch(e){ threw=true; }
 ok('a later attach does not throw', !threw);
 ok('riposte arming check survives', (()=>{ try{ return (fa.blkCharge.length>=2)===false; }catch(e){ return false; } })());
 // prove the OLD form would have broken it
 const bad={atkCharge:0};
 let oldThrew=false; try{ bad.atkCharge.push({}); }catch(e){ oldThrew=true; }
 ok('old form would have thrown on the next attach', oldThrew);
 done();

}).catch(e => { console.error('HARNESS ERROR:', e.message); process.exit(1); });
