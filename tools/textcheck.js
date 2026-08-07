const {JSDOM}=require('jsdom'),fs=require('fs');
const w=new JSDOM(fs.readFileSync(require('path').join(__dirname,'..','dist','stub.html'),'utf8'),{runScripts:'dangerously',pretendToBeVisual:true,url:'https://example.org/'}).window;
setTimeout(()=>{
 const T=w.DATA.characters,R=[],ok=(n,c,x='')=>R.push((c?'  PASS  ':'  FAIL  ')+n+(x?'   '+x:''));
 console.log('OTHELLO');
 T.othello.forEach(c=>console.log(`  ${c.name.padEnd(19)} ATK ${c.atk.n}\n${' '.repeat(22)}${c.atk.t}\n${' '.repeat(22)}BLK ${c.blk.n}\n${' '.repeat(22)}${c.blk.t}`));
 const SCIFI=/plasma|laser|telemetry|holograph|thruster|drone|cyber|orbital|neon|beacon|firewall|data-log|energy|grid|credit chit|starship|protocol|micro-woven|kinetic|stasis/i;
 let sf=[];
 T.othello.forEach(c=>['atk','blk'].forEach(s=>{if(SCIFI.test(c[s].n+' '+c[s].t))sf.push(c.id+'/'+s)}));
 ok('no sci-fi vocabulary left in Othello', sf.length===0, sf.join(', '));
 // every inflicting card names its status
 const NM={tear:'Tear',rip:'Rip',glue:'Glue',spill:'Spill',burn:'Burn',smudge:'Smudge'};
 let unnamed=[];
 for(const k in T)for(const c of T[k])for(const s of ['atk','blk']){
   const ab=c[s],inf=ab.inflict; if(!inf||ab.cond)continue;
   const arr=Array.isArray(inf)?inf:[inf];
   for(const st of arr){const n=NM[String(st).toLowerCase()]; if(n&&!new RegExp(n,'i').test(ab.t||''))unnamed.push(`${k}/${c.id}.${s}:${st}`);}
 }
 ok('every inflicting card names its status', unnamed.length===0, unnamed.slice(0,5).join(', '));
 let empty=[],n=0;
 for(const k in T)for(const c of T[k]){n++;for(const s of ['atk','blk'])if(!c[s].t||!c[s].t.trim())empty.push(k+'/'+c.id+'.'+s);}
 ok('no empty ability text', empty.length===0, empty.join(', '));
 ok('roster intact', n===134, n+' characters');
 // labels still consistent
 let bad=0;
 for(const k in T)for(const c of T[k])for(const s of ['atk','blk']){const m=c[s];if(!m.label)continue;
   const v=(s==='atk')?m.dmg:m.block,L=String(m.label).match(/^(\d+|X)/);
   if(v!=null&&L&&L[1]!=='X'&&Number(L[1])!==v)bad++;}
 ok('values still match labels', bad===0, bad+' mismatches');
 const f=R.filter(x=>x.includes('FAIL')).length;
 console.log('\n'+R.join('\n')); console.log(`\n${R.length-f} passed, ${f} failed`);
},2600);
setTimeout(()=>process.exit(0),9000);
