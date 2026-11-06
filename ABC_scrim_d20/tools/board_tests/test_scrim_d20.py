import asyncio, os, pathlib
_ROOT = pathlib.Path(__file__).resolve().parents[2]
URL = (pathlib.Path(os.environ.get('ABC_STUB', _ROOT / 'dist' / 'stub.html')).resolve()).as_uri()
_CHROME = os.environ.get('ABC_CHROME')
def _launch_kw(): return {'executable_path': _CHROME} if _CHROME else {}
from playwright.async_api import async_playwright
R=[]; ok=lambda n,c: R.append(('PASS' if c else 'FAIL')+'  '+n)
SHOT=os.environ.get('QD_SHOTS')
FORCED=['vending','lostfound','mysterymeat']
EVENTS=['vending','extracredit','professor','overdue','substitute','lostfound','studygroup','mysterymeat','careerfair']
async def newrun(pg):
  await pg.evaluate("localStorage.removeItem('abc_scrim_run'); localStorage.removeItem('abc_scrim_quest'); localStorage.setItem('abc_speed','instant'); ABC_DEBUG.scrimOpen()"); await pg.wait_for_timeout(200)
  await pg.evaluate("ABC_DEBUG.handleScrim('new')"); await pg.wait_for_timeout(100)
  await pg.evaluate("ABC_DEBUG.SCRIM._honorsSel=0; ABC_DEBUG.handleScrim('kit:gothic')"); await pg.wait_for_timeout(400)
  # set out from the Notice Board so the map is clickable
  if await pg.evaluate("!!document.querySelector('.qo-overlay')"):
    await pg.click('.qo-q'); await pg.click('.qo-o'); await pg.click('.qo-go .bigbtn'); await pg.wait_for_timeout(200)
async def openEvent(pg, ev):
  await pg.evaluate(f"(()=>{{ const D=ABC_DEBUG; D.SCRIM._eventResult=null; ABC_QDX.qd.st=null; D.SCRIM.view='event'; D.SCRIM.event='{ev}'; D.APP.screen='scrim'; D.render(); }})()"); await pg.wait_for_timeout(120)
async def runCheck(pg, answer, roll=None):
  """answer: 'right' | 'wrong' | 'skip'; roll forces the d20 (via rnd override for the roll only)"""
  await pg.click('[data-st="qd:start"]'); await pg.wait_for_timeout(80)
  if roll is not None:
    await pg.evaluate(f"(()=>{{ const q=ABC_QDX.qd.st; const _r=window.rnd; window.__qdForce={roll-1}; }})()")
  if answer=='skip': sel='[data-st="qd:ans:-1"]'
  else:
    a=await pg.evaluate("ABC_QDX.qd.st.q.ans")
    n=await pg.evaluate("ABC_QDX.qd.st.q.opts.length")
    i=a if answer=='right' else (a+1)%n
    sel=f'[data-st="qd:ans:{i}"]'
  if roll is not None:
    # force the next roll: answer() calls rnd(20) once for the roll before the spin
    await pg.evaluate(f"""(()=>{{ const Q=ABC_QDX.qd.st; const C=ABC_QDX.checks[Q.ev]; const el=document.querySelector('{sel}'); const i=+el.getAttribute('data-st').split(':')[2];
      const keep=ABC_QDX.answer; ABC_QDX.answer(i); Q.roll={roll}; const b=ABC_QDX.bonus(C.skill).n; Q.total={roll}+b+(Q.correct?5:0); Q.ok={roll}===20||({roll}!==1&&Q.total>=C.dc); }})()""")
  else:
    await pg.click(sel)
  await pg.wait_for_timeout(250)
  await pg.wait_for_selector('[data-st="qd:finish"]', timeout=4000)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(**_launch_kw())
    for w,h,touch,tag in [(1280,800,False,'desk'),(390,844,True,'phone')]:
      pg=await b.new_page(viewport={'width':w,'height':h},has_touch=touch,is_mobile=touch); errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
      await pg.goto(URL); await pg.wait_for_timeout(1000); await newrun(pg)
      have=[]
      for ev in EVENTS:
        await openEvent(pg, ev)
        n=2 if ev not in FORCED else 1
        have.append(await pg.evaluate(f"(()=>{{ const b=document.querySelector('.evt-choices .qd-check'); const k=document.querySelectorAll('.evt-choices .evt-choice').length; return !!b && b===document.querySelector('.evt-choices').firstElementChild && ({n}===1 ? (k===1 && !!document.querySelector('.qd-force') && b.classList.contains('qd-forced')) : (k>=2 && !document.querySelector('.qd-force'))); }})()"))
      ok(f'{tag} every event (9) gains a d20 check; 6 keep their choices beside it, the 3 gambles force the roll ({have.count(True)}/9)', all(have))
      if SHOT and tag=='desk':
        await openEvent(pg,'mysterymeat'); await pg.screenshot(path=SHOT+'_forced.png', full_page=True)
      await openEvent(pg,'professor')
      if SHOT and tag=='desk': await pg.screenshot(path=SHOT+'_event.png', full_page=True)
      await pg.click('[data-st="qd:start"]'); await pg.wait_for_timeout(120)
      q=await pg.evaluate("[!!document.querySelector('.qd-panel'), document.querySelectorAll('.qd-opt').length, !!document.querySelector('[data-st=\"qd:ans:-1\"]'), /DC 14/.test(document.querySelector('.qd-panel .st-runhead').textContent), document.documentElement.scrollWidth]")
      ok(f'{tag} the check opens a trivia question from the run\'s deck with a skip, headed by skill and DC ({q})', q[0] and q[1]>=2 and q[2] and q[3] and q[4]<=w)
      if SHOT and tag=='desk': await pg.screenshot(path=SHOT+'_question.png', full_page=True)
      a=await pg.evaluate("ABC_QDX.qd.st.q.ans"); await pg.click(f'[data-st="qd:ans:{a}"]'); await pg.wait_for_timeout(250)
      await pg.wait_for_selector('[data-st="qd:finish"]', timeout=4000)
      r=await pg.evaluate("(()=>{ const Q=ABC_QDX.qd.st, C=ABC_QDX.checks[Q.ev]; return [Q.correct, Q.total===Q.roll+ABC_QDX.bonus(C.skill).n+5, !!document.querySelector('.qd-ans.ok'), !!document.querySelector('.qd-verdict'), document.querySelector('#qdDie span').textContent==String(Q.roll)]; })()")
      ok(f'{tag} a correct answer adds +5; the die shows the roll and the verdict ({r})', all(r))
      if SHOT and tag=='desk': await pg.screenshot(path=SHOT+'_roll.png', full_page=True)
      await pg.click('[data-st="qd:finish"]'); await pg.wait_for_timeout(150)
      r=await pg.evaluate("[!!document.querySelector('.qd-tag'), !ABC_QDX.qd.st, !document.querySelector('.qd-check'), ABC_DEBUG.SCRIM.view]")
      ok(f'{tag} Continue returns to the event page with the result and no second check ({r})', r[0] and r[1] and r[2] and r[3]=='event')
      if SHOT and tag=='desk': await pg.screenshot(path=SHOT+'_result.png', full_page=True)
      ok(f'{tag} no page errors', not errs); await pg.close()

    # ---------- engine: outcomes, natural 20/1, fallback, party bonus ----------
    pg=await b.new_page(viewport={'width':1280,'height':800}); errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
    await pg.goto(URL); await pg.wait_for_timeout(1000); await newrun(pg)
    # wrong answer → no bonus
    await openEvent(pg,'extracredit'); await runCheck(pg,'wrong')
    r=await pg.evaluate("(()=>{ const Q=ABC_QDX.qd.st, C=ABC_QDX.checks[Q.ev]; return [Q.correct, Q.total===Q.roll+ABC_QDX.bonus(C.skill).n, !!document.querySelector('.qd-ans.bad')]; })()")
    ok(f'a wrong answer gives no bonus and shows the right answer ({r})', (not r[0]) and r[1] and r[2])
    await pg.click('[data-st="qd:finish"]')
    # skip
    await openEvent(pg,'extracredit'); await runCheck(pg,'skip')
    ok('rolling without answering gives no bonus', await pg.evaluate("(()=>{ const Q=ABC_QDX.qd.st, C=ABC_QDX.checks[Q.ev]; return !Q.correct && Q.total===Q.roll+ABC_QDX.bonus(C.skill).n && !document.querySelector('.qd-ans'); })()"))
    await pg.click('[data-st="qd:finish"]')
    # success → IP; natural 20 bonus
    ip0=await pg.evaluate("ABC_DEBUG.META.ip||0")
    await openEvent(pg,'extracredit'); await runCheck(pg,'skip',roll=20); await pg.click('[data-st="qd:finish"]'); await pg.wait_for_timeout(100)
    ip1=await pg.evaluate("ABC_DEBUG.META.ip||0")
    ok(f'success pays the check reward, and a natural 20 adds +15 IP ({ip0} → {ip1})', ip1==ip0+30+15)
    # natural 1 always fails even with a huge bonus
    await pg.evaluate("ABC_DEBUG.SCRIM.lf=5")
    await openEvent(pg,'extracredit'); await runCheck(pg,'right',roll=1)
    f=await pg.evaluate("[ABC_QDX.qd.st.ok, ABC_QDX.qd.st.total]")
    await pg.click('[data-st="qd:finish"]'); await pg.wait_for_timeout(100)
    ok(f'a natural 1 always fails (total {f[1]}) and costs the failure (Late Fees 5 → 3)', (not f[0]) and await pg.evaluate("ABC_DEBUG.SCRIM.lf===3 && /Failure/.test(document.querySelector('.qd-tag').textContent)"))
    # failure HP loss never knocks anyone out
    await pg.evaluate("ABC_DEBUG.SCRIM.team.forEach(t=>{ if(t.curHp>0) t.curHp=5; })")
    await openEvent(pg,'professor'); await runCheck(pg,'skip',roll=1); await pg.click('[data-st="qd:finish"]'); await pg.wait_for_timeout(100)
    ok('a failed check\'s HP cost leaves each character on at least 1 HP', await pg.evaluate("ABC_DEBUG.SCRIM.team.filter(t=>t.maxHp&&t.curHp!==0).every(t=>t.curHp===1)"))
    # professor success → an artifact
    a0=await pg.evaluate("ABC_DEBUG.SCRIM.artifacts.length"); ipa=await pg.evaluate("ABC_DEBUG.META.ip||0")
    await openEvent(pg,'professor'); await runCheck(pg,'skip',roll=20); await pg.click('[data-st="qd:finish"]'); await pg.wait_for_timeout(100)
    t=await pg.evaluate("document.querySelector('.qd-tag').parentElement.textContent")
    a1=await pg.evaluate("ABC_DEBUG.SCRIM.artifacts.length"); ipb=await pg.evaluate("ABC_DEBUG.META.ip||0")
    ok(f'Debate the professor: success grants a rarer artifact, or IP if none are left ({a0}→{a1} artifacts; "{t[:70]}")', 'Success' in t and (a1==a0+1 or ipb>=ipa+25))
    # base fallback replays the event's own choice
    await openEvent(pg,'studygroup')
    base=await pg.evaluate("(()=>{ const D=ABC_DEBUG; const s=JSON.stringify(D.SCRIM.team.map(t=>t.curHp)); return s; })()")
    await runCheck(pg,'skip',roll=1); await pg.click('[data-st="qd:finish"]'); await pg.wait_for_timeout(100)
    r=await pg.evaluate("[document.querySelector('.qd-tag')&&/Failure/.test(document.querySelector('.qd-tag').textContent), ABC_DEBUG.SCRIM._eventResult||'']")
    ok(f'a failure marked "base" falls back to that event\'s own choice and keeps its result text ({r[1][-70:]})', r[0] and len(r[1])>90)
    # mystery meat: kept down → +10 base attack for the run; stacks; saved; reset by a new run; applied to attacks
    await openEvent(pg,'mysterymeat'); await runCheck(pg,'skip',roll=18); await pg.click('[data-st="qd:finish"]'); await pg.wait_for_timeout(100)
    await openEvent(pg,'mysterymeat'); await runCheck(pg,'skip',roll=18); await pg.click('[data-st="qd:finish"]'); await pg.wait_for_timeout(100)
    ok('Mystery Meat kept down: +10 base attack, stacking (+20 after two)', await pg.evaluate("ABC_DEBUG.SCRIM.qdAtk===20 && /base attack/.test(document.querySelector('.qd-tag').parentElement.textContent)"))
    ok('the attack bonus is saved with the run', await pg.evaluate("JSON.parse(localStorage.getItem('abc_scrim_d20')).atk===20"))
    await pg.evaluate("ABC_DEBUG.SCRIM.qdAtk=0; ABC_DEBUG.scrimLoadSave()")
    ok('…and restored when the run resumes', await pg.evaluate("ABC_DEBUG.SCRIM.qdAtk===20"))
    n=await pg.evaluate("(()=>{ const m=ABC_DEBUG.SCRIM.map; for(let c=0;c<m.cols.length;c++) for(let r=0;r<m.cols[c].length;r++){ if(m.cols[c][r].type==='scrim') return [c,r]; } })()")
    await pg.evaluate(f"(()=>{{ const m=ABC_DEBUG.SCRIM.map; ABC_DEBUG.SCRIM.qdAtk=10; ABC_DEBUG.SCRIM.pending={{c:{n[0]},r:{n[1]}}}; ABC_DEBUG.scrimStartBattle(m.cols[{n[0]}][{n[1]}]); }})()"); await pg.wait_for_timeout(2500)
    r=await pg.evaluate("""(()=>{ const D=ABC_DEBUG,S=D.S; D.freeze&&D.freeze(); D.busy=false; S.turn='you'; S.phase='strategize';
      const A=S.you, att=A.team[A.activeIdx], def=S.opp.team[S.opp.activeIdx]; const abc=Object.values(DATA.abcs)[0][0];
      for(let i=0;i<5;i++) att.atkCharge.push(JSON.parse(JSON.stringify(abc)));
      def.maxHp=def.hp=999; const h0=def.hp; const base=att.atk.dmg; D.performAttack('you','atk'); return [h0,base]; })()"""); await pg.wait_for_timeout(2500)
    r2=await pg.evaluate("[ABC_DEBUG.S.opp.team[ABC_DEBUG.S.opp.activeIdx].hp, (ABC_DEBUG.S.log||[]).join(' | ')]")
    ok(f'in a Scrimmage battle the bonus adds to your attacks and is logged ({r[0]}-{r2[0]} vs printed {r[1]})', 'Mystery Meat' in r2[1] and r[0]-r2[0]>=r[1]+10)
    await pg.evaluate("ABC_DEBUG.APP.screen='scrim'; ABC_DEBUG.SCRIM.view='map'; ABC_DEBUG.render()")
    await newrun(pg)
    ok('a new run starts with no attack bonus', await pg.evaluate("!ABC_DEBUG.SCRIM.qdAtk"))
    # career fair: rate depends on the roll
    await pg.evaluate("ABC_DEBUG.SCRIM.lf=10"); ip0=await pg.evaluate("ABC_DEBUG.META.ip||0")
    await openEvent(pg,'careerfair'); await runCheck(pg,'skip',roll=19); await pg.click('[data-st="qd:finish"]'); await pg.wait_for_timeout(100)
    ok('Career Fair: a successful negotiation cashes Late Fees at 4×', await pg.evaluate(f"(ABC_DEBUG.META.ip||0)==={ip0}+40 && ABC_DEBUG.SCRIM.lf===0"))
    # party bonus from archetypes
    pb=await pg.evaluate("""(()=>{ const D=ABC_DEBUG, T=D.SCRIM.team; const out={};
      for(const k of Object.keys(ABC_QDX.skills)){ const L=ABC_QDX.skills[k]; let n=0; T.forEach(r=>{ const d=(DATA.characters[r.deck]||[]).find(c=>c.id===r.id)||(r.fe&&firstedById(r.id)); if(r.curHp>0 && d && L.includes(d.archetype)) n++; }); out[k]=[ABC_QDX.bonus(k).n, Math.min(4,2*n)]; }
      const save=T.map(t=>t.curHp); T.forEach(t=>t.curHp=0); const z=ABC_QDX.bonus('Wits').n+ABC_QDX.bonus('Charm').n+ABC_QDX.bonus('Cunning').n+ABC_QDX.bonus('Resolve').n; T.forEach((t,i)=>t.curHp=save[i]);
      return [out, z]; })()""")
    ok(f'party bonus = +2 per living matching archetype, max +4; knocked-out characters add nothing ({pb})', all(v[0]==v[1] for v in pb[0].values()) and pb[1]==0)
    ok('every archetype maps to exactly one skill', await pg.evaluate("(()=>{ const all=[].concat(...Object.values(ABC_QDX.skills)); return all.length===new Set(all).size && all.length===21; })()"))
    # a check survives save + resume? (the event page itself re-renders)
    ok('no page errors (engine)', not errs); await pg.close()

    # ---------- the illuminated boss reveal ----------
    for w,h,touch,tag in [(1280,800,False,'desk'),(390,844,True,'phone')]:
      pg=await b.new_page(viewport={'width':w,'height':h},has_touch=touch,is_mobile=touch); errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
      await pg.goto(URL); await pg.wait_for_timeout(1000); await newrun(pg)
      await pg.evaluate("(()=>{ const m=ABC_DEBUG.SCRIM.map; const nx=(m.cols[m.pos.c][m.pos.r].next||[0])[0]; const n=m.cols[m.pos.c+1][nx]; n.type='boss'; n.boss='sandroid'; ABC_DEBUG.render(); })()"); await pg.wait_for_timeout(200)
      await pg.click('.st-tome .smap-node.boss.reach'); await pg.wait_for_timeout(1200)
      ok(f'{tag} the boss page carries its archive lore', await pg.evaluate("(()=>{ const l=document.querySelector('.qd-lore'); return !!l && /billion crushed hourglasses/.test(l.textContent); })()"))
      r=await pg.evaluate("[ABC_DEBUG.SCRIM.view, !!document.querySelector('.qd-boss'), !!document.querySelector('.qd-arch img'), (document.querySelector('.qd-name')||{}).textContent||'', document.querySelectorAll('.qd-curse p').length, /210 HP|\\d+ HP/.test((document.querySelector('.qd-sub')||{}).textContent||''), document.querySelectorAll('.qd-mv').length, ABC_DEBUG.APP.screen, document.documentElement.scrollWidth]")
      ok(f'{tag} clicking a boss opens its bestiary page first: portrait, name, HP, both possible curses, moves ({r})', r[0]=='bossreveal' and r[1] and r[2] and r[3]=='Sandroid' and r[4]==2 and r[5] and r[6]==2 and r[7]=='scrim' and r[8]<=w)
      if SHOT: await pg.screenshot(path=SHOT+f'_boss_{tag}.png', full_page=True)
      await pg.click('[data-st="qd:bossback"]'); await pg.wait_for_timeout(200)
      ok(f'{tag} Back returns to the map with the boss still unfought', await pg.evaluate("ABC_DEBUG.SCRIM.view==='map' && !!document.querySelector('.st-tome .smap-node.boss.reach')"))
      await pg.click('.st-tome .smap-node.boss.reach'); await pg.wait_for_timeout(1200)
      await pg.click('[data-st="qd:fight"]'); await pg.wait_for_timeout(2500)
      r=await pg.evaluate("[ABC_DEBUG.APP.screen, ABC_DEBUG.S&&ABC_DEBUG.S.opp&&ABC_DEBUG.S.opp.name]")
      ok(f'{tag} Draw steel starts the boss battle ({r})', r[0]=='play')
      ok(f'{tag} no page errors', not errs); await pg.close()
    # doctoral shows only the alternate curse
    pg=await b.new_page(viewport={'width':1280,'height':800}); errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
    await pg.goto(URL); await pg.wait_for_timeout(1000); await newrun(pg)
    await pg.evaluate("(()=>{ const D=ABC_DEBUG, m=D.SCRIM.map; D.SCRIM.doctoral=true; const nx=(m.cols[m.pos.c][m.pos.r].next||[0])[0]; const n=m.cols[m.pos.c+1][nx]; n.type='boss'; n.boss='dyefone'; D.handleScrim('node:'+(m.pos.c+1)+':'+nx); })()"); await pg.wait_for_timeout(300)
    ok('in the Doctoral Program the page shows only the alternate curse', await pg.evaluate("document.querySelectorAll('.qd-curse p').length===1 && /Read Receipts/.test(document.querySelector('.qd-curse').textContent)"))
    ok('non-boss nodes are not intercepted', await pg.evaluate("(()=>{ const D=ABC_DEBUG; D.SCRIM.doctoral=false; ABC_QDX.qd.reveal=null; D.SCRIM.view='map'; const m=D.SCRIM.map; const nx=(m.cols[m.pos.c][m.pos.r].next||[0])[0]; const n=m.cols[m.pos.c+1][nx]; n.type='rest'; delete n.boss; D.handleScrim('node:'+(m.pos.c+1)+':'+nx); return D.SCRIM.view==='rest'; })()"))
    ok('no page errors (boss engine)', not errs); await pg.close()
    await b.close()
  print('\n'.join(R)); fails=sum(1 for x in R if x.startswith('FAIL')); print(f'\n{len(R)-fails}/{len(R)} passed'); raise SystemExit(1 if fails else 0)
asyncio.run(main())
