# Parley: The Negotiating Table

## At a glance

- 🟢 **Version 1.0.0** · Built for CK3 **1.19.x**; tested on **1.19.0.6**.
- 🟢 **No other mod required.** Adds its own negotiation interface and scripts.
- 🟢 **AGOT 0.5.2.1:** a combined gameplay smoke test passed with the checked developer build. The release package is awaiting its focused smoke test.
- 🟢 **Nine languages:** English, French, German, Japanese, Korean, Polish, Russian, Simplified Chinese and Spanish.
- 🔴 **Gameplay changes:** treaties can move money, people, land and vassalage. Read the final terms before agreeing.
- 🔴 **Coverage limits:** multiplayer, long-term AI offer frequency and compatibility with every overhaul have not been established.

## A wedding can win what a war cannot

Put the marriage, the money and the terms on the same table. Build an agreement between two houses, give your counterpart a reason to sign, and leave the battlefield for another day.

## A full treaty, negotiated together

Parley adds a diplomatic negotiation window to Crusader Kings III: what you offer, what they offer, and how your counterpart values the complete agreement.

The table shows their expected answer as you edit. Add a payment, choose a marriage or negotiate allegiance. Use the balancing tool to seek acceptable terms, then review before confirming. Your relationship and the concessions affect the result.

Other rulers can take the initiative. AI envoys bring offers and demands, and you can accept, enter negotiations or turn them away. A separate game rule controls treaties between AI rulers.

## What you can negotiate

- **Payments:** gold, with prestige and piety governed by game rules; influence when both governments support it.
- **Marriage pacts:** choose the people and marriage form, combine multiple couples, arrange eligible betrothals, and promise a grand wedding where available. Eligible marriages can create alliances through the game's marriage rules.
- **Land and allegiance:** cede eligible titles, swear fealty with an editable contract, grant independence, or transfer eligible direct vassals.
- **People and possessions:** exchange eligible artifacts, pledge eligible relatives as hostages, or transfer eligible courtiers and their accompanying families.
- **Favors and pressure:** promise a hook, call in an existing hook, or threaten an eligible ruler when your military strength, prestige and dread provide enough weight. Threat access uses the same minimum for player and AI.
- **Readable terms:** see selected people and objects, the partner's assessment, refusal reasons and applicable personal consequences before committing.

Terms depend on the rulers, government, game rules and the relevant game mechanics. Read the eligibility tooltips when a term is unavailable. Parley does not offer a separate standalone alliance purchase: the alliance described above is a consequence of an eligible marriage.

## Getting started

1. Right-click an eligible landed ruler and choose **Negotiate a Treaty** in the Diplomacy category.
2. Add terms in **You offer** and **They offer**. Open the relevant picker or editor to choose the exact people, titles or objects.
3. Read **Their Answer** and its breakdown. Adjust the package yourself or use the balancing tool.
4. Review and confirm the agreement. The mod checks the staged package again before applying it; an agreement that can no longer be carried out is rejected.

Game rules control advanced terms, prestige and piety trading, AI treaties, incoming offer frequency and threat scaling. The detailed eligibility checks still apply when a feature is enabled.

## Compatibility and load order

**Vanilla file replacements: none.** Parley adds files under its own names in `common/`, `events/`, `gui/`, `data_binding/` and `localization/`. It does not replace the vanilla marriage window. Other mods can still change mechanics or interface structures that a treaty relies on.

**Vanilla game with the optional marriage assistant:**

1. Parley: The Negotiating Table
2. Marriage Calculation Assistant

**Verified AGOT family order:**

1. A Game of Thrones
2. Parley: The Negotiating Table
3. Marriage Calculation Assistant
4. AGOT: Marriage Calculation Assistant

Parley works without either assistant. MCA adds marriage-candidate comparison; AGOT:MCA adapts that score for AGOT and requires MCA. These are not general AGOT compatibility patches. The smoke covered this combination, not every possible AGOT treaty.

**Submods and companion mods:**

- Marriage Calculation Assistant: candidate scores, native breakdowns and optional score sorting in the marriage picker.
- AGOT: Marriage Calculation Assistant: AGOT candidate scoring support for MCA.

No additional compatibility patches are included in this release. Enable only one installed copy of each mod in a playset.

## Saves and known limits

Parley stores negotiation and AI state in saves. Before removing it, use **Fold Away the Negotiating Table** under **Mod Removal Decisions** while the mod is still enabled, save, and then disable it. Completed treaties are part of your campaign: uninstalling does not reverse marriages, payments, land transfers or other completed outcomes. Close MCA's marriage picker before saving or removing that companion as well.

Targeted tests covered incoming offers and demands, payment and refusal, save/reload, and a short combined AGOT run. Normal-frequency long campaigns, multiplayer and all changed-eligibility cases remain outside that coverage. Some AI-to-AI rule-policy and delayed-letter currency cases remain documented limitations; not every AI path applies identical rule semantics.

## Feedback and support

For a useful bug report, include the mod version, CK3 version, relevant total conversion version, load order, UI scale, steps to reproduce and a screenshot of the affected interface. Mention whether the issue occurs with the required mod family alone.


## Find Parley elsewhere

- Steam Workshop
- Paradox Mods
- Nexus Mods
- GitHub

## My mods

- Parley: The Negotiating Table — negotiate complete diplomatic agreements.
- Marriage Calculation Assistant — compare marriage candidates with readable scores and sorting.
- AGOT: Marriage Calculation Assistant — add AGOT candidate potential to MCA.
