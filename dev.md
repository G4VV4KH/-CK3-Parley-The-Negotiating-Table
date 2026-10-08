# Contributing to Parley

Parley 1.3.0 is developed in `mod/parley/` for CK3 1.20.0.4. This working tree adds Negotiation interests and is not the published 1.2.2 snapshot. Candidate preparation uses `tools/release/prepare_parley_1_3_candidate.py`; the historical 1.2.2 publication guard must not be repinned or bypassed. The new projection contains 88 runtime files and 720 public localization keys per language, with developer diagnostics removed. All-language native localization and exact-candidate acceptance remain release gates; a version number, static pass or prepared candidate does not establish publication. Read actual delivery status from the current release registry. Historical records below retain their original dates and limits.

The player guide remains canonical in `publishing/description.en.md`; README and store variants are generated. Version 1.3.0 adds an explicitly highlighted Negotiation interests rule and a text-annotated authentic screenshot. Its original capture is preserved in `publishing/media-sources/`; the rejected AI-redrawn attempt is not publication media. The deterministic annotation helper verifies zero changed pixels outside the caption rectangle.

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

## Parley 1.2.1 development

2026-10-06: **Threat frequency** adds a per-aggressor global cooldown of 0
(default), 1, 5 or 10 years. **Threat strength** keeps the prior rule IDs and
coefficients under clearer labels. This change is independent of Classic/Scaled.
Run `python -B tests/parley/test_threat_frequency.py --source mod/parley` for
source-backed duration, actor/target, stale-deal, AI and cleanup regressions.
The runtime needs a new GAME candidate: the frozen 1.2.1 RC1 predates this rule.
Do not overwrite RC1 or infer engine validation from these model/source tests.

The new optional **Advanced term valuation — Classic / Scaled** is described in [the implementation and coverage record](docs/ADVANCED-VALUATION-1.2.1.md). Published 1.2.0 remains the current public release until a separately verified upload. Classic is the default and preserves earlier calculations, including absent-setting saves. Scaled needs fresh native gameplay and large-realm responsiveness evidence; source/model passes alone do not establish that.

Run the three additional source-backed suites with `--source mod/parley`: `test_scaled_valuation.py`, `test_scaled_people.py`, and `test_scaled_strategic.py` under `tests/parley/`. The normal developer runner includes them. They use strict explicit-fixture models and baseline AST/numeric comparisons, not an alternative game engine.

## Change conventions

Preserve `tnt_` identifier ownership, existing encoding and LF line endings. Keep all nine localization languages synchronized, including formatting and data tokens. Preserve the standalone Parley hooks and the MCA extension boundary. A new game rule must be reflected in the rule checker.

For a pull request, include the problem, resulting behavior, affected files, checks run and any untested case relevant to the change. Do not commit saves, game logs, credentials, local launcher paths or generated Workshop downloads.

The original `_docs`, `CLAUDE.md` and Git history were copied to the local `backup-storage/2026-09-30-pre-release/` archive before publication preparation. After checking every file against that copy, the live `_docs` directory was also moved into the archive. The original runtime sources remain in place. The archive preserves historical evidence; its old specifications are not current requirements. Current facts belong in `docs/CURRENT-CONTRACT.md` and the source checks.

## Release-chain journals

[The dev-to-game journal](docs/releases/HISTORY.md) records verified associations between a committed developer runtime and a frozen game build. Its JSON source is `docs/releases/history.json`. A newly recorded association identifies the matching commit checked at that time; it does not assert the original build commit or build date.

Use [the shared journal CLI](tools/release/README.md#release-chain-journals) to initialize and inspect the chain or append publication evidence. Each platform has a separate journal at the release workspace's `game/_history/<build>/<mod>/<platform>/history.json` and `HISTORY.md`, for Steam, Paradox, Nexus and GitHub. These records remain outside immutable `game/<build>` payloads and upload archives.

Runtime hashes determine whether dev still matches game. GitHub's published commit is tracked separately, so a documentation-only commit can require a GitHub push without invalidating the game build. `UPLOADED` and `VERIFIED` require a publication URL, artifact identity and evidence; recording an upload does not verify its downloaded result.

RC3 retains its CK3 1.19.0.6 / AGOT 0.5.2.1 evidence scope. Parley 1.1.0 has a reviewed CK3 1.20.0.2 source adaptation; its [compatibility record](docs/CK3-1.20-COMPATIBILITY.md) separates the scoped RC6/RC7 observations, RC7 rejection, RC8 native mutation and natural-offer passes, same-save vanilla control and remaining coverage gaps. AGOT 0.5.2.1 still belongs to the old baseline. The release workspace's `release-workflow.json` manages the publication hold.

## CAA family metadata revision

The current publication copy includes all seven other maintained mods, with Steam Workshop links. Update only the canonical My other mods block and project that block into the existing README and platform outputs; preserve the rest of each platform description. Parley and Vassalization Extended Steam exports use whitespace-only BBCode compaction to remain within the 8,000-byte UTF-8 CRLF form limit. Recheck the current shared publication contract and scoped release metadata guide before publishing. Runtime, version, archives, media, and prior localization evidence are unchanged.
