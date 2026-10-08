# Currency rules — Parley 1.2.0

Recorded 2026-10-04. Status: developer-session functional acceptance complete; publication preparation in progress. The existing published release is Parley 1.1.0 / RC11. A new transformed GAME candidate needs its own focused smoke before publication. This record does not claim an upload, clean whole-game logs or a long campaign.

## Implementation contract

- Canonical transfer permissions live in `common/scripted_triggers/tnt_40_triggers.txt`: A is the actual giver, B the receiver.
- Prestige: unrestricted, disabled, same faith, strictly higher fame, or equal-or-higher fame. Piety: unrestricted, disabled, same faith, different faiths, same religion, or same faith plus strictly higher devotion. Both defaults remain unrestricted.
- Direction uses fame/devotion **levels**, not resource balances. Equal levels fail the strict rules. Exact faith and broader religion are different checks.
- Four UI currency lanes and their amount controls use those permissions. Clearing a draft remains possible; unavailable positive lanes cannot be sent.
- The shared manual and AI settlement path clears denied amounts before pricing/netting and tests each direction separately. The separate AI-world prestige path is guarded as well.
- Whole-deal preflight checks positive currency terms before mutations. There is no per-leg policy recheck after a transfer changes levels.
- Nine localizations have matching keys/tokens and compact rule titles. No window enlargement or vanilla GUI replacement was added.
- MCA and AGOT:MCA runtime, public ABI and ownership remain unchanged. AGOT support remains on hold.

## Completed developer-session observations

The user performed the guided vanilla tests, principally from Salah al-Din's 1178 start, and provided screenshots and confirmations:

1. New settings appeared; shortened labels and the negotiation layout were readable.
2. Same-faith and directional visibility behaved correctly. Equal-devotion and different-faith cases denied the strict same-faith piety transfer.
3. A permitted 100-piety transfer executed; both balances matched the stated amounts.
4. Manual auto-balance excluded forbidden currencies.
5. A natural incoming offer asked 195 gold for Ushmun at +2. Opening its negotiating table retained the same terms. This was a gold-only offer, not proof of a natural prestige/piety-bearing letter.
6. With prestige limited to same faith and piety to different faiths, the Ghurid table exposed prestige but not piety; Baudouin's table exposed piety but not prestige.
7. Controlled zero-gold probes invoked the actual AI settlement stage: 132 prestige for the same-faith Ghurid fixture, and 848 piety for the different-faith Baudouin fixture, both at +1. These were pricing probes, not naturally delivered letters or executed transfers.
8. The user confirmed reloading the pre-probe save. No additional randomized run was requested to repeat these closed cases.

The dated local evidence collection is `ck3-mods-artifacts/2026-10-04-currency-rules/`, kept outside this repository. Its `manual-smoke-disposition.json` indexes the final scope; `manual-smoke-stage-2.json`, `ai-prestige-native-probe.json` and `ai-piety-native-probe.json` retain individual observations. Engine/build identity and logs belong to those captured technical records; the public description gives the target CK3 version without converting a target into a blanket compatibility claim.

## Automated evidence and limits

`post-smoke-dev-checks.json` records 11 successful check blocks: family gate, frozen GUI reconstruction, rule conformance, auto-balance, currency policies, held-AGOT boundary, AI dispatcher model, offer-rate contract, MCA source and sorting checks, and adapter checks. The source/live comparison matched 75 tracked runtime files excluding the local descriptor. `git diff --check` passed.

The focused currency suite has 20 tests, including 1,296 piety-policy cases, 1,080 prestige-policy cases and 528 solver combinations. These are interpreted source/model regressions, not exhaustive CK3 execution. The held-AGOT regression's immutable-baseline delta test was explicitly skipped when no baseline argument was supplied; the other four tests passed.

Run the focused suite from this repository:

```powershell
python -B tests/parley/test_currency_trade_rules.py --source mod/parley
python -B tests/parley/test_autobalance.py --source mod/parley
```

## Console diagnostic caveat

Early probe instructions included an overlong console command that was truncated and an invalid negative `add_gold` use. Those failures are not successful gameplay tests. The corrected short command removed short-term gold as intended.

Direct console invocation of the settlement effect produced tooltip-preview temporary-variable diagnostics, including `tnt_ab_search_target`; wrapping it in `hidden_effect` did not eliminate them. Functional settlement results above passed. Named observed stacks terminate in the console invocation; a blank-variable warning's origin remains unresolved, and one appeared with a gold-only instruction as well. There were no matching new currency-rule errors in the captured pre-probe interval.

Do not report globally clean logs or silently classify every warning as harmless. Conversely, these console-only observations do not establish a natural-event gameplay failure. No gameplay workaround was added merely to suppress synthetic probe output. Retain the diagnostic evidence and investigate further if the issue occurs in ordinary use.

## Publication boundary

The release projection strips developer telemetry and its game rule, plus the developer-only very-frequent offer rate. The player-facing guide therefore describes six rules, not the DEV diagnostic option. Version 1.2.0 adds no dependency and keeps the CK3 1.20 AGOT hold.

The canonical `publishing/description.en.md` contains the full guide and an explicitly marked Steam summary. GitHub, Paradox, Nexus and the preview render the full guide; Steam renders the short text plus the GitHub `#game-rules-guide` link, bounded to 8,000 UTF-8 bytes. The renderer rejects malformed marker pairs before writing outputs. This is one source with platform presentation variants, not independent maintained guides.

Preparation must pin the committed source and generator/media inputs, retain RC11 untouched, verify each platform package and record **PREPARED**, not **UPLOADED** or **VERIFIED**. Before any upload, perform a short smoke on the new GAME projection: rules and directional visibility, one legal balanced/confirmed deal, and closed-log review with the console caveat kept separate. Do not repeat the entire closed DEV matrix. Publish the GitHub guide before updating the Steam description so its new anchor is available.
