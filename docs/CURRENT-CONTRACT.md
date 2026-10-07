# Current development and release contract

Updated 2026-10-07: published Parley 1.2.1 is the runtime parent of the 1.2.2 localization candidate targeting CK3 1.20.0.4. Only 13 translated values and the descriptor version change in GAME. The ten DEV diagnostic keys per language remain in source and are removed only by the reviewed release projection. See [the 1.2.2 candidate record](LOCALIZATION-1.2.2.md) for the exact scope and pending release gates. Historical records below retain their original versions and acceptance scope.

Historical record, 2026-10-05: Parley 1.2.1 is in local development for CK3 1.20.0.3, adding optional **Advanced term valuation — Classic / Scaled**. [The implementation record](ADVANCED-VALUATION-1.2.1.md) describes formulas, AI coverage and pending native evidence. Classic remains the default, including saves without the new setting. Parley 1.2.0 is the verified public release on all four platforms; its immutable payload is `2026-10-04-parley-1.2.0-rc1`. The earlier 1.1.0 payload `2026-10-01-game-rc11` and all historical evidence remain unchanged. The currency-rule developer evidence is in [CURRENCY-RULES-1.2.md](CURRENCY-RULES-1.2.md); it is not Scaled evidence. Standalone MCA remains version 3.1.0. AGOT:MCA 2.2.0 remains on its historical CK3 1.19.0.6 / AGOT 0.5.2.1 / MCA 3.0.1 baseline, pending compatible upstream AGOT. Publication records remain separate. Runtime source and explicit checks resolve implementation details; historical `_docs` specifications must not override this record.

The historical RC10 compatibility candidate contained only Parley and MCA; RC11 is the published payload. Parley's AGOT-specific integration is disabled at the author's request, with the checks and their calls preserved as comments: dragon exclusions, Night's Watch and wildling restrictions, uninteractable-government checks and the temporary-independence marker are no longer queried by Parley. Current public copy states **AGOT compatibility: awaiting the AGOT update for CK3 1.20.** The original AGOT screenshot is preserved but excluded from the current public gallery. Source/package checks and a fresh Parley-only native startup/UI smoke passed. The smoke covered the empty table, ordinary fealty, courtiers and the native marriage picker on a paused original baseline, with no proposal, time advance or save. Post-exit logs contain only two known human-only interaction notices; the 38 prior AGOT diagnostics are absent. This is scoped RC10 evidence, not a repeated full gameplay or AI-campaign test.

RC9 removed obsolete Parley dependency metadata from MCA and passed a separate MCA-only native picker smoke. Parley's RC9 runtime matched RC8. RC4 exposed the removed administrative rule and stale marriage balance verdict; RC6 verified the corresponding corrections through native UI checks and 34 engine-harness assertions. RC7 verified MCA's identity-scale fix and both picker sides, but was rejected after natural AI-world submission called vanilla vassalization without its new effective-actor alias. RC8 supplies that alias at the shared AI-world apply seam. RC8 separately passed 12 native mutation assertions and a no-harness short campaign with an accepted natural fealty treaty. Earlier scoped passes are reused only for unchanged bytes and semantics; RC7 remains rejected. Historical locks and packages are unchanged. See [CK3-1.20-COMPATIBILITY.md](CK3-1.20-COMPATIBILITY.md) for witnesses and limits.

## Three copies

| Copy | Purpose | Editing and verification |
| --- | --- | --- |
| `dev` | Runtime source, tests, developer references and publication material | Author changes here and commit reviewed work to the appropriate Git repository. |
| `game` | Clean platform upload payload | Generate from a fixed developer revision through the release tool; verify exact inventory, transformations and hashes. |
| `workshop` | Steam-downloaded copy of the uploaded mod | Treat as delivery output; compare to the uploaded package and do not develop in it. |

Runtime source resides under `dev/<repository>/mod/<folder>/`. The folders are `parley`, `marriage_calc_assistant` and `agot_marriage_calc_assistant`. The same clean game content is intended for Steam, Paradox and Nexus; platform-specific packaging and metadata are recorded separately.

Publication preparation deliberately creates a different Parley game projection: developer documents, telemetry and the test-only AI offer-rate option are excluded by the release tool in `tools/release/`. Instrumented developer logic remains in `dev`. Package verification must prove the allowed differences explicitly, not silently refresh or relax the source checks. The frozen 1.19 package `2026-09-30-game-rc3` includes the corrected auto-balancer and matches its engine-tested staging payload for all 104 files. Its focused result and limits are recorded in [AUTOBALANCE-FIX.md](AUTOBALANCE-FIX.md). The earlier [RC2 smoke](RC2-SMOKE.md) remains historical evidence for its stated scenarios; it did not exercise the later-reported balancing failure. Neither record establishes publication or Workshop delivery, nor compatibility with CK3 1.20.

## Parley behavior and ownership

As of 2026-10-06, 1.2.1 also adds **Threat frequency**: a global cooldown on
the threatening character, 0/1/5/10 years, default0 including missing-setting
saves. It applies to manual and AI threats independently of Classic/Scaled.
Drafts do not consume it; successful threatened treaties and valid paid/refused
AI demands do. The separate 15-year same-target memory remains. Existing
calibration is visibly renamed **Threat strength**, retaining IDs/coefficients.
See [the 1.2.1 record](ADVANCED-VALUATION-1.2.1.md) for execution boundaries and
pending native checks. Frozen 1.2.1 RC1 is Scaled-only and must not be reused
to test or publish the new rule.

Parley provides a two-sided negotiation window, partner-oriented valuation and auto-balancing, incoming AI letters and an AI-to-AI negotiation layer. It owns its `tnt_` runtime namespace and five legacy addon hooks. MCA does not define or call those hooks. Parley does not override a vanilla file path in the checked source tree; this is a measured compatibility surface, not a guarantee for every mod combination.

On 1.20, marriage defaults and gender-dominance pricing read the character's Rite. Legality continues to use current native helpers. Parley supports direct ruler negotiations; its opener and borrowed marriage picker are hidden for proxy arrangements where the effective arranger is another character. Marriage edits invalidate an old auto-balance verdict; committed line flips also refresh cached prices. Jizya protection intentionally follows the native faith-level contract parameter.

AI-world paid fealty and coerced submission share one native apply seam. It refreshes `puppet_or_actor` from `actor`: the actor becomes liege and the recipient becomes vassal. Existing obligation options remain boolean false. Six source regressions cover alias freshness, caller scope and both routes. RC8 passed 12 engine assertions for absent/stale aliases, actual vassalage, opinion and ownership. Its separate no-harness run reached 24 January 1179 from the original 1 October 1178 baseline and executed Amr's natural fealty offer for 743 gold at +2: player gold changed 1,318 to 575 and Asir joined the realm. The run does not certify every AI scheduling or policy branch.

The current threat access minimum is 100 points inclusive in player and AI paths. The multiplier ladder remains 2.5 / 5 / 7.5 / 10, with normal at 5. Selected threats below the minimum contribute zero, cannot seed Equalize, and can be unticked. The rule-conformance check protects the current consumers.

Version 1.2's prestige and piety permissions use one directional policy per currency: parameter A is the actual giver and B the receiver, independently of who opened negotiations. Prestige supports unrestricted, disabled, exact same faith, strictly higher fame and the retained equal-or-higher fame mode. Piety supports unrestricted, disabled, exact same faith, different faiths, the retained same-religion mode, and same faith with strictly higher devotion. Defaults remain unrestricted. Fame/devotion checks compare levels, not resource balances or title tiers. The four table lanes and amount controls, shared manual/AI settlement, AI-world resource guards and whole-deal preflight obey these policies. Disallowed draft amounts are cleared before settlement/netting. Final validation is atomic before resource mutation; rechecking each leg after the first transfer could incorrectly invalidate the second leg when levels change. Currency restrictions do not suppress unrelated prestige/piety consequences. No MCA/adapter ABI or on-action ownership changes accompany this update.

The hidden AI-letter composer has no engine cooldown. PICK writes no provisional recipient cooldown. Only visible letters write the recipient rate variable: frequent six months, normal one year, rare three years. The developer test rate skips it. The hidden composer rechecks off/rate/open/partner/refused-envoys/live-proposer conditions. A valid draft remains owned by `tnt_partner` until its visible letter is answered; aborts clear it so another proposer may try. The correction added no queue or saved variable. The developer source checks and dispatcher model protect this structure; the release projection must preserve the non-test behavior.

## MCA behavior and boundary

MCA works independently of Parley and requires no other mod. It scores candidate gameplay potential, not marriage acceptance or guaranteed benefit from a particular pairing. Both picker sides share inheritable-quality, skill, age-based reproductive, dynastic-prestige and explicit-claim components. Native potential-alliance metadata and optional adapter components are included through the existing wrappers. The score and its native breakdown use the same component values.

Optional sorting keeps a saveable snapshot on the local player and projects native list items. It does not stamp candidates or change who a displayed row selects. Lifecycle/context guards clear the snapshot; close the picker before saving or uninstalling. MCA adds no global cleanup sweep or on-action.

MCA 3.1.0 follows the 1.20 effective-arranger portrait and carries arranger ownership through all eight GUI context packets. Scoring and sorting require both the interaction actor and effective arranger to be the local player. Proxy arrangements use the native unscored, unsorted list; switching arranger invalidates a stale snapshot. Score weights and adapter component names remain unchanged.

Twelve MCA sorter callback states carry native identity `scale = 1` to avoid empty-animation diagnostics. RC7 verified the large list, both picker sides, tooltip arithmetic, selected-character identity and exercised filter/default/back/close resets with no animation-state warnings. Native puppet UI, active-snapshot time advancement and save/reload remain unverified. MCA runtime is unchanged in RC8; the combined candidate passed the separate Parley retest without repaired scope or MCA animation diagnostics.

Its sole vanilla-path override is `gui/interaction_marriage.gui`. A mod replacing that file requires a reviewed functional compatibility patch. The derived marriage row depends on the base row's `character_relation` seam. The frozen patch and inherited-row checks guard these boundaries against the installed vanilla and AGOT versions.

Eight public adapter component defaults use formula blocks `{ value = 0 }`; scalar zeros caused the tested missing-adapter-value regression. Public names and core aggregate ownership remain stable. Adapters must be pure, deterministic contributions and supply matching localized descriptions.

The developer source inventory is 18 files including its existing README. The documentation-free game inventory is 17 files. Preserve both contracts explicitly and keep historical release manifests unchanged.

## AGOT:MCA behavior and boundary

AGOT:MCA owns six pure overrides: P c1, R c1–c4, and alliance base 40. P c1 aliases R c1. Passing AGOT's `is_current_dragonrider` predicate contributes +30 on each picker side; R c2–c4 remain zero compatibility slots. The weight describes current-dragonrider potential and does not promise dragon transfer or control.

The adapter owns twelve payload files and five localization keys in each of nine languages. It adds no GUI, interaction, effect, decision or on-action files. Its checks pin the relevant upstream predicate bodies and require the current MCA formula-zero defaults. MCA owns the aggregate scores, row and sorting state.

## Localization and compatibility evidence

The pending RC3 display-correction profile has **662 DEV / 652 GAME keys**
per language and **83 DEV / 82 GAME files**. It adds a display-only rounding
file and read-only cooldown custom localization. Existing RC2 saves require no
migration. The RC2 native follow-up and RC3 smoke boundaries are recorded in
`ADVANCED-VALUATION-1.2.1.md`; all earlier counts below remain historical.

The RC2 1.2.1 rules added fifteen keys per language: 657 DEV / 647 GAME keys across the same nine languages. Five new script-value files brought its explicit runtime inventory to 81 DEV / 80 GAME files. The earlier Scaled-only RC1 retains 647/637 keys; its frozen manifests are not rewritten. Fresh native verification of RC3's display changes remains necessary.

RC8 retains 40 classified startup diagnostics. Seven additional native log records reproduced exactly apart from wall-clock timestamps with all mods disabled on the same original save through 24 May 1179. This supports attribution outside active Parley/MCA for those records, not a globally clean log or an explanation of the original saved state. The separate AI harness also retains 11 nonshipping fixture-format warnings despite its 12 passing assertions. See the compatibility record for archived evidence.

The audited developer trees each contain English, French, German, Japanese, Korean, Polish, Russian, Simplified Chinese and Spanish. Current developer key counts are Parley 642, MCA 22 and AGOT:MCA 5 per language. The 1.2 projection removes Parley's ten diagnostic/test-only entries, leaving 632 public keys per language. RC10 comments out the unused AGOT-only error key in all nine languages, retaining its original translations for later review. RC3 contains 623, 22 and 5 keys per language respectively after removal of Parley's ten diagnostic/test-only entries. The auto-balance correction added one public verdict key in every language; historical RC2 retains its original 622 Parley keys. Matching key/token coverage across all nine languages passed; this does not assert a linguistic review of every translation.

The historical checked environment is CK3 1.19.0.6 and AGOT 0.5.2.1. The 1.20.0.2 adaptation and engine evidence remain historical; Parley now targets 1.20.0.3 after the separate source review above. AGOT remains excluded from the current vanilla release. Source checks establish Parley's zero vanilla-path collisions, MCA's one reviewed GUI override, and the adapter's pure script-value boundary. Compatibility descriptions must also state dependencies and required ordering. They must not infer universal compatibility, multiplayer coverage or normal-rate balance from these checks.

## Development and release evidence

Development finalization recorded scoped source checks, independent models and targeted runtime observations. The dispatcher correction received a completed vanilla test; the combined AGOT smoke delivered Jeyne Arryn's ordinary 165-gold offer after three empty drafts. The formula-zero correction restored the observed rider contribution to 95 = 35 dynasty + 30 inheritable qualities + 30 rider potential on P and the native pinned R row. A later 125% UI acceptance was user-reported, with closed-log inspection; it was not an independent visual observation by the assistant.

These results have bounded coverage. They do not establish every unpinned R rider case, multiplayer behavior, all snapshot/save scenarios, normal-rate balance or whole-game clean logs. The control and localization audits refer to the frozen developer trees. Do not re-run closed development scenarios merely for publication bookkeeping.

The historical `2026-09-30-game-rc2` projection passed inventory/hash checks, validation of the permitted telemetry/test-rate removal, and a focused combined smoke on CK3 1.19.0.6 with AGOT 0.5.2.1. In a fresh English Viserys campaign from 8106.4.18 to 8106.6.27, public Frequent rules, Parley's UI, an MCA component tooltip and Lord Bernard's natural offer of Fine Regalia for 124 gold were observed. No treaty was committed and the closed development cases were not repeated.

That RC2 smoke is a scoped PASS, not a whole-game clean-log claim. Startup contained 112 references to removed developer rules: 108 in older-save enumeration blocks and four whose source remains unlocalized. Three generic animation warnings remain unattributed, with no visible issue observed. No new family-namespace errors appeared during the short run. [RC2-SMOKE.md](RC2-SMOKE.md) records the historical scope and evidence location. RC2 is superseded by RC3 and is not the current upload candidate.

RC3 corrects a shared original-dev/RC2 auto-balance defect. A controlled same-save comparison reproduced +23 with opposing payments in the old developer build; the corrected game build reached +1 with player-only currency payments, and a repeat left the terms unchanged. The canonical RC3 payload is byte-identical to that tested staging build. Source regressions also cover the shared incoming-letter solver; the separate AI-to-AI direct-pricing path was unchanged. MCA and AGOT:MCA payloads remain byte-identical to RC2, so their closed tests were not repeated. This focused evidence does not certify every treaty combination, long-term AI behavior, multiplayer or globally clean logs. See [AUTOBALANCE-FIX.md](AUTOBALANCE-FIX.md). Workshop delivery verification remains pending until an actual upload and download.

## Documentation and source evidence

The original Parley `_docs` tree, original `CLAUDE.md` and Git history were copied to local `backup-storage/2026-09-30-pre-release/`. After every document was checked against that copy, the live `_docs` directory was also moved into the archive; the original runtime sources remain unchanged. Retain the archive for provenance. Most `_docs` files describe retired iterations. The telemetry guide remains useful for developer diagnostics, the backlog mixes historical and open entries, and `94-MCA-2.2-INTEGRATION.md` explicitly describes an older contract.

Current detailed evidence remains in MCA's source README and `tests/mca/SMOKE.md`, the adapter's `tests/agot_mca/README.md`, the family source checkers, and the local dated finalization/control/localization reports. These records describe their exact observed builds. Publication descriptions and screenshots must follow the current behavior and coverage above.
