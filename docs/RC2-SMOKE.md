# RC2 focused engine smoke

Recorded 2026-09-30. **Result: PASSED within the scope below.** This record covers the exact `2026-09-30-game-rc2` package, not a later build or the full gameplay test matrix.

## Package and environment

- Game: CK3 1.19.0.6; A Game of Thrones 0.5.2.1.
- Load order: AGOT, Parley 1.0.0, MCA 3.0.1, AGOT:MCA 2.2.0.
- Package manifest SHA-256: `72752dc0fea338e6af3e1b0bc5a0caa227760d47d91d9d566f55845e01533a9c`.
- Fresh campaign: King Viserys I, The Rogue Prince bookmark, 8106.4.18 to 8106.6.27; English UI, Ironman off.
- Incoming offers: public **Frequent**. AI-to-AI treaties: **Frequent** (`common`). Threat scaling: **Standard**. Developer telemetry and the TEST offer-rate option were absent.

The release workspace's `smoke/rc2-2026-09-30/smoke-result.json` contains the machine-readable result and evidence references. Logs, screenshots, saves and local launcher paths stay outside this source repository.

## Observed behavior

- The public incoming-offer settings cycled through Never, Rare, Normal and Frequent, with no TEST setting or telemetry rule.
- Parley's English introduction and two-sided negotiation window displayed readable public text without raw localization keys.
- MCA's candidate list and native component tooltip displayed Ser Ronald Tinpenny's total of 24 = 6 skill potential + 18 age-based reproductive potential.
- The fresh campaign advanced to 8106.6.27 and naturally received **An Embassy from Lord Bernard**: Fine Regalia in exchange for 124 gold from the player. The terms, partner assessment and response actions were visible.

No treaty or marriage was committed. The previously closed payment, refusal, save/reload, sorting and dragonrider-contribution cases were not repeated. The adapter's presence in this combined run is not a new nonzero-rider test.

## Log findings and limits

Startup logged 112 references to removed developer rule values: 108 were in older-save enumeration blocks, and the source of the remaining four was not independently localized. These do not establish errors in the fresh campaign, and the four unresolved origins must not be described as proven save or preset warnings.

Three generic animation warnings remained unattributed; no visible issue was observed. No new family-namespace errors appeared during the short run. The result does not claim whole-game clean logs.

This short public-Frequent run does not establish long-term offer frequency, normal-rate balance, multiplayer compatibility, every treaty outcome, all save/selection scenarios or a newly repeated nonzero dragonrider contribution. Existing development evidence retains its original scope. Platform publication and verification of a downloaded Workshop copy are separate steps.
