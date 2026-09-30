# Current development and release contract

Recorded 2026-09-30 for Parley 1.0.0, MCA 3.0.1 and AGOT:MCA 2.2.0. This is the concise current reference for publication preparation. Runtime source and its explicit checks resolve implementation details; historical `_docs` specifications must not override this record.

## Three copies

| Copy | Purpose | Editing and verification |
| --- | --- | --- |
| `dev` | Runtime source, tests, developer references and publication material | Author changes here and commit reviewed work to the appropriate Git repository. |
| `game` | Clean platform upload payload | Generate from a fixed developer revision through the release tool; verify exact inventory, transformations and hashes. |
| `workshop` | Steam-downloaded copy of the uploaded mod | Treat as delivery output; compare to the uploaded package and do not develop in it. |

Runtime source resides under `dev/<repository>/mod/<folder>/`. The folders are `parley`, `marriage_calc_assistant` and `agot_marriage_calc_assistant`. The same clean game content is intended for Steam, Paradox and Nexus; platform-specific packaging and metadata are recorded separately.

Publication preparation deliberately creates a different Parley game projection: developer documents, telemetry and the test-only AI offer-rate option are excluded by the release tool in `tools/release/`. Instrumented developer logic remains in `dev`. Package verification must prove the allowed differences explicitly, not silently refresh or relax the source checks. The projected package's focused engine smoke is pending; no publication or Workshop-delivery verification is implied by source readiness.

## Parley behavior and ownership

Parley provides a two-sided negotiation window, partner-oriented valuation and auto-balancing, incoming AI letters and an AI-to-AI negotiation layer. It owns its `tnt_` runtime namespace and five legacy addon hooks. MCA does not define or call those hooks. Parley does not override a vanilla file path in the checked source tree; this is a measured compatibility surface, not a guarantee for every mod combination.

The current threat access minimum is 100 points inclusive in player and AI paths. The multiplier ladder remains 2.5 / 5 / 7.5 / 10, with normal at 5. Selected threats below the minimum contribute zero, cannot seed Equalize, and can be unticked. The rule-conformance check protects the current consumers.

The hidden AI-letter composer has no engine cooldown. PICK writes no provisional recipient cooldown. Only visible letters write the recipient rate variable: frequent six months, normal one year, rare three years. The developer test rate skips it. The hidden composer rechecks off/rate/open/partner/refused-envoys/live-proposer conditions. A valid draft remains owned by `tnt_partner` until its visible letter is answered; aborts clear it so another proposer may try. The correction added no queue or saved variable. The developer source checks and dispatcher model protect this structure; the release projection must preserve the non-test behavior.

## MCA behavior and boundary

MCA scores candidate gameplay potential, not marriage acceptance or guaranteed benefit from a particular pairing. Both picker sides share inheritable-quality, skill, age-based reproductive, dynastic-prestige and explicit-claim components. Native potential-alliance metadata and optional adapter components are included through the existing wrappers. The score and its native breakdown use the same component values.

Optional sorting keeps a saveable snapshot on the local player and projects native list items. It does not stamp candidates or change who a displayed row selects. Lifecycle/context guards clear the snapshot; close the picker before saving or uninstalling. MCA adds no global cleanup sweep or on-action.

Its sole vanilla-path override is `gui/interaction_marriage.gui`. A mod replacing that file requires a reviewed functional compatibility patch. The derived marriage row depends on the base row's `character_relation` seam. The frozen patch and inherited-row checks guard these boundaries against the installed vanilla and AGOT versions.

Eight public adapter component defaults use formula blocks `{ value = 0 }`; scalar zeros caused the tested missing-adapter-value regression. Public names and core aggregate ownership remain stable. Adapters must be pure, deterministic contributions and supply matching localized descriptions.

The developer source inventory is 18 files including its existing README. The documentation-free game inventory is 17 files. Preserve both contracts explicitly and keep historical release manifests unchanged.

## AGOT:MCA behavior and boundary

AGOT:MCA owns six pure overrides: P c1, R c1–c4, and alliance base 40. P c1 aliases R c1. Passing AGOT's `is_current_dragonrider` predicate contributes +30 on each picker side; R c2–c4 remain zero compatibility slots. The weight describes current-dragonrider potential and does not promise dragon transfer or control.

The adapter owns twelve payload files and five localization keys in each of nine languages. It adds no GUI, interaction, effect, decision or on-action files. Its checks pin the relevant upstream predicate bodies and require the current MCA formula-zero defaults. MCA owns the aggregate scores, row and sorting state.

## Localization and compatibility evidence

The audited developer trees each contain English, French, German, Japanese, Korean, Polish, Russian, Simplified Chinese and Spanish. Developer key counts are Parley 632, MCA 22 and AGOT:MCA 5 per language. Release removal of diagnostic/test-only entries may change Parley's game key count; the generated package must still have matching key/token coverage across all nine languages.

The checked environment is CK3 1.19.0.6 and AGOT 0.5.2.1. Source checks establish Parley's zero vanilla-path collisions, MCA's one reviewed GUI override, and the adapter's pure script-value boundary. Compatibility descriptions must also state dependencies and required ordering. They must not infer universal compatibility, multiplayer coverage or normal-rate balance from these checks.

## Existing evidence and pending release evidence

Development finalization recorded scoped source checks, independent models and targeted runtime observations. The dispatcher correction received a completed vanilla test; the combined AGOT smoke delivered Jeyne Arryn's ordinary 165-gold offer after three empty drafts. The formula-zero correction restored the observed rider contribution to 95 = 35 dynasty + 30 inheritable qualities + 30 rider potential on P and the native pinned R row. A later 125% UI acceptance was user-reported, with closed-log inspection; it was not an independent visual observation by the assistant.

These results have bounded coverage. They do not establish every unpinned R rider case, multiplayer behavior, all snapshot/save scenarios, normal-rate balance or whole-game clean logs. The control and localization audits refer to the frozen developer trees. Do not re-run closed development scenarios merely for publication bookkeeping.

The new game projection needs inventory/hash checks, validation of the permitted telemetry/test-rate removal, and a short focused engine smoke of that exact package. Workshop download comparison comes after an actual upload. Until those steps are recorded, the game projection is a publication candidate rather than a verified delivered release.

## Documentation and source evidence

The original Parley `_docs` tree, original `CLAUDE.md` and Git history were copied to local `backup-storage/2026-09-30-pre-release/`; original sources were left untouched. Retain the archive for provenance. Most `_docs` files describe retired iterations. The telemetry guide remains useful for developer diagnostics, the backlog mixes historical and open entries, and `94-MCA-2.2-INTEGRATION.md` explicitly describes an older contract.

Current detailed evidence remains in MCA's source README and `tests/mca/SMOKE.md`, the adapter's `tests/agot_mca/README.md`, the family source checkers, and the local dated finalization/control/localization reports. These records describe their exact observed builds. Publication descriptions and screenshots must follow the current behavior and coverage above.
