# Parley 1.2.1 — Advanced term valuation

Implementation record, 2026-10-05. Target CK3 1.20.0.3. This is a new local candidate, not a published release or native-engine certification. Published 1.2.0 and its frozen evidence remain unchanged. Source baseline for Classic regression: `e17e147cec14975196ce6338e3e2e41afab2bcb5`.

## Policy and scope

`tnt_advanced_valuation`: **Classic** (default) / **Scaled**. The sole rule read is `tnt_scaled_valuation_enabled_value` in `tnt_5e_valuation_policy.txt`; no character variable caches it. Missing setting returns Classic. The existing advanced-terms visibility rule is independent. Currency permissions, eligibility, atomic settlement, MCA and the held AGOT integration are not expanded.

Covering all aspects means auditing every live term and its consumers, not multiplying every price by a universal difficulty factor. The original low territorial ceilings were real; vassals were not originally a universal fixed 200 points.

## Reviewed valuation coverage

| Term | Scaled policy | Consumer safeguards |
| --- | --- | --- |
| Ceded county | `20 + development / 2`; existing de jure ×1.4, culture ×1.25 and border ×1.2 contexts remain | Single, multiselect and AI-world share the county helper. Higher-rank cession remains prohibited; no untransferred de jure land is priced. |
| Fealty | Voluntary `50 + land`; requested `100 + land` | Window and incoming voluntary archetypes14/20 retain distinct contexts. AI-world requests use demanded cost, with no 1,200-gold price compression. |
| Independence | `100 + released ruler's land` | Mirror directions price the actual released ruler, not the former liege. |
| Transfer vassal | `40 + transferred ruler's land`, existing de jure ×1.4 | No 200-point ceiling; no implied claim to the giver's remaining territory. |
| Courtiers | Baseline 1; strongest regular skill, separate prowess, concrete qualities/status, bounded attachment and accompanying family up to 60 | Same intrinsic head value governs useful AI candidate admission/pick/motive; global meaningful-offer floor is not reduced. Scaled preflight rejects overlapping family bundles. |
| Hostages | Native `hostage_value` once, minimum10; bounded home-realm leverage | Heir10%/cap60, child5%/cap30, other kin2.5%/cap15, exclusive branches. No whole-realm sale price. |
| Promised/spent hooks | Original tier ×`clamp(1 + debtor land/400, 1, 2)` | Correct debtor on both sides and AI-world; availability booleans remain booleans. |
| Economic obligations | Original tax/levy/fortification/coinage row ×`clamp(1 + subject land/200, 1, 3)` | Factor applied once, original sign intact; inactive/default rows perform no realm walk. |
| Personal contract rights | Existing native/contextual anchors | No arbitrary territorial multiplier for council/religion/revocation/war/succession rights. |
| Marriage, betrothal, grand wedding and resulting alliance | Existing detailed pair-specific formulas and diminishing returns | Gain cap2000 remains; Scaled removes the aggregate loss cap6000. Native eligibility remains. AI-world dowry stays a separate eligible-kin matching mechanism, not territorial ownership. |
| Artifacts | Existing rarity, durability, usefulness and ownership/claim adjustments | Audited, not globally inflated. |
| Currency and relationship values | Existing conversion, traits and standing | Faith/fame/devotion permissions remain directional, including manual and incoming-AI settlement. No new tax on late-game piety generation. |
| Threats | Existing strength calculation and minimum100 | Scaled AI-world coercive fealty additionally requires pressure to cover demanded fealty value; existing raw ratio4 and relational guards remain. |
| Retired claims, prisoners and wards | Remain retired | No accidental reactivation or hidden new eligibility. |

`land` sums **each actual sub-realm county once**, including subordinate vassals, at `20 + development/2`, then adds one primary-rank premium: duchy20, kingdom40, empire60, hegemony80. No low cap; secondary titles do not multiply the territory. `realm_size` is not used as a county count. The native iterator precedent is `every_sub_realm_county` in installed `00_law_values.txt`, `00_invasion_values.txt` and `00_hold_court_values.txt`.

Courtiers use the strongest of diplomacy/martial/stewardship/intrigue/learning: skill10/12/15/18/20/25/30 adds2/5/10/16/24/40/60, one band only. Prowess12/15/20/25/30 adds3/6/12/20/30. Inspiration15; physician6; intellect3/6/10, physique2/4/6, beauty2/4/6, highest tier in each group. Dynasty renown adds half its level, maximum5. One strongest eligible explicit claim adds county4/duchy10/kingdom18/empire-or-higher26, halved when unpressed. Giver kinship and receiver friendship/romance each add5 once. These are designer weights, not native acceptance or future lifespan/health predictions.

Native traveling-family membership determines accompanying people. Their intrinsic values add up to 60 per selected head, excluding the head itself and anyone already a courtier of the receiving ruler. Existing explicit courtier/hostage overlap guards remain. Scaled additionally rejects two selected heads sharing an otherwise unselected traveling dependent, preventing duplicate pricing and movement. A moving dependent also cannot be an endpoint of a selected marriage: marriage executes before courtier transfer and could change the priced family bundle. Both directions, either marriage endpoint and nonmoving-family exceptions have source-backed tests. AI usefulness still tests the selected head's intrinsic value, not an accumulated family premium. Native membership and actual family movement remain part of the engine test.

## Auto-balance and AI review

Fixed acquisition bounds252 for fealty and65 for a county were tied to Classic prices. Scaled uses `partner demanded fealty + 2`, and `2.1 × county value + 2`, respectively. These are conservative acquisition budgets, not another multiplier on settled prices. Final acceptance still reads the shared raw values. The standing, relationship and signed-obligation boundaries are preserved; displayed multipliers are not applied twice.

Every new realm calculation is live. This avoids stale persistent caches when territory changes, but engine UI responsiveness with very large realms needs measurement. Empty hook/default contract rows are guarded before expensive walks.

## Verification boundaries and next native checks

### Additional 1.2.1 rule: Threat frequency (2026-10-06)

Independent of Classic/Scaled, `tnt_threat_frequency` selects 0 (default), 1,
5 or 10 years. `tnt_threat_cooldown_years_value` is the only policy read;
`tnt_threat_cooldown_available_trigger` checks the actual aggressor's timed
`tnt_threat_cooldown` variable. Zero and absent settings bypass the global
timer. The separate 15-year target-specific opinion lock remains intact.
The old `tnt_threat_scale` IDs and 2.5/5/7.5/10 coefficients are unchanged;
its visible name is now Threat strength.

The timer starts at five valid resolution seams: manual threatened treaty,
paid incoming demand, refused valid incoming demand, AI-world cash ultimatum,
and AI-world coerced fealty. It is not a draft/checkbox cost. Invalid pending
demands dismiss without a new timer or resource charge. Both general threat
gates, the GUI reason and effect, pressure value, final preflight, incoming
demand payment and AI-world cash settlement enforce the rule. Closing or
clearing a deal cannot clear the timer; uninstall removes it from player and
AI characters. Timers belong to characters, not dynasties or successors.

The 15 new source-backed tests execute production ASTs in a strict fixture
model (including simulated time expiry); they do not execute CK3 itself.
The Classic composer comparison now explicitly asserts and removes only its
two new zero-duration no-op calls; negative mutations protect that boundary.
Current localization contracts are 657 DEV / 647 GAME keys in nine languages,
with unchanged 81/80 runtime-file inventories. Frozen Scaled-only RC1 retains
its original 647/637 counts and source evidence. Its engine test cannot certify
this addition, and a new candidate must be prepared before native testing.

Native checks for the new candidate: RU/EN rule labels and blocked tooltip;
one successful threat followed by a different target; ordinary diplomacy still
available; 1/5/10-year expiry; same target still blocked for 15 years; save/reload;
valid paid/refused AI demands; stale pending demand with no second payment;
AI-world ultimatum/fealty and closed-game logs. Use copies of test saves.

Final local checks on 2026-10-06: all 15 developer-runner components passed;
the new cooldown suite passed 15/15, release-tool tests 41/41 (including an
actual in-memory 81-to-80-file GAME projection preserving all cooldown sites),
and publication tests 42/42. Rule, tooltip and nine-language checks passed.
The updated guide renders deterministically and passed 134 local publication
checks; Steam's serialized CRLF form is 7,806 UTF-8 bytes. Initial failures
from old exact-shape checker expectations were repaired to require both the
new cooldown and retained old guards, not waived. Evidence files use the
`parley-1.2.1-threat-frequency` prefix under the external release workspace's
`verification-evidence/`. No new frozen GAME candidate, engine test or external
publication was performed in this step. Pre-existing publication-tool changes
in DEV were preserved and not committed wholesale.

### RC2 preparation (2026-10-06)

The new immutable GAME candidate `2026-10-06-parley-1.2.1-rc2` includes both
Scaled and Threat frequency. It was built from clean source commit
`71e8ce2b5fbe87cf8ceb215ac6426062da47691e`; its separate numbered kit is
`deploy/parley-1.2.1-rc2/` in the release workspace. The old RC1 and public
1.2.0 builds/kits remain unchanged. This is preparation, not publication or
native verification.

Independent reconstruction and archive CRC/member checks passed: 80 GAME
files, 647 keys in each of nine languages; five cooldown-consumption sites
retained. Compared with RC1, 18 files changed and 62 are byte-identical;
the Scaled helper files themselves are unchanged. Parley discovery passed
112 tests with three explicit baseline/native-input skips (115 total),
release tools 41/41, publication tools 42/42, and frozen-copy validation
134/134. Counts overlap with earlier suites and are not additive.

The launcher wrapper is `game_parley_1_2_1_rc2.mod` in the CK3 user-data
`mod/` directory; its metadata and target path are checked, but launcher UI
visibility and actual loading are not yet observed. No playset or save was
changed. All four candidate platform journals remain `NOT_PUBLISHED`.
External evidence: `verification-evidence/2026-10-06-parley-1.2.1-rc2/`.

### RC2 native follow-up and RC3 display corrections (2026-10-06)

The owner manually exercised RC2 in CK3 1.20.0.3 as Saladin. Screenshot,
save and log reviews in the Parley task established the following scoped results:

- One-year global threat lock applied after a resolved threat, blocked another
  ruler, survived save/reload and was absent by 29 October 1180. The original
  victim remained blocked by the separate 15-year memory. Exact expiry-day
  behavior was not observed because time was advanced beyond it.
- Scaled vassal offers distinguished Baalbek (one county), Fayyum (three), and
  Medina (six including sub-vassals). The combined Medina/Baalbek transfer
  preserved subordinate hierarchy and conserved the auto-balanced payments.
- A courtier transferred to the correct court. Alexios travelled and arrived as
  Manuel's hostage at Saladin's court. Musa swore fealty with both duchies and
  all seven counties, paying/receiving the observed 413-gold leg correctly.
- Tughtekin became independent with his realm intact and no currency change.
  Dakhla and its occupied capital barony transferred together. A weak favor
  then created the correctly directed ten-year hook, with no currency change.
- No new transaction errors were found for these settlements. The complete
  game log is NOT clean: prior native/other diagnostics remain, and the newly
  observed missing negated hatred localization is addressed below.

Named save witnesses include `parley121_cooldown_used`,
`parley121_cooldown_expired`, `parley121_scaled_subjects_done`,
`parley121_scaled_courtier_done`, `parley121_scaled_hostage_sent`,
`parley121_scaled_hostage_arrived`, `parley121_scaled_fealty_done`, and the
paired `parley121_scaled_independence_*`, `parley121_scaled_title_*`,
`parley121_scaled_hook_*` saves. This is bounded RC2 evidence, not a new
RC3 engine pass or comprehensive AI/Classic/5-year/10-year certification.

RC3 adds display-only wrappers that apply the same explicit `round = yes`
used by aggregates. Fractional prices are still summed BEFORE rounding;
two independently displayed rounded rows may differ by one from their total.
Landless character rows hide invalid primary titles. The compact ledger has
a fixed-height gift-floor correction beside net pressure, including the
signed reverse-hook contribution. Pure gifts floored to zero still follow
the existing greater-than-zero acceptance rule; this is not a balance change.
All nine languages define the missing `NOT_tnt_err_hatred` fallback.

Threat tracking uses the existing `tnt_threat_cooldown` variable through native
`VarRemaining` / `GetVarTimeRemaining`, `GetTimeDifferenceWithDays` and
`GetCurrentDateWithDiff`. It adds no saved state, migration, modifiers or timer
writers. Read-only custom localization shows the remaining time in the threat
row, the remaining time plus expiry date in its checkbox tooltip, and the same
status in the right-click negotiation tooltip. Dynamic text is deliberately
outside BuildTooltip's bare failure keys. Zero/missing frequency hides an old
timer because the same availability policy is reused. The Russian zero option
is the owner's requested «нету». The independent victim-memory reason remains;
no unsupported exact date is inferred from the unrelated global timer.

Native UI checks still required on the new build: load a COPY of an existing
cooldown save, hover the threat and negotiation menu entry, verify countdown
and expiry, recheck Maria's half-point score and landless title, and inspect
the compact floor line. Do not overwrite frozen RC2 or its historical reports.

### Earlier Scaled-only evidence

Local validation on 2026-10-05: the developer runner passed all 14 component suites; Parley discovery passed 95 tests with 3 explicit baseline/native-input skips (98 total) before the final mixed-family safeguard. The final people suite passed 14/14, including the added marriage/dependent-overlap regression; the separate installed-CK3 compatibility run passed all 13 tests, including the two native-input checks skipped by discovery. The remaining discovery skip is the historical AGOT-removal delta check requiring the immutable RC9 baseline, not a Scaled scenario. All 36 new Scaled tests passed (14 territorial/balance, 14 people, 8 strategic). Publishing tests passed 19/19 and release-tool tests 40/40. `git diff --check` passed. These totals overlap and must not be added as independent coverage. External developer reports are under `verification-evidence/` in the release workspace, with the final run named `parley-1.2.1-rc1-final-dev-checks.json`.

- Strict source-AST models execute production land/person/strategic formulas against explicit native-fact fixtures; unknown executed syntax fails. Native iterator membership and arithmetic precision still need an engine check.
- Classic AST pruning compares changed paths to the pinned 1.2.0 source. Strategic cases that insert a multiplication by 1 additionally use numeric baseline comparisons.
- Tests cover nested sub-vassals, development, rank counted once, no territorial cap, directionality, useful-person selection, strongest claims, bounded hostages/hooks/contracts, signed obligations, AI affordability/coercion, and manual/incoming-AI currency settlement.
- Existing source, currency-rule, dispatcher, localization, packaging and compatibility suites remain required; their pass does not certify a new GAME candidate.
- Next native scope: new rule and text in RU/EN; one-county versus multi-county/sub-vassal valuation; representative people/family bundles; both directions of hooks/contracts; repeated Auto-balance and actual settlement; incoming/world AI; large-realm UI response; save/reload; post-exit logs. Use a disposable test save and exact1.2.1 build, with Classic as control.

Do not reply to the community that the feature is released or fully balanced before the relevant GAME test and verified publication. Scaled does not stop all piety-to-gold income or prove long-campaign/multiplayer balance.
