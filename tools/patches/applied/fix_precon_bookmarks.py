#!/usr/bin/env python3
"""
fix_precon_bookmarks.py — the 13 precon Bookmarks the digital game was missing,
plus the Gatsby 1E passive rework.

1. DATA.bookmarks: +13 cards, appended at the END so every existing index (and
   every saved deck) is unchanged.  Generated from the catalog.
     reskins of existing effects : The Nurse's Errand, A Plague on Both Your
       Houses, Forty-Two Hours, The Valley of Ashes, The Green Light, Repeat the Past
     new effects                 : Dramatis Personae (searchchar); Plot Summary,
       The Prologue, Boats Against the Current (searchact); Inciting Incident
       (incite); In Medias Res (inmedias); Character Study (charstudy)
   All 13 carry pool:false — they never appear in random loadouts, opponent
   loadouts, packs, Scrimmage rewards, or locked builder rows / collection
   totals.  They exist for the precons (and sandbox).
2. The four new effects, in playBookmark() and bmPlayable() (the AI's gate).
   * Inciting Incident: Active takes 20 (refused if that would KO it); its
     Plot Point 1 counts as met.
   * In Medias Res: this turn, one Act II card with the "took damage" trigger
     may evolve without it.  Climax-gated cards are never affected.
   * Only one evolution-speeding Bookmark per turn (both cards).
   * The AI retries its Act cards right after playing any of these.
3. Gatsby 1E (The Colossal Illusion): was +1 free, no-trivia attach every turn
   onto ANY character.  Now: once per turn, after a correct trivia attach, one
   extra ABC may attach to Gatsby himself, free of trivia (player and AI).

USAGE (repo root):  python3 fix_precon_bookmarks.py   then   python3 build.py
Writes src/game.src.html.bak.  Refuses to run twice.
"""
import os, shutil, sys
SRC = os.path.join('src', 'game.src.html')
NEW_BM = "    { id:\"nurseerrand\", name:\"The Nurse's Errand\", kind:\"UTILITY\", rarity:\"U\", pool:false, text:\"Return any 1 card from your discard pile to your hand. You cannot attack this turn.\", effect:\"bookreturn\" },\n    { id:\"bothhouses\", name:\"A Plague on Both Your Houses\", kind:\"SUPPORT\", rarity:\"U\", pool:false, text:\"If you knock out an enemy character this turn, draw 2 cards.\", effect:\"extracredit\" },\n    { id:\"fortytwohours\", name:\"Forty-Two Hours\", kind:\"SUPPORT\", rarity:\"E\", pool:false, text:\"Until the start of your next turn, neither Active character can drop below 1 HP.\", effect:\"cliffhanger\" },\n    { id:\"incitingincident\", name:\"Inciting Incident\", kind:\"SUPPORT\", rarity:\"C\", pool:false, text:\"Your Active takes 20 damage. Its Plot Point 1 counts as met this turn. Only one evolution-speeding Bookmark per turn.\", effect:\"incite\" },\n    { id:\"inmediasres\", name:\"In Medias Res\", kind:\"UTILITY\", rarity:\"R\", pool:false, text:\"Play one Act II card this turn without meeting Plot Point 1. Its climax question, if it has one, must still be answered. Only one evolution-speeding Bookmark per turn.\", effect:\"inmedias\" },\n    { id:\"characterstudy\", name:\"Character Study\", kind:\"BOOST\", rarity:\"U\", pool:false, text:\"If your Active has reached Act II or beyond, heal it 30 HP and draw a card.\", effect:\"charstudy\" },\n    { id:\"dramatispersonae\", name:\"Dramatis Personae\", kind:\"UTILITY\", rarity:\"C\", pool:false, text:\"Search your deck for 1 character card that is not an Act card, reveal it, and add it to your hand. Then shuffle your deck.\", effect:\"searchchar\" },\n    { id:\"plotsummary\", name:\"Plot Summary\", kind:\"UTILITY\", rarity:\"U\", pool:false, text:\"Search your deck for 1 Act card, reveal it, and add it to your hand. Then shuffle your deck.\", effect:\"searchact\" },\n    { id:\"theprologue\", name:\"The Prologue\", kind:\"UTILITY\", rarity:\"C\", pool:false, text:\"Search your deck for 1 Act card, reveal it, and add it to your hand. Then shuffle your deck.\", effect:\"searchact\" },\n    { id:\"boatsagainst\", name:\"Boats Against the Current\", kind:\"UTILITY\", rarity:\"C\", pool:false, text:\"Search your deck for 1 Act card, reveal it, and add it to your hand. Then shuffle your deck.\", effect:\"searchact\" },\n    { id:\"valleyofashes\", name:\"The Valley of Ashes\", kind:\"ITEM\", rarity:\"C\", pool:false, text:\"Both Active characters lose 20 HP at the start of the next 2 turns.\", effect:\"poison\" },\n    { id:\"greenlight\", name:\"The Green Light\", kind:\"BOOST\", rarity:\"U\", pool:false, text:\"Give one character ✨ Highlight. That character's next attack deals +20 damage.\", effect:\"horizonspromise\" },\n    { id:\"repeatthepast\", name:\"Repeat the Past\", kind:\"RESET\", rarity:\"E\", pool:false, text:\"Reattach up to 2 Attack and 2 Block ABC from your discard onto your Active, free of trivia.\", effect:\"restoration\" }"

CASES = r"""    case 'searchchar': case 'searchact':{   /* fix_precon_bookmarks */
      remove();
      const _wantAct=card.effect==='searchact';
      const _ok=_wantAct?function(c){ return c.cat==='act'; }:function(c){ return c.cat==='char'; };
      const finish=(i)=>{ if(i!=null && i>=0){ const c=P.deck.splice(i,1)[0]; if(c){ c._new=true; P.hand.push(c); pushLog(`${who(P)} searches the deck \u2014 ${lbl(c)} to hand.`); } }
        else pushLog(`${card.name}: nothing to find.`);
        P.deck=shuffle(P.deck); if(!isYou) P.flags._aiEvoRetry=true; commit(); render&&render(); };
      const hits=P.deck.map((c,i)=>({c,i})).filter(o=>_ok(o.c));
      if(!hits.length){ finish(-1); return; }
      if(isYou && hits.length>1) askPick(card.name+' \u2014 which card?', hits.map(o=>({label:lbl(o.c)+(o.c.cat==='act'?' (Act '+roman(o.c.act)+')':''),val:o.i})), finish);
      else { let best=hits[0];
        if(_wantAct){ const on=hits.find(o=>{ const z=actById(o.c.actId); return z && P.team.some(t=>t.hp>0 && actStageId(t)===z.from); }); if(on) best=on; }
        finish(best.i); }
      return;
    }
    case 'incite':{
      if(P.flags._evoBmTurn===(S._turnNo||0)){ if(isYou) toast('Only one evolution-speeding Bookmark per turn.'); return; }
      if(!act || act.hp<=20){ if(isYou) toast(`${act?act.name:'Your Active'} cannot take 20 damage.`); return; }
      remove(); P.flags._evoBmTurn=(S._turnNo||0);
      applyDmg(act,20); act._tookHit=true; if(!isYou) P.flags._aiEvoRetry=true;
      pushLog(`${card.name}: ${act.name} takes 20 \u2014 Plot Point 1 is met.`); break;
    }
    case 'inmedias':{
      if(P.flags._evoBmTurn===(S._turnNo||0)){ if(isYou) toast('Only one evolution-speeding Bookmark per turn.'); return; }
      remove(); P.flags._evoBmTurn=(S._turnNo||0); P.flags._inMediasTurn=(S._turnNo||0); if(!isYou) P.flags._aiEvoRetry=true;
      pushLog(`${card.name}: one Act II card may skip Plot Point 1 this turn. Climax questions still apply.`); break;
    }
    case 'charstudy':{
      if(!act || !(act.act>=2)){ if(isYou) toast(`${act?act.name:'Your Active'} has not reached Act II.`); return; }
      remove(); const _h=healChar(act,30); drawN(side,1);
      pushLog(`${card.name}: ${act.name} heals ${_h} HP and ${who(P)} draws a card.`); break;
    }
    case 'cardcatalog':{"""

GATES = r"""    case 'searchchar': return (p.deck||[]).some(x=>x.cat==='char');
    case 'searchact':  return (p.deck||[]).some(x=>x.cat==='act');
    case 'incite':     return p.flags._evoBmTurn!==(S._turnNo||0) && !!(a&&a.hp>20&&!a._tookHit) &&
                         p.hand.some(x=>{ if(x.cat!=='act') return false; const z=actById(x.actId); return z&&z.plot==='hit'&&z.from===actStageId(a); });
    case 'inmedias':   return p.flags._evoBmTurn!==(S._turnNo||0) &&
                         p.hand.some(x=>{ if(x.cat!=='act') return false; const z=actById(x.actId); return z&&z.act===2&&z.plot==='hit'&&p.team.some(t=>t.hp>0&&!t._tookHit&&(t.turnsInPlay||0)>=1&&actStageId(t)===z.from); });
    case 'charstudy':  return !!(a&&a.hp>0&&a.act>=2);
    default: return true;"""

EDITS = [
 ('DATA.bookmarks — append 13', "\n  ],\n  // -------- 1ST EDITION (Commander) CARDS --------",
  "\n" + NEW_BM + "\n  ],\n  // -------- 1ST EDITION (Commander) CARDS --------", 1),
 ('playBookmark — new effects', "    case 'cardcatalog':{", CASES, 1),
 ('bmPlayable — new gates', "    default: return true;", GATES, 1),
 ('actCanEvolve — In Medias Res',
  "  if(a.plot==='hit' && !c._tookHit) return",
  "  if(a.plot==='hit' && !c._tookHit && !(a.act===2 && S && ((S.you.team.indexOf(c)>=0?S.you:S.opp).flags||{})._inMediasTurn===(S._turnNo||0))) return", 1),
 ('actEvolve — consume In Medias Res',
  "  const taken=Math.max(0,c.maxHp-c.hp), from=c.name;",
  "  if(a.plot==='hit' && !c._tookHit && p.flags && p.flags._inMediasTurn===(S._turnNo||0)){ p.flags._inMediasTurn=null; pushLog('In Medias Res \\u2014 the story starts mid-scene.'); }\n"
  "  const taken=Math.max(0,c.maxHp-c.hp), from=c.name;", 1),
 ('AI — retry Act cards after an evolution Bookmark',
  "      if(bi>=0 && (p.flags.bmCount||0)<2){ try{ playBookmark('opp',bi); }catch(e){} }",
  "      if(bi>=0 && (p.flags.bmCount||0)<2){ try{ playBookmark('opp',bi); }catch(e){} }\n"
  "      if(p.flags._aiEvoRetry){ p.flags._aiEvoRetry=false; try{ actAiTurn(p); }catch(e){} }", 1),
 ('pool:false — random/opponent loadouts',
  "function bmIdxByRarity(rs){ const o=[]; DATA.bookmarks.forEach((b,i)=>{ if(rs.includes(bmRarity(b))) o.push(i); }); return o; }",
  "function bmIdxByRarity(rs){ const o=[]; DATA.bookmarks.forEach((b,i)=>{ if(b.pool!==false && rs.includes(bmRarity(b))) o.push(i); }); return o; }", 1),
 ('pool:false — packs',
  "      C:DATA.bookmarks.map(function(b,i){return {k:'bm',id:i,name:b.name};}),",
  "      C:DATA.bookmarks.map(function(b,i){return {k:'bm',id:i,name:b.name,_np:b.pool===false};}).filter(function(o){ return !o._np; }),", 1),
 ('pool:false — Scrimmage rewards',
  "    else if(r2<0.85){ out.push({t:'bm',i:rnd(DATA.bookmarks.length)}); }",
  "    else if(r2<0.85){ const _bp=DATA.bookmarks.map((b,i)=>b.pool===false?-1:i).filter(i=>i>=0); out.push({t:'bm',i:_bp[rnd(_bp.length)]}); }", 1),
 ('pool:false — hide locked builder rows',
  "    if(bmOwned(i)<1) return `<div class=\"bd-bm lockcard\">",
  "    if(b.pool===false && bmOwned(i)<1) return '';\n    if(bmOwned(i)<1) return `<div class=\"bd-bm lockcard\">", 1),
 ('pool:false — collection totals',
  "  var bmT=DATA.bookmarks.length,",
  "  var bmT=DATA.bookmarks.filter(function(b){ return b.pool!==false; }).length,", 1),
 ('Gatsby 1E — new flag', ", freeAttach:1, spillLock:true}", ", bonusAttachOnCorrect:true, spillLock:true}", 1),
 ('Gatsby 1E — reset each turn', "  p.flags.feFree = _feFree;", "  p.flags.feFree = _feFree; p.flags.feFreeTo = null;", 1),
 ('Gatsby 1E — grant after a correct attach',
  "    p.critTurn.correct=(p.critTurn.correct||0)+1;",
  "    p.critTurn.correct=(p.critTurn.correct||0)+1;\n"
  "    if(!p.flags._freeNow){ const _gb=p.team.find(c=>c.hp>0&&c.fe&&c.passive&&c.passive.bonusAttachOnCorrect);\n"
  "      if(_gb && p.flags._gbTurn!==(S._turnNo||0)){ p.flags._gbTurn=(S._turnNo||0); p.flags.feFree=(p.flags.feFree||0)+1; p.flags.feFreeTo=_gb.uid;\n"
  "        pushLog(`${_gb.passive.name}: one more ABC may attach to ${_gb.name}, free of trivia.`); } }", 1),
 ('Gatsby 1E — player: attach count',
  "  if(p.attachesLeft<=0){ toast('No attaches left this turn.'); return; }",
  "  const _gFree=(p.flags.feFree||0)>0 && card.cat==='abc' && !!p.flags.feFreeTo && ((targetUid||(active(p)||{}).uid)===p.flags.feFreeTo);\n"
  "  if(p.attachesLeft<=0 && !_gFree){ toast('No attaches left this turn.'); return; }", 1),
 ('Gatsby 1E — player: free attach goes to Gatsby only',
  "  if((p.flags.feFree||0)>0 && card.cat==='abc'){ p.flags.feFree--;",
  "  if((p.flags.feFree||0)>0 && card.cat==='abc' && p.flags.feFreeTo && tgt.uid===p.flags.feFreeTo){ p.flags.feFree--; p.flags.feFreeTo=null; p.attachesLeft++; p.flags._freeNow=true; pushLog('The Colossal Illusion \\u2014 free attach.'); attach('you',idx,true,tgt.uid); p.flags._freeNow=false; return; }\n"
  "  if((p.flags.feFree||0)>0 && card.cat==='abc' && !p.flags.feFreeTo){ p.flags.feFree--;", 1),
 ('Gatsby 1E — AI: use the free attach on Gatsby',
  "        const useFree=(p.flags.feFree||0)>0 && p.hand[pick] && p.hand[pick].cat==='abc'; if(useFree) p.flags.feFree--;",
  "        const useFree=(p.flags.feFree||0)>0 && p.hand[pick] && p.hand[pick].cat==='abc'; const _ft=useFree?(p.flags.feFreeTo||null):null; if(useFree){ p.flags.feFree--; if(_ft){ p.flags.feFreeTo=null; p.attachesLeft++; } }", 1),
 ('Gatsby 1E — AI: may still use the free attach with no attaches left',
  "if(p.attachesLeft>0 && pick>=0 && guard<9){ guard++;",
  "if((p.attachesLeft>0 || ((p.flags.feFree||0)>0 && p.flags.feFreeTo)) && pick>=0 && guard<9){ guard++;", 1),
 ('Gatsby 1E — AI: target',
  "        attach('opp',pick,ok||!S.settings.triviaOn); setTimeout(step,400);",
  "        p.flags._freeNow=useFree; attach('opp',pick,ok||!S.settings.triviaOn,_ft||undefined); p.flags._freeNow=false; setTimeout(step,400);", 1),
]

def main():
    if not os.path.exists(SRC): sys.exit('Run from the repo root: %s not found.' % SRC)
    s = open(SRC, encoding='utf-8').read()
    if 'romeojuliet' not in s: sys.exit('This is not the live src/game.src.html.')
    if 'case \'searchact\'' in s or 'id:"dramatispersonae"' in s: sys.exit('Already applied. Nothing changed.')
    if 'romeo_husband_of_juliet' not in s: sys.exit('Run fix_precon_acts.py first. Nothing changed.')
    for label, a, _, n in EDITS:
        if s.count(a) != n: sys.exit('Anchor "%s" found %d times (need %d). Nothing changed.' % (label, s.count(a), n))
    for _, a, b, _ in EDITS: s = s.replace(a, b)
    shutil.copy2(SRC, SRC + '.bak')
    open(SRC, 'w', encoding='utf-8').write(s)
    print('fix_precon_bookmarks: +13 Bookmarks, 4 new effects, Gatsby 1E reworked. Backup: %s.bak' % SRC)
if __name__ == '__main__': main()
