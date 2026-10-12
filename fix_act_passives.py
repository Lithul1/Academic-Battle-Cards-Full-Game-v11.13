#!/usr/bin/env python3
"""
fix_act_passives.py — makes the Act-card passives work.  Before this patch only
"can't be healed" and "+20 below half health" (Macbeth's pilot) were wired.

PASSIVE                     CARD                         ENGINE FLAGS
Headlong                    Fortune's Fool (Romeo III)   entryAtkAdd 20 (the turn it evolves), recoil 10
Her Own Hand                O Happy Dagger (Juliet III)  statusedAtkAdd 20, noSelfCleanse
Grave Man                   Worms' Meat (Mercutio II)    inflictAtkAdd 10, spillLock
King of Cats                Prince of Cats (Tybalt II)   costMod -1 (attack + block, min 1), noHealAbove
Golden Statues              The Reconciled (Capulets II) healTurn 10, dmgCap 40
Platonic Conception         Doomed Dreamer (Gatsby III)  peekOwnDeck, koDiscardRandom
So We Beat On               Westward Traveler (Nick III) onAllyKO.attachFromDiscard 1, noBlockOnEvolve
Given Time                  Careless Fool (Daisy III)    retaliate 20, retaliateSelf 10
Cursed Crown                Fallen Ashes (Myrtle II)     koRetaliate 40, noBlockAfterAttack
The Eyes of T. J. Eckleburg Tragic Avenger (George II)   vsKillerOf "myrtle" + dmgAdd 30, noHeal

Four cards already carry their flags (from the catalog's passive_json); this
patch adds the flags to the other six Act passives and wires all ten.

RULINGS (flagged for review)
  * "the turn it evolves or enters play"  = the turn it evolved.
  * "starting health" (King of Cats)      = its HP at the moment it evolved.
  * "cannot block on the turn it attacks / evolves": blocks happen on the
    OPPONENT's turn, so read literally these do nothing.  Implemented as
    "can't block during the opponent's next turn".
  * "can never clear a status from itself": its own block cleanses and any
    cleanse that targets it (Proofread, team cleanses) skip it.  Permanent
    locks still apply.
  * "Whoever knocks it out takes 40": the attacker whose attack KO'd it.
  * "attack ... knocked out Myrtle Wilson": tracked per attacker, any form of
    Myrtle (base or Fallen Ashes).

USAGE (repo root, after fix_precon_acts.py):
  python3 fix_act_passives.py      then   python3 build.py
Writes src/game.src.html.bak.  Refuses to run twice.
"""
import os, shutil, sys
SRC = os.path.join('src', 'game.src.html')
MARK = '/* Act passives (fix_act_passives) */'

FLAGS = {   # passive id -> JS text appended inside the passive object
    'grave_man':           'inflictAtkAdd:10, spillLock:true',
    'king_of_cats':        'costMod:-1, noHealAbove:true',
    'golden_statues':      'healTurn:10, dmgCap:40',
    'platonic_conception': 'peekOwnDeck:true, koDiscardRandom:true',
    'given_time':          'retaliate:20, retaliateSelf:10',
    'cursed_crown':        'koRetaliate:40, noBlockAfterAttack:true',
}

ATK_BONUS = r"""  if(att.act>1&&att.passive){ const _P=att.passive;   """ + MARK + r"""
    if(_P.entryAtkAdd && (att.turnsInPlay||0)===0){ dmg+=_P.entryAtkAdd; pushLog(`${_P.name}: +${_P.entryAtkAdd} on the turn it evolves.`); }
    if(_P.statusedAtkAdd && STATUS_NEG.some(function(x){ return att.status[x]; })){ dmg+=_P.statusedAtkAdd; pushLog(`${_P.name}: +${_P.statusedAtkAdd} while ${att.name} carries a negative status.`); }
    if(_P.inflictAtkAdd && (ab.inflict||ab.inflictChoice||ab.siphon||ab.inflictIfHas)){ dmg+=_P.inflictAtkAdd; pushLog(`${_P.name}: +${_P.inflictAtkAdd} on an attack that afflicts.`); }
    if(_P.vsKillerOf && def && (def._killedIds||[]).indexOf(_P.vsKillerOf)>=0){ dmg+=(_P.dmgAdd||0); pushLog(`${_P.name}: +${_P.dmgAdd||0} \u2014 ${def.name} knocked out ${actStageName(_P.vsKillerOf)}.`); }
  }
"""

EDITS = [  # (label, anchor, replacement, count)
 ('attack bonuses (Headlong / Her Own Hand / Grave Man / Eckleburg)',
  "  if(att.act>1&&att.passive&&att.passive.lowHpAtkAdd&&att.hp>0&&att.hp<att.maxHp/2){",
  ATK_BONUS + "  if(att.act>1&&att.passive&&att.passive.lowHpAtkAdd&&att.hp>0&&att.hp<att.maxHp/2){", 1),
 ('damage cap (Golden Statues)',
  "  S.lastAtk={ side:side, name:ab.n,",
  "  if(att.act>1&&att.passive&&att.passive.dmgCap&&net>att.passive.dmgCap){ net=att.passive.dmgCap; pushLog(`${att.passive.name}: ${att.name} can deal at most ${net} in one attack.`); }\n"
  "  S.lastAtk={ side:side, name:ab.n,", 1),
 ('recoil (Headlong) + attacker pays (Given Time)',
  "  if(ab.sacrifice && !symbolsOff(side)){ const _sac=applyDmg(att,ab.sacrifice);",
  "  if(att.act>1&&att.passive&&att.passive.recoil&&att.hp>0){ const _rc=applyDmg(att,att.passive.recoil); if(_rc>0) pushLog(`${att.passive.name}: ${att.name} takes ${_rc} recoil.`); }\n"
  "  if(def.act>1&&def.passive&&def.passive.retaliate&&att.hp>0){ const _rt=applyDmg(att,def.passive.retaliate); pushLog(`${def.passive.name}: ${att.name} takes ${_rt} for attacking ${def.name}.`);\n"
  "    if(def.passive.retaliateSelf&&def.hp>0){ const _rs=applyDmg(def,def.passive.retaliateSelf); if(_rs>0) pushLog(`${def.name} loses ${_rs} HP.`); } }\n"
  "  if(ab.sacrifice && !symbolsOff(side)){ const _sac=applyDmg(att,ab.sacrifice);", 1),
 ('KO bookkeeping (Eckleburg) + KO-er pays (Cursed Crown) + no block after attacking',
  "  const koed = def.hp<=0;\n",
  "  const koed = def.hp<=0;\n"
  "  if(koed){ (att._killedIds=att._killedIds||[]).push(def.id);\n"
  "    if(def.act>1&&def.passive&&def.passive.koRetaliate&&att.hp>0){ const _kr=applyDmg(att,def.passive.koRetaliate); pushLog(`${def.passive.name}: ${att.name} takes ${_kr} for knocking out ${def.name}.`); } }\n"
  "  if(att.act>1&&att.passive&&att.passive.noBlockAfterAttack) att._noBlockTurn=(S._turnNo||0)+1;\n", 1),
 ('block lockout (Cursed Crown / So We Beat On)',
  "const bb=def.blk, canBlock=(!pierce||deconOn()) && !def.status.glue &&",
  "const bb=def.blk, canBlock=(!pierce||deconOn()) && !def.status.glue && !(def._noBlockTurn!=null && def._noBlockTurn===(S._turnNo||0)) &&", 1),
 ('start-of-turn heal (Golden Statues)',
  "  p.team.forEach(c=>{ if(c.hp>0) c.turnsInPlay++; });\n",
  "  p.team.forEach(c=>{ if(c.hp>0) c.turnsInPlay++; });\n"
  "  p.team.forEach(c=>{ if(c.hp>0&&c.act>1&&c.passive&&c.passive.healTurn){ const _h=healChar(c,c.passive.healTurn); if(_h>0) pushLog(`${c.passive.name}: ${c.name} heals ${_h} HP.`); } });\n", 1),
 ('no self-cleanse (Her Own Hand) — cleanse helper',
  "function cleanseNeg(t){ if(!t) return;",
  "function cleanseNeg(t){ if(!t) return; if(t.act>1&&t.passive&&t.passive.noSelfCleanse){ if(typeof pushLog==='function') pushLog(`${t.passive.name}: ${t.name} cannot clear its own statuses.`); return; }", 1),
 ('no self-cleanse (Her Own Hand) — block cleanse',
  "  if(b.blkCleanse){ [].concat(b.blkCleanse)",
  "  if(b.blkCleanse && !(def.act>1&&def.passive&&def.passive.noSelfCleanse)){ [].concat(b.blkCleanse)", 1),
 ('on evolve: Spill lock, starting health, block lockout',
  "  clearAllStatus(c);\n  c.turnsInPlay=0;",
  "  clearAllStatus(c);\n"
  "  if(c.passive){ if(c.passive.spillLock){ c.status.spill=true; c.status._spillLock=true; } if(c.passive.noHealAbove) c._evoHp=c.hp; if(c.passive.noBlockOnEvolve) c._noBlockTurn=(S._turnNo||0)+1; }\n"
  "  c.turnsInPlay=0;", 1),
 ('KO caveat (Platonic Conception)',
  "function actOnKO(p,c){\n  if(!c||!c._actBase) return;\n",
  "function actOnKO(p,c){\n  if(!c||!c._actBase) return;\n"
  "  if(c.passive&&c.passive.koDiscardRandom&&p.hand.length){ const _lost=p.hand.splice(rnd(p.hand.length),1)[0]; p.discard.push(_lost); pushLog(`${c.passive.name}: ${who(p)} discards a random card.`); }\n"
  "  delete c._evoHp; delete c._noBlockTurn;\n", 1),
 ('ally KO (So We Beat On)',
  "    actOnKO(p,a);\n  }\n  if(!p.team.some(c=>c.hp>0)){",
  "    p.team.forEach(function(c){ const _o=c.act>1&&c.passive&&c.passive.onAllyKO; if(!_o||c===a||c.hp<=0) return;\n"
  "      for(let _n=0;_n<(_o.attachFromDiscard||0);_n++){ let _i=-1; for(let _k=p.discard.length-1;_k>=0;_k--){ if(p.discard[_k]&&p.discard[_k].cat==='abc'){ _i=_k; break; } }\n"
  "        if(_i<0) break; const _ab=p.discard.splice(_i,1)[0]; (_ab.type==='BLOCK'?c.blkCharge:c.atkCharge).push(_ab);\n"
  "        pushLog(`${c.passive.name}: ${c.name} takes up a ${_ab.type==='BLOCK'?'Block':'Attack'} ABC from the discard.`); } });\n"
  "    actOnKO(p,a);\n  }\n  if(!p.team.some(c=>c.hp>0)){", 1),
 ('top-of-deck peek (Platonic Conception)',
  "if(pHasPassive(p,'peekOwnDeck') && p.deck.length)",
  "if((pHasPassive(p,'peekOwnDeck')||p.team.some(function(c){ return c.hp>0&&c.act>1&&c.passive&&c.passive.peekOwnDeck; })) && p.deck.length)", 1),
 ('attack cost (King of Cats)',
  "    if(act&&act.fe&&act.passive&&act.passive.costMod) cost+=act.passive.costMod;",
  "    if(act&&(act.fe||act.act>1)&&act.passive&&act.passive.costMod) cost+=act.passive.costMod;", 1),
 ('block cost (King of Cats)',
  "function blockCostFor(ch,ab){ return ab ? escCost(ch,ab,'Blk') : 0; }",
  "function blockCostFor(ch,ab){ if(!ab) return 0; let k=escCost(ch,ab,'Blk'); if(ch&&ch.act>1&&ch.passive&&ch.passive.costMod) k=Math.max(1,k+ch.passive.costMod); return k; }", 1),
 ('heal ceiling (King of Cats)',
  "const b0=c.hp; c.hp=Math.min(c.maxHp, c.hp+amt); return c.hp-b0; }",
  "const b0=c.hp; const _cap=(c.act>1&&c.passive&&c.passive.noHealAbove&&c._evoHp!=null)?Math.min(c.maxHp,c._evoHp):c.maxHp; c.hp=Math.max(c.hp,Math.min(_cap, c.hp+amt)); return c.hp-b0; }", 1),
]

def add_flags(s, pid, extra):
    key = 'passive:{id:"%s"' % pid
    if s.count(key) != 1: sys.exit('Passive "%s" found %d times (need 1). Nothing changed.' % (pid, s.count(key)))
    i = s.index(key) + len('passive:'); depth = 0; j = i; q = None
    while True:
        ch = s[j]
        if q:
            if ch == '\\': j += 2; continue
            if ch == q: q = None
        elif ch in '"\'': q = ch
        elif ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0: break
        j += 1
    return s[:j] + ', ' + extra + s[j:]

def main():
    if not os.path.exists(SRC): sys.exit('Run from the repo root: %s not found.' % SRC)
    s = open(SRC, encoding='utf-8').read()
    if 'romeojuliet' not in s: sys.exit('This is not the live src/game.src.html.')
    if MARK in s: sys.exit('Already applied. Nothing changed.')
    if 'romeo_husband_of_juliet' not in s: sys.exit('Run fix_precon_acts.py first. Nothing changed.')
    for label, a, _, n in EDITS:
        if s.count(a) != n: sys.exit('Anchor "%s" found %d times (need %d). Nothing changed.' % (label, s.count(a), n))
    for pid, extra in FLAGS.items(): s = add_flags(s, pid, extra)
    for _, a, b, _ in EDITS: s = s.replace(a, b)
    shutil.copy2(SRC, SRC + '.bak')
    open(SRC, 'w', encoding='utf-8').write(s)
    print('fix_act_passives: 10 Act passives wired. Backup: %s.bak' % SRC)

if __name__ == '__main__': main()
