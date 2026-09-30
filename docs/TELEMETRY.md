# 91 - AI TELEMETRY: LINE FORMAT AND READER'S GUIDE

**parley v3 iteration 7. Format version `v1`.**

You are probably reading this because someone handed you a CK3 log and asked how
the mod's AI is using the deal system. Start here, then run the queries in
section 7. You do not need to read any script file to interpret the log.

---

## 1. WHERE THE LINES ARE, AND WHAT TO ASK FOR

| | |
|---|---|
| **File to ask the user for** | `C:\Users\<user>\Documents\Paradox Interactive\Crusader Kings III\logs\error.log` |
| **Also contains the same lines** | `game.log` (either file works; `error.log` is smaller) |
| **Mechanism** | the `error_log` script effect |
| **Debug mode required?** | **No.** See section 8 for the evidence and its limits. |
| **Game rule that must be on** | `tnt_ai_telemetry` = `on` (ships **off**) |

The mod writes into the *error* log. That is deliberate, not a bug: `error_log`
is the only logging effect in CK3 that both interpolates values inline and can be
shown to work without launching the game in debug mode. Section 8 records the
whole investigation.

### Coverage check before counting a complete run

Compare the last `TNTLOG` year with the save date and the continuing game/debug
log. Error output can stop during a running game: the 2026-09-29 vanilla test
ended with exactly 100,000 error entry headers. Of these, 78,637 were repeated
Russian marriage-label localization errors from MCA's former visibility guard.
All three log copies stopped recording `TNTLOG` in 1181 although the autosave
reached 1188.1.1. The matching mirrors cannot recover the missing interval.

Treat counts from such a log as a partial-period minimum, never as a full-run
total or proof of later AI inactivity. Retained `tnt_threat_opinion` records in a
save can establish later threats, but do not by themselves distinguish forced
submission, gold demands, or a manual player deal. Preserve the logs and save
before the next launch. A namespace-only error scan also misses this defect:
the errors name vanilla localization keys even though MCA caused the calls.

### If the log has no `TNTLOG` lines at all

Work down this list; the causes are ordered by likelihood.

1. The game rule `tnt_ai_telemetry` was left at **off**. It ships off. This is by
   far the most likely cause and it is invisible in the log by construction.
2. The user sent the wrong file (`debug.log` instead of `error.log`).
3. The log was rotated - CK3 truncates its logs on every launch, so the file must
   be collected **after** the run and before the next start.
4. Only then suspect that `error_log` needs debug mode after all. Section 8.

---

## 1b. "THE AI MADE NO OFFERS. WHY?"

This is the first question anyone will ask. Run Q1 and Q3 from section 7, then read
straight down this table - **the first row that matches is the answer.** Every
cause is distinguishable from every other by the presence or absence of a specific
line, which is the property the instrumentation was built for.

| Look for | If it says | The cause is |
|---|---|---|
| any line containing `TNTLOG` | **none at all** | Telemetry was off, or the wrong file was sent. Section 1. |
| `NOTRY\|why=rule_off` | **present** | The `tnt_ai_offer_rate` game rule is at **off**. Nothing was ever attempted. |
| `TRY` lines | **none, but BANNER present** | The pulse's own trigger or its 11% dice never passed for anybody. Suspect the proposer-side cooldown or a mod conflict on `ai_character_pulse`. |
| `TRY` count | **present** | This is the real denominator. Continue down. |
| `NOTRY\|why=no_candidate` | **~all of the TRY count** | **Normal.** Only the human is a legal recipient, so every non-neighbour AI lands here. The mod is working; the player simply has few AI neighbours, or none that passed. |
| `REJECT\|why=target_cooldown` | **a large share** | The **player-side lock** is the binding constraint - it blocks every ruler in the world at once. Set the rule to `frequent` or `test`. This is the single commonest real cause. |
| `REJECT\|why=target_busy_negotiating` or `target_window_open` | **a large share** | The player keeps the negotiation window open or holds stale partner state. |
| `REJECT\|why=partner_gate` | **a large share** | The mod's own `tnt_partner_valid_trigger` is refusing. A gate bug or an over-strict gate. |
| `PICK` present but `COMPOSE` **absent** | | The event was queued and never ran: `tnt_ai_offer.0001`'s own `trigger` or its engine-side `cooldown = { years = 1 }`. Neither is in the telemetry author's files. |
| `COMPOSE` + `SETTLE` present, no `APPLY` | `accept` **<= 0** | The package **evaluated below acceptance** and was silently abandoned. The AI is pricing, not failing. |
| `COMPOSE` + `SETTLE` present, no `APPLY` | `accept` **> 0** | The letter was presented and the player declined, hushed it or let it time out. Not separable yet - section 9. |

The two causes most often confused with each other, and how they differ here:
`no_candidate` means **nobody eligible was found**; `target_cooldown` means
**somebody was found and the rate limit refused them.** They are separate tokens on
separate kinds and can never be mistaken for one another.

---

## 2. THE LINE GRAMMAR

Every line the mod emits looks like this, and **it is always exactly one line** -
no field ever contains a newline.

```
[00:41:07][E][jomini_effect_impl.cpp:450]: file: common/scripted_effects/tnt_3b_log.txt line: 214 (tnt_log_try_effect): TNTLOG|v1|TRY|y=1067|rate=normal|pro=Salamon Arpad of k_hungary (Internal ID: 37343 - Historical ID 476)|proid=37343
```

- `[00:41:07]` - **real-world** wall clock, added by the engine. Monotonic within
  a session, so it orders events inside a game year.
- `[E]` - severity. Always `E`.
- `file: ... line: N (tnt_log_try_effect):` - added by the engine, free of charge.
  The name in brackets is the helper that emitted the line, which is a second,
  independent way to identify a line kind.
- Everything from `TNTLOG` on is the mod's payload.

### > `TNTLOG` IS NOT AT THE START OF THE LINE.

Never anchor a pattern with `^`. Always match `TNTLOG` anywhere in the line.

### Payload

```
TNTLOG | v1 | KIND | key=value | key=value | ...
         ^     ^
         |     +-- the event kind, always the 3rd pipe-delimited field
         +-------- format version; bump it if any field changes meaning
```

Fields are `key=value`, pipe-separated, order stable per kind. **A value may
contain spaces, brackets, parentheses and hyphens** (character names do), so
split on `|` and then on the **first** `=` only.

---

## 3. FIELD DICTIONARY

The same name always means the same thing, so lines of different kinds join on
these.

| Field | Meaning |
|---|---|
| `y` | in-game **year**. See the note below. |
| `date` | full localised date. **BANNER lines only.** |
| `rate` | the `tnt_ai_offer_rate` setting in force: `off` / `rare` / `normal` / `frequent` / `test` |
| `pro`, `proid` | the AI **proposer**: log name, then numeric character id |
| `indep` | **PICK lines only.** `1` if the proposer is an independent ruler, `0` if he is somebody's vassal. Added in V12 for user item 2: archetype A14 (fealty) can only ever be composed by an independent proposer, and three runs in a row that had to be inferred from title prefixes. `Group-Object indep` over the PICK lines now answers it directly. |
| `tgt`, `tgtid` | the **recipient** of an AI offer - the human player |
| `a`, `aid` | AI-to-AI: the **actor**, the side that initiates and pays |
| `b`, `bid` | AI-to-AI: the **recipient** |
| `me`, `meid` | APPLY lines: the player (root of the deal) |
| `other`, `otherid` | APPLY lines: the counterparty |
| `via` | how the recipient was found: `neigh` (neighbour iterator) or `liege` (one-link fallback) |
| `why` | the single reason this attempt stopped. One token, one cause. |
| `arch` | archetype. **AI-to-player: a NUMBER**, one of `3 8 9 10 13 14 16 17 18 19 20 21`, or `none`; the legend is `CLAUDE.md` §3, and indices `1 2 4 5 6 7 11 12 15` are retired and are never reused. **AI-to-AI: a WORD**, one of `hook` / `ultimatum` / `hookcall` / `title` / `artifact` / `wed` / `vassal` / `none`. **`tribute`, `truce` and `ally` can no longer occur** - those archetypes were retired and their emitters are commented out (`tnt_3b_log.txt:1207`, `:1221`, `:1813-1867`); such a line means the log predates the retirement. *(Row corrected 2026-08-17: it used to read "AI-to-player: `1`..`7`", which is two renumberings out of date.)* |
| `item` | which term. Live vocabulary, read off the emitters in `tnt_3b_log.txt` on 2026-08-17: `gold` `prestige` `piety` `influence` `hook` `title` `artifact` `vassal` `ward` `hostage` `courtier` `contract` `marriage` `indep`. Retired, emitters commented out but the token kept readable for old logs: `alliance` `truce` `prisoners` `claim` `tribute`. *(Row corrected 2026-08-17.)* |
| `side` | `p`, `r` or `mutual`. **See the direction warning below.** |
| `ask` | plain-language direction: `ai_wants` or `ai_gives` |
| `amt` | the amount of that term |
| `accept` | `tnt_ai_accept_value` - the headline verdict. **`> 0` means the AI would sign.** |
| `gain` | what the partner receives, in points |
| `loss` | what the partner hands over, in points |
| `rel` | the standing between the two rulers |
| `thresh` | what the AI wants on top of a merely fair trade, **expressed in PERCENT of `gain`, not in points** - unlike `gain`, `loss` and `rel`, which are all points. Mixing the two units is what made the old reconstruction formula wrong; see the identity note in §7. *(Row corrected 2026-08-17.)* |
| `margin`, `ceiling` | the settle-up band in force (8 and 20 as shipped) |
| `tier` | AI-to-AI price tier actually used: `low` or `high` |
| `gold` | AI-to-AI: the lump sum sent |
| `yearly` | AI-to-AI tribute: the standing yearly payment |
| `bal` | AI-to-AI: the balance the tier was judged on. `> 0` means sign. |
| `ratio` | actor's strength over recipient's. `< 0.9` = the actor is weaker. |
| `chance` | the per-pulse percentage the AI-to-AI dice were rolled against |
| `src` | APPLY only: `ai_offer` (the AI composed it) or `player` (the player did) |
| `had_arch` | CLEAR only: the archetype that existed at teardown, or `none` |
| `letter` | APPLY only (V18): `1` = the deal came through a letter and the stress layer was **SUPPRESSED**; `0` = manual, so the layer **RAN**. `0` means eligible, **not** charged - every arm carries a trait test no field records. |
| `osided` | APPLY only (V18): `tnt_gain_total_value - 2 x tnt_loss_total_value`. **V30 retired it from every gate** - no leg tests it any more and these two emitters are its only reader in the mod. Kept because it is the one continuous series across runs. All twelve run-B readings were negative. |
| `gave` | APPLY only (V30): `tnt_stress_gave_value` = `tnt_gain_total_value`, i.e. everything the partner receives = everything the player handed over. **Arm B fires at `>= 200` (grave) and `>= 75` (ordinary).** |
| `took` | APPLY only (V30): `tnt_stress_took_value` = `tnt_loss_total_value`, i.e. everything the partner hands over = everything the player took in. **Arm C fires at the same two rungs, and only if arm B did not.** |

### `y` is a YEAR, not a full date

Only the year is on event lines, on purpose: it is pure ASCII digits, whereas the
full date renders through the active language and would write Cyrillic month
names into the data on a Russian install. Order events **within** a year by the
engine's `[HH:MM:SS]` wall clock. A half-year run is one session, so that works.
The BANNER line carries the full localised date for human reference.

### > DIRECTION WARNING - READ THIS BEFORE INTERPRETING ANY `TERM` LINE

The mod's internal convention is **`_p` = the PLAYER gives it, `_r` = the PARTNER
gives it**, and on the AI-offer path the partner *is* the AI. So:

- `side=p` -> the AI is **asking for** this
- `side=r` -> the AI is **offering** this

This inverts what "p" intuitively suggests. The `ask` field states it in words
(`ai_wants` / `ai_gives`) so you never have to rely on remembering. `side=mutual`
is `alliance` and `truce`, which are single two-sided terms priced once.

---

## 4. EVENT KINDS - THE AI-TO-PLAYER OFFER PATH

Emitted from `tnt_37_ai_offer.txt`. One AI ruler tries to send the player a
letter. Roughly one evaluation per AI count-or-above per half game year, then an
11% dice roll (times 0.4 for a count).

| Kind | Meaning |
|---|---|
| ~~`BANNER`~~ | **RETIRED IN V11 AND IT WILL NEVER APPEAR AGAIN. Do not use it as proof of life.** `tnt_log_banner_effect` has had zero call sites since V11 — it survives only as a tombstone at `tnt_3b_log.txt:179`, and the retirement is argued at `tnt_37_ai_offer.txt:458-464` and `tnt_38_ai_world.txt:950`. **Proof of life is `COUNT(TRY) + COUNT(WTRY) > 0`.** The 08-19 run has 17,335 `TNTLOG` lines and zero `BANNER`, exactly as designed. |
| `TRY` | **attempt start.** The denominator for everything below. |
| `NOTRY` | the attempt stopped before a candidate was picked. See `why`. |
| `CAND` | a candidate was found; `via` says by which of the two searches. |
| `REJECT` | the candidate was found and then refused. See `why`. |
| `PICK` | gate passed, cooldowns written, event queued onto the player. Carries `indep` since V12. |
| `COMPOSE` | archetype drawn, terms on the table, **before** the settle-up. |
| `TERM` | one term as composed. One line per term. |
| `SETTLE` | **the numbers**, after the one corrective step. |
| `TERM2` | the same term sweep **after** the settle-up. |
| `CLEAR` | offer state torn down. |
| `OUTCOME` | reserved; not emitted in this iteration (see section 9). |
| `DEMANDGATE` | **B2, VERBOSE ONLY.** `tnt_can_demand_trigger` passed for this pair, emitted in the composer prologue **before** the draw. Fields: `y`, `proid`, `tgtid`, `road=dread|army`. |
| `DEMAND` | **B2.** Archetype 21 won the draw. Emitted in the entry body, so it survives an abort. Fields: `y`, `proid`, `tgtid`, `edge`, `dread`, `prest`, `pts`, `gold` (the raw ask), `cap` (80% of the player's purse), `ask` (what was actually staged = `min(gold, cap)`). `gold != ask` means the purse clamp bit. |
| `DEMANDEND` | **B2.** The player answered. Fields: `y`, `tgtid`, `paid=0|1`, `gold`, `prestige`, `dread`, `free=0|1`. `free=1` is the out-grown waiver — T53 no longer passed at click time, so the refusal cost nothing. |
| `ARTGATE` | **Run C follow-up, VERBOSE ONLY.** A13's entry trigger split in half, emitted in the composer prologue **before** the draw, one line per composition attempt. Fields: `y`, `proid`, `tgtid`, `has=0\|1` (the proposer holds at least one artifact vanilla would let him give to the player), `afford=0\|1` (at least one of *those* pieces also passes `tnt_ai_art_afford_gap_value <= 0`). `has=0 afford=1` cannot occur — `afford` is the conjunction, not a second question. |

### > B2, 2026-08-23 — THE DEMAND (ARCHETYPE 21) AND ITS THREE NEW KINDS

**Why three and not one.** A21 has two failure modes that are indistinguishable
in the old vocabulary — *never eligible* and *eligible, never drawn* —
and that is exactly the pair archetypes 19 and 20 could not be told apart for two
rounds. `DEMANDGATE` separates them on the **first** run: 0 means the gate is the
problem and the weight is irrelevant.

**Three structural absences under `arch=21`, all of them CORRECT:**

* **no `SETTLE`** — A21 skips `tnt_ai_offer_settle_effect` by design (the settle
  would make the AI pay the victim back);
* **no `TERM2`** — `tnt_log_terms_after_effect` is reachable only from
  `tnt_log_settle_effect`, so a `TERM2` census under-counts `item=gold side=p` by
  exactly the arch-21 population. Section 6's three-snapshot table applies to
  every archetype **except** this one;
* **no `OUTCOME|what=aborted_below_threshold`** — arch 21 never reaches the trade
  go/no-go. When its own dispatch gate refuses it, the line is
  **`OUTCOME|what=demand_gate_lapsed|arch=21`**, carrying `gate` (T53 still
  passes, 0/1), `gold` (the staged ask, 0 if none) and `lock` (the player is
  inside `var:tnt_demand_lock`, 0/1) so the cause is readable without a second
  query.

**The one grep that answers "did the AI lean on me, and did it work":**

```powershell
Select-String -Path $log -Pattern 'TNTLOG\|v1\|DEMAND(GATE|END)?\|'
```

Everything else about the demand is ordinary vocabulary reused unchanged:
`COMPOSE|arch=21|goal=14` (or `goal=6` when the demander's chest is empty),
`TERM|item=gold|side=p`, `OUTCOME|what=player_accepted|arch=21` /
`player_declined|arch=21`, `APPLY|src=ai_offer`, `TERM3|item=gold|side=p`,
`CLEAR`.

### > RUN C FOLLOW-UP, 2026-08-24 — `ARTGATE`, THE SAME INSTRUMENT FOR A13

**Why it exists.** Three runs in a row measured `COMPOSE|arch=13 = 0` — 86 non-empty
draws in run C alone, where `P(0)` is under 0.31% if the entry trigger ever passed —
and no line in the vocabulary could tell two very different worlds apart: *the
neighbours own no giftable artifact* (the map, not a defect) and *they own one and
the gate or the dice refused it*. That is `DEMANDGATE`'s argument applied to an
archetype that has no gate line of its own, which is exactly the diagnosis A19 and
A20 lacked for two rounds.

**It is a reader, not a gate.** The round that added it changed neither A13's weight
(still 6) nor its affordability row. Emitter: `tnt_3b_log.txt`, block **L15b**
(the suffix is deliberate — every plain number in that file is taken).

| what you see | what it means |
|---|---|
| no `ARTGATE` at all | telemetry is not at `verbose`, or nothing ever composed |
| `has=0` on every line | **nothing is wrong with A13.** The proposers own nothing giftable. Do not touch the weight and do not loosen T9. |
| `has=1 afford=0` often | the affordability row is the binding half — read the charter in `tnt_ai_art_afford_gap_value`'s own header before touching it |
| `has=1 afford=1`, still no `COMPOSE\|arch=13` | the gate is open and the **draw** is the delta; only here is the weight even a question |

```powershell
Select-String -Path $log -Pattern 'TNTLOG\|v1\|ARTGATE\|' |
    ForEach-Object { ($_ -split '\|' | Where-Object { $_ -like 'has=*' -or $_ -like 'afford=*' }) -join ' ' } |
    Group-Object | Sort-Object Count -Descending
```

### The `why` tokens, and they partition cleanly

Exactly one `NOTRY` or `REJECT` line is written per stopped attempt, so these
counts add up to the number of attempts that produced no offer.

| `why` | What it means |
|---|---|
| `rule_off` | the `tnt_ai_offer_rate` game rule is at `off`. Nothing was attempted. |
| `no_candidate` | neither search found an eligible ruler. **Expected to dominate - see below.** |
| `target_is_ai` | the picked ruler is not human |
| `target_unlanded` | the picked ruler holds no land |
| `target_window_open` | the player has the negotiation window open right now |
| `target_busy_negotiating` | the player is mid-negotiation with somebody |
| `target_cooldown` | the player-side lock is still running - **the real ceiling on offer rate** |
| `at_war_with_target` | proposer and player are at war with each other |
| `partner_gate` | failed the mod's own `tnt_partner_valid_trigger` |
| `unexplained` | should never appear. If it does, the gate and the diagnostic ladder have drifted apart - a mod bug, report it. |

### > `why=no_candidate` DOMINATING IS NORMAL. DO NOT REPORT IT AS A FAULT.

The candidate filter requires `is_ai = no`, so in single player **the only legal
recipient in the entire world is the one human player.** Every AI that is not a
neighbour of the player *must* produce this line. Expect it to be 90%+ of all
`NOTRY`/`REJECT` lines. It is evidence the pulse is running, not that it is
broken.

### The gap between `PICK` and `COMPOSE`

`PICK` means the event was queued. `COMPOSE` means it actually ran. Two throttles
sit in between and neither is in the telemetry author's files:
`tnt_ai_offer.0001`'s own `trigger`, and its engine-side `cooldown = { years = 1 }`.
`COUNT(PICK) - COUNT(COMPOSE)` measures exactly what they cost.

---

## 5. EVENT KINDS - THE SILENT AI-TO-AI TREATY PATH

Emitted from `tnt_38_ai_world.txt`. Gated by the separate rule `tnt_ai_treaties`,
which defaults to `rare`.

| Kind | Meaning |
|---|---|
| `WPULSE` | **`verbose` only.** One per AI ruler per year, *before* the dice. |
| `WTRY` | the dice passed; a partner search is really happening. The denominator here. |
| `WSTOP` | the attempt ended. See `why`. |
| `WPAIR` | a legal pair was found; carries `ratio`. |
| `WARCH` | the archetype drawn - **including `arch=none`**. |
| `WDONE` | **a treaty was concluded.** Carries `tier`, `gold`/`yearly` and `bal`. |
| `WSKIP` | **V4:** the ultimatum archetype was drawn and came to nothing. Carries `pts`, `ask`, `bal`. |

| `why` | What it means |
|---|---|
| `no_candidate` | nobody in the neighbourhood passed the filter |
| `player_negotiating` | the pair was legal and the pulse **stood down** because a human has one of the two open in the window |
| `actor_broke` | the actor has less gold than even the cheap tier costs |
| `unbalanced_both_tiers` | the actor could pay, but the recipient's valuation refused at both prices |
| `tribute_burden_too_high` | tribute archetype only: the standing payment would swallow too much of the actor's income |

### `arch=none` is a real outcome, not a gap

The "nothing happens this year" entry in the archetype draw carries weight **13
out of 100** (`tnt_38_ai_world.txt:1672`; it was 25 until V4's ultimatum took ten
of it, and 15 until a later pass). **DO NOT READ THE NOMINAL WEIGHT AS THE
EXPECTED SHARE** — `random_list` renormalises over entries whose triggers pass, and
this entry is untriggered so it always passes while the other seven often do not.
Measured on the 08-19 run: `arch=none` won **1058 of 2373** draws, i.e. **45%**
against a nominal 13, which puts the average passing weight per draw near 29. That
is the pulse behaving as designed, not a bug and not a mis-set weight.

### `arch=hookcall` — V4 item A2: the AI collecting a debt

Weight **5 out of 100**, the smallest in the draw, taken from the "nothing happens" entry
(15 -> 10) so the total stayed 100 and no existing archetype changed frequency. Trigger:
the actor holds a weak or a strong hook on the neighbour.

Like the ultimatum it is a **one-way transfer** - the actor demands gold and pays nothing
- so its lines carry the same two extra fields: `pts` (the leverage: 45 for a favour
called in, 120 for blackmail-grade) and `ask` (a fraction of it, in coin). Three endings, all
logged: `WARCH` drawn, `WDONE` collected, `WSKIP|why=debtor_broke_or_unmoved`
refused.

**What separates it from the ultimatum in a log:** no opinion modifier follows a
`WDONE|arch=hookcall`. A debt collected is not a threat made, vanilla charges no
opinion for using a hook, and the price is already paid in the hook itself - a weak one
is gone, spent through vanilla's own `use_hook`. So a serial creditor does NOT poison
the well the way a serial extortionist does. To see whether leverage is being farmed,
count `WDONE|arch=hookcall` per `aid` instead of watching opinion decay.
### `arch=ultimatum` — V4 expansion 1, and it has three endings, not two

Weight **10 out of 100**, the smallest in the draw, and its entry trigger is the
narrowest: the actor needs a bigger army, a prestige level above 0, and a neighbour
who already fears him (`tnt_can_threat_trigger`). Extortion should be the rarest
thing in the world's diplomacy.

It is the one archetype where the actor **pays nothing**: he demands gold, and the
transfer balances only because the recipient is afraid. So its lines carry two
fields the others do not:

| field | meaning |
|---|---|
| `pts` | the pressure, `25 × edge × dread × prestige` capped at 150 |
| `ask` | the coin demanded — **15%** of `pts` since 2026-08-25, converted at `tnt_ai_gold_per_point_value` and capped at 12 × the threat scale. It was 60% and a flat 400 until the ratio ruling multiplied the points scale by ten, at which point the cap bound on **every** qualifying pair and the ask stopped varying at all. If a run ever shows the same `gold=` beside wildly different `pts=`, that regression is back. (The hook-call archetype still takes 60% of its own, much smaller, points — do not "harmonise" the two.) |

Three outcomes, and all three are logged, so an `arch=ultimatum` line always has a
partner:

- `WDONE|arch=ultimatum|tier=only` — gold moved, and the victim took
  `tnt_threat_opinion` (−100, decaying 15 years — raised from −30 in V5, user
  item 4) towards the extortionist.
- `WSKIP|arch=ultimatum|why=fear_too_small_or_broke` — drawn and refused. Read `bal`
  to tell the two apart: `bal > 0` with a skip means the recipient simply could not
  pay, `bal <= 0` means the fear was not worth the demand.
- `tier=only` and never `low`/`high`: a threat has no second bid. The price is set by
  how frightened the other man is, not by what the actor is willing to offer.

**The interesting thing to look for over a long run** is the racket eating itself.
Each success lowers the victim's opinion, opinion feeds `tnt_ai_relation_value`, and
that is a term of the very balance the next ultimatum must clear — so a repeat
extortionist should show `WDONE` first and `WSKIP|bal<=0` later against the same
`bid`. If you never see that turn, the opinion penalty is not landing.

### `WSTOP|why=actor_broke` and the `gold_have` field

`gold_have` is read with `GetGold` (the displayed treasury) while the script's own
test uses `short_term_gold`. On an AI with no active loans these agree. If a line
ever shows `gold_have` well above `gold_need`, that difference is the reason - not
a broken test.

---

## 6. EVENT KINDS - A DEAL IS ACTUALLY APPLIED

Emitted from `tnt_32_apply.txt`, from the one place that serves **both** the
player's manual Propose button and an accepted AI letter.

| Kind | Meaning |
|---|---|
| `APPLY` | a package stopped being a proposal. Carries `src` and `accept`. |
| `TERM3` | the terms as applied. One line per term. |
| `ALLY` | one per marriage pair that reached the wedding, with the engine's alliance verdict. Emitted from `tnt_34_marriage.txt` (not from `tnt_32_apply.txt`), below. |

**`src` is what makes the comparison the whole iteration exists for:**

- `src=ai_offer` - the AI composed this package and the player accepted it
- `src=player` - the player built it in the window and pressed Propose

Both carry `accept`, the AI's own valuation of that package. Group `SETTLE` by
archetype and `APPLY` by `src`, then compare the `accept` columns: that is the
AI's pricing of its own deals set against its pricing of the player's.

### Three term snapshots, and why

| Kind | When |
|---|---|
| `TERM` | as composed, before the settle-up |
| `TERM2` | after the settle-up moved the money |
| `TERM3` | as actually applied |

Diff `TERM` against `TERM2` for one pair in one year to see what the corrective
step did. Diff `TERM2` against `TERM3` to confirm nothing was lost between the
offer and the signature.

### > COUNT MANUAL-ONLY TERMS ON `TERM3`. `TERM` AND `TERM2` CANNOT CARRY THEM.

Both are emitted from inside the **AI composer** — L8 is reached only through
`tnt_log_compose_effect`, L10 only through `tnt_log_settle_effect` — so eight
directed slots that exist, are priced and apply correctly will read as **dead
forever** in a `TERM2` census: `threat/p`, `usehook/p`, `hook/r`, `vassal/p`,
`indep/r`, `hostage/p`, `artifact/p`, `courtier/r`. Their only stage is `TERM3`,
joined on `y=` + `meid=` to an `APPLY` line with `src=player`. This has already
produced one false "the option is ignored" verdict.

### `SPOUSE` — marriage ownership, one row per staged pair (V19)

Emitted from L10 beside the marriage `TERM2` row, so it appears **only for the AI
composer's letters**; a pair the player stages by hand in the window never reaches
L8/L10 and would need the same block in L19.

```
TNTLOG|v1|SPOUSE|y=<year>|pid=<char id>|pdoor=<0-4>|rid=<char id>|rdoor=<0-4>
```

| Field | Meaning |
|---|---|
| `pid` / `rid` | the two staged spouses: `p` measured against `root`, `r` against `var:tnt_partner` |
| `pdoor` / `rdoor` | **which** of T51's four rows admitted that spouse — the first one that passes |

Door codes, copied from `tnt_may_offer_spouse_trigger`
(`common\scripted_triggers\tnt_41_gates.txt:2127-2138`) in its own row order:

| Code | Relationship to the offering side |
|---|---|
| `1` | himself (`$SIDE$ = this`) |
| `2` | his courtier (`is_courtier_of`) |
| `3` | his pool guest (`is_pool_guest_of`) — the mod's only widening past vanilla |
| `4` | his own child at or below him in the vassal chain (`is_child_of` + `target_is_liege_or_above`) |
| `0` | **no door — the pair will be silently dropped** at `tnt_34_marriage.txt:1862-1870` |

**A single `0` is the acceptance test for the whole V18 ownership gate** and the
only visible trace of that silent drop. The codes are a **verbatim copy** of T51's
rows, which is the one place in the mod that can disagree with the gate: re-copy
them if T51's doors ever change. Legend also carried in-code at
`common\scripted_effects\tnt_3b_log.txt:1153-1159` (that citation read `:1046-1052` until 2026-08-24
and was already ~100 lines stale before the round that repaired it — re-anchor, never add a delta).

### `ALLY` — the marriage alliance, one row per pair that reached the wedding (round 11)

Emitted from **L20 `tnt_log_wedally_effect`**, called by `tnt_wed_one_pair_effect`
(`common\scripted_effects\tnt_34_marriage.txt`) inside a `hidden_effect`, **above**
the grant and above the grand/plain dispatch. Unlike `SPOUSE` it covers **both**
paths — a pair the player stages by hand and a pair that arrived in an A16 letter
reach the identical loop — and it fires only on a treaty that is **actually
applied**, so an `ALLY` row always has an `APPLY` row of the same `y=`.

```
TNTLOG|v1|ALLY|y=<year>|pid=<char id>|rid=<char id>|otherid=<char id>|yield=<0/1>|pre=<0/1>|adult=<0/1>
```

| Field | Meaning |
|---|---|
| `pid` / `rid` | the two spouses — `pid` is our side (the list member, i.e. root of the emitter), `rid` is theirs (`var:tnt_wed_partner`) |
| `otherid` | the **partner ruler**, `scope:tnt_deal_partner` — the other arranger, i.e. the man the alliance is *with* |
| `yield` | the **engine's own verdict** via T54 `tnt_pair_yields_alliance_trigger`: `1` = this marriage gives the two arrangers an alliance and `create_alliance` ran on the next line; `0` = it does not and nothing was granted |
| `pre` | were the two arrangers **already allied** at the moment of the call. Recorded *before* the grant, which is the whole reason the emitter runs first |
| `adult` | `1` = both spouses adult, so the pair **married**; `0` = a minor is involved, so the pair was **betrothed** and the alliance stands on the betrothal |

**Every row is the denominator and `yield` is the numerator**, so the grant rate is
one query: `(rows with yield=1) / (all ALLY rows)`.

**`pre` IS AN OPEN ENGINE QUESTION, NOT A DIAGNOSTIC.** It is proven that an
alliance carries a *list* of reason pairs and that a duplicate `create_alliance` is
not an error path; it is **not** proven whether `yields_alliance` returns false once
the two arrangers are already allied. Stage **two qualifying couples in one treaty**
and read the second row:

| second row | what it proves |
|---|---|
| `yield=1 pre=1`, alliance survives | reasons **stack** — one alliance carries both marriages as reasons and outlives either one alone |
| `yield=0 pre=1` | the engine **excludes an already-allied pair** from the predicate; one alliance, one reason |

Do not write either conclusion down until the row exists. The argument in full is in
`tnt_exec_marriage_pair_effect`'s header (`tnt_34_marriage.txt`).

**`adult=0` beside a live alliance in the diplomacy screen** is the measurement that
confirms a betrothal-backed alliance, the one claim in this design that currently
rests on vanilla's script rather than on our own observation.

Volume: single digits per run — one row per staged pair per applied deal (run B
produced 12 `APPLY` records in 13,791 lines).

---

## 6b. `LEAN` — THE ALERT PROBE, ONE LINE PER PLAYER PER YEAR (V33, 2026-08-24)

**Why it exists.** The important-action alert `tnt_action_can_lean_on`
(`common\important_actions\tnt_91_alerts.txt`) **cannot log at all**: its
`check_create_action` is an interface effect, and
`GAME\common\important_actions\_important_actions.info:12` says *"Only interface
effects are allowed"* — `error_log`, `set_variable` and `add_character_flag` are all
discarded at parse time with a single `jomini_effect.cpp ... in forbidden area`
line and nothing else. Three rounds were spent guessing why the alert listed
nobody. `LEAN` is the probe put where telemetry is legal: **L21
`tnt_log_lean_probe_effect`**, called from `yearly_playable_pulse` →
`tnt_yearly_cleanup` (`common\on_action\tnt_70_on_actions.txt`) behind
`is_ai = no`. It re-walks the alert's **two pools** with the alert's **own three
triggers** — called, never copied — so it can never disagree with the code it
measures.

```
TNTLOG|v1|LEAN|y=<year>|dread=<n>|prlvl=<n>|vassals=<n>|nbrs=<n>|passT=<n>|passDoor=<n>|passT1=<n>|pass=<n>
```

| Field | Meaning |
|---|---|
| `dread` | the player's **raw** dread. The field this round is about |
| `prlvl` | his `prestige_level` — row 2 of `tnt_can_threat_trigger` |
| `vassals` | size of POOL 1, `every_vassal` (direct vassals only) |
| `nbrs` | size of POOL 2, `every_neighboring_top_liege_realm_owner` |
| `passT` | candidates passing `tnt_can_threat_trigger`, both pools summed |
| `passDoor` | candidates passing `tnt_door_open_trigger`, both pools summed |
| `passT1` | candidates passing `tnt_partner_valid_trigger`, both pools summed |
| `pass` | candidates passing **all three** — exactly what the alert would list |

The three row counts are **independent, not nested**, on purpose: a nested ladder
would only ever report "the first row failed", and *which* row failed is precisely
what the last three rounds cost. `pass` is the single nested figure and it is the
alert's own conjunction.

**How to read it in one glance.**

| reading | verdict |
|---|---|
| `dread=0` on every line | the alert was **unreachable for that run**: EVERY branch of `tnt_threat_feared_trigger` wants `$A$` dread >= 30, and `$A$` is the player here, so a player under 30 empties both pools at once. Nothing is broken |
| `dread>=30` with `passT` anywhere between 1 and `vassals` + `nbrs` | **expected, and NOT a defect.** At or above 30 the row is genuinely PER CANDIDATE, because two of its three branches also read `$B$`: branch 1 wants `target_is_liege_or_above` (true of every direct vassal, false of most neighbours) and branch 3 wants `ai_boldness < 50` (per candidate). A ruler at raw dread 45 passes branch 1 on every direct vassal but reaches only the timid among his neighbours - a real partial pass. **The row is NOT root-invariant; only `$A$`'s side of it is** |
| `passT=0` with `passDoor` and `passT1` both large | the same thing from the other side: the pools are healthy, the threat gate is the blocker |
| `pass>0` and no row in Current Situation | **a real defect** — and the only reading that is one. Suspect the alert file first, then the still-unverified `try_create_important_action` -> `open_interaction_window` hop that `tnt_91_alerts.txt` flags as "THE ONE UNVERIFIED HOP" |

Volume: one line per player per year, i.e. 8 lines in an eight-year run against the
17,178 TNTLOG lines run C produced. At the shipped telemetry default the helper is
a single `has_game_rule` lookup.

**Run C, 2026-08-24, is the baseline this instruments and the probe did not exist
for it, so run C's "correct and unreachable" verdict is PROVISIONAL until run D's
first `LEAN` line.** The finding was reached indirectly instead, and neither leg
of that inference proves what it was read as proving:

* The string `threat` occurs **0** times in 17,178 TNTLOG lines. That means
  **he never staged a threatened deal** - nothing more. Exactly three rows in the
  whole mod can print the token: the `item=threat` rows of `TERM`, `TERM2` and
  `TERM3` in `common\scripted_effects\tnt_3b_log.txt` (grep `item=threat` - no
  line numbers here on purpose, that file grows every round), and **all three are
  gated `limit = { exists = var:tnt_threat_p }`**, whose sole writer is the
  `effect` block of the `tnt_threat_p_toggle` scripted GUI
  (`common\scripted_guis\tnt_20_scripted_guis.txt`) - i.e. the player CLICKING
  the toggle. A count of 0 therefore says nothing at all about whether the
  checkbox was ever AVAILABLE to tick.
* His raw dread being 0 is an **inference, not a measurement**: `BASE_DREAD = 0`
  plus no `dread_baseline_add` on the starting traits plus `DREAD_MONTHLY_CHANGE`
  decay describes the STARTING value and its drift. It covers neither dread
  gained over eight years (executions, imprisonment, tyranny, Dread perks) nor
  any actual reading of the field.

Those two gaps are exactly why the `LEAN` probe was built. Run D is the first run
that answers the question with one grep.

---

## 7. READY-TO-RUN QUERIES (PowerShell)

Set the path once. **Do not use a `^` anchor** - the payload is mid-line.

> Every command in this section was executed against a synthetic log during
> authoring, including a proposer name containing spaces, parentheses, a colon and
> a hyphen. The `F` helper extracts such values intact. Windows PowerShell 5.1: no
> `&&`, no ternary, no `?.`.
>
> **CORRECTION 2026-08-17 - THE ACCEPT IDENTITY.** This guide used to say `accept`
> reconstructs from `gain - loss + rel - thresh`. **That is wrong**, because `rel` is
> logged in POINTS while `thresh` is logged in PERCENT. The true identity, verified
> exactly on eight real letters from the 2026-08-17 run, is
>
> ```
> accept = gain - loss + rel - thresh * gain / 100
> ```
>
> Worked examples from that log: `230 - 120 - 117 - 0.07*230 = -23.1` and the line
> logs `accept=-23`; `23 - 36 + 16 - 0.08*23 = 1.2` and the line logs `accept=1`.
> One letter in 29 (a `SETTLE` carrying `gain=254 loss=0 rel=-343`) logged
> `accept=0` where the identity gives `-89`, which suggests a floor or a partially
> abandoned settle - unexplained, and worth one probe rather than a rewrite.
>
> **CORRECTION 2026-08-24 - IT WAS A FLOOR, AND THE IDENTITY IS NOW EXACT. THE
> "UNEXPLAINED" NOTE ABOVE IS RETIRED; IT IS KEPT ONLY SO THE TRAIL READS.** The
> missing term is figure row 4b, `tnt_deal_floor_value`
> (`common\script_values\tnt_50_values.txt`, summed into `tnt_ai_accept_value`),
> which never appeared in this formula at all:
>
> ```
> accept = gain - loss + rel - thresh * gain / 100
>          + max(0, -(100 + rel * 100 / gain - thresh)) * gain / 100
> ```
>
> Measured on run C: the OLD identity leaves **1 discrepancy in 86** (`gain=262
> loss=66 rel=-270 thresh=2 accept=-66`, identity -79.24); the corrected one leaves
> **0 in 86**. It also settles the 08-17 outlier above without a probe: the floor
> contributes +88.9, the sum is -0.1, i.e. `accept=0` - **for any value of
> `thresh`**, which is why no `thresh` could ever have been found to fit it.
> **Use the corrected identity in any new reconstruction; the short form is still
> fine for a quick read of a healthy letter, and diverges only where the floor
> bites (deeply negative `rel` against a large `gain`).**

```powershell
$log = "$env:USERPROFILE\Documents\Paradox Interactive\Crusader Kings III\logs\error.log"

# Pull the mod's lines out of a log that also holds tens of thousands of engine
# lines, strip the engine prefix, and cache the payloads for every query below.
$twd = Select-String -Path $log -Pattern 'TNTLOG\|' |
       ForEach-Object { ($_.Line -split 'TNTLOG\|')[1] }
"total TNTLOG lines: $($twd.Count)"

# A tiny helper: pull one field out of a payload.
function F($line, $key) {
  $m = [regex]::Match($line, "\|$key=([^|]*)")
  if ($m.Success) { $m.Groups[1].Value } else { $null }
}
```

### Q1 - Did telemetry run at all, and at what rate?

```powershell
# Proof of life. BANNER was RETIRED IN V11 and never appears - do not look for it.
@($twd | Where-Object { $_ -like 'v1|TRY*' }).Count + @($twd | Where-Object { $_ -like 'v1|WTRY*' }).Count
$twd | Where-Object { $_ -like 'v1|TRY*' } |
       ForEach-Object { F $_ 'rate' } | Group-Object | Format-Table Count, Name -AutoSize
```

If that count is **0**, go back to section 1 — the game rule was off, or the log is from a
different session. If it is non-zero the telemetry ran, whatever else is missing.
*(This query read `v1|BANNER*` until 2026-08-19 and would have sent a reader hunting a game
rule that was demonstrably on: the 08-19 run carries 17,335 `TNTLOG` lines and zero `BANNER`.)*

### Q2 - How many offers were attempted, and how many fired?

```powershell
$kinds = $twd | ForEach-Object { ($_ -split '\|')[1] } | Group-Object
$kinds | Sort-Object Count -Descending | Format-Table Count, Name -AutoSize

$attempted = ($twd | Where-Object { $_ -like 'v1|TRY*' }).Count
$picked    = ($twd | Where-Object { $_ -like 'v1|PICK*' }).Count
$composed  = ($twd | Where-Object { $_ -like 'v1|COMPOSE*' }).Count
$applied   = ($twd | Where-Object { $_ -like 'v1|APPLY*' -and $_ -like '*src=ai_offer*' }).Count
"attempted $attempted -> picked $picked -> composed $composed -> accepted $applied"
```

### Q3 - Rejection reasons ranked by frequency

This is the answer to "why so few offers".

```powershell
$twd | Where-Object { $_ -like 'v1|NOTRY*' -or $_ -like 'v1|REJECT*' -or $_ -like 'v1|WSTOP*' } |
       ForEach-Object { F $_ 'why' } |
       Group-Object | Sort-Object Count -Descending |
       Format-Table Count, Name -AutoSize
```

Read it with section 4's warning in hand: `no_candidate` on top is normal.

### Q4 - Average acceptance value, and the breakdown, by archetype

A `SETTLE` line carries the numbers but not the archetype, so it has to be joined
to the `COMPOSE` line that precedes it. They share `tgtid`, and `COMPOSE` always
comes first, so one pass with a lookup table does it.

```powershell
# Join each SETTLE line to the COMPOSE that preceded it, by recipient id.
# NOTE: this must use ForEach-Object, not a `foreach` statement - a foreach
# statement cannot be piped ("An empty pipe element is not allowed").
$archMap = @{}
$rows = $twd | ForEach-Object {
  if ($_ -like 'v1|COMPOSE*') { $archMap[(F $_ 'tgtid')] = (F $_ 'arch'); return }
  if ($_ -like 'v1|SETTLE*') {
    [pscustomobject]@{
      arch   = $archMap[(F $_ 'tgtid')]
      accept = [double](F $_ 'accept')
      gain   = [double](F $_ 'gain')
      loss   = [double](F $_ 'loss')
      rel    = [double](F $_ 'rel')
      thresh = [double](F $_ 'thresh')
    }
  }
}

$rows | Group-Object arch | ForEach-Object {
  [pscustomobject]@{
    arch    = $_.Name
    n       = $_.Count
    accept  = [math]::Round(($_.Group | Measure-Object accept -Average).Average, 1)
    gain    = [math]::Round(($_.Group | Measure-Object gain   -Average).Average, 1)
    loss    = [math]::Round(($_.Group | Measure-Object loss   -Average).Average, 1)
    rel     = [math]::Round(($_.Group | Measure-Object rel    -Average).Average, 1)
    thresh  = [math]::Round(($_.Group | Measure-Object thresh -Average).Average, 1)
  }
} | Sort-Object arch | Format-Table -AutoSize
```

**Archetype numbers, for reading the `arch` column - CORRECTED 2026-08-17.** The list that
stood here (1 buy a truce, 2 buy an alliance, 4 tribute for protection, 5 ransom
prisoners, 6 a public compact, 7 a loan against tribute, "8 reserved and unused")
described the pre-retirement draw and every one of those indices except 3 is now
dead. The live twelve, with their weights, are in `CLAUDE.md` §3:

```
 3 buy a favour (hook) 12 |  8 buy land 12 |  9 call in a debt 10 | 10 sell land  8
13 sell an artifact     6 | 14 offer fealty 16 | 15 offer a ward   6 | 16 propose a marriage 16
17 buy my freedom      10 | 18 offer a hostage 8 | 19 buy a courtier 8 | 20 fealty on contract terms 8
```

Indices `1 2 4 5 6 7 11 12 15` are **burnt** - never reused, because the letter's `desc`
branches on the index and a reused one would print a dead archetype's prose.

`accept` reconstructs as **`gain - loss + rel - thresh * gain / 100`** (then rounded) -
`rel` is in points, `thresh` in percent - **plus the floor term
`max(0, -(100 + rel * 100 / gain - thresh)) * gain / 100`, without which one letter in
86 does not reconstruct.** See BOTH correction notes at the head of §7. If a
line does not reconstruct, a value in the chain is not being read the way this guide
assumes.

### Q5 - What the AI-to-AI world actually did

```powershell
# Concluded treaties by archetype and tier, with average price.
$twd | Where-Object { $_ -like 'v1|WDONE*' } | ForEach-Object {
  [pscustomobject]@{
    arch = F $_ 'arch'; tier = F $_ 'tier'
    gold = F $_ 'gold'; bal = [double](F $_ 'bal')
  }
} | Group-Object arch, tier | ForEach-Object {
  [pscustomobject]@{
    key = $_.Name; n = $_.Count
    avg_bal = [math]::Round(($_.Group | Measure-Object bal -Average).Average, 1)
  }
} | Sort-Object key | Format-Table -AutoSize

# Draw outcomes, including the deliberate "nothing this year".
$twd | Where-Object { $_ -like 'v1|WARCH*' } |
       ForEach-Object { F $_ 'arch' } | Group-Object |
       Sort-Object Count -Descending | Format-Table Count, Name -AutoSize
```

### Q6 - Which terms the AI actually trades, and for how much

```powershell
$twd | Where-Object { $_ -like 'v1|TERM|*' } | ForEach-Object {
  [pscustomobject]@{ item = F $_ 'item'; ask = F $_ 'ask'; amt = [double](F $_ 'amt') }
} | Group-Object item, ask | ForEach-Object {
  [pscustomobject]@{
    key = $_.Name; n = $_.Count
    avg_amt = [math]::Round(($_.Group | Measure-Object amt -Average).Average, 1)
  }
} | Sort-Object key | Format-Table -AutoSize
```

### Q7 - The AI's pricing versus the player's

```powershell
$twd | Where-Object { $_ -like 'v1|APPLY*' } | ForEach-Object {
  [pscustomobject]@{ src = F $_ 'src'; accept = [double](F $_ 'accept') }
} | Group-Object src | ForEach-Object {
  [pscustomobject]@{
    src = $_.Name; n = $_.Count
    avg_accept = [math]::Round(($_.Group | Measure-Object accept -Average).Average, 1)
  }
} | Format-Table -AutoSize
```

---

## 8. HOW THE LOGGING MECHANISM WAS CHOSEN

Recorded because the choice is not obvious and a future maintainer will ask.

**The candidates.** The engine string table in `binaries/ck3.exe` carries three
parallel triads: `debug_log` / `_scopes` / `_date` / `_details` / `_stack_trace`,
`error_log` / `_scopes` / `_stack_trace`, and `info_log` / `_scopes` /
`_stack_trace`. Measured call sites across the install:

| Effect | Call sites | Verdict |
|---|---|---|
| `debug_log` | 367 | rejected - see below |
| `debug_log_scopes` | 115 | rejected - emits a **multi-line** block |
| `error_log` | 16 | **chosen** |
| `info_log` | 0 | rejected under R2 (no call site anywhere) |
| `log` | 0 | does not exist |

**Why not `debug_log`.** Two disqualifying findings.

1. *It cannot interpolate inline.* Of 221 `debug_log =` lines measured across
   `game/common` and `game/events`, **zero** contain a square bracket. Its only
   route to dynamic text is an unquoted **loc key**
   (`debug_log = debug_log.swing_scales.diarch_swung`, 24 such sites), which would
   have put every line of this telemetry into a `.yml` file owned by another
   author. Confirmed live: that call site appears in this install's `debug.log`
   rendered as *Russian* text, proving the loc pipeline resolves the key.
2. *It looks debug-gated.* Vanilla repeatedly wraps it in
   `if = { limit = { debug_only = yes } }`
   (`10_dlc_tgp_house_bloc_scripted_effects.txt:904-908`). Those wrapped call
   sites **do** appear in this install's `debug.log`, which incidentally proves
   the user's last session was already running in debug mode.

**Why `error_log`.**

1. *It interpolates inline, with square-bracket datafunctions.* Verbatim vanilla:
   `error_log = "[THIS.Char.GetLogName] is married but not an adult!"`
   (`00_setup_tests_effect.txt:10`) and
   `error_log = "Invalidating [activity.GetName] of [activity.GetOwner.GetLogName] because a spouse is dead"`
   (`ep2_wedding_events.txt:1282`). No loc key needed, so the whole format lives
   in one file this author owns.
2. *It needs no debug mode.* **Not one** of the 16 vanilla call sites is wrapped
   in `debug_only`. They sit on ordinary gameplay paths that would be pointless if
   the call wrote nothing in a normal session. Error-severity script output is not
   suppressed - this install's `error.log` is 2 MB from one session.
3. *It lands in a file the user can name.* Vanilla says so itself, discussing two
   `error_log` calls: *"this does lead to potential duplication in the error log"*
   (`00_romance_effects.txt:399`).

**The honest limit of finding 2.** It is inference from vanilla's usage plus
severity, **not** a runtime A/B of one session with the debug flag and one
without - which cannot be done from the file system. If a run produces no
`TNTLOG` line while the game rule was demonstrably on, that inference is the
thing to doubt: relaunch in debug mode and compare. Nothing else in the design
changes if that turns out to be needed.

**The cost of the choice.** Telemetry lines land in the file modders read to find
real bugs. That is the price of working without debug mode, and it is why the rule
ships **off**.

### > INSIDE AN `error_log` STRING, `THIS` IS THE ONLY PROMOTE THAT RESOLVES

Measured, not assumed — this is the finding of the first full half-year run
(2026-08-13), and it silently emptied **every number** in the telemetry until it
was fixed. The run produced 17,262 `TNTLOG` lines and, beside them, 24,767
`pdx_data_factory` errors saying exactly which promotes the data layer could not
find:

| written in the string | result in the log | verdict |
|---|---|---|
| `[THIS.Char.GetLogName]` | `Yuangui_5143 Фэн of c_zhengzhou (Internal ID: 44987…)` | **works** |
| `[GetCurrentDate.GetYear]` | `1178` | **works** |
| `[ROOT.Char.GetID]` | `ERROR:[ROOT.Char.GetID]` | fails |
| `[actor.Char.GetLogName]` | `ERROR:[actor.Char.GetLogName]` | fails |
| `[ROOT.Char.MakeScope.ScriptValue('x')]` | *empty* — `chance=`, `gold=`, `bal=`, `ratio=` | fails |

**It is not about temporary versus permanent scopes.** That was the first
hypothesis and the log refutes it: `tnt_ai_proposer` is saved with
`save_scope_as` (`tnt_37_ai_offer.txt:269`), i.e. permanent, and it fails
identically. An `error_log` string is localized in a bare data context that
carries the current scope and nothing else — no `ROOT`, no named scopes, however
they were saved. Vanilla never contradicts this: its two interpolating call sites
use `[THIS.Char…]` and an event's own `[activity…]`, never a script-saved name.

**THE TWO RULES THAT FOLLOW, and both are now applied throughout `tnt_3b_log.txt`:**

1. **People:** print the character you are standing on as `[THIS.Char.…]`. Anybody
   else goes through a variable on that same character — `set_variable` before the
   line, `remove_variable` after it — read back as
   `[THIS.Char.MakeScope.Var('tnt_log_b').Char.GetLogName]`. The deal partner needs
   no bridge at all: he already lives in `var:tnt_partner`.
2. **Numbers:** never call `ScriptValue` from the string. Compute the value in
   **script** — `set_variable = { name = tnt_log_n1  value = tnt_ai_gold_low_value }`
   — and let the string only read it back with
   `[THIS.Char.MakeScope.Var('tnt_log_n1').GetValue]`. This is not merely a
   promote fix: a value evaluated through `MakeScope` from the data layer stands in
   a fresh scope context where `scope:recipient` and `var:tnt_partner` do not
   exist, so any partner-dependent price would have come out wrong even if the
   promote had resolved. Computing in script keeps every scope the value needs.

The bridge variables (`tnt_log_b`, `tnt_log_n1`…`tnt_log_n5`) are set and removed
inside the same rule-gated block, 77 pairs of them, so nothing survives into a
savegame and nothing is computed when the rule is off.

**What this means for the first run's data.** Its category counts are sound —
`WARCH` archetype mix, `WDONE`, `WSTOP` reasons all printed literal tokens. Every
numeric field in it is blank and must not be read as a zero: `gold=`, `bal=`,
`ratio=`, `chance=`, `accept=` were never written. Rerun before drawing any
conclusion about the AI's *pricing*.

---

## 9. VOLUME, AND WHAT IS NOT INSTRUMENTED

### Expected volume, half a game year, 1066 start (~2,000 AI rulers count+)

| Setting | Lines | Notes |
|---|---|---|
| `off` | **0** | one `has_game_rule` lookup per log site, nothing else |
| `on` | **~600 - 1,600** | dominated by `TRY` + `NOTRY|why=no_candidate` |
| `verbose` | **~2,000 - 4,000** | adds `WPULSE`, ~1,000-2,500 lines on its own |

Use `on` for the half-year run. `verbose` buys exactly one thing: it separates
"the AI-to-AI pulse never ran" from "it ran and the dice said no", which at `on`
a `WTRY` count of zero cannot distinguish. Use it for a short confirmation run.

### Not instrumented in this iteration

Each needs a one-line edit in a file the telemetry author does not own. The
helpers are already written and named in `tnt_3b_log.txt` (L12/L13).

| Gap | File that needs the line | Helper to call |
|---|---|---|
| the offer was composed but **aborted below threshold** | `events/tnt_ai_events.txt`, `.0001` abort branch | `tnt_log_abort_effect` |
| the player **accepted / declined / countered / hushed** | `events/tnt_ai_events.txt`, `.0002` options | `tnt_log_verdict_*_effect` |
| which of six callers tore the offer down | `.0002`, `on_trigger_fail`, `tnt_71_ai.txt` GC | - |

**Workaround for the outcome gap, and it is good enough for this run:** a `CLEAR`
line with a matching `APPLY|src=ai_offer` for the same player in the same year
means the player **accepted**. A `CLEAR` with no `APPLY` means the offer died -
aborted, declined, hushed or timed out, and those four are not separable yet.

---

## 10. VERSIONING

The `v1` in every line is the format version. **Bump it** if any field changes
meaning, any `why` token is renamed, or the direction convention changes. A
consumer should refuse to parse a version it does not know rather than silently
misreading a field. The `TNTLOG` prefix itself must never change - it is the only
thing that makes the mod's lines extractable from an engine log.

Term-sweep helpers `L8` / `L10` / `L19` are three near-identical copies by design
(there is no parameter substitution into log strings - zero vanilla call sites for
`error_log = "...$X$..."`). **Edit all three or none**, or `TERM`, `TERM2` and
`TERM3` stop being comparable and section 6's diffs become meaningless.
