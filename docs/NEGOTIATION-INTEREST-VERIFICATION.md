# Parley negotiation interests verification

8 October 2026. This developer record distinguishes inherited gameplay evidence,
native GUI-state checks, user-confirmed visual review and the separate Parley
1.3.0 release gates. It is not a whole-candidate native PASS or publication receipt.

The user confirmed the outstanding physical-hover check with:
**“я уже проверил - всё в порядке”** (“I already checked — everything is fine”). The visual/physical
hover status for the UI under discussion is therefore `USER_CONFIRMED`. No new
visible session was launched. This does not turn the failed automated component
observer into a PASS or establish an automated pixel/row-arithmetic proof.

## Candidate identity and evidence inheritance

The frozen candidate is `2026-10-08-parley-1.3.0-rc1`, targeting CK3 1.20.0.4.
Its candidate-manifest SHA256 is
`5f497d6c591b8fc5f5fba3032020a54154b7e7fa40110cccdd88ac5853722061`.
The active 89-file DEV runtime and frozen 88-file GAME payload both match their
respective candidate inventories. GAME excludes developer diagnostics; it is not
byte-identical to DEV and needs its own native acceptance.

The latest badge/hover snapshots and candidate DEV differ in exactly ten files:
`descriptor.mod` changes only `1.2.2` to `1.3.0`, and each of the nine locale files
changes only `tnt_item_title_desc`. All other 79 files, including the complete GUI,
bindings and gameplay scripts, are byte-identical. The title wording now avoids
promising full valuation under enabled interests. Its translations are part of
the separately reviewed localization gate, not inherited native text evidence.

Current DEV relative-path-to-SHA256 inventory fingerprint:
`ca0f46d695d0f99454d57c9507cc1a6a5bc0e5f34ff15e4969511d28b7eb8c21`
(sorted UTF-8 JSON, compact comma/colon separators).

The private audit `publication130/interest-qa-lineage-r1.json`, SHA256
`c82e4848423aeb2876db4ba89daaf8ca6aae98d5c776aeeb26ff4e09b80a2c06`,
rechecks ten reports' manifest/log/runtime bindings and eight complete merged
snapshots. It predates the user's final visual confirmation; the separate
`publication130/interest-visual-user-confirmation-r1.json` records that addendum.
These private records, saves and logs are not bundled in the public repository.
The user's reported check is associated with the unchanged candidate UI; the
user's running process was not independently fingerprinted for that confirmation.

The all-nine-language, candidate-bound GAME localization/native gate is still
**pending at this documentation revision**. Neither scoped inheritance nor the
user's visual confirmation closes that mandatory publication gate.

## Historical tooltip crash and repair

The user crash at 15:18:40 +0200 records `C00000FD EXCEPTION_STACK_OVERFLOW`
and the engine error that a flowcontainer cannot have a direct hbox/vbox child
at `gui/tnt_types.gui:159`. All eight original crash files were archived and
SHA-verified. Nothing was uploaded; the original Crash Reporter was not controlled.

Ordinary production-window opening survived, but independently instantiating the
exact empty gold-interest tooltip reproduced the same exception class and exact
layout diagnostic. Two children, `tnt_interest_points` and
`tnt_interest_capacity`, were illegal direct vboxes. The A/B candidate changes
only those two nodes to vertical flowcontainers and passes 9/9 native assertions.
Its 60 startup diagnostics were reviewed separately against the bound historical
controls; none is a GUI or crash exception.

At that stage the repaired authoring file was byte-identical to the A/B candidate.
The actual-source run, `interest-window-final-source-002`, passed 17/17 assertions:
real production opening and window survival; exact production receive/surrender
tooltip instances, empty and selected; production add/clear GUI commands. No
wallet or pricing mocks are used. There are no crash files, GUI errors, failed
assertions or unreviewed diagnostics. Only the two unchanged player-only
interaction discovery messages remain. An earlier final run had four test-only
unused-variable diagnostics and remains failed; the test now independently
checks its host-show witnesses in native script and was rerun in a fresh profile.

- Crash repair evidence record `negotiation-open-crash-2026-10-08-001/final-result.json` (local-only evidence, not bundled).
- Final native report `interest-window-final-source-002/native-report-reviewed.json` (local-only evidence, not bundled), SHA256 `ed57ec1a1dffe0565659a75ddf5c32886b90393faae632d480bb596367f3608d`.
- Historical 88-file runtime fingerprint: `35e7e3ae533088f2e7ac0cc3bd2a645b29fca19b3860e65f0e187852d758ac6c`.
- The sole repair-stage runtime change was `gui/tnt_types.gui`, from `bd78030ec497624766797e66ac19f65e7295a2363e564d40e492cd967d525b19` to `c8dac88105242a18d3a439e9763caf07705d885b529db0d01775a53519133ac8`. Later preview/exclusivity/badge changes supersede this full-source fingerprint.

This proves the shared tooltip construction regression and its repair, not an
identical unsymbolized instruction address or exact user-save replay. The isolated
host can construct its children before becoming visible. Computer-use discovery
did not expose the hidden CK3 window, so this historical run did not certify actual
pointer hover, popup placement or clipping. Unselected terms now show contextual
previews; the earlier empty-dash description no longer describes the current UI.

## Currency exclusivity and current-context previews

The later native cycles `interest-ui-refresh-standard-002` and
`interest-ui-refresh-off-001` each passed **206/206** assertions on CK3 1.20.0.4.
Their aggregate `interest-ui-refresh-2026-10-08-result.json` has SHA256
`d7069b52de3a89381be8cd7fe730c2892387f171a3778b335363b49751405845`.
The candidate retains their exact 68 common/events files, inventory SHA256
`2962d8ee6d6fa83eeed90fe220c5b2e45f81d170234ed49870587f97e0bc46e4`.

- Gold, prestige and piety were exercised in both directions: add and presets,
  blocked opposite positive writers, subtraction to zero, individual/global clear,
  immediate amount/trigger checks and next-phase native GUI validity.
- Malformed legacy 10/20 drafts fail preflight and disable Send. The actual master
  performs no transfer; exact net repair yields 0/10. Actual Auto-balance restores
  exclusivity and affordability, reports an honest result and leaves wallets alone.
- Off independently verifies this legality protection without the enabled-interest
  economic rejection gate. Influence exclusivity was deliberately not added.
- Currency previews are checked against independent native-input arithmetic.
  Advanced/contract previews have routing/bounds checks, not an independent full
  motive oracle for an unselected object.

Each final cycle has four narrowly reviewed startup diagnostics: two unchanged
discovery records and two static-loader warnings for test-only GUI-supplied bool
scopes, whose producer/consumer and both boolean polarities were verified. The
initial Standard001 failure remains preserved; stale same-frame GUI observations
and an incorrect signed-shortfall equality assertion were repaired in a new
harness/run rather than waived. Later GUI changes prevent inheriting these runs'
old appearance or claiming a new whole-feature settlement regression.

## Final badge state and hover-content evidence

The current GUI uses one persistent text widget in each fixed 52x23 badge. Clear
and selected terms share its position; their previews and chosen-term models remain
distinct. Both tooltip states include the precise effective total, while concrete
base/adjusted point prices remain selected-only. Native state checks do not by
themselves prove the rendered position or component content.

Earlier EN/RU badge-layout runs passed 17/17 each, but three GUI files subsequently
changed. The latest evidence is:

| Run | Result | Actual scope |
| --- | --- | --- |
| `interest-stable-badge-en-001` | 17/17; two localization witnesses | Production opening, tooltip construction, add/clear state cycle; 60 exact reviewed startup records |
| `interest-hover-content-ru-002` | 23/23 state markers; component observer **FAIL** | Correct window/participant/draft states; two exact reviewed startup records; rendered components not verified by automation |

The latest English report SHA256 is
`f18772e91049f5b62881a13fb8bba5ea35e90a511262198b74fac9e35bc44e60`;
the Russian observer report SHA256 is
`3fb94fb5cb4196beb0639542fd77fce7373f8a20a43708ca7a844ce1c95f07d5`.

Both observer attempts remain failed immutable evidence. At all six gold
receive/surrender clear-selected-clear checkpoints, the callback captured empty
or mismatched `ValueBreakdown` providers despite correct widget identities. The
second attempt separated pure GUI capture from script consumption and still
failed. No production component defect or correctness follows from that result.
The installed widget API exposed no rendered-text getter to resolve this ambiguity.

The user's subsequent explicit confirmation closes the targeted visual/physical
hover check as **`USER_CONFIRMED`**, not `AUTOMATED_PASS`. No additional screenshot
sequence, pixel measurements, per-row arithmetic proof or independent process
identity was produced with that reply. The automated observer remains
`NOT_VERIFIED` for actual rendered components; its original report status is FAIL.

## Historical calculation matrix and source

Authoring runtime:
`mod/parley`.
Resolved through the existing release-workflow registry; it is distinct from the
published source projection. Unrelated dirty authoring changes were preserved.

All four accepted historical runs contain exactly the same 88 production files
from before the tooltip repair. All 22 script-value files and the AI-world effect
remain unchanged in candidate DEV, supporting bounded calculation/pressure and
synchronous AI-helper inheritance. Later exclusivity changes touched the shared
solver and preflight: the older positive master settlement and save/load results
remain historical, not fresh acceptance of those changed paths or the complete
candidate. Only their isolated merged
test layer changes the rule preset and adds fixtures. No normal CK3 saves, playsets or settings were
changed. The root agent launched each test hidden and stopped its exact recorded
PID only after checking executable, start-time ticks and isolated user directory.

The immutable native matrix `interest-native-matrix-2026-10-08-001.json` (local-only evidence, not bundled)
records `PASS_WITH_SCOPED_DIAGNOSTICS_REVIEW`, 352 passing native assertions and
zero unreviewed diagnostics. Each assertion belongs to its recorded preset;
352 is not a count of distinct scenarios across the four runs.

| Preset | Stopped run | Native assertions | Reviewed diagnostic records |
| --- | --- | ---: | ---: |
| Standard | interest-standard-final-003 | 97 / 97 | 118 |
| Off | interest-off-final-001 | 85 / 85 | 64 |
| Mild | interest-mild-final-001 | 85 / 85 | 60 |
| Strict | interest-strict-final-001 | 85 / 85 | 60 |

Run records are retained in the maintainer's external test-evidence store; they are not bundled in this repository.
Each has `native-report-reviewed-final-001.json`, a frozen full-file manifest,
native save, logs, process record and exact diagnostic-review bindings. The
matrix re-inspects those reports and preserves their hashes.

- Matrix SHA256: `fe17743114cde8fe0980a6eb9dd29d9f2ae3b7005eacba151fa4165ee560aa82`.
- Historical runtime fingerprint: `629ce3647b242cb77967a1fdae572f5635b0e480c4c817a1b5e753eb00bb5a3c`.
  Format: SHA256 of the UTF-8 JSON sorted relative-path to SHA256 map, compact
  comma/colon separators. Any production-file change invalidates current parity.

## What the historical matrix exercised

- Four currencies, both directions: useful-demand saturation, protected reserves,
  stock refresh, net scoring with gross affordability, and high-value fixed-point
  cases. Positive relations do not restore value to fully unwanted surplus.
- Nine ordinary advanced families and nine signed obligation families. Applicable
  rights have nonzero fixtures; illegal or unavailable rights remain gated.
- Unchanged threat and called-in-hook pressure, explicit Off parity, and the
  authoritative interest penalty in the central acceptance ledger.
- Actual Auto-balance callbacks with unchanged wallets during quotation, followed
  by actual save and disk-load callbacks, rather than an in-memory reload imitation.
- Actual manual master settlement, currency conservation, stale-economic refusal
  and stale-affordability refusal before mutation.
- Actual synchronous AI-world settlement helpers using AI characters, including
  both-side interest checks, conservation and stale-state refusal. This does not
  establish autonomous candidate selection or the scheduler's campaign behavior.

The rich fixtures include 36 selected objects. Ten quotes and Auto-balance each
fit within one timestamp second in the accepted logs. This is coarse evidence,
not a frame-time measurement or proof of large-campaign responsiveness.

## Save and load diagnosis

Standard final runs 001 and 002 failed unconditional equality of the pre-load and
post-load quote: -24 became -23. Their failures remain preserved. The production
code was not changed to cache the old number or hide the difference.

Diagnostic run 003 captured the cause: native monthly expenses changed from
41.70 to 44.27 in the two-decimal dump. The useful gold target consequently rose
from 7069.30 to 7100.21, and adjusted gold points from 468.97 to 470.00. Other
captured draft, stock, strategy and non-gold term inputs remained unchanged.

Independent formulas rebuilt capacity from raw native inputs, gold utility and
the complete score before and after load. All matched the live implementation.
Exact quote equality is required when valuation inputs are identical; a genuine
native economic-state change must update the quote. The disk token check also
proved that the saved state, not the unsaved modified state, was restored.

## Diagnostic scope

Two exact player-only interaction discovery messages are inherited unchanged
from the frozen public payload. Their complete source-file hashes are checked;
no broad Parley namespace exception is permitted.

The remaining native court-initialization messages reproduce the exact 58-record
multiset observed before any fixture effects in the feature-Off control. Standard
003 contains that sequence once during initial load and once during the explicit
disk load. The classifier accepts at most one exact sequence in each evidenced
phase, with identical messages, locations and invalid-character ID. Additional
records, duplicate phases, a third burst or source drift fail the review. The
inspector reruns the classifier rather than trusting a supplied PASS label.

Off additionally has four exact unused-variable warnings from two test-only
read-only stock captures. Those variables are absent from the production runtime.
The old single-burst classifier's failed report for Standard 003 is retained.

The court sequence's underlying cause is not proven or fixed. Feature-Off still
loads Parley; it is not a no-mod vanilla control. These records cannot establish
visual correctness and are not described as a clean engine log.

## Static verification

The later tooling-portability receipt
`publication130/source-portability-implementation-r1.json` records the complete
`tests/parley` suite at 374 tests, OK, with three skips. The historical installed-game
compatibility run is separately 13/13; the immutable RC9 AGOT comparison remains
unexecuted. Counts from overlapping suites are not added together. Earlier 221,
267 and 364-test records retain their original source scopes.

Public native helpers now require explicit external paths instead of this
maintainer's machine defaults. Their original bytes were preserved before those
changes. Portability/static checks and this documentation update do not rerun the
engine, reclassify old diagnostics or turn old helper reports into fresh evidence.

## Remaining release gates and implementation limits

- The targeted layout/physical-hover check is `USER_CONFIRMED`; automated rendered
  component capture remains `NOT_VERIFIED`. Multiplayer is `NOT_VERIFIED`.
- Exact-candidate GAME/native and all-nine-language localization acceptance is
  pending at this revision and remains a blocking publication gate.
- Existing-save migration with a missing rule is `NOT_VERIFIED`. Explicit Off
  works; the policy's absent-setting fallback does not prove whether CK3 inserts
  the new default while loading an old save.
- Full MCA selection/settlement, incoming-letter button execution and autonomous
  AI scheduling are not established by cached marriage or synchronous helper tests.
- Long-campaign balance and arbitrary cross-resource split/reversal resistance
  are not proven. Hypothetical territory/courtier changes do not yet feed future
  income into other terms' currency capacities.
- Advanced multi-object rows use aggregate context; per-object harmonic
  valuation and interest drill-down are not implemented.
- The live-consent guard suppresses consequence previews for already-refused
  manual offers. Refusal/retry remain functional; a future preview fix must not
  create a live execution bypass.

The 1.3.0 candidate is prepared; this document does not certify external
publication, deployment, delivered bytes or a whole-candidate native PASS.
