# Contributing to Parley

Parley 1.0.0 is developed in `mod/parley/`. Read [the current contract](docs/CURRENT-CONTRACT.md) before changing runtime behavior. Keep a pull request focused on one behavior, describe its visible effect, and include the relevant source checks and any observed game result.

## Repository and release copies

- `mod/parley/`: developer runtime source, including diagnostic instrumentation.
- `tools/family/`: source checks, models and shared MCA contract helpers.
- `tools/release/`: release projection and package checks.
- `docs/`: current implementation references.
- `publishing/`: store descriptions and publication material, when present.

The sibling MCA and AGOT:MCA repositories own their own runtime files and tests. Keep shared tools in this repository instead of maintaining three diverging copies. Keep the frozen helper, its JSON contract and its patch together: their adjacent paths are part of the check.

`dev`, `game` and `workshop` are distinct copies. Edit `dev`; generate `game` through the release tooling; compare the Steam-downloaded `workshop` copy with the uploaded package. Do not edit downloaded Workshop files as the source of a release.

The game projection removes developer documents and diagnostics, including telemetry and the test-only AI offer-rate option. Source checks intentionally continue to protect the instrumented developer source. A package has its own explicit inventory and allowed transformations; a smaller inventory must not weaken a source check. The projected package requires its own focused game smoke before publication. Earlier development smoke results do not certify that newly transformed package, and closed development tests need not be repeated in full.

The exact `2026-09-30-game-rc2` package passed that focused combined smoke on CK3 1.19.0.6 with AGOT 0.5.2.1. It covered a fresh English campaign, public Frequent rules, Parley's negotiation UI, an MCA tooltip and a natural incoming offer. No treaty was committed. [The smoke record](docs/RC2-SMOKE.md) describes the startup developer-rule warnings, three unattributed animation warnings and coverage limits; it does not claim whole-game clean logs or Workshop delivery.

## Running checks

Use Windows PowerShell 5.1 or PowerShell 7, with installed CK3 and AGOT paths. From this repository root, replace the two upstream paths below if needed:

```powershell
$parleySource = (Resolve-Path './mod/parley').Path
$mcaSource = (Resolve-Path '../marriage_calc_assistant/mod/marriage_calc_assistant').Path
$adapterSource = (Resolve-Path '../agot_marriage_calc_assistant/mod/agot_marriage_calc_assistant').Path
$vanillaSource = 'D:/SteamLibrary/steamapps/common/Crusader Kings III/game'
$agotSource = 'D:/SteamLibrary/steamapps/workshop/content/1158310/2962333032'
& ./tools/family/tnt_frozen_sync_check.ps1 -McaRoot $mcaSource -AdapterRoot $adapterSource -VanillaRoot $vanillaSource -AgotRoot $agotSource
& ./tools/family/tnt_family_gate.ps1 -CoreRoot $parleySource -McaRoot $mcaSource -AdapterRoot $adapterSource -VanillaRoot $vanillaSource -AgotRoot $agotSource
& ./tools/family/tnt_rule_conformance.ps1 -ModRoot $parleySource
& ./tools/family/tnt_ai_offer_rate_check.ps1 -ParleyRoot $parleySource
& ./tools/family/tnt_ai_dispatch_model.ps1 -ParleyRoot $parleySource
```

Inspect each result and exit code. Localization and tooltip edits also use `tnt_loc_token_check.ps1` and `tnt_bare_tooltip_row_check.ps1`, both with explicit `-ModRoot` and `-VanillaRoot`. `tnt_balance_model.ps1` is a standalone pricing model with its own assumptions; it takes no source-root argument and does not read the current game scripts.

For currency balancing, run the source-executing regression with Python:

```powershell
python tests/parley/test_autobalance.py --source mod/parley
```

See [the auto-balance audit](docs/AUTOBALANCE-FIX.md) for the reported failure, AI impact, coverage and runtime verification status. The harness approximates CK3 execution and does not replace a focused game check.

Do not rely on the relocated tools' original root defaults. Most still derive a root two directories above the script. `tnt_citation_check.ps1` additionally needs an explicit `-Doc` for the document being checked. `tnt_incode_citation_check.ps1` expects the three mod folders under one parent; use a verified combined source staging tree for a complete family citation scan. A run against only this repository is not a full three-mod citation check.

The checks are source contracts and bounded models, not a CK3 parser or proof of engine behavior. When a change needs runtime evidence, record the exact package, playset, save, date, UI scale and observed result; inspect logs after the game closes. Do not replace a pinned vanilla/AGOT baseline with whatever is installed merely to make a failed check pass.

## Change conventions

Preserve `tnt_` identifier ownership, existing encoding and LF line endings. Keep all nine localization languages synchronized, including formatting and data tokens. Preserve the standalone Parley hooks and the MCA extension boundary. A new game rule must be reflected in the rule checker.

For a pull request, include the problem, resulting behavior, affected files, checks run and any untested case relevant to the change. Do not commit saves, game logs, credentials, local launcher paths or generated Workshop downloads.

The original `_docs`, `CLAUDE.md` and Git history were copied to the local `backup-storage/2026-09-30-pre-release/` archive before publication preparation. After checking every file against that copy, the live `_docs` directory was also moved into the archive. The original runtime sources remain in place. The archive preserves historical evidence; its old specifications are not current requirements. Current facts belong in `docs/CURRENT-CONTRACT.md` and the source checks.
