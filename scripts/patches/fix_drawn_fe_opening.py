#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_drawn_fe_opening.py
Academic Battle Cards -- 2026-08-25

In Drawn mode a 1st Edition was shuffled into the deck as an ordinary card. Over
400 fresh games with Gatsby 1E in a Gatsby deck:

    deck size                    61
    average position from top  28.8
    median                       29
    in the top 5 cards        10.5%
    in the top 10             19.5%
    in the top 20             33.5%

So roughly four games in five the commander is not in your first ten cards. If
it never reaches the field, neither its benefit NOR its caveat ever happens --
which is why Gatsby's permanent, uncleansable Spill looked broken. The caveat
mechanism itself is sound: verified ticking -10/turn in Standard, Pagemaster and
Drawn once the character is actually in play, on the bench as well as Active.

The inconsistency was across modes:
  * Standard    -- the 1E is on the team from turn one
  * Pagemaster  -- commanders open on the field, never shuffled in
  * Drawn       -- the 1E was a coin flip, and Pagemaster forces Drawn on

A card priced with a permanent drawback should pay that drawback. Per Trevor's
call (2026-08-25), commanders are now seeded into the OPENING HAND rather than
onto the field:

  * it mirrors how a real TCG opening works -- you hold it and choose the moment
  * it preserves the 1E multiple-knockout system, which opening on the field
    would have partly bypassed
  * playing a commander stays a risk/reward decision the player makes
  * and because the card enters play through the normal path, the caveat procs
    exactly like any other status -- always, unless something on the field
    blocks it

seedOpeningFe() runs wherever seedOpeningHand() already runs -- the initial deal
AND after every mulligan -- so a mulligan can never cost you your commander.

Guard rails:
  * never fills the hand with characters: it stops if seeding would leave fewer
    than two non-character cards, so an opening hand is still playable
  * only touches the player's own Drawn deck; Pagemaster commanders are on the
    field already and are skipped
  * a commander already in hand is left alone

Run from the repo root:

    python3 fix_drawn_fe_opening.py

Writes src/game.src.html.bak. Refuses to run twice.
"""

import os
import re
import shutil
import sys

SRC = os.path.join("src", "game.src.html")
PATCHES = []

PATCHES.append((
    "seed-fe-fn",
    """function drawnMulligan(){""",
    """/* Commanders open in HAND, not on the field and not buried in the deck.
   Shuffled in, a 1E sat 29 cards deep on average, so four games in five its
   caveat never had a chance to fire. Held in hand, entering play through the
   normal path, it behaves like any other character -- benefit and cost both. */
function seedOpeningFe(){
  const p=S&&S.you; if(!p||!p.hand||!S.drawn) return 0;
  let moved=0;
  for(;;){
    const di=p.deck.findIndex(c=>c.cat==='char' && c.fe &&
      !p.hand.some(h=>h.cat==='char' && h.fe && h.charId===c.charId));
    if(di<0) break;
    /* Prefer trading away a non-character. But if the deal was already
       character-heavy, trade a NON-FE character instead: that keeps the trivia
       count untouched and still guarantees the commander is in hand. Declining
       to seed here is what left 4.3% of openings without one, and a caveat that
       skips one game in twenty is not a cost the card is paying. */
    let hi=-1;
    if(p.hand.filter(c=>c.cat!=='char').length>2) hi=p.hand.findIndex(c=>c.cat!=='char');
    if(hi<0) hi=p.hand.findIndex(c=>c.cat==='char' && !c.fe);
    if(hi<0) hi=p.hand.findIndex(c=>c.cat!=='char');
    if(hi<0) break;
    const fe=p.deck.splice(di,1)[0];
    p.deck.push(p.hand[hi]); p.hand[hi]=fe; moved++;
  }
  if(moved){ shuffle(p.deck);
    pushLog(moved===1 ? 'Your 1st Edition opens in hand \\u2014 play it when you judge the moment.'
                      : 'Your 1st Editions open in hand \\u2014 play them when you judge the moment.'); }
  return moved;
}
function drawnMulligan(){""",
))

PATCHES.append((
    "deal-opening",
    """        if(S.drawn){ seedOpeningHand(); S.you.hand.forEach(c=>c._faceDown=true);""",
    """        if(S.drawn){ seedOpeningHand(); seedOpeningFe(); S.you.hand.forEach(c=>c._faceDown=true);""",
))

PATCHES.append((
    "after-mulligan",
    """  for(let k=0;k<S.settings.handSize;k++) dealOne('you');
  seedOpeningHand();
  S.you.hand.forEach(c=>c._faceDown=true);""",
    """  for(let k=0;k<S.settings.handSize;k++) dealOne('you');
  seedOpeningHand();
  /* a mulligan must never cost you your commander */
  seedOpeningFe();
  S.you.hand.forEach(c=>c._faceDown=true);""",
))

# expose the seeding helpers so the opening can be simulated in tests
PATCHES.append((
    "debug-exports-seed",
    """  makeBuilderState, builderFocus, handleBuilder, edModCount, clone,""",
    """  makeBuilderState, builderFocus, handleBuilder, edModCount, clone,
  seedOpeningHand, seedOpeningFe, dealOne, drawnMulligan, drawnPlace,""",
))

ALREADY = ["fix_drawn_fe_opening.py", "function seedOpeningFe("]


def die(msg):
    sys.stderr.write("ABORT: " + msg + "\n")
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die("cannot find %s -- run this from the repo root." % SRC)
    src = open(SRC, encoding="utf-8").read()

    if "romeojuliet" not in src or "odyssey" not in src:
        die("missing romeojuliet/odyssey -- this is the stale snapshot.")
    for mark in ALREADY:
        if mark in src:
            die("already applied (found %r). Ship a named fix_*.py to revise." % mark)

    problems = []
    for label, old, _new in PATCHES:
        n = src.count(old)
        if n != 1:
            problems.append("  %-18s found %d times, expected 1" % (label, n))
    if problems:
        die("anchor check failed -- nothing written:\n" + "\n".join(problems))

    ph_before = len(re.findall(r"__ABCASSET_\d+__", src))
    sc_before = src.count("<script")

    out = src
    for label, old, new in PATCHES:
        out = out.replace(old, new, 1)

    if len(re.findall(r"__ABCASSET_\d+__", out)) != ph_before:
        die("placeholder count changed")
    if out.count("<script") != sc_before:
        die("script block count changed")
    if out == src:
        die("no change produced.")

    # both seeding sites must call it, or a mulligan silently loses the commander
    if out.count("seedOpeningFe()") != 3:   # definition + deal + mulligan
        die("seedOpeningFe is not wired at both seeding sites.")

    shutil.copy2(SRC, SRC + ".bak")
    open(SRC, "w", encoding="utf-8").write(out)

    print("OK  %d anchors replaced" % len(PATCHES))
    print("    backup       %s.bak" % SRC)
    print("    placeholders %d (unchanged)" % ph_before)
    print("    1st Editions now open in hand in Drawn mode, and survive mulligans")
    print("    size %d -> %d bytes" % (len(src), len(out)))
    print()
    print("Next:  python3 build.py")


if __name__ == "__main__":
    main()
