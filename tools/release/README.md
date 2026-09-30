# Reproducible CK3 game packages

`build_game.py` creates three game-only packages from the checked dev runtime.
`release-inputs.json` is an explicit file allowlist with pinned SHA-256 hashes;
it does not require the original health-finalization archive to remain at its
original location. Python 3.10 or later and its standard library are sufficient.

The builder never edits dev files, live mods, saves, playsets or Workshop files.
It refuses to overwrite an existing build. Reports and the manifest are siblings
of the three mod folders and are not part of any game payload.

Expected layout:

```text
ck3-mods-release/
  dev/<mod>/mod/<mod>/
  dev/parley/tools/release/build_game.py
  dev/parley/tools/release/release-inputs.json
  game/<build-id>/
    parley/
    marriage_calc_assistant/
    agot_marriage_calc_assistant/
    manifest.json
    transform-report.json
```

The current frozen package is `2026-09-30-game-rc3`. From
`dev/parley/tools/release/`, validate its pinned source inputs in memory and
independently read back the existing result:

```powershell
python .\build_game.py --build-id 2026-09-30-game-rc3 --check
python .\build_game.py --build-id 2026-09-30-game-rc3 --verify
```

To create a new candidate after a source change, review its pinned inputs and use
a new, unused build ID without `--check` or `--verify`. Do not overwrite RC3.

The canonical Parley dev location detects the family `dev/` and `game/` roots.
The preparation workspace's `tools/` location also detects its sibling roots.
When moving these tools to a different layout, use explicit family paths with
`--dev-root` and `--output-root`. `--lock` optionally points to the checked-in lock
file. The same arguments must be used for build and verification.

```powershell
python .\build_game.py --dev-root 'C:/path/to/ck3-mods-release/dev' --output-root 'C:/path/to/ck3-mods-release/game' --build-id 2026-09-30-game-rc3 --verify
```

## Exact public projection

MCA and AGOT:MCA runtime files remain byte-for-byte identical to the checked
source. README, development tools, tests, history and other documents are never
copied into any mod payload. Parley's runtime projection applies only the
following explicit, counted transformations:

- Omit `common/scripted_effects/tnt_3b_log.txt` (75 logging definitions).
- Remove `tnt_log_preflight_fail_effect` from `tnt_32_apply.txt` (one definition).
- Remove 72 external logging calls in six files. Six internal logger calls
  disappear with the omitted logger file. All 191 `error_log` emitters disappear.
- Remove the diagnostic telemetry rule and its seven localization keys in all
  nine languages.
- Remove exactly eleven diagnostic `exists = var:tnt_log_*` atoms and eleven
  matching `remove_variable = tnt_log_*` statements from the uninstall decision.
  All surrounding OR blocks and gameplay cleanup entries remain intact. This
  prevents the game package from referencing diagnostic variables whose setters
  were removed with the logger.
- Remove the test-rate option. Replace only eight active
  `has_game_rule = tnt_ai_offer_rate_test` predicates with `always = no`, retaining
  the surrounding `NOT`, `trigger_if`, conditions, cooldowns and effect bodies.
- Remove exactly the diagnostic intro's `triggered_desc` and its localization
  key, plus the test-rate option's two localization keys. No public intro branch
  is rewritten. This is explicitly reported, not silently left dangling.

For each of the four public rate settings, the old test-setting predicate was
false; `always = no` is also false. The frequent default and public option order
are unchanged. Debug saves containing the removed test preset are not a public
configuration whose accelerated cooldown behavior this build promises to retain.

Source comments, strings, UTF-8 BOMs, and untouched line endings are preserved.
An empty wrapper left by a removed log call is kept to preserve adjacent branch
relationships. No active diagnostic variable reference remains, including in the
uninstall decision. The dev source retains complete diagnostic state cleanup for
dev saves; the public game build is not a migration tool for torn debug sessions.

Input files: Parley 76, MCA 17, AGOT:MCA 12. Output files: 75, 17, 12. Localization
coverage: nine languages per mod; 623, 22, and 5 keys per language respectively.
Parley's 633 dev keys minus ten diagnostic keys give 623 public keys in RC3.

## Validation scope

Verification independently reconstructs the expected projection from pinned dev
inputs and compares every output byte and file inventory. It also checks active
tokens for diagnostic emitters/helpers/rules, script brace balance, all language
file/key inventories, default/public rate options, exact transformation counts,
and seven controls:

1. Reject an altered gameplay predicate in the output.
2. Reject an active diagnostic emitter leak.
3. Reject a diagnostic variable reader/cleanup leaking into uninstall after its
   setter has been removed.
4. Reject a source byte mismatch against the pinned release baseline.
5. Reject an extra localization key in one language.
6. Reject a documentation file leaked into the game payload.
7. Preserve comment/quoted-string lookalikes, BOM and CRLF unchanged.

`--check` and `--verify` write nothing. The controls run in memory and do not
corrupt files to demonstrate detection. Manifest validation also pins the builder
and input-lock bytes, so a changed builder needs a new build ID and manifest.

The older development gates deliberately remain development gates: some assert
telemetry call locations or logger definitions and cannot be applied unchanged to
the game projection. This validator does not weaken those assertions. The frozen
health-finalization snapshot remains immutable. Each new generated package needs
its own focused engine evidence before being called runtime verified; the earlier
gameplay matrix does not need to be replayed. The current
`2026-09-30-game-rc3` package matches the engine-tested staging payload for all
104 files. Its focused same-save auto-balance check reached +1 with one-way
currency payments and an unchanged repeat; see
[the RC3 audit and limits](../../docs/AUTOBALANCE-FIX.md).

The earlier `2026-09-30-game-rc2` package passed a focused combined smoke on
CK3 1.19.0.6 with AGOT 0.5.2.1, before the balancing defect was reported.
MCA and AGOT:MCA payloads are unchanged in RC3. Preserve
[the historical smoke result and log caveats](../../docs/RC2-SMOKE.md) within
that scope; it is not a whole-game clean-log claim.

## Generic distribution payloads

`package_game.py` reads a completed game build's manifest, checks the exact file
inventory, size and SHA-256 of all three payloads, and creates one ZIP per mod.
Each ZIP has `descriptor.mod` at its root alongside the game files. Reports,
development files and launcher `.mod` wrappers are excluded. The external
`archive-manifest.json` records the source build manifest hash, archive hashes,
versions and every archived member's hash and size.

```powershell
python .\package_game.py --build-dir 'C:/path/to/ck3-mods-release/game/2026-09-30-game-rc3' --output-dir 'C:/path/to/ck3-mods-release/distribution/2026-09-30-game-rc3' --verify
```

The frozen RC3 archives already exist in the release workspace. For a new build,
use its own build and distribution paths and omit `--verify` to create archives.

Creation refuses a nonempty output directory and uses exclusive file creation.
Every created archive is read back and checked for exact members, bytes, order,
timestamps, and permissions. `--verify` also checks the saved archive manifest and
writes nothing. ZIP members use fixed timestamps, lexicographic order, fixed
permissions and `ZIP_STORED` (no compression) for repeatable archive bytes without
depending on a compressor version.

These are generic payload archives. Steam receives the corresponding game folder.
Paradox's upload workflow and a Nexus manual-install package with an appropriate
launcher wrapper are separate deployment steps; no platform installation format
is implied by these ZIPs. Creating payload archives does not publish anything or
establish runtime behavior. RC3's focused engine result is recorded separately;
verification of platform delivery remains pending until upload and download.

## Release-chain journals

`release_journal.py` links committed developer runtime, immutable game builds and
separate platform publication records. It performs no upload or Git push. Run it
from this tools directory, supplying the release workspace that contains `dev/`,
`game/` and `distribution/`:

```powershell
$releaseWorkspace = 'C:/path/to/ck3-mods-release'
python ./release_journal.py init --workspace $releaseWorkspace --build-id 2026-09-30-game-rc3
python ./release_journal.py status --workspace $releaseWorkspace --build-id 2026-09-30-game-rc3
```

Initialization checks all manifest source/game inventories and hashes, committed
runtime state, and existing generic archive hashes. It creates each dev repo's
`docs/releases/history.json` and `HISTORY.md`, plus one journal per platform at
`game/_history/<build>/<mod>/<platform>/`. Platforms are `steam`, `paradox`,
`nexus` and `github`. The `_history` sibling is never part of a frozen
`game/<build>` payload or its upload archive. Repeating initialization preserves
events and does not reset publication status or duplicate an association.

A dev association states which matching commit was verified when the record was
created. It does not identify the original build commit or build time. Source
fingerprints determine runtime drift; current HEAD is compared separately with
GitHub's recorded published revision. A docs-only commit can therefore leave
runtime `MATCH` while GitHub reports `AHEAD_OR_DIFFERENT`.

Publication histories begin at `NOT_PUBLISHED`. Append `PREPARED`, `UPLOADED`,
`VERIFIED` or `FAILED` with `record --mod <slug> --platform <platform>` and the
same workspace/build arguments. `UPLOADED` and `VERIFIED` require `--url`,
`--evidence` (an existing file or evidence URL), and the artifact identity:

- For a game folder, `--artifact-sha256` is its manifest-based payload fingerprint.
- For a generic ZIP, use its verified archive SHA-256.
- For GitHub source publication, use `--revision` with the full local commit ID;
  this revision is independent of the game payload hash.

Use `--remote-id` for the assigned platform item ID and `--note` for useful
context. `VERIFIED` must cite separate remote/download verification evidence;
recording `UPLOADED` does not perform or imply that check. JSON is authoritative;
the readable Markdown is regenerated from its events. Never erase historical
events to represent a newer release; use its own build ID and append evidence.

RC3's evidence remains scoped to CK3 1.19.0.6 with AGOT 0.5.2.1. The newly
installed CK3 1.20 requires a separate compatibility review. Journal integrity
checks do not certify that upgrade; the workspace's `release-workflow.json`
manages the publication hold until the review is resolved.
