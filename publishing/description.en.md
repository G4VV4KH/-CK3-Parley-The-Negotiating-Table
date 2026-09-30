# Parley: The Negotiating Table

## At a glance

- 🟢 **Version 1.0.0** · Built for CK3 **1.19.x**; tested on **1.19.0.6**.
- 🟢 **No other mod required.** Adds its own negotiation interface and scripts.
- 🟢 **AGOT 0.5.2.1:** checked in a short session with MCA and AGOT:MCA.
- 🟢 **Nine languages:** English, French, German, Japanese, Korean, Polish, Russian, Simplified Chinese and Spanish.
- 🔴 **Changes gameplay:** treaties can transfer money, people, land and vassalage.
- 🔴 **Multiplayer and long campaigns are not fully verified.** Other overhauls may need compatibility work.

## A wedding can win what a war cannot

Put marriage, money and allegiance on the same table. Give your counterpart a reason to sign, and leave the battlefield for another day.

## A full treaty, negotiated together

Parley adds a negotiation window: what you offer, what they offer, and how your counterpart values the agreement.

See their expected answer as you edit. **Auto-balance** adjusts currencies toward **+1** acceptance and reports when it cannot reach that target. Relationships and concessions affect the result. Review the terms before confirming.

Other rulers can take the initiative. AI envoys bring offers and demands, and you can accept, enter negotiations or turn them away. A separate game rule controls treaties between AI rulers.

## What you can negotiate

- **Payments:** gold, with prestige and piety governed by game rules; influence when both governments support it.
- **Marriage pacts:** choose couples and marriage form, combine multiple marriages, arrange eligible betrothals or promise a grand wedding. Eligible marriages can create alliances.
- **Land and allegiance:** cede eligible titles, swear fealty with an editable contract, grant independence, or transfer eligible direct vassals.
- **People and possessions:** exchange artifacts, pledge relatives as hostages, or transfer eligible courtiers and accompanying families.
- **Favors and pressure:** promise a hook, use an existing hook, or threaten a ruler when your army, prestige and dread provide enough weight. Player and AI threats share the same minimum.

Availability depends on the rulers, governments and game rules; the tooltips explain restrictions. An alliance comes from an eligible marriage, rather than a separate alliance purchase.

## Reading the central panel

**Their Answer evaluates the treaty from your counterpart's perspective.** The headline combines benefits, costs, standing, extra demands and pressure into the final acceptance score.

In the AGOT screenshot, the displayed calculation is **197 + 136 - 322 - 10 = +1**, with no pressure:

- **They receive: 197** — your offer's positive value: gold, the marriage's positive factors and its alliance.
- **Standing, share: +136** — the combined relationship adjustment, applied as a share of that positive offer.
- **What they give up: 322** — their costs: fealty and the marriage's negative factors.
- **Wanted on top, share: -10** — their additional demand, also calculated from the positive offer.

The individual treaty rows show a different level of detail:

- **Gold: 88** — the point value of the **1,324 gold** offered in this example.
- **Patrilineal: -32** — the marriage's own positive factors minus its own costs. This row excludes the alliance and shared relationship adjustments.
- **Military alliance: 68** — the separate value of the alliance this marriage brings, counted once.
- **Swear fealty: 250** — the cost assigned to the counterpart's submission in this example.

**Why can a marriage marked -32 improve the treaty by about +100?** Its alliance adds value, and its positive components also change the standing and extra-demand shares. Those shares apply to the positive offer, not to the net -32 row. The visible figures imply roughly **106-107 points** of improvement for this marriage-and-alliance package: an illustration inferred from the panel, rather than an exact measured before-and-after result.

Rows and totals are rounded, so adding displayed term values can differ slightly from the totals. These are this proposal's values, not universal prices.

## Getting started

1. Right-click an eligible landed ruler: **Diplomacy > Negotiate a Treaty**.
2. Add terms in **You offer** and **They offer**; use the pickers for people, titles and objects.
3. Read **Their Answer**, adjust the package or use **Auto-balance**.
4. Review and confirm. The mod rechecks whether the agreement can still be carried out.

Game rules control advanced terms, prestige and piety trading, AI treaties, incoming offer frequency and threat scaling. AI-to-AI treaties use their own system and frequency rule; the advanced-terms setting is not a universal restriction on those treaties.

## Compatibility and load order

**Vanilla file replacements: none.** Parley adds its own files in `common/`, `events/`, `gui/`, `data_binding/` and `localization/`. It does not replace the marriage window. Other mods can still change mechanics the treaties rely on.

**Vanilla game with the optional marriage assistant:**

1. Parley: The Negotiating Table
2. Marriage Calculation Assistant

**Verified AGOT family order:**

1. A Game of Thrones
2. Parley: The Negotiating Table
3. Marriage Calculation Assistant
4. AGOT: Marriage Calculation Assistant

Both assistants are optional for Parley. They provide candidate comparison, not general compatibility patches for AGOT or its submods.

**Submods and companion mods:**

- [Marriage Calculation Assistant]({{MCA_STEAM_URL}}): candidate scores, native breakdowns and optional score sorting in the marriage picker.
- [AGOT: Marriage Calculation Assistant]({{AGOT_MCA_STEAM_URL}}): AGOT candidate scoring support for MCA.

No additional compatibility patches are included in this release. Enable only one installed copy of each mod in a playset.

## Saves and known limits

Parley stores negotiation and AI state in saves. Before removing it, use **Fold Away the Negotiating Table** under **Mod Removal Decisions** while it is still enabled, save, then disable it. Uninstalling does not reverse completed marriages, payments or transfers. Close MCA's marriage picker before saving or removing that companion as well.

Some combinations are deliberately refused, including title transfers bundled with fealty or independence. Overlapping courtier and hostage selections can also make a package invalid. Parley checks the staged terms again before execution. Multiplayer and long-campaign balance remain unverified.

## Feedback and support

For bug reports, include mod/game versions, load order, UI scale, reproduction steps and a screenshot. Mention whether the issue occurs with this mod family alone.

- [Source and issue reports]({{PARLEY_GITHUB_URL}})
- [Contact the author](mailto:{{CONTACT_EMAIL}})
- [Donation information]({{DONATION_URL}})

## Find Parley elsewhere

- [Steam Workshop]({{PARLEY_STEAM_URL}})
- [Paradox Mods]({{PARLEY_PARADOX_URL}})
- [Nexus Mods]({{PARLEY_NEXUS_URL}})
- [GitHub]({{PARLEY_GITHUB_URL}})

## My mods

- [Parley: The Negotiating Table]({{PARLEY_STEAM_URL}}) — negotiate complete diplomatic agreements.
- [Marriage Calculation Assistant]({{MCA_STEAM_URL}}) — compare marriage candidates with readable scores and sorting.
- [AGOT: Marriage Calculation Assistant]({{AGOT_MCA_STEAM_URL}}) — add AGOT candidate potential to MCA.
