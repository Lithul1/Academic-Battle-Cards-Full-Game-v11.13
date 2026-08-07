const {JSDOM}=require('jsdom'),fs=require('fs');
const w=new JSDOM(fs.readFileSync(require('path').join(__dirname,'..','dist','stub.html'),'utf8'),{runScripts:'dangerously',pretendToBeVisual:true,url:'https://example.org/'}).window;
setTimeout(()=>{
 const T=w.DATA.characters,R=[],ok=(n,c,x='')=>R.push((c?'  PASS  ':'  FAIL  ')+n+(x?'   '+x:''));
 let broken=[],jam=[],n=0;
 const JAM=/(Highlight|Laminate|Hardcover|Smudge|Spill|Glue|Burn|Tear|Rip|Pierce|Siphon|Riposte)(is|are|until|before|after|on|to|from|and|or|the|this|when|while|next|your|instead|has)\b/;
 for(const k in T)for(const c of T[k])for(const s of ['atk','blk']){
   const t=c[s].t||''; n++;
   if(/U\+?000[0-9A-F]|\\u[0-9a-f]{4}|\\U/.test(t)) broken.push(`${k}/${c.id}.${s}`);
   if(JAM.test(t)) jam.push(`${k}/${c.id}.${s}`);
 }
 ok('no broken escape sequences in card text', broken.length===0, broken.join(', '));
 ok('no missing-space typos', jam.length===0, jam.join(', '));
 ok(`${n} ability texts scanned`, n===268, n+'');
 // every mechanic-bearing card must say something mechanical
 const MECH=/(Inflict|Grant|Gain|Clear|Prevent|Heal|Draw|Block|Negat|Discard|Deal|\+\d|Strikes|Ignores|Takes|Caps|Force|Remove|Return|Switch|Cannot|Costs|Riposte|Siphon|Halves|Leaves|All allies|reduce)/i;
 let silent=[];
 for(const k in T)for(const c of T[k])for(const s of ['atk','blk']){
   const ab=c[s], mech=Object.keys(ab).filter(x=>!['n','t','cost','dmg','block','label'].includes(x));
   if(mech.length && !MECH.test(ab.t||'')) silent.push(`${k}/${c.id}.${s}`);
 }
 ok('every card with mechanics describes them', silent.length===0, silent.join(', '));
 const f=R.filter(x=>x.includes('FAIL')).length;
 console.log(R.join('\n')); console.log(`\n${R.length-f} passed, ${f} failed`);
},2600);
setTimeout(()=>process.exit(0),9000);
