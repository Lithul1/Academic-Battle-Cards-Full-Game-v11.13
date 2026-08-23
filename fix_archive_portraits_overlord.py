#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_archive_portraits_overlord.py
Academic Battle Cards -- bug-fix pass 2026-08-23

Fixes four issues, each independently anchored:

  ISSUE 6  Drawn/Pagemaster face-down cards showed a hand-rolled striped tile
           with an "A" circle instead of the real card back. Now routed through
           cardBackHTML(), the same helper the deck stack already uses.

  ISSUE 2  Archive expansion cards rendered bespoke ".char" field-token markup
           with an HP bar computed as hp/220, so a 120 HP character displayed a
           55%-full bar and read as damaged. Both expCardFull() and mhCardFull()
           now delegate to buildCharPreview(), the canonical preview builder,
           tagged .ed-pv exactly as the deck builder already does.

  ISSUE 5  handCard()'s character branch read d.img directly. 27 of the 28
           First Editions ship img:"" and resolve their portrait through
           base:[deck,char] via feImg(), so every one of them fell back to the
           initials monogram. Now resolved through feImg() with a raw-img
           fallback. handViewModal() reuses handCard(), so it is fixed too.

  ISSUE 3  The Sensory Over-lord's inspect panel showed no move text and no
           passive. Three causes, all fixed:
             a) benchInfoModal gated the passive block on `ch.fe && ch.passive`
                and the boss is not an FE. Widened to any character carrying a
                passive with text. Verified safe: no base character in
                DATA.characters carries a `passive` key -- the only non-FE
                passives in the file belong to Critical Lenses, which are
                strings and never reach this modal.
             b) SUPER_BOSS carried no move text and no passive at all, so there
                was nothing to render. Authored from the real behaviour in
                overlordTurn().
             c) overlordTurn() reassigns boss.atk wholesale every attack, which
                would have discarded any .t set at construction. The two
                reassignment sites now carry their own text.

Run from the repo root:

    python3 fix_archive_portraits_overlord.py

Writes src/game.src.html.bak before touching anything. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")

# --------------------------------------------------------------------------
# anchors: (label, old, new)
# Every one is checked for exactly-once presence BEFORE any write happens.
# --------------------------------------------------------------------------

PATCHES = []

# ---------------------------------------------------------------- ISSUE 6 --
# Face-down drawn-mode card -> real card back.
PATCHES.append((
    "issue6-facedown-markup",
    """    return `<div class="hc dm-fd playable${deal}" data-do="dmflip:${idx}">
      <div class="dm-fd-in"><span>A</span></div></div>`;""",
    """    return `<div class="hc dm-fd playable${deal}" data-do="dmflip:${idx}">
      <div class="dm-fd-in">${cardBackHTML()}</div></div>`;""",
))

# The striped gradient stays as the no-asset fallback; the art sits on top of
# it. .dm-fd-in needs to be a positioning context because .cb-img is absolute,
# and the shared .cb-img rule insets by 5px, which reads as a border on a tile
# this small.
PATCHES.append((
    "issue6-facedown-css",
    """.dm-fd-in span{font-family:var(--disp);font-size:24px;color:var(--gold);text-shadow:2px 2px 0 rgba(0,0,0,.45);
  border:3px solid var(--gold);border-radius:50%;width:50px;height:50px;display:grid;place-items:center}""",
    """.dm-fd-in span{font-family:var(--disp);font-size:24px;color:var(--gold);text-shadow:2px 2px 0 rgba(0,0,0,.45);
  border:3px solid var(--gold);border-radius:50%;width:50px;height:50px;display:grid;place-items:center}
/* the face-down tile now shows the real card back; the stripes remain as the
   no-asset fallback underneath, and the medallion path is scaled to fit. */
.dm-fd-in{position:relative;overflow:hidden}
.hc.dm-fd .cb-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;
  border:none;border-radius:9px}
.hc.dm-fd .cb-medallion{width:44px;height:44px;border-width:2px}
.hc.dm-fd .cb-tag{font-size:6px;bottom:4px}""",
))

# ---------------------------------------------------------------- ISSUE 2 --
# Archive expansion card -> canonical preview builder.
PATCHES.append((
    "issue2-expCardFull",
    """function expCardFull(key,id){ var E=window.EXPANSIONS[key]; if(!E) return ''; var c=null; var rs=expRoster(E);
  for(var i=0;i<rs.length;i++){ if(rs[i].id===id){ c=rs[i]; break; } } if(!c) return '';
  var im=(E.img||{})[id]||'', ip=(E.imgpos||{})[id]||'50% 22%'; var hp=Math.min(100,Math.round(c.hp/220*100));
  return '<div class="char mh-ed" style="width:236px">'
    +'<div class="pc-plate"><div class="pc-name">'+c.name+'</div><div class="pc-hp"><i style="width:'+hp+'%"></i><b>'+c.hp+'</b></div></div>'
    +'<div class="pc-art"><img class="port-img" src="'+im+'" style="object-position:'+ip+'"></div>'
    +'<div class="mv-row atk"><b>'+c.atk.n+'</b><span>'+c.atk.label+'</span></div><div class="mv-txt">'+(c.atk.t||'')+'</div>'
    +'<div class="mv-row blk"><b>'+c.blk.n+'</b><span>'+c.blk.label+'</span></div><div class="mv-txt">'+(c.blk.t||'')+'</div>'
    +'</div>';
}""",
    """function expCardFull(key,id){ var E=window.EXPANSIONS[key]; if(!E) return ''; var c=null; var rs=expRoster(E);
  for(var i=0;i<rs.length;i++){ if(rs[i].id===id){ c=rs[i]; break; } } if(!c) return '';
  /* Use the same preview the deck builder uses. The old bespoke markup drew an
     HP bar as hp/220, so a 120 HP character rendered 55% full and read as
     damaged; buildCharPreview shows max HP as a figure, not a meter. */
  return buildCharPreview(edPreviewChar(E,c), E.base||'').replace('pv-card pvchar','pv-card pvchar ed-pv');
}
/* Portraits live on the expansion's img map keyed by character id. The
   one-time attach pass covers battle.chars, but a roster-only entry (Elsinore)
   never receives one, so resolve it here rather than trusting c.img. */
function edPreviewChar(E,c){
  var o={}; for(var k in c) o[k]=c[k];
  if(!o.img){ var IM=E.img||{}, IP=E.imgpos||{};
    if(IM[c.id]){ o.img=IM[c.id]; o.imgpos=IP[c.id]||'50% 18%'; } }
  if(!o.archetype && E.base && typeof edBaseChar==='function'){
    var b=edBaseChar(E.base,c.id); if(b&&b.archetype) o.archetype=b.archetype; }
  return o;
}""",
))

PATCHES.append((
    "issue2-mhCardFull",
    """function mhCardFull(id){var E=window.EXPANSIONS.modern_hamlet;var c=null;for(var i=0;i<E.roster.length;i++){if(E.roster[i].id===id){c=E.roster[i];break;}}if(!c)return'';
  var im=(E.img||{})[id]||'',ip=(E.imgpos||{})[id]||'50% 18%';var hp=Math.min(100,Math.round(c.hp/220*100));
  return '<div class="char mh-ed" style="width:236px">'
    +'<div class="pc-plate"><div class="pc-name">'+c.name+'</div><div class="pc-hp"><i style="width:'+hp+'%"></i><b>'+c.hp+'</b></div></div>'
    +'<div class="pc-art"><img class="port-img" src="'+im+'" style="object-position:'+ip+'"></div>'
    +'<div class="pc-moves"><div class="pc-move atk"><span class="mv-n">'+c.atk.n+'</span><span class="mv-l">'+c.atk.label+'</span></div>'
    +'<div class="pc-move blk"><span class="mv-n">'+c.blk.n+'</span><span class="mv-l">'+c.blk.label+'</span></div></div></div>'; }""",
    """function mhCardFull(id){var E=window.EXPANSIONS.modern_hamlet;if(!E)return'';
  /* Prefer battle.chars over roster: same ids, but the battle entries carry the
     move flavour text (.t) that the roster stubs omit. */
  var c=null,src=(E.battle&&E.battle.chars)||[];
  for(var i=0;i<src.length;i++){if(src[i].id===id){c=src[i];break;}}
  if(!c){ for(var j=0;j<(E.roster||[]).length;j++){ if(E.roster[j].id===id){ c=E.roster[j]; break; } } }
  if(!c)return'';
  return buildCharPreview(edPreviewChar(E,c), E.base||'hamlet').replace('pv-card pvchar','pv-card pvchar ed-pv'); }""",
))

# ---------------------------------------------------------------- ISSUE 5 --
# Character card in hand -> resolve the portrait the way FE cards require.
PATCHES.append((
    "issue5-handcard-portrait",
    """    const img=d.img?`<img class="hcc-img" src="${d.img}" alt="${c.name}">`:`<span class="hcc-mono" style="background:${c.accent||'#444'}">${initials(c.name)}</span>`;""",
    """    /* 27 of the 28 First Editions ship img:"" and inherit their portrait from
       base:[deck,char]; expansion commanders inherit from the expansion's img
       map. feImg() resolves all three cases -- reading d.img raw meant every
       1st Edition fell back to the initials monogram. */
    const _pi=(typeof feImg==='function'?feImg(d):null)||(d.img?{img:d.img,pos:d.imgpos}:null);
    const img=_pi&&_pi.img?`<img class="hcc-img" src="${_pi.img}" alt="${c.name}"${_pi.pos?` style="object-position:${_pi.pos}"`:''}>`:`<span class="hcc-mono" style="background:${c.accent||'#444'}">${initials(c.name)}</span>`;""",
))

# Second half of issue 5, found while verifying the archive fix. modern_hamlet
# points ed.img at window.HAMLET_MODERN_IMG, whose values carry the
# "data:image/jpeg;base64," prefix. frankenstein_2077 and sengekokujo instead
# use inline maps holding BARE base64. Every portrait in those two sets was
# therefore emitted as src="iVBORw0..." with no data: scheme and rendered
# blank -- in the archive, in hand, on the field, and for their commanders.
# Normalising here fixes all consumers at once, since every one of them reads
# through ed.img.
#
# The same pass also wires boosterPool.commanders, which it previously skipped
# entirely -- Muneshige and Genba received neither .img nor .base, so feImg()
# had nothing to inherit from.
PATCHES.append((
    "issue5-expansion-img-prefix",
    """(function(){ var E=window.EXPANSIONS||{}; for(var k in E){ var ed=E[k]; if(!ed.battle) continue;
  var IM=ed.img||{}, IP=ed.imgpos||{};
  (ed.battle.chars||[]).forEach(function(c){ if(IM[c.id]){ c.img=IM[c.id]; c.imgpos=IP[c.id]||'50% 18%'; } });
  (ed.battle.commanders||[]).forEach(function(f){ var bc=f.baseChar;
    if(bc && IM[bc]){ f.img=IM[bc]; f.imgpos=IP[bc]||'50% 16%'; }
    if(!f.base && bc) f.base=[ed.base,bc]; });
} })();""",
    """(function(){ var E=window.EXPANSIONS||{}; for(var k in E){ var ed=E[k]; if(!ed.battle) continue;
  var IM=ed.img||{}, IP=ed.imgpos||{};
  /* Some expansion img maps store bare base64 (frankenstein_2077, sengekokujo)
     while others point at a window map that already carries the data: scheme
     (modern_hamlet). Normalise once, here, so every consumer downstream --
     archive, hand, field, commanders -- gets a usable src. */
  Object.keys(IM).forEach(function(id){ var v=IM[id];
    if(typeof v==='string' && v && v.slice(0,5)!=='data:'){ IM[id]='data:image/jpeg;base64,'+v; } });
  ed.img=IM;
  (ed.battle.chars||[]).forEach(function(c){ if(IM[c.id]){ c.img=IM[c.id]; c.imgpos=IP[c.id]||'50% 18%'; } });
  var wireCmd=function(f){ var bc=f.baseChar;
    if(bc && IM[bc]){ f.img=IM[bc]; f.imgpos=IP[bc]||'50% 16%'; }
    if(!f.base && bc) f.base=[ed.base,bc]; };
  (ed.battle.commanders||[]).forEach(wireCmd);
  /* boosterPool commanders were skipped entirely: Muneshige and Genba got
     neither a portrait nor a base to inherit one from. */
  ((ed.boosterPool && ed.boosterPool.commanders) || []).forEach(wireCmd);
} })();""",
))

# ---------------------------------------------------------------- ISSUE 3 --
# (a) the passive block was FE-only, so bosses could never show one.
PATCHES.append((
    "issue3-passive-gate",
    """    ${ch.fe&&ch.passive?`<div class="bv-passive"><div class="bv-ph">Passive \\u2014 ${ch.passive.name}</div><p>${ch.passive.text||''}</p></div>`:''}""",
    """    ${(ch.passive&&ch.passive.text)?`<div class="bv-passive"><div class="bv-ph">${ch._boss?'Behaviour':'Passive'} \\u2014 ${ch.passive.name||''}</div><p>${ch.passive.text}</p></div>`:''}""",
))

# (b) the boss had no text to show in the first place.
PATCHES.append((
    "issue3-superboss-data",
    """const SUPER_BOSS = { id:'overlord', name:'The Sensory Over-lord', accent:'#3a2f28', hp:300, sub:'Commencement' };""",
    """const SUPER_BOSS = { id:'overlord', name:'The Sensory Over-lord', accent:'#3a2f28', hp:300, sub:'Commencement',
  /* Descriptive only -- the live numbers come from overlordTurn(). Kept in step
     with it: damage 40/50/65 by phase, Recalibrate every 5 turns and every 3
     below a third, Amplify +20 and Laminate at phase 3, Disorient 15 + Weaken. */
  passive:{ name:'Total Saturation', text:'It does not tire and it does not forget. Below two-thirds health it strikes harder and more often; below a third it strikes harder still and mends itself twice as fast. Every few turns it RECALIBRATES, purging every affliction on it and healing 5% of its maximum. Half of what you inflict slides off it entirely. And it feeds on a full hand \\u2014 hold six cards or more at the start of your turn and the noise takes one from you, though the adrenaline sharpens your next strike.' },
  atkText:'A wall of light and sound with nothing behind it. Hits for 40, for 50 below two-thirds health, and for 65 below a third \\u2014 and 20 harder still if it spent the previous turn amplifying.',
  disorientText:'A glancing burst of static, 15 damage, that leaves your Active overstimulated \\u2014 its attacks are weakened until it clears.',
  blkText:'It gathers the signal instead of striking, powering up its next assault by 20. Below a third health it shields itself as it does so.' };""",
))

PATCHES.append((
    "issue3-boss-construction",
    """    const bc=makeChar({id:'overlord',name:b.name,hp:b.hp,accent:b.accent,tags:['villain'],
      atk:{n:'Sensory Overload',dmg:40,cost:0,label:'40'},blk:{n:'Amplify',block:20,cost:2,label:'20/2'}},1.0);""",
    """    const bc=makeChar({id:'overlord',name:b.name,hp:b.hp,accent:b.accent,tags:['villain'],
      passive:b.passive,
      atk:{n:'Sensory Overload',dmg:40,cost:0,label:'40',t:b.atkText||''},
      blk:{n:'Amplify',block:20,cost:2,label:'20/2',t:b.blkText||''}},1.0);""",
))

# (c) overlordTurn() rebuilds boss.atk from scratch on every attack, which would
#     have dropped the text again on turn one.
PATCHES.append((
    "issue3-overlordturn-text",
    """  boss.atk={ n:(mv==='disorient'?'Disorient':'Sensory Overload'), dmg:dmg, cost:0, label:String(dmg) };""",
    """  boss.atk={ n:(mv==='disorient'?'Disorient':'Sensory Overload'), dmg:dmg, cost:0, label:String(dmg),
             t:(mv==='disorient'?(SUPER_BOSS.disorientText||''):(SUPER_BOSS.atkText||'')) };""",
))

# --------------------------------------------------------------------------

ALREADY_APPLIED_MARKS = [
    "issue6/2/5/3 applied",
    "edPreviewChar",
    "Total Saturation",
]


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)

    with open(SRC, "r", encoding="utf-8") as fh:
        src = fh.read()

    # ---- guard: the live file, not the stale snapshot -------------------
    if "romeojuliet" not in src:
        die("this file has no 'romeojuliet' -- it is the stale snapshot, not "
            "the live build. Patch src/game.src.html from your working tree.")
    if "odyssey" not in src:
        die("this file has no 'odyssey' -- refusing to patch a stale build.")

    # ---- guard: refuse to run twice -------------------------------------
    for mark in ALREADY_APPLIED_MARKS:
        if mark in src:
            die("already applied (found %r). If you need to revise this patch, "
                "ship a named fix_*.py instead of re-running this one." % mark)

    # ---- check EVERY anchor before writing anything ----------------------
    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-28s found %d times, expected exactly 1" % (label, n))
    if problems:
        die("anchor check failed -- nothing was written:\n" + "\n".join(problems))

    placeholders_before = len(re.findall(r"__ABCASSET_\d+__", src))
    scripts_before = src.count("<script")

    # ---- build in memory -------------------------------------------------
    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)

    out = out.replace(
        "function cardBackHTML(){",
        "/* issue6/2/5/3 applied -- fix_archive_portraits_overlord.py */\n"
        "function cardBackHTML(){",
        1,
    )

    # ---- invariants ------------------------------------------------------
    placeholders_after = len(re.findall(r"__ABCASSET_\d+__", out))
    if placeholders_after != placeholders_before:
        die("asset placeholder count changed (%d -> %d) -- nothing written."
            % (placeholders_before, placeholders_after))

    scripts_after = out.count("<script")
    if scripts_after != scripts_before:
        die("script block count changed (%d -> %d) -- nothing written."
            % (scripts_before, scripts_after))

    if out == src:
        die("no change produced -- nothing written.")

    # ---- write -----------------------------------------------------------
    bak = SRC + ".bak"
    shutil.copy2(SRC, bak)
    with open(SRC, "w", encoding="utf-8") as fh:
        fh.write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup      %s" % bak)
    print("    placeholders %d (unchanged)" % placeholders_after)
    print("    script blocks %d (unchanged)" % scripts_after)
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
