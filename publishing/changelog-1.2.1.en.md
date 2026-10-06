# Parley 1.2.1

- Added **Parley: Advanced term valuation — Classic / Scaled**. Classic is the default and preserves the earlier valuation behavior.
- Scaled prices land, fealty, independence and vassal transfers by actual territory and development without the old small territorial ceilings.
- Scaled refines courtier and hostage values, adds bounded realm-sensitive hook and economic-contract weights, and removes the aggregate ceiling on marriage costs.
- Accompanying courtier families contribute a bounded premium in Scaled; overlapping family groups cannot be charged or transferred twice in one package.
- Applied the policy to Auto-balance, incoming offers and relevant AI-to-AI paths, including territory-aware coercive submission.
- Added **Parley: Threat frequency — 0 / 1 / 5 / 10 years**: a global cooldown on the threatening ruler, shared by player and AI and independent of the existing 15-year same-target restriction. Default 0 preserves the previous global frequency.
- Renamed the previous threat calibration rule to **Parley: Threat strength**, with Weak / Normal / Strong / Very strong labels and unchanged coefficients. Drafts do not start the cooldown; resolved threats do, including valid refused AI demands.
- Expanded the Getting started game-rules guide with formulas, examples, defaults and limitations.
- Added the remaining global threat cooldown and its expiry date to the threat tooltip and the negotiation interaction tooltip, plus a compact countdown in the deal window. Existing saved cooldowns are read directly. The Russian zero-cooldown option now reads «нету».
- Fixed landless courtiers displaying “None”, inconsistent half-point score rounding, a missing gift-floor line in the compact breakdown, and the negated hatred-gate localization. These display fixes do not change treaty prices or acceptance rules.
