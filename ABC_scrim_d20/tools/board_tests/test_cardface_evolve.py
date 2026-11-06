import asyncio, os, pathlib
_ROOT = pathlib.Path(__file__).resolve().parents[2]
URL = (pathlib.Path(os.environ.get('ABC_STUB', _ROOT / 'dist' / 'stub.html')).resolve()).as_uri()
_CHROME = os.environ.get('ABC_CHROME')
def _launch_kw(): return {'executable_path': _CHROME} if _CHROME else {}
from playwright.async_api import async_playwright
R=[]; ok=lambda n,c: R.append(('PASS' if c else 'FAIL')+'  '+n)
SETUP="""(elig=>{ const D=ABC_DEBUG,S=D.S,P=S.you; D.freeze(); D.busy=false; S.turn='you'; S.phase='strategize';
  const ids=P.team.filter(c=>c.hp>0).map(c=>c.id);
  const a=DATA.acts.find(x=>x.act===2 && ids.indexOf(x.from)>=0 && x.plot!=='climaxQ'); if(!a) return null;
  const tgt=P.team.filter(c=>c.id===a.from && c.hp>0); const t=tgt.find(c=>P.team.indexOf(c)!==P.activeIdx)||tgt[0];
  P.team.forEach(c=>{ c.turnsInPlay=elig?2:0; c._tookHit=true; });
  P.hand.unshift({cat:'act', actId:a.id, name:a.name, act:a.act, deck:a.deck, cid:'tst_evo', _new:false}); D.render();
  return {aname:a.name, uid:t.uid, onBench:P.team.indexOf(t)!==P.activeIdx}; })"""
GRAB="""(()=>{ const el=document.querySelector('#game .hand .hc[data-idx="0"]'); const r=el.getBoundingClientRect();
  for(const fy of [0.35,0.2,0.5,0.65]) for(const fx of [0.1,0.25,0.5,0.75]){ const x=r.left+r.width*fx, y=r.top+r.height*fy, h=document.elementFromPoint(x,y); if(h && h.closest('.hc')===el && !h.closest('button')) return [x,y]; }
  return [r.left+12, r.top+r.height*0.35]; })()"""
CEN="(s=>{ const r=document.querySelector(s).getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2]; })"
async def fresh(b,w=1280,h=800,touch=False):
  pg=await b.new_page(viewport={'width':w,'height':h},has_touch=touch,is_mobile=touch); pg._e=[]; pg.on('pageerror',lambda e: pg._e.append(str(e)))
  await pg.goto(URL); await pg.wait_for_timeout(1000); await pg.evaluate("ABC_DEBUG.startBattle()"); await pg.wait_for_timeout(3000); return pg
async def evo(b, elig):
  pg=await fresh(b); info=await pg.evaluate(SETUP, elig)
  if not info: ok('an Act II card fits this match', False); return
  sel=f'#game .bench-mini[data-benchinfo="you:{info["uid"]}"]' if info['onBench'] else f'#game .char.you[data-charuid="{info["uid"]}"]'
  a=await pg.evaluate(GRAB); t=await pg.evaluate(CEN, sel)
  await pg.mouse.move(*a); await pg.mouse.down()
  for k in range(1,9): await pg.mouse.move(a[0]+(t[0]-a[0])*k/8, a[1]+(t[1]-a[1])*k/8); await pg.wait_for_timeout(16)
  await pg.wait_for_timeout(60)
  chips=await pg.evaluate("[...document.querySelectorAll('.dd-chip.hot')].map(c=>c.textContent).join('|')")
  # record every toast as it appears (it can come and go before a busy machine reads it)
  await pg.evaluate("(()=>{ window.__toasts=[]; const t=document.getElementById('toast'); if(!t||window.__toastObs) return; window.__toastObs=new MutationObserver(()=>{ if(t.textContent) window.__toasts.push(t.textContent); }); window.__toastObs.observe(t,{childList:true,characterData:true,subtree:true}); })()")
  await pg.mouse.up(); await pg.wait_for_timeout(700)
  if not elig:
    try: await pg.wait_for_function("(window.__toasts||[]).length || ((document.getElementById('toast')||{}).textContent||'')", timeout=3000)
    except Exception: pass
  r=await pg.evaluate(f"(()=>{{ const c=ABC_DEBUG.S.you.team.find(x=>x.uid==='{info['uid']}'); return [c.name, c.act||1, ABC_DEBUG.S.you.hand.some(h=>h.cid==='tst_evo'), ((window.__toasts||[]).join(' / '))||(document.getElementById('toast')||{{}}).textContent||'']; }})()")
  if elig:
    ok(f'evolution card dropped on {"a Backstage" if info["onBench"] else "the Active"} character evolves THAT character ({chips} → {r[0]})', 'Evolve' in chips and r[0]==info['aname'] and r[1]==2 and not r[2])
  else:
    ok(f'not-yet character: red reason, drop refused with the reason shown ({chips[:50]}…; toast "{r[3][:40]}")', 'next turn' in chips and r[1]==1 and r[2] and 'next turn' in r[3])
  ok(f'no page errors ({"eligible" if elig else "not yet"})', not pg._e); await pg.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(**_launch_kw())
    for w,h,touch,tag in [(1280,800,False,'desk'),(390,844,True,'phone')]:
      pg=await fresh(b,w,h,touch)
      await pg.evaluate("ABC_DEBUG.freeze(); ABC_DEBUG.busy=false; ABC_DEBUG.render()"); await pg.wait_for_timeout(200)
      for side in ['you','opp']:
        r=await pg.evaluate(f"""(()=>{{ const ch=document.querySelector('.side .char.{side}'); if(!ch) return null; const h=ch.querySelector('.pfs-hp'), a=ch.querySelector('.pfs-arch'); const c=ch.getBoundingClientRect(), ar=a&&a.getBoundingClientRect(); const S=ABC_DEBUG.S[{repr(side)}], m=S.team[S.activeIdx];
          return {{pf:ch.classList.contains('pf'), hp:h&&h.textContent, want:m.maxHp+'HP', arch:a&&a.textContent, wantA:m.archetype, right:!!ar && ar.left>c.left+c.width*0.75, vert:!!a && getComputedStyle(a.firstElementChild).writingMode==='vertical-rl'}}; }})()""")
        ok(f'{tag} {side} Active: max HP + archetype on the right strip ({r})', bool(r) and (not r['pf'] or (r['hp']==r['want'] and r['arch']==r['wantA'] and r['right'] and r['vert'])))
      ok(f'{tag} Backstage minis skip the strip', await pg.evaluate("document.querySelectorAll('.bench-mini .pfs-arch, .bench-mini .pfs-hp').length===0"))
      img=await pg.evaluate("(()=>{ const i=document.querySelector('.deckstack .cardback.top .cb-img'); return i?{w:i.naturalWidth,h:i.naturalHeight,src:i.src.slice(0,15)}:null; })()")
      ok(f'{tag} deck shows the new card back ({img})', bool(img) and img['w']==375 and img['h']==525)
      ok(f'{tag} no page errors', not pg._e); await pg.close()
    await evo(b,True); await evo(b,False)
    print('\n'.join(R)); print(sum(r.startswith('PASS') for r in R),'/',len(R)); globals()['_FAILS']=sum(r.startswith('FAIL') for r in R); await b.close()
asyncio.run(main())
import sys; sys.exit(1 if globals().get('_FAILS') else 0)
