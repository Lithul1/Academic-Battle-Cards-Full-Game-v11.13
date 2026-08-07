const {JSDOM}=require('jsdom'),fs=require('fs');
const w=new JSDOM(fs.readFileSync(require('path').join(__dirname,'..','dist','stub.html'),'utf8'),{runScripts:'dangerously',pretendToBeVisual:true,url:'https://example.org/'}).window;
setTimeout(()=>{
 const H=w.STATUS_HELP, R=[], ok=(n,c,x='')=>R.push((c?'  PASS  ':'  FAIL  ')+n+(x?'   '+x:''));
 const D=w.ABC_DEBUG;
 console.log('CODE TABLE');
 const seen={};let dup=0,bad=0;
 for(const k in H){const h=H[k];
   console.log(`  ${k.padEnd(13)} ${h.ic.padEnd(4)} ${(h.tone||'-').padEnd(4)} ${h.n}`);
   if(!/^[A-Z]{2}$/.test(h.ic)){bad++;}
   if(seen[h.ic])dup++; seen[h.ic]=1;
   if(!h.t||!h.fix)bad++;}
 ok('all codes are two uppercase letters', bad===0);
 ok('no duplicate codes', dup===0);
 ok('15 statuses defined', Object.keys(H).length===15, Object.keys(H).length+' entries');
 const html=D.statusBubbles({status:{siphon:{amt:10},tear:true,highlight:true}});
 ok('badge emits tone class', /class="sb key"/.test(html)&&/class="sb neg"/.test(html), html.replace(/</g,'\n<').trim().split('\n').slice(1).join(' '));
 ok('siphon badge reads SI', /data-statushelp="siphon"[^>]*>SI</.test(html));
 // glyphs on cards
 const T=w.DATA.characters;
 let sg=0,rg=0;
 for(const k in T)for(const c of T[k]){
   if(c.atk&&c.atk.siphon&&/\uD83E\uDE78/.test(c.atk.t))sg++;
   if(c.blk&&c.blk.riposte&&/\uD83E\uDE83/.test(c.blk.t))rg++;}
 ok('10 cards show the blood glyph', sg===10, sg+'/10');
 ok('10 cards show the boomerang',   rg===10, rg+'/10');
 ok('roster intact', Object.values(T).reduce((n,d)=>n+d.length,0)===134);
 const f=R.filter(x=>x.includes('FAIL')).length;
 console.log('\n'+R.join('\n')); console.log(`\n${R.length-f} passed, ${f} failed`);
},2600);
setTimeout(()=>process.exit(0),9000);
