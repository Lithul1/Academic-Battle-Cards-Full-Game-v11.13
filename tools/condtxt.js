const {JSDOM}=require('jsdom'),fs=require('fs');
const w=new JSDOM(fs.readFileSync(require('path').join(__dirname,'..','dist','stub.html'),'utf8'),{runScripts:'dangerously',pretendToBeVisual:true,url:'https://example.org/'}).window;
setTimeout(()=>{
 const T=w.DATA.characters,R=[],ok=(n,c,x='')=>R.push((c?'  PASS  ':'  FAIL  ')+n+(x?'   '+x:''));
 let noExplain=[],n=0,names=new Set();
 for(const k in T)for(const c of T[k]){names.add(c.id);}
 for(const k in T)for(const c of T[k])for(const s of ['atk','blk']){
   const ab=c[s]; if(!ab.cond)continue; n++;
   const t=ab.t||'';
   // must describe a condition
   if(!/\b(while|once|against|if|when)\b/i.test(t)) noExplain.push(`${k}/${c.id}.${s}`);
 }
 ok('every conditional card explains its condition', noExplain.length===0, noExplain.join(', '));
 ok(`${n} conditional fields checked`, n===36, n+' (Montano lost his when it became inflictAtt)');
 // no dead targets left
 let dead=[];
 for(const k in T)for(const c of T[k])for(const s of ['atk','blk'])
   for(const r of (c[s].cond||[]))
     for(const i of (r.ids||(r.id?[r.id]:[]))) if(!names.has(i)) dead.push(`${c.id}.${s}->${i}`);
 ok('no conditional points at a missing character', dead.length===0, dead.join(', '));
 // text must not name a character who is not in the game
 let ghost=[];
 for(const k in T)for(const c of T[k])for(const s of ['atk','blk'])
   if(/stapleton/i.test(c[s].t||'')) ghost.push(c.id);
 ok('no ghost names in card text', ghost.length===0, ghost.join(', '));
 ok('roster intact', Object.values(T).reduce((a,d)=>a+d.length,0)===134);
 const f=R.filter(x=>x.includes('FAIL')).length;
 console.log(R.join('\n')); console.log(`\n${R.length-f} passed, ${f} failed`);
},2600);
setTimeout(()=>process.exit(0),9000);
