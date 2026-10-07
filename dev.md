# Contributing to Parley

Parley 1.2.2 is prepared in `mod/parley/` for CK3 1.20.0.4. This candidate corrects 13 translations across four languages; gameplay logic is unchanged from published 1.2.1. Its complete localization gate and external publication remain pending. See [the candidate record](docs/LOCALIZATION-1.2.2.md).

Historical 1.2.1 evidence: The new optional Scaled valuation and global threat cooldown are in GAME candidate `2026-10-06-parley-1.2.1-rc5`, which passed the scoped native acceptance below. Platform availability and delivered-byte verification are separate release-chain steps. The [currency-rule record](docs/CURRENCY-RULES-1.2.md) retains the earlier directional faith/fame/devotion test evidence and its diagnostic caveats. Read [the current contract](docs/CURRENT-CONTRACT.md) and [the 1.20 compatibility decisions](docs/CK3-1.20-COMPATIBILITY.md) before changing runtime behavior. Keep a pull request focused on one behavior, describe its visible effect, and distinguish passing source checks from observed game results.

**Historical publication addendum, 2026-10-04 (Parley 1.2.0 only):** the frozen `2026-10-04-parley-1.2.0-rc1` GAME candidate passed its focused standalone CK3 1.20.0.3 smoke with retained log notes; see the [acceptance addendum](docs/CURRENCY-RULES-1.2.md#game-acceptance-addendum-2026-10-04). This historical acceptance does not certify RC5 or Steam, Paradox or Nexus delivery. The AGOT support hold remains unchanged. No runtime or frozen-package bytes were changed by this publication-only documentation update.

## Repository and release copies

- `mod/parley/`: developer runtime source, including diagnostic instrumentation.
- `tools/family/`: source checks, models and shared MCA contract helpers.
- `tools/release/`: release projection and package checks.
- `docs/`: current implementation references.
- `publishing/`: store descriptions and publication material, when present.

Parley's AGOT-specific checks and their calls are commented out for the RC10 candidate while an AGOT update for CK3 1.20 is pending. Do not reactivate AGOT-specific checks without reviewing the updated upstream definitions and recording fresh focused verification. Historical AGOT files, screenshots and test reports are evidence for their original versions, not current support.

The sibling MCA and AGOT:MCA repositories own their own runtime files and tests. Keep shared tools in this repository instead of maintaining three diverging copies. Keep the frozen helper, its JSON contract and its patch together: their adjacent paths are part of the check.

`dev`, `game` and `workshop` are distinct copies. Edit `dev`; generate `game` through the release tooling; compare the Steam-downloaded `workshop` copy with the uploaded package. Do not edit downloaded Workshop files as the source of a release.

The game projection removes developer documents and diagnostics, including telemetry and the test-only AI offer-rate option. Source checks intentionally continue to protect the instrumented developer source. A package has its own explicit inventory and allowed transformations; a smaller inventory must not weaken a source check. The projected package requires its own focused game smoke before publication. Earlier development smoke results do not certify that newly transformed package, and closed development tests need not be repeated in full.

The historical 1.19 release baseline is `2026-09-30-game-rc3`. Its controlled same-save auto-balance check reached +1 with one-way currency payments and an unchanged repeat. All 104 RC3 payload files match that engine-tested staging build; MCA and AGOT:MCA are unchanged from RC2. See [the focused RC3 audit](docs/AUTOBALANCE-FIX.md) for scope and log caveats. The 1.20 adaptation uses a separate vanilla Parley/MCA playset. RC6 passed focused UI and 34 harness assertions; RC7 passed the MCA picker sequence but was rejected for an AI-world vassalization scope failure. RC8 supplies the native alias and separately passed 12 native mutation assertions plus a no-harness short campaign with an executed natural fealty offer. Seven native log records reproduced with all mods off on the same original save. These are bounded results, not a global clean-log or long-campaign claim.

Parley transactions remain owned by the direct actor. The negotiation opener and borrowed marriage picker are hidden when the effective arranger is a different puppet ruler. Redirection to a courtier's matchmaker must update both actor aliases while preserving ownership of candidate pools and the staged deal. Version 1.1 follows character Rites for marriage defaults and lineality pricing, with native eligibility helpers retained.

The earlier `2026-09-30-game-rc2` package passed a focused combined smoke on CK3 1.19.0.6 with AGOT 0.5.2.1. It covered a fresh English campaign, public Frequent rules, Parley's negotiation UI, an MCA tooltip and a natural incoming offer, but did not exercise the later-reported balancing failure. No treaty was committed. [The historical smoke record](docs/RC2-SMOKE.md) describes the startup developer-rule warnings, three unattributed animation warnings and coverage limits; it does not claim whole-game clean logs or Workshop delivery.

## Running checks

Use Windows PowerShell 5.1 or PowerShell 7, with installed CK3 and AGOT paths. From this repository root, replace the two upstream paths below if needed:

```powershell
$parleySource = (Resolve-Path './mod/parley').Path
$mcaSource = (Resolve-Path '../marriage_calc_assistant/mod/marriage_calc_assistant').Path
$adapterSource = (Resolve-Path '../agot_marriage_calc_assistant/mod/agot_marriage_calc_assistant').Path
$vanillaSource = './game'
$agotSource = './agot'
& ./tools/family/tnt_frozen_sync_check.ps1 -McaRoot $mcaSource -AdapterRoot $adapterSource -VanillaRoot $vanillaSource -AgotRoot $agotSource
& ./tools/family/tnt_family_gate.ps1 -CoreRoot $parleySource -McaRoot $mcaSource -AdapterRoot $adapterSource -VanillaRoot $vanillaSource -AgotRoot $agotSource
& ./tools/family/tnt_rule_conformance.ps1 -ModRoot $parleySource
& ./tools/family/tnt_ai_offer_rate_check.ps1 -ParleyRoot $parleySource
& ./tools/family/tnt_ai_dispatch_model.ps1 -ParleyRoot $parleySource
```

Inspect each result and exit code. Localization and tooltip edits also use `tnt_loc_token_check.ps1` and `tnt_bare_tooltip_row_check.ps1`, both with explicit `-ModRoot` and `-VanillaRoot`. `tnt_balance_model.ps1` is a standalone pricing model with its own assumptions; it takes no source-root argument and does not read the current game scripts.

For currency balancing and AI-world native scope bindings, run the focused source regressions with Python:

```powershell
python tests/parley/test_autobalance.py --source mod/parley
python -B tests/parley/test_currency_trade_rules.py --source mod/parley
python -B tests/parley/test_ai_world_native_scopes.py --source mod/parley --game './game'
```

See [the auto-balance audit](docs/AUTOBALANCE-FIX.md) for the reported failure, AI impact, coverage and runtime verification status. The harness approximates CK3 execution and does not replace a focused game check.

Do not rely on the relocated tools' original root defaults. Most still derive a root two directories above the script. `tnt_citation_check.ps1` additionally needs an explicit `-Doc` for the document being checked. `tnt_incode_citation_check.ps1` expects the three mod folders under one parent; use a verified combined source staging tree for a complete family citation scan. A run against only this repository is not a full three-mod citation check.

The checks are source contracts and bounded models, not a CK3 parser or proof of engine behavior. When a change needs runtime evidence, record the exact package, playset, save, date, UI scale and observed result; inspect logs after the game closes. Do not replace a pinned vanilla/AGOT baseline with whatever is installed merely to make a failed check pass.

Publication copy has one editable English source: `publishing/description.en.md`. The shared release-workspace wrapper renders **only Parley** with `--mod parley`; do not call the original family-wide renderer CLI for a scoped edit. The full game-rules guide lives in that canonical source. Steam and Paradox get the marked short summary and a link to the README guide; GitHub, Nexus and the preview get the full guide. Steam is validated against 8,000 UTF-8 bytes before outputs are written, and Paradox against its 10,000-character limit. Run `python -B -m unittest discover -s tests/publishing -v` for the renderer and `python -B -m unittest discover -s tests/release -v` for the numbered deployment-kit checks. Follow the existing release journal procedure after committing reviewed inputs; no tool in this preparation flow uploads a release.

The `parley-rules-media-2026-10-06` metadata revision replaces only the selected game-rules screenshot and its provenance/caption. Resolve its current canonical working projection through the release registry before synchronizing future edits; older publication projections remain historical. The repository retains the user-supplied PNG at `publishing/screenshots/04-game-rules.png`; store galleries use a same-resolution JPEG derivative. The two negotiation screenshots retain their historical CK3 1.19.0.6 provenance. The replacement shows Scaled valuation and a five-year threat cooldown as selected examples, not defaults, and does not establish an exact capture-game patch. Runtime, mod version, current CK3 target and downloadable archive bytes are unchanged by this media revision.

## Parley 1.2.1 development

2026-10-06: **Threat frequency** adds a per-aggressor global cooldown of 0
(default), 1, 5 or 10 years. **Threat strength** keeps the prior rule IDs and
coefficients under clearer labels. This change is independent of Classic/Scaled.
Run `python -B tests/parley/test_threat_frequency.py --source mod/parley` for
source-backed duration, actor/target, stale-deal, AI and cleanup regressions.
The frozen 1.2.1 RC1 predates this rule; the release candidate is RC5.
Do not overwrite earlier candidates or infer engine validation from model/source tests.

The new optional **Advanced term valuation — Classic / Scaled** is described in [the implementation and coverage record](docs/ADVANCED-VALUATION-1.2.1.md). Classic is the default and preserves earlier calculations, including absent-setting saves. The scoped native results below supplement source/model checks; large-realm responsiveness and long-campaign behavior remain outside this acceptance.

Run the three additional source-backed suites with `--source mod/parley`: `test_scaled_valuation.py`, `test_scaled_people.py`, and `test_scaled_strategic.py` under `tests/parley/`. The normal developer runner includes them. They use strict explicit-fixture models and baseline AST/numeric comparisons, not an alternative game engine.

### Scoped native acceptance — 2026-10-06

RC5 was checked in standalone CK3 1.20.0.3, with the final UI session using only the frozen release mod. Read-only opening, hovering and clearing did not consume or refresh the global threat cooldown. Six natural game days changed the saved timer from 365 to 359 days; saving and reloading preserved 359 days and the same 1 October 1179 expiry. The row, toggle tooltip and negotiation opener exposed the countdown. The zero-cooldown Russian rule label is `нету`. In a Classic fixture, Musa's fealty cost was 135 and threat-free auto-balance reached +1; this was a preview, not a committed treaty.

Ten isolated native harness suites produced 101 passing assertions across the 0/1/5/10-year duration primitive, AI-world cash and submission effects, and paid/refused/stale incoming-demand effects. They exercise real production effect bodies and guards, not random AI-pulse frequency or spontaneous letter/option-button dispatch. One original primitive verifier was corrected in a separate receipt. An earlier incoming fixture had no eligible proposer and failed; that raw failure remains preserved. Four later successful incoming runs are accepted only within their byte-pinned run windows, not as a clean whole-session result.

Earlier RC2 manual settlements covered scaled vassals, courtiers, a hostage, fealty, independence, a title transfer and a hook; RC2-to-RC5 gameplay script bytes are unchanged. RC4 UI observations covered the displayed gift-floor adjustment, landless courtier labels and rounding; RC5 changes only two cooldown localization strings per language from RC4. These prior observations retain their own candidate scope.

The final no-harness session exited normally. Its logs retain persistent-reader key diagnostics, two human-only interaction AI-frequency warnings, and wrong-scope records at the game's adoption-interaction path. File location alone does not establish causality, and the complete session is not claimed error-free. No new cooldown or custom-localization error was found. Full-year natural expiry, full 5/10-year persistence, multiplayer, spontaneous demand dispatch and long campaigns are not certified by this focused acceptance. Private receipts, original failed runs, saves and raw logs remain in the release evidence store; they are not shipped in this public repository.

## Change conventions

Preserve `tnt_` identifier ownership, existing encoding and LF line endings. Keep all nine localization languages synchronized, including formatting and data tokens. Preserve the standalone Parley hooks and the MCA extension boundary. A new game rule must be reflected in the rule checker.

For a pull request, include the problem, resulting behavior, affected files, checks run and any untested case relevant to the change. Do not commit saves, game logs, credentials, local launcher paths or generated Workshop downloads.

The original `_docs`, `CLAUDE.md` and Git history were copied to the local `backup-storage/2026-09-30-pre-release/` archive before publication preparation. After checking every file against that copy, the live `_docs` directory was also moved into the archive. The original runtime sources remain in place. The archive preserves historical evidence; its old specifications are not current requirements. Current facts belong in `docs/CURRENT-CONTRACT.md` and the source checks.

## Release-chain journals

[The dev-to-game journal](docs/releases/HISTORY.md) records verified associations between a committed developer runtime and a frozen game build. Its JSON source is `docs/releases/history.json`. A newly recorded association identifies the matching commit checked at that time; it does not assert the original build commit or build date.

Use [the shared journal CLI](tools/release/README.md#release-chain-journals) to initialize and inspect the chain or append publication evidence. Each platform has a separate journal at the release workspace's `game/_history/<build>/<mod>/<platform>/history.json` and `HISTORY.md`, for Steam, Paradox, Nexus and GitHub. These records remain outside immutable `game/<build>` payloads and upload archives.

Runtime hashes determine whether dev still matches game. GitHub's published commit is tracked separately, so a documentation-only commit can require a GitHub push without invalidating the game build. `UPLOADED` and `VERIFIED` require a publication URL, artifact identity and evidence; recording an upload does not verify its downloaded result.

RC3 retains its CK3 1.19.0.6 / AGOT 0.5.2.1 evidence scope. Parley 1.1.0 has a reviewed CK3 1.20.0.2 source adaptation; its [compatibility record](docs/CK3-1.20-COMPATIBILITY.md) separates the scoped RC6/RC7 observations, RC7 rejection, RC8 native mutation and natural-offer passes, same-save vanilla control and remaining coverage gaps. AGOT 0.5.2.1 still belongs to the old baseline. The release workspace's `release-workflow.json` manages the publication hold.
