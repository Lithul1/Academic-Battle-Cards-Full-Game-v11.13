#!/usr/bin/env python3
"""
fix_catalog_v2.py — catalog fixes after the first round of testing.

1. Deck builder exit: every open deck now has Done (save and return to My Decks),
   Discard changes / Cancel new deck (puts the deck back the way it was when you
   opened it, or removes a deck you just started) and Delete deck.
2. Printing: the catalog now saves a print-ready PDF instead of using the
   browser's print dialog, which added its own margins and pushed the cards off
   the top of the page. Cards are exactly 2.5 x 3.5 in, the 3 x 3 grid is centred
   on US Letter, crop marks sit in the margins, and back pages follow the chosen
   two-sided flip (long edge or short edge), with an optional 180-degree back rotation.

Edits src/catalog.src.html only (anchor-verified, all-or-nothing, writes a .bak).
Requires fix_catalog_v1.py. Refuses to run twice. Standard library only.

RUN (repo root)
  python3 fix_catalog_v2.py
  python3 tools/build_catalog.py
"""
import os, shutil, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src", "catalog.src.html")
MARK = "function buildPrintPdf("
def die(m): sys.exit("[fix_catalog_v2] " + m)
EDITS = [
[
"/* ---------- print ---------- */\nfunction printCards(d,opts){",
"/* ---------- print-ready PDF (fix_catalog_v2) ----------\n   Browser printing shifts and clips card sheets (each browser adds its own\n   margins). The catalog now writes the PDF itself, so every card lands at an\n   exact position: 2.5 x 3.5 in cards, 3 x 3 grid centred on US Letter\n   (0.5 in left/right, 0.25 in top/bottom), crop marks in the margins, and back\n   pages laid out for the chosen duplex flip. Print the PDF at 100% / Actual Size. */\nvar CW=180, CH=252, PW=612, PH=792, GX=(PW-3*CW)/2, GY=(PH-3*CH)/2;\nfunction b64bytes(uri){var s=atob(uri.split(',')[1]),a=new Uint8Array(s.length);for(var i=0;i<s.length;i++)a[i]=s.charCodeAt(i);return a;}\nfunction loadImg(src){return new Promise(function(ok,no){var i=new Image();i.onload=function(){ok(i);};i.onerror=no;i.src=src;});}\nfunction cardJpeg(c,light){ /* -> Promise of {w,h,bytes} */\n  var cv=document.createElement('canvas'); cv.width=600; cv.height=840; var g=cv.getContext('2d');\n  g.fillStyle='#fff'; g.fillRect(0,0,600,840);\n  function done(){return {w:600,h:840,bytes:b64bytes(cv.toDataURL('image/jpeg',0.9))};}\n  var src=c==='back'?(light?BACK.emblem:BACK.full):SC[c.key];\n  if(c==='back'&&light){\n    g.strokeStyle='#222'; g.lineWidth=4; roundRect(g,22,22,556,796,26); g.stroke();\n    if(!src){ g.fillStyle='#222'; g.font='bold 64px Georgia,serif'; g.textAlign='center'; g.fillText('ABC',300,440); return Promise.resolve(done()); }\n    return loadImg(src).then(function(im){ g.drawImage(im,90,210,420,420); return done(); });\n  }\n  if(src) return loadImg(src).then(function(im){ g.drawImage(im,0,0,600,840); return done(); });\n  if(c==='back'){ g.fillStyle='#1b1712'; g.fillRect(0,0,600,840); g.fillStyle='#E3C27A'; g.font='bold 72px Georgia,serif'; g.textAlign='center'; g.fillText('ABC',300,440); return Promise.resolve(done()); }\n  /* placeholder front for a card with no scan */\n  g.strokeStyle='#888'; g.lineWidth=4; g.setLineDash([16,12]); roundRect(g,20,20,560,800,24); g.stroke(); g.setLineDash([]);\n  g.textAlign='center'; g.fillStyle='#555'; g.font='26px Helvetica,Arial,sans-serif';\n  g.fillText(TN[c.t].one+(c.b?' \u00b7 '+BN[c.b]:''),300,330);\n  g.fillStyle='#111'; g.font='bold 40px Helvetica,Arial,sans-serif';\n  wrap(g,c.n,300,400,500,48,4);\n  g.fillStyle='#777'; g.font='24px Helvetica,Arial,sans-serif'; g.fillText('No scan yet \u00b7 '+c.id,300,640);\n  return Promise.resolve(done());\n}\nfunction roundRect(g,x,y,w,h,r){g.beginPath();g.moveTo(x+r,y);g.arcTo(x+w,y,x+w,y+h,r);g.arcTo(x+w,y+h,x,y+h,r);g.arcTo(x,y+h,x,y,r);g.arcTo(x,y,x+w,y,r);g.closePath();}\nfunction wrap(g,t,x,y,maxw,lh,maxl){var w=String(t).split(/\\s+/),line='',n=0;for(var i=0;i<w.length;i++){var tst=line?line+' '+w[i]:w[i];if(g.measureText(tst).width>maxw&&line){g.fillText(line,x,y+n*lh);n++;line=w[i];if(n>=maxl-1){line=w.slice(i).join(' ');break;}}else line=tst;}g.fillText(line,x,y+n*lh);}\n/* WinAnsi text for the checklist (standard Helvetica, no font embedding) */\nvar WA={'\u2018':145,'\u2019':146,'\u201c':147,'\u201d':148,'\u2013':150,'\u2014':151,'\u2026':133,'\u00b7':183};\nfunction pdfStr(t){var o='';for(var i=0;i<t.length;i++){var ch=t[i],cd=t.charCodeAt(i);if(WA[ch])cd=WA[ch];else if(cd>255){var n=ch.normalize?ch.normalize('NFD').replace(/[\u0300-\u036f]/g,''):'?';cd=n.charCodeAt(0)<256?n.charCodeAt(0):63;}\n  var c=String.fromCharCode(cd); o+=(c==='('||c===')'||c==='\\\\')?'\\\\'+c:c;}return '('+o+')';}\nfunction listPages(d){\n  var lines=[{t:d.name,s:16,b:1},{t:FMT[d.fmt].n+' \u00b7 '+d.books.map(function(b){return BN[b];}).join(' + ')+' \u00b7 '+count(d).total+' cards',s:9},{gap:8}];\n  TYPES.forEach(function(T){ if(!d[T.t].length) return; lines.push({t:T.n.toUpperCase()+' ('+d[T.t].length+')',s:9,b:1});\n    d[T.t].forEach(function(id){var c=BY[T.t+':'+id]; var txt=c.n, w=[], cur=''; txt.split(' ').forEach(function(x){ if((cur+' '+x).length>54&&cur){w.push(cur);cur=x;} else cur=cur?cur+' '+x:x; }); w.push(cur);\n      w.forEach(function(x,i){lines.push({t:x,s:8.5,box:i===0,ind:1});}); });\n    lines.push({gap:5}); });\n  var pages=[], ops=[], col=0, y=PH-54, x0=[54,324];\n  function flush(){pages.push(ops.join('\\n'));ops=[];col=0;y=PH-54;}\n  lines.forEach(function(L,i){ var hgt=L.gap||(L.s+3.5);\n    if(y-hgt<48){ if(col===0){col=1;y=PH-54-(pages.length===0?40:0);} else flush(); }\n    if(L.gap){y-=L.gap;return;}\n    var x=x0[col]+(L.ind?14:0);\n    if(L.box) ops.push('0.6 w '+(x0[col])+' '+(y-L.s+1)+' 8 8 re S');\n    ops.push('BT /F'+(L.b?2:1)+' '+L.s+' Tf '+x+' '+(y-L.s+1.5)+' Td '+pdfStr(L.t)+' Tj ET');\n    y-=hgt; });\n  if(ops.length) flush();\n  return pages;\n}\nfunction makePdf(pages){ /* pages: [{ops, imgs:{name:jpeg}}] -> Blob */\n  var parts=[], off=0, xref=[], enc=function(s){var a=new Uint8Array(s.length);for(var i=0;i<s.length;i++)a[i]=s.charCodeAt(i)&255;return a;};\n  function put(x){var b=typeof x==='string'?enc(x):x;parts.push(b);off+=b.length;}\n  var objs=[]; function obj(body){objs.push(body);return objs.length;} /* body: string or [string, bytes, string] */\n  var F1=obj('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>');\n  var F2=obj('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>');\n  var imgObj=new Map(), pageIds=[], pagesId=obj(null);\n  pages.forEach(function(p){\n    var xo=[]; Object.keys(p.imgs||{}).forEach(function(nm){var j=p.imgs[nm]; if(!imgObj.has(j)) imgObj.set(j,obj(['<< /Type /XObject /Subtype /Image /Width '+j.w+' /Height '+j.h+' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length '+j.bytes.length+' >>\\nstream\\n',j.bytes,'\\nendstream'])); xo.push('/'+nm+' '+imgObj.get(j)+' 0 R');});\n    var cs=obj(['<< /Length '+p.ops.length+' >>\\nstream\\n',enc(p.ops),'\\nendstream']);\n    pageIds.push(obj('<< /Type /Page /Parent '+pagesId+' 0 R /MediaBox [0 0 '+PW+' '+PH+'] /Resources << /Font << /F1 '+F1+' 0 R /F2 '+F2+' 0 R >> /XObject << '+xo.join(' ')+' >> >> /Contents '+cs+' 0 R >>'));\n  });\n  objs[pagesId-1]='<< /Type /Pages /Kids ['+pageIds.map(function(i){return i+' 0 R';}).join(' ')+'] /Count '+pageIds.length+' >>';\n  var cat=obj('<< /Type /Catalog /Pages '+pagesId+' 0 R >>');\n  put('%PDF-1.4\\n%\u00e2\u00e3\u00cf\u00d3\\n');\n  objs.forEach(function(b,i){ xref.push(off); put((i+1)+' 0 obj\\n'); if(typeof b==='string') put(b); else {put(b[0]);put(b[1]);put(b[2]);} put('\\nendobj\\n'); });\n  var xo=off; put('xref\\n0 '+(objs.length+1)+'\\n0000000000 65535 f \\n'+xref.map(function(o){return ('0000000000'+o).slice(-10)+' 00000 n \\n';}).join(''));\n  put('trailer\\n<< /Size '+(objs.length+1)+' /Root '+cat+' 0 R >>\\nstartxref\\n'+xo+'\\n%%EOF\\n');\n  return new Blob(parts,{type:'application/pdf'});\n}\nfunction cropOps(){ var o=['0 G 0.5 w'], L=GX, T=GY;\n  [0,1,2,3].forEach(function(i){ var x=L+i*CW, y=T+i*CH;\n    o.push(x+' 0 m '+x+' '+(T-4)+' l S', x+' '+(PH-T+4)+' m '+x+' '+PH+' l S');\n    o.push('0 '+y+' m '+(L-6)+' '+y+' l S', (PW-L+6)+' '+y+' m '+PW+' '+y+' l S'); });\n  return o.join('\\n'); }\nfunction slotXY(i){ var r=Math.floor(i/3), c=i%3; return [GX+c*CW, PH-GY-(r+1)*CH]; }\nfunction buildPrintPdf(d,opts){\n  var cards=cardsOf(d), light=!!PREF.lightBack, flip=PREF.flip||'long';\n  toast('Building PDF\u2026');\n  var uniq=new Map(); cards.forEach(function(c){uniq.set(c.key,c);});\n  var jobs=[], J={};\n  uniq.forEach(function(c,k){ jobs.push(cardJpeg(c,false).then(function(j){J[k]=j;})); });\n  if(opts.backs) jobs.push(cardJpeg('back',light).then(function(j){J.__back=j;}));\n  return Promise.all(jobs).then(function(){\n    var pages=[];\n    for(var i=0;i<cards.length;i+=9){\n      var pg=cards.slice(i,i+9), ops=[], imgs={};\n      pg.forEach(function(c,k){ var xy=slotXY(k), nm='I'+k; imgs[nm]=J[c.key]; ops.push('q '+CW+' 0 0 '+CH+' '+xy[0]+' '+xy[1]+' cm /'+nm+' Do Q'); });\n      ops.push(cropOps()); pages.push({ops:ops.join('\\n'),imgs:imgs});\n      if(opts.backs){ var bo=[];\n        /* long edge (book flip): columns mirror. short edge (calendar flip): rows mirror.\n           rot180 turns each back upside down for printers that print the reverse side inverted. */\n        pg.forEach(function(c,k){ var r=Math.floor(k/3), col=k%3, t=flip==='short'?(2-r)*3+col:r*3+(2-col), xy=slotXY(t);\n          bo.push(PREF.rot180?('q '+(-CW)+' 0 0 '+(-CH)+' '+(xy[0]+CW)+' '+(xy[1]+CH)+' cm /B Do Q'):('q '+CW+' 0 0 '+CH+' '+xy[0]+' '+xy[1]+' cm /B Do Q')); });\n        pages.push({ops:bo.join('\\n'),imgs:{B:J.__back}});\n      }\n    }\n    /* checklist last; front/back pairs keep it on a fresh sheet */\n    listPages(d).forEach(function(o){pages.push({ops:o,imgs:{}});});\n    var blob=makePdf(pages), nm=(d.name||'deck').replace(/[^\\w\\- ]+/g,'').trim()||'deck';\n    var a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=nm+' - print.pdf'; document.body.appendChild(a); a.click();\n    setTimeout(function(){URL.revokeObjectURL(a.href);a.remove();},1500);\n    toast('Saved \u201c'+nm+' - print.pdf\u201d. Print it at 100% / Actual Size.');\n    return blob;\n  }).catch(function(e){ toast('Could not build the PDF: '+(e&&e.message||e)); });\n}\n\n/* ---------- print ---------- */\nfunction printCards(d,opts){"
],
[
"    case 'doprint': var _pd=S.modal.deck||d; S.modal=null; renderModal(); printCards(_pd,{backs:true,cut:true}); break;",
"    case 'doprint': var _pd=S.modal.deck||d; S.modal=null; renderModal(); buildPrintPdf(_pd,{backs:true}); break;"
],
[
"    case 'doprintfront': var _pf=S.modal.deck||d; S.modal=null; renderModal(); printCards(_pf,{backs:false,cut:true}); break;",
"    case 'doprintfront': var _pf=S.modal.deck||d; S.modal=null; renderModal(); buildPrintPdf(_pf,{backs:false}); break;"
],
[
"each followed by its back page. Print at <b>100% / Actual size</b>, two-sided, <b>flip on long edge</b>. Cards without a Dextrous scan print as a labeled placeholder; A checklist page prints at the end.</p>'+",
"each followed by its back page, centred with crop marks. This saves a PDF: open it and print at <b>100% / Actual Size</b> (not \u201cFit to page\u201d), two-sided, using the same flip you choose here. Cards without a Dextrous scan print as a labeled placeholder. A checklist page prints at the end.</p>'+\n      '<label style=\"display:flex;align-items:center;gap:10px;font-size:14px\">Two-sided flip <select class=\"sel\" data-in=\"flip\" aria-label=\"Two-sided flip\"><option value=\"long\"'+((PREF.flip||'long')==='long'?' selected':'')+'>Long edge (book)</option><option value=\"short\"'+(PREF.flip==='short'?' selected':'')+'>Short edge (calendar)</option></select></label>'+\n      '<label style=\"display:flex;align-items:center;gap:10px;font-size:14px\"><input type=\"checkbox\" data-a=\"rot180\"'+(PREF.rot180?' checked':'')+' style=\"width:18px;height:18px\"> Rotate backs 180\u00b0 <span class=\"hint\">(if your printer prints the backs upside down)</span></label>'+"
],
[
"'<div class=\"dacts\"><button class=\"btn pri\" data-a=\"doprint\">Print cards with backs</button><button class=\"btn\" data-a=\"doprintfront\">Fronts only</button>",
"'<div class=\"dacts\"><button class=\"btn pri\" data-a=\"doprint\">Save print PDF (with backs)</button><button class=\"btn\" data-a=\"doprintfront\">Fronts only PDF</button>"
],
[
"    case 'lightback': PREF.lightBack=!PREF.lightBack; store('abc_catalog_prefs',PREF); renderModal(); break;",
"    case 'lightback': PREF.lightBack=!PREF.lightBack; store('abc_catalog_prefs',PREF); renderModal(); break;\n    case 'rot180': PREF.rot180=!PREF.rot180; store('abc_catalog_prefs',PREF); renderModal(); break;"
],
[
"  else if(k==='book1') mutate(function(d){ if(v) d.books[1]=v; else d.books.splice(1,1); });",
"  else if(k==='book1') mutate(function(d){ if(v) d.books[1]=v; else d.books.splice(1,1); });\n  else if(k==='flip'){ PREF.flip=v; store('abc_catalog_prefs',PREF); }"
],
[
"  h+='<aside class=\"deckp\" aria-label=\"Deck\"><input class=\"dname\"",
"  var dirty=S.orig!==JSON.stringify(stripUpd(d));\n  h+='<aside class=\"deckp\" aria-label=\"Deck\"><div class=\"exitbar\"><button class=\"btn pri\" data-a=\"bdone\">Done</button><button class=\"btn\" data-a=\"bdiscard\"'+(dirty||S.isNew?'':' disabled')+'>'+(S.isNew?'Cancel new deck':'Discard changes')+'</button><button class=\"btn\" data-a=\"bdelete\">Delete deck</button></div><input class=\"dname\""
],
[
"function snapshot(){",
"function stripUpd(d){var o=JSON.parse(JSON.stringify(d));delete o.upd;return o;}\nfunction beginEdit(isNew){var d=curDeck(); S.orig=d?JSON.stringify(stripUpd(d)):null; S.isNew=!!isNew; S.undo=[]; S.redo=[];}\nfunction leaveBuilder(){ S.deckId=null; S.orig=null; S.isNew=false; S.undo=[]; S.redo=[]; S.view='mydecks'; document.getElementById('main').scrollTop=0; render(); }\nfunction snapshot(){"
],
[
"    case 'create': var nd=blank(S.nf==='classic'?'classic':'pm',[S.nfb||'gatsby']); DECKS.push(nd); save(); S.deckId=nd.id; S.undo=[];S.redo=[]; render(); break;",
"    case 'create': var nd=blank(S.nf==='classic'?'classic':'pm',[S.nfb||'gatsby']); DECKS.push(nd); save(); S.deckId=nd.id; beginEdit(true); render(); break;"
],
[
"    case 'clone': var cd=fromPrecon(D.precons[+p[1]]); DECKS.push(cd); save(); S.deckId=cd.id; S.view='builder'; S.undo=[];S.redo=[]; render();",
"    case 'clone': var cd=fromPrecon(D.precons[+p[1]]); DECKS.push(cd); save(); S.deckId=cd.id; S.view='builder'; beginEdit(true); render();"
],
[
"    case 'open': S.deckId=p[1]; S.view='builder'; S.undo=[];S.redo=[]; render(); break;",
"    case 'open': S.deckId=p[1]; S.view='builder'; beginEdit(false); render(); break;\n    case 'bdone': toast('Saved \\u201c'+(d?d.name:'deck')+'\\u201d to My Decks.'); leaveBuilder(); break;\n    case 'bdiscard': if(!d) break;\n      if(S.isNew){ if(window.confirm('Cancel this new deck? It will be removed.')){ DECKS=DECKS.filter(function(x){return x.id!==d.id;}); save(); toast('New deck cancelled.'); leaveBuilder(); } }\n      else if(window.confirm('Discard every change since you opened \\u201c'+d.name+'\\u201d?')){ Object.keys(d).forEach(function(k){delete d[k];}); Object.assign(d,JSON.parse(S.orig)); d.upd=Date.now(); save(); toast('Changes discarded.'); leaveBuilder(); }\n      break;\n    case 'bdelete': if(d&&window.confirm('Delete \\u201c'+d.name+'\\u201d? This can\\u2019t be undone.')){ DECKS=DECKS.filter(function(x){return x.id!==d.id;}); save(); toast('Deck deleted.'); leaveBuilder(); } break;"
],
[
"      DECKS.push(r.deck); save(); S.deckId=r.deck.id; S.view='builder'; S.modal=null; S.undo=[];S.redo=[]; render();",
"      DECKS.push(r.deck); save(); S.deckId=r.deck.id; S.view='builder'; S.modal=null; beginEdit(true); render();"
],
[
"      else if(p[1]==='builder'){S.view='builder'; if(p[2]==='new') S.deckId=null; else if(!curDeck()&&DECKS.length) S.deckId=DECKS.slice().sort(function(a,b){return b.upd-a.upd;})[0].id;}",
"      else if(p[1]==='builder'){S.view='builder'; if(p[2]==='new'){S.deckId=null;S.orig=null;} else if(!curDeck()&&DECKS.length){ S.deckId=DECKS.slice().sort(function(a,b){return b.upd-a.upd;})[0].id; beginEdit(false); }}"
],
[
".deckp>*{flex:none}",
".deckp>*{flex:none}\n.exitbar{display:flex;gap:6px;flex-wrap:wrap;padding-bottom:10px;border-bottom:1px solid var(--sep)}"
],
[
"@media (max-width:980px){.bwrap{grid-template-columns:minmax(0,1fr)}",
"@media (max-width:980px){.exitbar{position:sticky;top:0;z-index:3;background:var(--group);padding-top:8px}.bwrap{grid-template-columns:minmax(0,1fr)}"
]
]
if not os.path.exists(SRC): die("src/catalog.src.html not found. Run fix_catalog_v1.py first (from the repo root).")
s = open(SRC, encoding="utf-8").read()
if MARK in s: die("already applied. Nothing to do.")
bad = [a[:70] for a, b in EDITS if s.count(a) != 1]
if bad: die("src/catalog.src.html has changed since v1; these anchors were not found exactly once, nothing written:\n  " + "\n  ".join(bad))
for a, b in EDITS: s = s.replace(a, b)
shutil.copyfile(SRC, SRC + ".bak")
open(SRC, "w", encoding="utf-8").write(s)
print("[fix_catalog_v2] %d edits applied to src/catalog.src.html (backup: src/catalog.src.html.bak)" % len(EDITS))
print("[fix_catalog_v2] next:  python3 tools/build_catalog.py")
