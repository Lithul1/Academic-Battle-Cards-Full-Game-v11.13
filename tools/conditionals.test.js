// migrated onto the shared deterministic harness
const {boot, idle, turn, attack} = require('./harness');
boot().then(async ({w, D, S, ok, results, done}) => {
  const T = w.DATA.characters;
 
 const A=()=>S.you.team[S.you.activeIdx], B=()=>S.opp.team[S.opp.activeIdx];
 const cm=(rule,own,other,oc)=>w.ABC_DEBUG.condMatch? w.ABC_DEBUG.condMatch(rule,own,other,oc):null;

 // structural rewrites landed
 const sc=T.oz.find(c=>c.id==='scarecrow'), ww=T.oz.find(c=>c.id==='witchwest'), mo=T.othello.find(c=>c.id==='montano');
 ok('Scarecrow now keys off Burn', sc.blk.cond[0].test==='defenderHasStatus'&&sc.blk.cond[0].status==='burn');
 ok('Witch now keys off Spill on herself', ww.blk.cond[0].test==='selfHasStatus'&&ww.blk.cond[0].status==='spill');
 ok('Witch still self-KOs', ww.blk.cond[0].then.selfKO===true);
 ok('Montano uses a real status', !mo.blk.cond && mo.blk.inflictAtt==='glue');
 ok('no "disoriented" anywhere', !JSON.stringify(T).includes('disoriented'));
 // texts match behaviour
 ok('Scarecrow text names Burn', /Burn/.test(sc.blk.t));
 ok('Witch text names Spill', /Spill/.test(ww.blk.t));
 ok('Montano text names Glue', /Glue/.test(mo.blk.t));
 // tags exist for defenderHasTag
 ok('Othello characters carry tags', (T.othello.find(c=>c.id==='iago').tags||[]).length>0,
    JSON.stringify(T.othello.find(c=>c.id==='iago').tags));
 const br=T.othello.find(c=>c.id==='brabantio');
 ok('Brabantio targets tags that exist', br.atk.cond[0].tags.some(t=>
    Object.values(T).flat().some(c=>(c.tags||[]).map(x=>x.toLowerCase()).includes(t.toLowerCase()))),
    br.atk.cond[0].tags.join('/'));
 const mt=T.othello.find(c=>c.id==='montano');
 ok('Montano ATK Soldier tag exists', Object.values(T).flat().some(c=>(c.tags||[]).map(x=>x.toLowerCase()).includes('soldier')));
 // oz fieldContains targets exist in their own deck
 const need=[['jinjur','guard'],['flyingmonkey','witchwest'],['munchkin','dorothy'],['quadling','glinda'],['cowardlylion','dorothy']];
 let miss=[];
 for(const [who,tgt] of need) if(!T.oz.some(c=>c.id===tgt)) miss.push(who+'->'+tgt);
 ok('all Oz conditional targets exist in the deck', miss.length===0, miss.join(', '));
 done();
 console.log('\nREWRITTEN CARDS');
 [sc,ww,mo].forEach(c=>console.log(`  ${c.name}\n    ${c.blk.n} — ${c.blk.t}`));

}).catch(e => { console.error('HARNESS ERROR:', e.message); process.exit(1); });
