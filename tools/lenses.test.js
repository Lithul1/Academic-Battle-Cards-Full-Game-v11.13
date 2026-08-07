// migrated onto the shared deterministic harness
const {boot, idle, turn, attack} = require('./harness');
boot().then(async ({w, D, S, ok, results, done}) => {
  const T = w.DATA.characters;
  const P = S.you;
 const CR=Object.values(w.DATA.crits);
 const SET={postcolonial:p=>p.critTurn.correct=2, newhist:p=>{}, queer:p=>p.critTurn.queerMismatch=true,
  structuralism:p=>{p.critTurn.atk=p.critTurn.blk=p.critTurn.bm=true}, reader:p=>p.critTurn.readerStreak=2,
  biographical:p=>p.critTurn.bm=true, ecocrit:p=>p.critEver.survivedAt10=true, marxist:p=>p.critTurn.koCost1=true,
  formalism:p=>p.critTurn.koPlain=true, russian:p=>p.critTurn.koLowAtk=true, feminist:p=>p.critEver.blockedToZero=true,
  archetypal:p=>p.critEver.atkEqBlk=true, psycho:p=>p.critEver.oppWrongBlk=true,
  affective:p=>p.critEver.oppWrong2=true, deconstruct:p=>p.critEver.oppBmBlocked=true};
 let pass=0,fail=[];
 console.log('ALL 15 LENSES — can the thesis be met at all?');
 for(const c of CR){
   P.crit=c; P.critTurn={}; P.critEver={};
   const before=D.thesisMet('you').ok;
   if(c.fx==='newhist'){ const a=P.team[P.activeIdx]; a.atkCharge=[{},{},{}]; }
   else (SET[c.fx]||(()=>{}))(P);
   const after=D.thesisMet('you').ok;
   const okRow = !before && after;
   console.log(`  ${okRow?'PASS':'FAIL'}  ${c.name.padEnd(24)} ${c.fx}`);
   okRow?pass++:fail.push(c.fx);
   if(c.fx==='newhist'){ P.team[P.activeIdx].atkCharge=[]; }
 }
 console.log(`\n${pass}/15 lenses fulfillable` + (fail.length?`   still broken: ${fail.join(', ')}`:''));

}).catch(e => { console.error('HARNESS ERROR:', e.message); process.exit(1); });
