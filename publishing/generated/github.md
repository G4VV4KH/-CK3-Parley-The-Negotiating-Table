# Parley: The Negotiating Table

## At a glance

- 🟢 **Version 1.1.0** · Targets CK3 **1.20.0.2**. Focused single-player checks passed.
- 🟢 **No other mod required.** Includes its own negotiation interface.
- 🟢 **Nine languages:** English, French, German, Japanese, Korean, Polish, Russian, Simplified Chinese and Spanish.
- 🔴 **Changes gameplay:** treaties can transfer money, people, land and vassalage.
- 🔴 **Direct ruler negotiations only.** Puppet proxy mode is unavailable. Current AGOT support is on hold; see the historical combination below.
- 🔴 **Multiplayer and long campaigns are not fully verified.** Other overhauls may need compatibility work.

## A wedding can win what a war cannot

Put marriage, money and allegiance on the same table. Give your counterpart a reason to sign, and leave the battlefield for another day.

## A full treaty, negotiated together

See both sides of the treaty and your counterpart's valuation in one window.

**Auto-balance** adjusts currencies toward **+1** acceptance and reports when it cannot reach that target. Relationships and concessions affect the result. Review the terms before confirming.

AI envoys bring offers and demands: accept, negotiate or turn them away. A separate game rule controls treaties between AI rulers.

## What you can negotiate

- **Payments:** gold, with prestige and piety governed by game rules; influence when both governments support it.
- **Marriage pacts:** choose couples and marriage form, combine multiple marriages, arrange eligible betrothals or promise a grand wedding. Eligible marriages can create alliances.
- **Land and allegiance:** cede eligible titles, swear fealty with an editable contract, grant independence, or transfer eligible direct vassals.
- **People and possessions:** exchange artifacts, pledge relatives as hostages, or transfer eligible courtiers and accompanying families.
- **Favors and pressure:** promise a hook, use an existing hook, or threaten a ruler when your army, prestige and dread provide enough weight. Player and AI threats share the same minimum.

Tooltips explain restrictions from rulers, governments and game rules. Alliances come from eligible marriages, not a separate purchase.

## Reading the central panel

**Their Answer evaluates the treaty from your counterpart's perspective:** benefits, costs, standing, extra demands and pressure combine into acceptance.

The historical AGOT screenshot shows **197 + 136 - 322 - 10 = +1**, with no pressure:

- **They receive: 197** — gold, the marriage's positive factors and its alliance.
- **Standing, share: +136** — the relationship adjustment, applied to that positive offer.
- **What they give up: 322** — fealty and the marriage's negative factors.
- **Wanted on top, share: -10** — their extra demand, also based on the positive offer.

The individual treaty rows use a different breakdown:

- **Gold: 88** — the point value of this offer's **1,324 gold**.
- **Patrilineal: -32** — the marriage's positive factors minus its costs, excluding the alliance and shared relationship adjustments.
- **Military alliance: 68** — this marriage's alliance value, counted once.
- **Swear fealty: 250** — the counterpart's submission cost in this example.

**Why can -32 improve the treaty by about +100?** The alliance adds value, and the marriage's positive components change the standing and extra-demand shares. Those shares apply to positive value, not the net -32 row. The figures imply roughly **106-107 points** of improvement for this marriage-and-alliance package: an inference from the panel, not an exact measured before-and-after result.

Rounding can make displayed rows differ slightly from totals. These values belong to this proposal; they are not universal prices.

## Getting started

1. Right-click an eligible landed ruler: **Diplomacy > Negotiate a Treaty**.
2. Add terms in **You offer** and **They offer**; use the pickers for people, titles and objects.
3. Read **Their Answer**, adjust the package or use **Auto-balance**.
4. Review and confirm. The mod rechecks whether the agreement can still be carried out.

Game rules control advanced terms, prestige and piety trading, AI treaties, incoming offer frequency and threat scaling. AI-to-AI treaties use their own system and frequency rule; the advanced-terms setting is not a universal restriction on those treaties.

Negotiate as your own ruler. When acting for a puppet, Parley's opener and treaty marriage picker are hidden. Version 1.1.0 follows personal Rites for marriage defaults and lineality pricing, while retaining native marriage eligibility checks.

## Compatibility and load order

**Vanilla file replacements: none.** Parley adds files in `common/`, `events/`, `gui/`, `data_binding/` and `localization/`. Other mods can still change mechanics treaties rely on.

**Vanilla game with the optional marriage assistant:**

1. Parley: The Negotiating Table
2. Marriage Calculation Assistant

**Historical RC3 AGOT order — CK3 1.19.0.6 only:**

1. A Game of Thrones
2. Parley: The Negotiating Table **1.0.0**
3. Marriage Calculation Assistant **3.0.1**
4. AGOT: Marriage Calculation Assistant **2.2.0**

That combination used **AGOT 0.5.2.1**. It does not establish AGOT support for Parley 1.1.0 on CK3 1.20. Both assistants are optional; they are not general AGOT compatibility patches.

**Submods and companion mods:**

- Marriage Calculation Assistant: candidate scores, native breakdowns and optional score sorting in the marriage picker.
- AGOT: Marriage Calculation Assistant: AGOT candidate scoring support for MCA.

No additional compatibility patches are included in this release. Enable only one installed copy of each mod in a playset.

## Saves and known limits

Before removal, use **Fold Away the Negotiating Table** under **Mod Removal Decisions**, save, then disable Parley. This cleans negotiation and AI state but does not reverse completed marriages, payments or transfers. Close MCA's picker before saving or removing that companion.

Title transfers cannot be bundled with fealty or independence. Overlapping courtier and hostage selections can invalidate a package. Terms are rechecked before execution; multiplayer and long-campaign balance remain unverified.

Gallery images show **RC3 on CK3 1.19.0.6**; the Dorne example uses **AGOT 0.5.2.1**. Current 1.20.0.2 tests covered direct negotiation, balancing, marriage staging/cleanup, Rites and influence. RC8 passed AI-world vassalization assertions and a short campaign with a natural fealty treaty for 743 gold at +2. Seven native diagnostics also reproduced with all mods off on the same save; logs are not empty. Native puppet UI, the full Jizya/legality matrix, multiplayer and long campaigns remain unverified.

## Feedback and support

Include mod/game versions, load order, UI scale, steps and a screenshot in bug reports. Mention whether the issue occurs with this family alone.

- [Source and issue reports](https://github.com/G4VV4KH/-CK3-Parley-The-Negotiating-Table)

## Find Parley elsewhere

- Steam Workshop
- Paradox Mods
- Nexus Mods
- [GitHub](https://github.com/G4VV4KH/-CK3-Parley-The-Negotiating-Table)

## My mods

- Parley: The Negotiating Table — negotiate complete diplomatic agreements.
- Marriage Calculation Assistant — compare marriage candidates with readable scores and sorting.
- AGOT: Marriage Calculation Assistant — add AGOT candidate potential to MCA.

## Screenshots

![Historical RC3 (CK3 1.19.0.6): Offer gold and prestige in exchange for fealty, with acceptance shown at the table.](publishing/screenshots/01-negotiating-table.png)

Historical RC3 (CK3 1.19.0.6): Offer gold and prestige in exchange for fealty, with acceptance shown at the table.

![Historical RC3 (CK3 1.19.0.6): Other rulers make offers of their own: gold today in exchange for a favor later.](publishing/screenshots/02-incoming-ai-offer.png)

Historical RC3 (CK3 1.19.0.6): Other rulers make offers of their own: gold today in exchange for a favor later.

![Historical RC3 (CK3 1.19.0.6, AGOT 0.5.2.1): Bring dynastic diplomacy to AGOT: combine marriage, alliance, gold and fealty in one proposal.](publishing/screenshots/03-agot-marriage-and-fealty.png)

Historical RC3 (CK3 1.19.0.6, AGOT 0.5.2.1): Bring dynastic diplomacy to AGOT: combine marriage, alliance, gold and fealty in one proposal.

![Historical RC3 (CK3 1.19.0.6): Choose which treaty terms are available and how often AI rulers negotiate.](publishing/screenshots/04-game-rules.png)

Historical RC3 (CK3 1.19.0.6): Choose which treaty terms are available and how often AI rulers negotiate.
