# Auto-balance correction — 2026-09-30

Status: source regression checks pass; the reported window defect is reproduced in original dev and corrected in the focused GAME RC3 TEST runtime check. The user also confirmed that the reported bug no longer occurs. This record does not authorize publication. The earlier [RC2 smoke](RC2-SMOKE.md) did not exercise this failure.

## Observed failure and cause

During screenshot preparation, a player asked High Chieftain Amr ibn Mu'ara of Asir to swear fealty. The selected fealty cost 130 points. Repeated Auto-balance presses produced the following displayed table; piety remained zero on both sides:

| Press | Player gold | Player prestige | Partner gold | Partner prestige | Acceptance |
|---|---:|---:|---:|---:|---:|
| Before balancing | 0 | 0 | 0 | 0 | -130 |
| 1 | 700 | 535 | 56 | 0 | +23 |
| 2 | 700 | 644 | 56 | 358 | +7 |
| 3 | 700 | 674 | 56 | 456 | +3 |
| 4 | 700 | 684 | 56 | 489 | +1 |

The source interpreter reproduces this sequence against RC2. Its fixture matches the displayed figures; it is not a reconstruction of every character field from a save. The affected algorithm and valuation logic were shared by pre-fix dev and RC2. Release projection and telemetry removal did not introduce the defect.

The old balancer estimated payments from nominal currency prices. Prestige, piety and influence valuations also apply personality multipliers, which those inverse steps omitted. The acceptance formula additionally rounds both column totals, scales positive offered value by relationships and rounds the final result. Nominal-price arithmetic was therefore not an exact inverse.

After overpaying, the window collected a payment from the partner to lower the score instead of reducing the player's overpayment. It had no currency-netting pass. Limited corrective passes and the partner's wallet cap left the first result at +23; further clicks accumulated offsetting payments. The success message described the branch entered, rather than confirming the final target had been reached.

## Change

`common/scripted_effects/tnt_39_autobalance.txt` now shares a bounded search between the window and incoming AI letters. It probes the real `tnt_ai_accept_value`, including trait modifiers and rounding, instead of estimating a currency slope. Each search has at most 32 iterations.

- Net existing opposing payments first. A currency cannot be added on one side while a positive amount remains on the other.
- Close deficits and remove overpayment before requesting new partner payments. Preserve selected noncurrency terms; retain the existing, separate partner-only lumpy-term policy.
- Respect currency rules, government gates, the 20% automatic-payment reserve and the influence cap. Preserve legal manual payments above the reserve, including fractional amounts.
- Target +1. When rounding or available resources leave a larger acceptable minimum, report that limitation instead of declaring an exact balance or manufacturing an offsetting payment.
- Keep the button available at +1 so an old draft with opposing payments can be normalized. Determine its status from the final table.

The reproduced fealty fixture now reaches +1 on the first press with 700 player gold and 356 player prestige, with no partner currency payments. Subsequent presses leave the table unchanged. These are model results for the original screenshot fixture; the controlled engine comparison below uses a saved campaign with different wallets and therefore different payments.

Review also caught a fractional-payment regression in an intermediate implementation: flooring a legal 952.5-gold manual offer changed +1 to 0 while the automatic reserve prevented restoring it. The final search preserves fractional bases and wallet endpoints; positive subunit payments survive cleanup. Both cases have regressions.

## AI scope

Incoming AI letters use `tnt_ai_offer_settle_effect` in `tnt_37_ai_offer.txt`, which calls the same currency solver. The old letter path did net currencies, but its subsequent corrective sweeten pass could recreate opposing prestige, piety or influence payments.

A source-level A19 counterexample uses a 35-point courtier purchase, relationship multiplier 2, an arrogant partner, prestige price 15, no gold and sufficient prestige. The old path ended at +5 with the player paying 60 prestige and the AI paying 772. Its existing go/no-go could allow that result. The corrected path ends at +1 with only the AI paying 694 prestige. This is a deterministic model counterexample, not an observed natural letter in CK3.

The letter caller sets the partner and refreshes both influence-government mirrors before composing, so the new solver does not require an open UI. Prestige and piety still use the live rule triggers. The intentional generosity ceiling and its purchase/independence exceptions are retained. A21 demands continue to bypass ordinary settlement.

AI-to-AI world trades use the separate dispatcher and prices in `tnt_38_ai_world.txt` and `tnt_56_ai_values.txt`; they do not call this balancer. Their fealty route checks its own price and acceptance, transfers gold once from prospective liege to vassal, then applies vanilla vassalization. This bug does not propagate through that route; this statement is not a new certification of every world-trade scenario.

The fix runs on fresh letter composition or an explicit Auto-balance press. It does not rewrite previously stored pending letters. Their terms can be normalized after entering the counteroffer window.

## Verification and limits

Run from the repository root:

```powershell
python tests/parley/test_autobalance.py --source mod/parley
```

The recorded source run passes 14 test methods, including:

- The four screenshot tables and first-press/repeated-press fealty regression.
- A 480-case matrix of UI/AI paths, directions, traits, opinion and available currency lanes.
- An independent brute-force minimum oracle over 240 single-currency configurations.
- 160 seeded mixed-currency tables, opposing-payment cleanup, AI generosity and A19 regressions.
- Exhausted wallets, signed noncurrency gain, manual payments above reserve, fractional/subunit amounts and the actual influence mirror gate.

An independent review additionally exercised 160 fractional mixed-currency tables. Their formulas agreed with the oracle, currencies remained one-directional, and repeat checks were stable with the same target. AI generosity cases must retain their raised ceiling during such a repeat check.

The Python harness reads the actual effect and value AST. An independent arithmetic oracle and exhaustive amount search check the results; unknown executed syntax fails. Noncurrency prices and relationship inputs are fixture leaves. Sorting and lumpy acquisition are explicit no-op mocks with no eligible inventory. Decimal arithmetic and rounding approximate CK3; the harness is not the engine parser, a performance benchmark, multiplayer proof or long-term AI simulation.

The older `tools/family/tnt_balance_model.ps1` is a separately maintained model that does not read current runtime source. Its currency routines still contain older full-wallet and 5,000/10,000 caps. A pass there could not prove the shipped button correct. The new source-executing regression closes that blind spot; earlier tests retain only their documented scope.

Local investigation records are under the release workspace's `verification-evidence/autobalance-2026-09-30/`: `rc2-source-witness.json`, `dev-source-witness.json`, `ai-a19-source-witness.json` and `source-script-regressions.json`. They record the tested source hashes and model limits. Saves and private game logs do not belong in this repository.

## Focused runtime verification

The controlled comparison used the same `parley_autobalance_repro.ck3` save, dated 1178.10.1, with Yusuf (50537) negotiating with Amr (51473). Its SHA-256 is `d6dba82f37753ea1347463b6419adbcc01becf2165ef31c75dc8a87b7fb2473f`. Each comparison started with partner fealty worth 130, no currency payments and acceptance -130. No deal was sent in the recorded original-dev reproduction.

| Runtime build | Player gold | Player prestige | Partner gold | Partner prestige | Acceptance after one press |
|---|---:|---:|---:|---:|---:|
| Unmodified original dev | 736 | 538 | 77 | 0 | +23 |
| GAME RC3 TEST | 736 | 352 | 0 | 0 | +1 |

These are displayed amounts from the controlled same-save comparison, not the 700/535/56 screenshot fixture above. The original-dev record confirms the mounted source path through `debug.log`. The corrected first-click capture shows +1 with no partner currency payments. A repeat press was observed by the assistant to leave the corrected amounts unchanged and show state 2; no separate clear repeat-click screenshot was retained. The user's subsequent confirmation is limited to the reported manual-window bug.

The original effect file SHA-256 was `bf5f73b702d48d76f4df89b52f20f0b4f21476f71f795ab4672f551e60a3439e`; the final corrected `tnt_39_autobalance.txt` SHA-256 is `f1a1d3d7e16d942341570c6111888552ac65de384f440d44f8f34df8f0bbb446`.

Local evidence in `verification-evidence/autobalance-2026-09-30/` includes `runtime-original-dev/result.json`, its `first-click.png`, `runtime-first-click.png`, and `runtime-rc3-user/user-confirmation.json`. This closes the focused engine check for the reported window defect. The AI model limits above remain: this is not a natural-letter, long-term AI or multiplayer certification, and no publication is authorized by this result.

The saved-log audit found no errors directly naming the new `tnt_ab_*` symbols or the changed balancer/value/GUI/localization files. The logs are not globally clean: old-save metadata and other startup errors remain; RC3 also contains vanilla court-scene errors whose connection to this change is unestablished. Exact counts and source attribution are in the local `runtime-log-audit.json`.

The final `2026-09-30-game-rc3` package has byte-identical payload inventories to the engine-tested staging build for all 104 files. MCA and AGOT:MCA payloads are byte-identical to RC2. The installed dev runtime receives the same 13 corrected Parley files. Current local game copies and canonical upload descriptors use clean public names. Installed local dev copies use a `[DEV]` name/dependency overlay; canonical dev descriptor templates retain clean public names. Historical test labels such as `[GAME RC3 TEST]` identify the captured test session.
