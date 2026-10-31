#!/usr/bin/env python3
"""fix_menu_book.py -- the main menu as an open book.

Run from the repo root:   python3 fix_menu_book.py
                          python3 build.py
Undo:                     restore src/game.src.html from the .bak this writes.
Needs:                    nothing else (uses the Challenges streak/badge when fix_challenges is in).

WHAT IT DOES
  * Left page: your crest, the title, and two featured buttons -- "Start here: Watch the Tutorial" on a first visit,
    afterwards "Continue reading: <your last mode>" -- plus Quickplay, and the daily-challenge strip (streak, today's
    progress, rewards to claim).
  * Right page: a table of contents in three acts (ACT I Play / ACT II Campaign / ACT III Study) with the ACT tab
    colours from the printed cards, roman numerals, dotted leaders, an ink underline and a one-line description on hover.
  * A red ribbon marks your last chapter (the Tutorial on a first visit). The last mode is kept in
    localStorage abc_lastmode (Quickplay, Custom, Pagemaster, Arena, Scrimmage).
  * Choosing a chapter plays the book_flip sound and turns the page (0.55 s). Calm effects / reduced motion: no
    animations, the action runs at once.
  * The menu sits on the board's dark table. Sub-screens keep their current backgrounds.
  * Phone: the two pages stack into one.
  * Every button keeps its existing data-do action. No assets added.

HOW IT HOOKS IN (1 one-line early return, nothing removed)
  menuScreen() returns the book menu; the old menu stays in place underneath as the fallback.
"""
import os, sys, shutil, datetime
SRC=os.path.join('src','game.src.html'); MARK='/* fix_menu_book */'; TAG='[fix_menu_book]'
if not os.path.exists(SRC): sys.exit(f'{TAG} ERROR: run from the repo root (src/game.src.html not found).')
s=open(SRC,encoding='utf-8').read()
if MARK in s: sys.exit(f'{TAG} Already applied -- nothing to do.')

JS = r'''/* fix_menu_book */
/* fix_menu_book: the main menu as an open book (title page + table of contents).
   Buttons keep their data-do actions, so every existing handler runs unchanged. */
const MB_PLAY={'go-quick':['Quickplay','Random decks for both sides, pick a difficulty.'],'go-custom':['Custom Play','Your deck, your opponent, house rules.'],
  'go-pagemaster':['Pagemaster','Two commanders, one or two books.'],'go-arena':['PreCon Arena','Precon vs precon, physical rules, CSV log.'],
  'go-scrim':['Literary Scrimmage','Roguelike map, bosses, unlockables.']};
let MB_SHOWN=0;
function abcMbLast(){ try{ const k=localStorage.getItem('abc_lastmode'); return MB_PLAY[k]?k:''; }catch(e){ return ''; } }
function abcMbCalm(){ try{ return document.body.classList.contains('calm-fx') || (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches); }catch(e){ return false; } }
function abcMbRow(n,act,title,desc,pg,extra){
  return `<li><button class="mb-row" data-do="${act}"><span class="mb-n">${n}</span><span class="mb-ti">${title}${extra||''}</span><span class="mb-dots"></span><span class="mb-pg">${pg}</span><span class="mb-ds">${desc}</span></button></li>`;
}
function abcMbMenu(){
  const last=abcMbLast(), first=!last;
  let claim=0, streak=0, done=0; try{ claim=abcChClaimable(); const st=abcChState(); streak=st.streak||0; done=st.daily.filter(function(c){ return c.done; }).length; }catch(e){}
  const ip=(typeof META!=='undefined'&&META&&META.ip)||0;
  const badge=claim?`<span class="mb-badge chs-badge">${claim}</span>`:'';
  const feat=function(act,kick,title,desc,cls){ return `<button class="mb-feat${cls?' '+cls:''}" data-do="${act}"><small>${kick}</small><b>${title}</b><i>${desc}</i><span class="mb-go">›</span></button>`; };
  const f1 = first ? feat('go-tutorial','Start here','Watch the Tutorial','Two minutes: how a turn works, start to finish.','cont')
                   : feat(last,'Continue reading',MB_PLAY[last][0],MB_PLAY[last][1],'cont');
  const f2 = (last==='go-quick') ? feat('go-scrim','Begin a new story','Literary Scrimmage',MB_PLAY['go-scrim'][1]) : feat('go-quick','Begin a new story','Quickplay','Random decks, pick a difficulty, play in a minute.');
  const fresh=(Date.now()-MB_SHOWN)>1500; MB_SHOWN=Date.now();
  setTimeout(abcMbRibbon,0);
  const crest=window.ABC_CREST||window.ABC_LOGO||'';
  return `<div class="mb${fresh&&!abcMbCalm()?' mb-in':''}"><div class="mb-book">
    <div class="mb-ribbon" title="${first?'Start here':'Your last chapter'}"></div>
    <div class="mb-page l">
      ${crest?`<img class="mb-crest" src="${crest}" alt="Academic Battle Cards">`:''}
      <h1 class="mb-wm"><span class="t1">ACADEMIC</span><span class="t2">Battle Cards</span><span class="t3">A LITERARY SCRIMMAGE</span></h1>
      <svg class="mb-flour" viewBox="0 0 220 16" aria-hidden="true"><path d="M0 8H86M134 8H220" stroke="currentColor"/><path d="M110 2c-6 0-10 6-16 6 6 0 10 6 16 6s10-6 16-6c-6 0-10-6-16-6z" fill="currentColor"/><circle cx="90" cy="8" r="2" fill="currentColor"/><circle cx="130" cy="8" r="2" fill="currentColor"/></svg>
      <p class="mb-epi">Deal, draw &amp; duel with trivia.</p>
      ${f1}${f2}
      <button class="mb-daily" data-do="go-challenges"><span class="mb-fl">${streak?'🔥':'🎯'}</span><span>${streak?`<b>${streak}-day streak.</b> `:'<b>Daily challenges.</b> '}Today: ${done} of 3 done${claim?` · ${claim} reward${claim>1?'s':''} to claim`:''}</span></button>
    </div>
    <div class="mb-page r">
      <div class="mb-toc-h">Contents</div>
      <div class="mb-part"><span class="mb-act" style="--c:#5ab3e6"><b>ACT I</b><i style="--c:#e86b78"></i><i style="--c:#f2cf5b"></i></span>Play</div>
      <ul class="mb-toc">
        ${abcMbRow('I','go-quick','Quickplay','Random decks for both sides.',1)}
        ${abcMbRow('II','go-custom','Custom Play','Your deck, your opponent, house rules.',7)}
        ${abcMbRow('III','go-pagemaster','Pagemaster','Two commanders, one or two books.',19)}
        ${abcMbRow('IV','go-arena','PreCon Arena','Precon vs precon, physical rules, CSV log.',28)}
      </ul>
      <div class="mb-part"><span class="mb-act" style="--c:#e86b78"><b>ACT II</b><i style="--c:#f2cf5b"></i><i style="--c:#5ab3e6"></i></span>Campaign</div>
      <ul class="mb-toc">
        ${abcMbRow('V','go-scrim','Literary Scrimmage','Roguelike map, bosses, unlockables.',41)}
        ${abcMbRow('VI','go-challenges','Challenges','Daily &amp; weekly goals for Intellect Points.',63,badge)}
      </ul>
      <div class="mb-part"><span class="mb-act" style="--c:#f2cf5b"><b>ACT III</b><i style="--c:#5ab3e6"></i><i style="--c:#e86b78"></i></span>Study</div>
      <ul class="mb-toc">
        ${abcMbRow('VII','builder','Deck Builder','Build, edit &amp; share decks.',70)}
        ${abcMbRow('VIII','go-index','Index','Look up any card, rule or status.',84)}
        ${abcMbRow('IX','go-guide','Quickstart Guide','How to play, and a rules refresher.',92)}
        ${abcMbRow('X','go-tutorial','Watch the Tutorial','Two minutes: a turn, start to finish.',99)}
      </ul>
      <div class="mb-foot"><span>Set 1</span><span>— 1 —</span><span>🧠 ${ip} IP</span></div>
    </div>
    <div class="mb-gutter"></div>
  </div></div>`;
}
/* the ribbon hangs from the top of the book down to your last chapter (or the Tutorial on a first visit) */
function abcMbRibbon(){
  try{
    const book=document.querySelector('.mb-book'), rib=book&&book.querySelector('.mb-ribbon'); if(!rib) return;
    const key=abcMbLast()||'go-tutorial', row=book.querySelector('.mb-toc [data-do="'+key+'"]');
    if(!row || window.innerWidth<=760){ rib.style.setProperty('--rh','70px'); return; }
    let y=0, el=row; while(el && el!==book){ y+=el.offsetTop; el=el.offsetParent; }   /* offsets ignore the entrance transform */
    rib.style.setProperty('--rh', Math.round(y+row.offsetHeight/2+16)+'px');
  }catch(e){}
}
window.addEventListener('resize', function(){ if(document.querySelector('.mb-book')) abcMbRibbon(); });
/* choosing a chapter: remember it, play the page flip, turn the page, then run the original action */
document.addEventListener('click', function(e){
  const t=e.target && e.target.closest && e.target.closest('.mb [data-do]'); if(!t) return;
  const act=t.dataset.do;
  if(MB_PLAY[act]){ try{ localStorage.setItem('abc_lastmode', act); }catch(err){} }
  if(t._mbGo){ t._mbGo=false; return; }                         /* second pass: let the game handle it */
  try{ SFX.card('book_flip',0.7); }catch(err){}
  if(abcMbCalm()) return;
  e.stopPropagation(); e.preventDefault();
  if(document.querySelector('.mb-turn')) return;
  const o=document.createElement('div'); o.className='mb-turn'; o.innerHTML='<i></i>'; document.body.appendChild(o);
  requestAnimationFrame(function(){ o.classList.add('go'); });
  setTimeout(function(){ t._mbGo=true; t.click(); }, 300);         /* the page is mid-turn: swap the screen under it */
  setTimeout(function(){ o.remove(); }, 560);
}, true);
'''
CSS = r"""
/* fix_menu_book -- main menu as an open book on the board's dark table */
body[data-screen="menu"][data-menuscreen="menu"]{background-color:#2b2620}
body[data-screen="menu"][data-menuscreen="menu"]::before{background:#2b2620 radial-gradient(rgba(0,0,0,.22) 1px,transparent 1.4px) 0 0/6px 6px!important}
.mb{--mb-ink:#241f1b;--mb-paper:#f6eedb;--mb-red:#b5402a;--mb-gold:#E3A92B;--mb-teal:#1F6A6A;padding:18px 4px 36px;color:var(--mb-ink);text-align:left}
.mb-book{position:relative;max-width:1020px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;filter:drop-shadow(0 18px 26px rgba(0,0,0,.55))}
.mb.mb-in .mb-book{animation:mbIn .5s cubic-bezier(.2,.8,.2,1) both}
@keyframes mbIn{from{opacity:0;transform:translateY(14px) scale(.985)}}
.mb-book::before,.mb-book::after{content:"";position:absolute;bottom:-9px;height:10px;background:repeating-linear-gradient(0deg,#d9ccae 0 1px,#f3ead4 1px 3px);border-radius:0 0 6px 6px}
.mb-book::before{left:6px;right:50%;transform:skewX(4deg);transform-origin:right}
.mb-book::after{right:6px;left:50%;transform:skewX(-4deg);transform-origin:left}
.mb-page{position:relative;min-height:600px;padding:40px 44px 50px;background:var(--mb-paper);overflow:hidden}
.mb-page::before{content:"";position:absolute;inset:0;pointer-events:none;opacity:.5;
  background:radial-gradient(120% 90% at 50% 0%,transparent 60%,rgba(120,90,40,.12)),repeating-linear-gradient(90deg,rgba(80,60,30,.025) 0 2px,transparent 2px 5px)}
.mb-page.l{border-radius:10px 2px 2px 10px;background:linear-gradient(90deg,var(--mb-paper) 78%,#e6d8b6 100%);text-align:center}
.mb-page.r{border-radius:2px 10px 10px 2px;background:linear-gradient(270deg,var(--mb-paper) 78%,#e6d8b6 100%)}
.mb-gutter{position:absolute;left:50%;top:0;bottom:0;width:60px;margin-left:-30px;pointer-events:none;z-index:3;
  background:linear-gradient(90deg,transparent,rgba(60,40,15,.22) 44%,rgba(40,25,10,.38) 50%,rgba(60,40,15,.22) 56%,transparent)}
.mb-ribbon{position:absolute;z-index:4;top:-8px;right:14px;width:26px;height:var(--rh,170px);pointer-events:none;background:linear-gradient(90deg,#8e2a1d,#c0452f 50%,#8e2a1d);
  clip-path:polygon(0 0,100% 0,100% 100%,50% calc(100% - 13px),0 100%);transition:height .45s cubic-bezier(.3,1.4,.4,1)}
.mb-crest{display:block;width:min(170px,60%);margin:0 auto 6px;position:relative}
.mb-wm{margin:0;font-weight:400}.mb-wm span{display:block}
.mb-wm .t1,.mb-wm .t3{font:400 15px/1 var(--cond);letter-spacing:.32em;color:#6b5f52}
.mb-wm .t2{font:400 44px/1 var(--disp);color:var(--mb-ink);margin:6px 0 2px;text-shadow:2px 2px 0 rgba(227,169,43,.55)}
.mb-flour{display:block;margin:12px auto;width:220px;height:16px;color:#8a6a2a}
.mb-epi{font:italic 400 16px/1.45 var(--body);color:#5a4a34;margin:0 0 20px}
.mb-feat{display:block;width:100%;text-align:left;cursor:pointer;border:2px solid var(--mb-ink);border-radius:12px;padding:13px 40px 13px 18px;margin:0 0 12px;
  background:#fffaf0;color:var(--mb-ink);box-shadow:4px 4px 0 var(--mb-ink);position:relative;transition:transform .18s,box-shadow .18s}
.mb-feat:hover,.mb-feat:focus-visible{transform:translate(-2px,-2px);box-shadow:6px 6px 0 var(--mb-ink);outline:none}
.mb-feat small{display:block;font:400 11px/1 var(--cond);letter-spacing:.24em;color:var(--mb-red);text-transform:uppercase;margin-bottom:5px}
.mb-feat b{display:block;font:400 22px/1.1 var(--disp)}
.mb-feat i{display:block;font:italic 14px/1.35 var(--body);color:#5a4a34;margin-top:3px}
.mb-go{position:absolute;right:14px;top:50%;transform:translateY(-50%);font:400 26px var(--disp);color:var(--mb-gold)}
.mb-feat.cont{background:var(--mb-teal);color:#fff;border-color:#0f3535;box-shadow:4px 4px 0 #0f3535}
.mb-feat.cont small{color:#ffd45e}.mb-feat.cont i{color:#d6f0ee}
.mb.mb-in .mb-feat{animation:mbDeal .5s cubic-bezier(.2,.9,.3,1) both}
.mb.mb-in .mb-feat+.mb-feat{animation-delay:.09s}
@keyframes mbDeal{from{opacity:0;transform:translateY(26px) rotate(-3deg)}}
.mb-daily{display:flex;align-items:center;justify-content:flex-start;gap:10px;width:100%;min-height:0;box-shadow:none;text-transform:none;letter-spacing:0;margin-top:16px;padding:10px 12px;border:1.5px dashed #b9a06a;border-radius:10px;background:none;cursor:pointer;
  font:13px/1.35 var(--body);color:#5a4a34;text-align:left}
.mb-daily:hover{background:rgba(185,160,106,.12)}.mb-daily .mb-fl{width:auto;font-size:20px;flex:none}.mb-daily>span:last-child{flex:1}.mb-daily b{color:var(--mb-ink)}
.mb-toc-h{display:flex;align-items:center;gap:12px;margin:0 0 6px;font:400 13px/1 var(--cond);letter-spacing:.42em;color:#6b5f52;text-transform:uppercase}
.mb-toc-h::before,.mb-toc-h::after{content:"";flex:1;height:1px;background:linear-gradient(90deg,transparent,#8a6a2a,transparent)}
.mb-part{display:flex;align-items:center;gap:10px;margin:14px 0 4px;font:400 17px/1 var(--disp);color:var(--mb-ink)}
.mb-act{display:inline-flex;align-items:center}
.mb-act b{font:italic 400 12px/1 var(--cond);letter-spacing:.06em;padding:4px 8px 3px;background:var(--c);color:#111;transform:skewX(-10deg);border-radius:3px}
.mb-act i{width:6px;height:17px;margin-left:2px;background:var(--c);transform:skewX(-10deg);border-radius:2px}
.mb-toc{list-style:none;margin:0;padding:0}
.mb-row{display:grid;grid-template-columns:34px auto 1fr auto;align-items:baseline;gap:8px;width:100%;padding:6px 4px;background:none;border:0;cursor:pointer;text-align:left;color:var(--mb-ink);min-height:40px}
.mb-n{font:400 13px var(--cond);color:#8a6a2a;letter-spacing:.06em}
.mb-ti{font:600 18px/1.2 var(--body);position:relative}
.mb-ti::after{content:"";position:absolute;left:0;right:100%;bottom:-2px;height:2px;background:var(--mb-red);transition:right .28s ease}
.mb-dots{border-bottom:2px dotted #b9a982;transform:translateY(-4px)}
.mb-pg{font:italic 14px var(--body);color:#6b5f52;min-width:20px;text-align:right;transition:color .2s}
.mb-row:hover .mb-ti::after,.mb-row:focus-visible .mb-ti::after{right:0}
.mb-row:hover .mb-pg,.mb-row:focus-visible .mb-pg{color:var(--mb-red)}
.mb-row:focus-visible{outline:2px solid var(--mb-gold);outline-offset:2px;border-radius:4px}
.mb-ds{grid-column:2/5;font:13px/1.3 var(--body);color:#6b5f52;max-height:0;overflow:hidden;transition:max-height .25s}
.mb-row:hover .mb-ds,.mb-row:focus-visible .mb-ds{max-height:40px}
.mb-badge{display:inline-grid;place-items:center;min-width:19px;height:19px;padding:0 5px;margin-left:6px;border-radius:999px;background:var(--mb-red);color:#fff;font:700 11px/1 Arial,sans-serif;vertical-align:2px}
.mb-foot{position:absolute;left:44px;right:44px;bottom:18px;display:flex;justify-content:space-between;font:italic 13px var(--body);color:#8a7a5c}
.mb-turn{position:fixed;inset:0;z-index:9000;pointer-events:none;perspective:1800px}
.mb-turn i{position:absolute;top:8vh;bottom:8vh;left:50%;width:min(510px,48vw);background:linear-gradient(90deg,#e6d8b6,#f6eedb 30%);transform-origin:left center;border-radius:2px 10px 10px 2px;box-shadow:-10px 0 30px rgba(0,0,0,.25)}
.mb-turn.go i{animation:mbTurn .55s cubic-bezier(.5,0,.3,1) forwards}
@keyframes mbTurn{to{transform:rotateY(-180deg);filter:brightness(.8)}}
@media (max-width:760px){
  .mb{padding:8px 0 24px}
  .mb-book{grid-template-columns:1fr}.mb-gutter,.mb-book::after{display:none}.mb-book::before{right:6px;transform:none}
  .mb-page{min-height:0;padding:26px 18px 22px}.mb-page.l{border-radius:10px 10px 0 0;background:var(--mb-paper)}.mb-page.r{border-radius:0 0 10px 10px;background:var(--mb-paper);border-top:1px dashed #cdbb92}
  .mb-wm .t2{font-size:34px}.mb-crest{width:120px}.mb-foot{position:static;margin-top:14px}.mb-ds{max-height:none}
  .mb-turn i{width:92vw;left:4vw}
}
@media (prefers-reduced-motion:reduce){.mb *{animation:none!important;transition:none!important}}
"""
EDITS = [('end of <head> styles', '</style>\n</head>', None, 'css'), ('menuScreen: book menu first', 'function menuScreen(){\n  return `<div class="title-screen menu-landing">', 'function menuScreen(){\n  try{ if(typeof abcMbMenu===\'function\') return abcMbMenu(); }catch(e){}   /* fix_menu_book */\n  return `<div class="title-screen menu-landing">', None), ('JS insertion point (before menuScreen)', 'function menuScreen(){\n', None, 'js')]

for l,a,_,k in EDITS:
    n=s.count(a)
    if n!=1: sys.exit(f'{TAG} ERROR: anchor "{l}" found {n} times (expected 1). Nothing written.')
for l,a,rep,k in EDITS:
    if k=='css': rep='\n'+MARK+CSS+a
    elif k=='js': rep=JS+'\n'+a
    s=s.replace(a,rep,1)
for need in [MARK,'function abcMbMenu(','return abcMbMenu();','.mb-book{']:
    if need not in s: sys.exit(f'{TAG} ERROR: post-check failed ({need}). Nothing written.')
bak=SRC+'.bak_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); shutil.copyfile(SRC,bak)
open(SRC,'w',encoding='utf-8').write(s)
print(f'{TAG} Applied.  Backup:',bak); print(f'{TAG} Next: python3 build.py')
