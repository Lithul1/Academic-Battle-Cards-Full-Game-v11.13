# ABC — fix_scrim_d20 handoff (2026-11-05)

This is Literary Scrimmage patch 3 of 3 (after fix_scrim_tome and fix_scrim_quests). It adds d20 skill checks to events, a trivia question that can add a bonus to the roll, and an illuminated page that introduces each Algorithm boss before the fight.

**Approved in preview** (`make_qd_preview2.py`). Trevor's calls:
- The rewards stand, except that Mystery Meat now gives +10 base attack.
- Some events force a roll.
- The boss page shows the archive lore, even before the boss is first defeated.

**Install:** `python3 fix_scrim_d20.py && python3 build.py`.
**Writes:** `src/game.src.html` only, plus a `.bak_<stamp>`.
**Needs:** fix_scrim_tome. fix_scrim_quests is not required, but it is in the tested chain.

## d20 checks
- **Where they appear:** every event in `SCRIM_EVENTS` gets one check (`QD_CHECKS`), shown as the first button in `.evt-choices` with `data-st="qd:start"`.
- **Flow:**
  - A trivia question from the run kit's `DATA.abcs` deck. A correct answer adds +5. You can also roll without answering.
  - A spinning d20, paced with `abcPace(1100)`, instant when reduced motion is on.
  - The result page: roll + party + answer = total, against the DC.
  - Continue sets `SCRIM._eventResult` to a `.qd-tag` header plus the outcome.
- **Party bonus:** +2 for each living party member whose archetype fits the skill, capped at +4.
  - Wits: Mentor, Elder, Inquisitor, Sentinel.
  - Cunning: Trickster, Shadow, Outlaw, Corrupter, Scourge, Urchin, Fallen.
  - Resolve: Steadfast, Martyr, Monument, Gatekeeper, Warden, Zealot, Force of Nature.
  - Charm: Hero, Paragon, Innocent.
- **Natural rolls:** a natural 20 always succeeds and adds +15 IP. A natural 1 always fails.
- **HP losses** from a failed check leave every character with at least 1 HP.
- **`base:i` failures** run that event's own choice `i` through `scrimEventChoose`, keeping the event's own result text.
- **Forced events (`force:1`):** Vending Machine, Lost & Found and Mystery Meat. The check replaces the event's choices, with the line "No walking away — the dice decide." The other six events keep their choices next to the check.

| Event | Skill · DC | Success | Failure |
|---|---|---|---|
| Vending (forced) | Cunning 12 | artifact (common/uncommon, else +15 IP) | −8 HP each |
| Extra credit | Wits 13 | +30 IP | −2 Late Fees |
| Professor | Wits 14 | rarer artifact (uncommon/rare, else +25 IP) | −10 HP each |
| Overdue | Charm 12 | +3 Late Fees | event choice 1 |
| Substitute | Charm 13 | +25 IP | −6 HP each |
| Lost & found (forced) | Cunning 14 | artifact + 5 Late Fees | −10 HP each |
| Study group | Wits 12 | full heal | event choice 0 |
| Mystery meat (forced) | Resolve 11 | **+10 base attack** for the run (stacks) | event choice 0 (the random meat outcome) |
| Career fair | Charm 13 | Late Fees → IP at 4× | at 2× |

## Base attack
- The bonus is stored in `SCRIM.qdAtk`.
- **Saving:** `scrimSave`, `scrimLoadSave` and `scrimClearSave` are wrapped to keep it in localStorage under `abc_scrim_d20`. `scrimStartKit` resets it to 0 for a new run.
- **In battle:** one line is anchored in `performAttack`, just before the Gutenberg Press line: `if(S.scrim && side==='you' && SCRIM.qdAtk){ dmg+=SCRIM.qdAtk; pushLog('Mystery Meat — +N base attack.'); }`.
  - It is the only in-place source change.
  - It adds before the Red Pen and Honorary multipliers, the same way Gutenberg does.

## Boss page
- `handleScrim` is wrapped. A `node:c:r` command on a reachable node with `node.boss` sets `ABC_QD.reveal` and `SCRIM.view='bossreveal'`, and `scrimScreen` is wrapped to render `qdBossPage()`.
- **The page shows:**
  - The arched portrait from `ABC_BOSS_IMG`.
  - A drop-cap name.
  - The subtitle and HP for the current Act (`scrimActMul`).
  - The `BOSS_LORE` text.
  - Curses: both `shiftName` and `altName`. In the Doctoral Program it shows only the alt curse, which matches the battle's `useAlt` rule.
  - The attack and block moves.
- **Buttons:**
  - "Draw steel" (`qd:fight`) re-sends the original command with `ABC_QD.pass=true`, which starts the battle.
  - "Back to the map" (`qd:bossback`) returns to the map; the boss stays unfought.

## Other notes
- **Button routing:** `data-st="qd:*"` buttons use a capture-phase click listener, as in st and qo.
- **Debug handle:** `window.ABC_QDX`.
- **Safari:** the d20 spin animates only transform; there are no filters.
- **vcheck** is clean: placeholders identical, DATA block identical, 0 original lines missing.

## Tests
- New: `test_scrim_d20.py`, 39 checks on desktop and phone. It covers:
  - All 9 events, and the forced versus normal layouts.
  - The question; right, wrong and skipped answers; the result and Continue.
  - Natural 20 and natural 1.
  - The HP floor.
  - The professor artifact.
  - The `base` fallback.
  - Career Fair at 4×.
  - Mystery Meat stacking, save and resume, the attack hit plus its log line in a real battle, and the reset on a new run.
  - The party-bonus maths and the archetype map.
  - The boss page: portrait, lore, both curses, moves, Back, Draw steel, the Doctoral alt-only rule, and that non-boss nodes are not intercepted.
- Changed: `test_cardface_evolve.py`. The "not-yet character" check now waits up to 3s for the refusal toast and records every toast as it appears. Under full-suite load the toast used to be read before it showed (test-only; the game is unchanged).
- `run_all.py` now includes `test_scrim_d20.py`.
- validate.js: 8/8. Full suite: 27/28 suites. The one miss was the known `test_cardplay` phone discard-flight timing flake (off by 46px under load); it passes 18/18 standalone. test_scrim_d20 39/39, test_cardface_evolve 14/14.

## Next
The Scrimmage overhaul (3 patches) is complete. Backlog: playable tutorial, more quests and oaths, the pixel booster-pack opening, and the Daisy catalog mismatches.
