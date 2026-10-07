# Parley: The Negotiating Table

## At a glance

- 🟢 **Version 1.2.2** · Targets CK3 **1.20.0.4**.
- 🟢 **Standalone:** no other mod required.
- 🟢 **Negotiate marriage, money and allegiance in one treaty.**
- 🟢 **Languages:** English, French, German, Japanese, Korean, Polish, Russian, Simplified Chinese, [來自無壹的中文翻譯](https://steamcommunity.com/sharedfiles/filedetails/?id=3090564070) and Spanish.
- 🔴 **Changes gameplay:** treaties can transfer money, people, land and vassalage.
- 🔴 **AGOT compatibility: awaiting the AGOT update for CK3 1.20.**
- 🔴 **Direct ruler negotiations only.** Puppet proxy mode is unavailable.

## A wedding can win what a war cannot

Negotiate marriage, money and allegiance with both sides and your counterpart's valuation visible.

**Auto-balance** adjusts currencies toward **+1** acceptance or reports it cannot; relationships and concessions affect the result.

AI envoys bring offers and demands: accept, negotiate or turn them away.

## What you can negotiate

- **Payments:** gold, with prestige and piety governed by game rules; influence when both governments support it.
- **Marriage pacts:** choose couples and marriage form, combine marriages, arrange eligible betrothals or promise a grand wedding.
- **Land and allegiance:** cede eligible titles, swear fealty with an editable contract, grant independence, or transfer eligible direct vassals.
- **People and possessions:** exchange artifacts, pledge relatives as hostages, or transfer eligible courtiers and accompanying families.
- **Favors and pressure:** promise or use a hook, or threaten a ruler with sufficient army, prestige and dread. Player and AI threats share the same minimum.

Tooltips explain eligibility and rules. Eligible marriages can create alliances, but alliances are not sold separately.

## Reading the central panel

**Their Answer** combines benefits, costs, standing, extra demands and pressure into acceptance from your counterpart's perspective.

This historical AGOT example gives **197 + 136 - 322 - 10 = +1**, with no pressure:

- **They receive: 197** — gold, the marriage's positive factors and its alliance.
- **Standing, share: +136** — the relationship adjustment, applied to that positive offer.
- **What they give up: 322** — fealty and the marriage's negative factors.
- **Wanted on top, share: -10** — their extra demand, also based on the positive offer.

The individual treaty rows use a different breakdown:

- **Gold: 88** — the point value of this offer's **1,324 gold**.
- **Patrilineal: -32** — the marriage's positive factors minus its costs, excluding the alliance and shared relationship adjustments.
- **Military alliance: 68** — this marriage's alliance value, counted once.
- **Swear fealty: 250** — the counterpart's submission cost in this example.

**Why can -32 improve the treaty by about +100?** The alliance adds value, while positive marriage components change standing and extra-demand shares. Those shares use positive value, not the net -32 row. The panel implies roughly **106-107 points** gained from this marriage-and-alliance package; this is an inference, not a measured before-and-after result.

Rounding can make rows differ slightly from totals. These example values are not universal prices.

## Getting started

1. Right-click an eligible landed ruler: **Diplomacy > Negotiate a Treaty**.
2. Add terms in **You offer** and **They offer**.
3. Read **Their Answer**, adjust the package or use **Auto-balance**.
4. Review and confirm. The mod rechecks that the agreement can be carried out.


### Game rules guide

Choose these rules in **Game Rules** before starting a campaign. Updating the mod does not replace the choices already stored in a save. Parley's eight public rules are independent: choose the combination you want rather than treating one setting as a master switch.

**Default setup:** advanced terms **Enabled**; advanced term valuation **Classic**; prestige and piety **Available**; threat strength **Normal**; threat frequency **0 years**; AI-to-AI treaties and offers sent to you **Frequent**.

#### 1. Advanced terms

- **Enabled** (default): permits advanced treaty terms such as marriage arrangements and betrothals, title transfers, sworn fealty, independence and transfers of direct vassals. Each still has its own eligibility checks.
- **Disabled**: hides the advanced table terms and removes their corresponding incoming proposal options, including marriage letters. Basic negotiations remain available.

This is not a universal restriction on the separate AI-to-AI treaty system. To stop autonomous bargains between AI rulers, set **AI-to-AI treaties** to **Disabled** as well.

#### 2. Advanced term valuation

- **Classic** (default): keeps the earlier valuation formulas and ceilings. A save without the new setting also uses Classic.
- **Scaled**: makes territorial and personal stakes matter more. The table, Auto-balance, incoming AI proposals and applicable AI-to-AI bargains all use the selected valuation policy.

This changes **prices**, not permissions. It does not enable a forbidden term, change who can be transferred, or override prestige/piety trading rules. Prices are points used to evaluate an entire treaty, not fixed gold fees or guarantees of acceptance.

**Land and allegiance.** Each actual county contributes **20 + half its development**. A ruler's territorial value includes counties held through subordinate vassals, counted once. Add one authority premium for the ruler's primary rank: **duke 20, king 40, emperor 60, hegemon 80**. Additional title names do not count the same land again. County cession prices only the county actually transferred, with the existing contextual adjustments; higher-rank title cession remains unavailable.

Before the existing contextual adjustments, a transferred vassal costs **40 + territorial value**. Voluntary fealty offers use **50 + territorial value**; requested fealty and independence use **100 + territorial value**. The old 200/250-point ceilings do not apply in Scaled. For example, a duke controlling twelve counties at development 10 has a territorial value of **12 × 25 + 20 = 320**: transferring that vassal starts at **360**, requesting their submission at **420**. A count with one equally developed county starts at **65** for a vassal transfer. De jure interest and the rest of the treaty can change the final result.

**Courtiers.** The minimum starts at **1**, not 10. The strongest of the five regular skills and prowess are assessed separately, with larger bonuses for exceptional ability. Inspiration, physician training, beneficial congenital traits, dynasty standing and the strongest relevant explicit claim can add value. Multiple claims do not stack; unpressed claims count less. Family attachment and an existing friendship or romance with the receiving ruler add small bounded adjustments. This does not make spouses, heirs, serving councillors, knights or employed court-position holders newly tradable. AI courtier proposals select useful candidates instead of treating every ordinary courtier as a meaningful payment.

Family members who accompany a selected courtier under the game's normal transfer rules contribute their own intrinsic values, up to **60 additional points per selected courtier**. The selected person and family already at the receiving court are excluded from that addition. In Scaled, two selections cannot share an accompanying dependent, and that dependent cannot also be selected for marriage in the same treaty: overlapping groups must be corrected before settlement. Age, future lifespan and health are not forecast by this price.

**Hostages.** Keep their native personal, family and succession value, with a minimum of 10. The home realm adds limited political leverage: an heir can add up to **60**, a child up to **30**, another relative up to **15**. These alternatives do not stack. A hostage is not priced as ownership of their family's whole realm.

**Favors and contracts.** Promised and spent hooks become more valuable against a larger debtor, up to **twice** their usual value. Economic contract changes—taxes, levies, fortification and coinage—scale with the subject's territory, up to **three times** their ordinary weight. Their direction and positive/negative sign remain intact. Personal protections keep their existing contextual weights.

**What stays contextual.** Artifact rarity, condition, usefulness and ownership claims retain their existing valuation. Marriage and alliance terms retain their pair-specific calculation and diminishing returns; positive marriage value stays bounded, while Scaled removes the aggregate ceiling on marriage costs. AI-to-AI marriage gifts remain a separate dowry system with native matching restrictions, not a purchase of a realm. Currency conversion, resource permissions, relationship adjustments and threat strength keep their own rules.

**AI and pressure.** A large realm must not become cheap through the autonomous AI path. Paid AI fealty uses the same demanded-fealty land basis and must be affordable; coercive AI submission must cover that value in threat points as well as passing the normal threat gates. Auto-balance uses the new values and may report that available payments are insufficient.

Scaled is useful if land expansion feels too inexpensive, but it is not a universal difficulty setting. It does not stop a piety-rich ruler selling piety, remove all sources of wealth, or guarantee that every exchange is equally attractive to the player and AI. Combine it with the separate currency rules if you want to restrict those transfers.

#### 3. Prestige trading

- **Available** (default): prestige may be offered or requested from any eligible partner.
- **Same faith only**: both rulers must follow exactly the same faith. Belonging to the same broader religion is not enough.
- **Lower fame only**: prestige can move only from a ruler with a **strictly higher level of fame** to one with a lower level. Equal levels are excluded.
- **Peers and lesser only**: the giver's fame level may be equal to or higher than the receiver's.
- **Disabled**: prestige cannot be traded.

The directional rules compare **level of fame**, not stored prestige, title rank or who initiated negotiations. With fame levels 4 and 2, **Lower fame only** permits 4 → 2, but not 2 → 4. At equal levels, neither direction is allowed in strict mode; **Peers and lesser only** permits both. The giver must still have enough spendable prestige.

#### 4. Piety trading

- **Available** (default): piety may be offered or requested regardless of faith.
- **Same faith only**: both rulers must follow exactly the same faith; devotion levels do not restrict the direction.
- **Same faith: less devout**: both rulers must follow the same faith, and the giver's **level of devotion must be strictly higher** than the receiver's. Equal levels are excluded.
- **Different faiths only**: the rulers must follow different faiths, including different faiths within the same religion.
- **Same religion only**: the rulers must belong to the same broader religion, even if their faiths differ.
- **Disabled**: piety cannot be traded.

For example, Catholic and Orthodox rulers have different faiths within Christianity. They qualify under **Different faiths only** and **Same religion only**, but not **Same faith only**. A Catholic and an Ash'ari ruler qualify under **Different faiths only**, not **Same religion only**.

The strict-devotion option compares **level of devotion**, not the amount of piety in the treasury. A same-faith ruler at devotion level 4 can give to one at level 2, but cannot receive piety from them under that rule.

#### How currency restrictions affect a deal

Each direction is checked separately. A prestige or piety row can appear on only one side of the table; unavailable rows disappear. **Auto-balance and AI proposals use the same restrictions**, including when pricing a counteroffer. Gold is unaffected by these two rules.

The final agreement is checked again before execution. If a ruler's faith or fame/devotion level changes and a positive currency term is no longer permitted, an old draft cannot bypass the rule: revise or reopen the deal. Restrictions govern negotiated payments, not unrelated resource gains, costs or consequences such as the prestige loss for refusing a threat.

The prestige and piety rules are separate choices. For the faith-based exchange suggested by the community, choose **Prestige: Same faith only** and **Piety: Different faiths only**. Compliance does not mean the AI must include prestige or piety in every offer; a gold-only proposal is still valid.

#### 5. Threat strength

These labels adjust **how much pressure military superiority provides**, not a guaranteed schedule of incoming demands:

- **Weak**: coefficient 2.5; at equal fame and dread, the military-strength ratio needed is 41:1.
- **Normal** (default): coefficient 5; at equal fame and dread, the ratio needed is 21:1.
- **Strong**: coefficient 7.5; at equal fame and dread, the ratio needed is about 14.34:1.
- **Very strong**: coefficient 10; at equal fame and dread, the ratio needed is 11:1.

Every option requires **at least 100 threat points**, for both player and AI. Under **Normal**, a 2:1 military advantage at equal fame and dread gives only 5 points: it is not enough to threaten. The comparison uses maximum military strength, not just the troops currently raised. Higher fame and dread can lower the military advantage needed; being a full fame level below the target makes the threat worth zero regardless of army size.

The target must be an independent ruler, cannot be your ally, and neither ruler may hold a hostage from the other's home court. Other eligibility checks still apply. A completed treaty signed under threat causes a **-100 opinion modifier that decays over 15 years**; while that modifier remains, the same ruler cannot threaten that target again.

Threatening adds pressure to negotiations; it is not an automatic declaration of war. A large army does not guarantee a demand letter or the annexation of neighbors. This rule has no **Disabled** option; incoming demands can instead be silenced with the incoming-offer rule or the embassy decision below.

#### 6. Threat frequency

Choose **0 years** (default), **1 year**, **5 years** or **10 years** between uses. This is a **global cooldown on the ruler making the threat**, applying equally to the player and AI: changing targets cannot bypass it. It does not change the pressure calculation or stop ordinary diplomacy.

The cooldown starts when a treaty using a threat is concluded. An AI demand consumes its use when a valid demand is paid or refused; a stale, invalid demand does not. Merely ticking the threat box, auto-balancing or abandoning a draft does not start it. Successful AI-to-AI extortion and coerced fealty use the same cooldown. Already-open drafts and demand letters are checked again before execution.

**0 years** means no additional global cooldown, not unlimited threats against the same victim. The existing **15-year same-pair restriction**, incoming-letter limits and AI-to-AI bargain cooldown remain separate. A timed cooldown belongs to the individual character and survives saving/reloading or closing the table; it is not inherited by a successor.

#### 7. AI-to-AI treaties

- **Disabled**: stops the autonomous system for bargains between AI rulers. It does not stop you opening talks or receiving AI offers.
- **Occasional**: fewer opportunities for autonomous bargains.
- **Frequent** (default): more opportunities, still subject to eligible partners and workable terms.

This separate system can arrange payments, favors, artifacts, eligible land transfers, marriages and fealty. Overwhelming rulers can force submission when the threat conditions are met. Concluded world bargains impose a three-year per-ruler cooldown. You receive notices about relevant bargains involving a border neighbor, ally or current opponent.

Frequency changes opportunities, not a guaranteed number of treaties per year, and it does not make the AI's prices more generous. **Advanced terms** is not a universal switch for this system.

#### 8. Offers sent to you

- **Never**: stops unsolicited AI offers and demands. You can still initiate negotiations; AI-to-AI treaties retain their own setting.
- **Rare**: a three-year recipient quiet period after a visible letter; an individual proposer has a six-year attempt cooldown.
- **Normal**: a one-year recipient quiet period; a three-year proposer attempt cooldown.
- **Frequent** (default): a six-month recipient quiet period; a one-year proposer attempt cooldown.

These periods are limits, **not delivery deadlines**. A suitable proposer, meaningful package and eligible game state are still needed. A year without a letter is not, by itself, proof that the system is inactive.

Demand letters have an additional recipient lock: **20 years on Rare, 10 on Normal, 3 on Frequent**, plus the separate 15-year same-pair threat memory after a response. Ordinary offer frequency therefore does not imply repeated demands at the same rate.

During a campaign, **Receive No More Embassies** silences incoming treaty envoys; **Receive Embassies Again** reverses that choice. Neither prevents you from opening negotiations yourself.

#### Suggested combinations

- **Start with the defaults** for the full negotiating table and unrestricted prestige/piety payments.
- **Territory-sensitive expansion:** advanced term valuation **Scaled**. Large realms cost more; ordinary courtiers no longer all start at 10 points.
- **Less frequent extortion:** threat frequency **5 years** or **10 years**. A ruler must wait before threatening another target, even with overwhelming dread and military strength.
- **Faith-based exchange:** prestige **Same faith only**, piety **Different faiths only**.
- **Strict downward transfers:** prestige **Lower fame only**, piety **Same faith: less devout**.
- **You initiate diplomacy:** incoming offers **Never**. Disable AI-to-AI treaties separately only if you also want to stop autonomous world bargains.

These are suggested combinations of the existing rules, not additional built-in presets.

When acting for a puppet, Parley's opener and marriage picker are hidden. Personal Rites determine marriage defaults and lineality pricing; native marriage eligibility checks still apply.

## Compatibility and load order

**Vanilla file replacements: none.** Other mods and overhauls can still alter mechanics treaties rely on and need compatibility work.

**Optional vanilla load order:**

1. Parley: The Negotiating Table
2. Marriage Calculation Assistant

**AGOT is not supported by this CK3 1.20 release.** Its integration is disabled pending an AGOT update and fresh checks. The calculation above is a historical example from CK3 1.19.0.6 with AGOT 0.5.2.1. Both marriage assistants are optional; neither is a general Parley compatibility patch.

**Submods and companion mods:**

- [Marriage Calculation Assistant](https://steamcommunity.com/sharedfiles/filedetails/?id=3811100163): marriage-candidate scores, breakdowns and sorting.
- [AGOT: Marriage Calculation Assistant](https://github.com/G4VV4KH/-CK3-AGOT-Marriage-Calculation-Assistant): AGOT scoring for MCA; current compatibility is on hold.

No other compatibility patches are included. Enable one copy of each mod.

## Saves and known limits

Before removal, use **Fold Away the Negotiating Table** under **Mod Removal Decisions**, save, then disable Parley. This clears negotiation and AI state, but completed marriages, payments and transfers persist. Close MCA's picker before saving or removing MCA.

Title transfers cannot be bundled with fealty or independence. Overlapping courtier and hostage selections can invalidate a package.

The negotiation screenshots were captured on **CK3 1.19.0.6**; some interface details may differ. **Multiplayer and long campaigns remain unverified.**

## Feedback and support

For bugs, include versions, load order, UI scale, steps and a screenshot; check whether this family alone reproduces it.

[Report an issue on GitHub](https://github.com/G4VV4KH/-CK3-Parley-The-Negotiating-Table/issues)

Email: g4vv4kh@gmail.com

### [Want to support my work? Donate on Ko-fi 💛](https://ko-fi.com/g4vv4kh)

## Find this mod elsewhere

- [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3811090081)
- [Paradox Mods](https://mods.paradoxplaza.com/mods/161475/Any)
- [Nexus Mods](https://www.nexusmods.com/crusaderkings3/mods/399)
- [GitHub](https://github.com/G4VV4KH/-CK3-Parley-The-Negotiating-Table)

## My other mods

- [Marriage Calculation Assistant](https://steamcommunity.com/sharedfiles/filedetails/?id=3811100163) — compare and sort marriage candidates.
- [Your Own Hegemony](https://steamcommunity.com/sharedfiles/filedetails/?id=3811201582) — found a custom hegemony.
- [Vassalization Extended](https://steamcommunity.com/sharedfiles/filedetails/?id=3813943691) — choose Forced Vassalization terms without a county limit.
- [Court Automation](https://steamcommunity.com/sharedfiles/filedetails/?id=3814028714) — automate court positions and recruit courtiers or knights.
- [Nomad Autorefill](https://steamcommunity.com/sharedfiles/filedetails/?id=3814793283) — automatically reinforce nomadic Men-at-Arms using herd or gold.
- [Tax Collection Automation](https://steamcommunity.com/sharedfiles/filedetails/?id=3815381275) — automatically assign tax collectors and optimize tax jurisdictions.

These mods are optional.

## Screenshots

![Captured on CK3 1.19.0.6: Offer gold and prestige in exchange for fealty, with acceptance shown at the table.](publishing/screenshots/01-negotiating-table.png)

Captured on CK3 1.19.0.6: Offer gold and prestige in exchange for fealty, with acceptance shown at the table.

![Captured on CK3 1.19.0.6: Other rulers make offers of their own: gold today in exchange for a favor later.](publishing/screenshots/02-incoming-ai-offer.png)

Captured on CK3 1.19.0.6: Other rulers make offers of their own: gold today in exchange for a favor later.

![Parley 1.2.1 game rules: Scaled valuation and a five-year threat cooldown selected (not defaults).](publishing/screenshots/04-game-rules.png)

Parley 1.2.1 game rules: Scaled valuation and a five-year threat cooldown selected (not defaults).
