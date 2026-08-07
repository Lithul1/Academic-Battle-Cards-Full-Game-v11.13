const fs=require('fs'), vm=require('vm');
const s=fs.readFileSync(process.argv[2],'utf8');
const re=/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi;
let m,i=0,ok=0,bad=0;
while((m=re.exec(s))){ i++;
  try{ new vm.Script(m[1],{filename:`block${i}`}); ok++; }
  catch(e){ bad++; console.log(`  block ${i} FAIL: ${e.message}`); }
}
console.log(`${ok}/${i} script blocks OK${bad?`, ${bad} FAILED`:''}`);
process.exit(bad?1:0);
