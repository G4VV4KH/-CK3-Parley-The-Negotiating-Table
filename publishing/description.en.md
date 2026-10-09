# Parley: The Negotiating Table

## At a glance

- 🟢 **Version 1.3.0** · Targets CK3 **1.20.0.4**.
- 🟢 **Standalone:** no other mod required.
- 🟢 **Negotiate marriage, money and allegiance in one treaty.**
- 🟢 **Languages:** English, French, German, Japanese, Korean, Polish, Russian, Simplified Chinese, [來自無壹的中文翻譯](https://steamcommunity.com/sharedfiles/filedetails/?id=3090564070) and Spanish.
- 🔴 **Changes gameplay:** treaties can transfer money, people, land and vassalage.
- 🔴 **WARNING — New rule: Negotiation interests.** **Standard** is the new-campaign default; unwanted payments lose value and wanted assets cost more to surrender. Choose **Off** for the earlier valuation.
- 🔴 **AGOT compatibility: awaiting the AGOT update for CK3 1.20.**
- 🔴 **Direct ruler negotiations only.** Puppet proxy mode is unavailable.

## A wedding can win what a war cannot

See both sides of the treaty and your counterpart's valuation.

**Auto-balance** adjusts currencies toward **+1** acceptance or reports it cannot.

Accept, negotiate or reject offers and demands from AI envoys.

## What you can negotiate

- **Payments:** gold, with prestige and piety governed by game rules; influence when both governments support it.
- **Marriage pacts:** choose couples and marriage form, combine marriages, arrange eligible betrothals or promise grand weddings.
- **Land and allegiance:** cede eligible titles, swear fealty with an editable contract, grant independence, or transfer eligible direct vassals.
- **People and possessions:** trade artifacts, pledge relatives as hostages, transfer eligible courtiers with their families.
- **Favors and pressure:** promise or use hooks or threaten with sufficient army, prestige and dread; player and AI share the threat minimum.

Tooltips show eligibility. Marriages may form alliances; alliances cannot be sold separately.

## Reading the central panel

**Their Answer** totals benefits, costs, standing, demands and pressure from your partner's perspective.

With **Negotiation interests** enabled, percentages show **valuation, not acceptance chance**:

- **You offer:** the partner's interest in receiving. A base 100-point term at 50% contributes 50 points.
- **They offer:** the partner's willingness to surrender. A base 100-point term at 50% costs 200 points.

Higher percentages favor you both ways. Rounded badges: red below **50%**, white at **50%**, green above. Hover for components and selected base/adjusted points. Empty rows preview interest, not prices or permission.

Rows show **base points**. **Interest** deducts receiving discounts, surrender premiums and standing/bargaining effects once. Threats and called-in hooks add separate pressure without interest badges.

With interests enabled, ordinary agreements need an answer **above zero**. Rounding affects display, not settlement. Points are not fixed gold prices.

## Getting started

1. Right-click an eligible landed ruler: **Diplomacy > Negotiate a Treaty**.
2. Add terms in **You offer** and **They offer**.
3. Read **Their Answer**, adjust the package or use **Auto-balance**.
4. Review and confirm; the mod rechecks the terms.

<!-- steam-guide-summary:start -->
🔴 **WARNING — Negotiation interests is new in 1.3.0:** Off / Mild / **Standard (new-campaign default)** / Strict. It changes valuations, not trading permissions or threat strength. Classic/Scaled base prices and currency restrictions remain separate. Gold, prestige and piety can each be selected on only one side. [Full rules, defaults and examples]({{PARLEY_GITHUB_URL}}#game-rules-guide).
<!-- steam-guide-summary:end -->

<!-- full-game-rules-guide:start -->
### Game rules guide

Choose these rules in **Game Rules** before starting a campaign. Updating the mod does not replace the choices already stored in a save. Parley's nine public rules are independent: choose the combination you want rather than treating one setting as a master switch. Check an older campaign's recorded rules rather than assuming it receives the new-campaign defaults.

**Default setup:** advanced terms **Enabled**; advanced term valuation **Classic**; negotiation interests **Standard**; prestige and piety **Available**; threat strength **Normal**; threat frequency **0 years**; AI-to-AI treaties and offers sent to you **Frequent**.

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

#### 3. 🔴 WARNING — Negotiation interests (new in 1.3.0)

**This new rule materially changes treaty valuations. Standard is enabled by default for new campaigns.** Select **Off** if you want the earlier interest-free evaluation; the other game rules remain independent.

- **Off:** no interest adjustments or percentage badges. It does not remove the one-direction currency safeguard described below.
- **Mild:** half the Standard strength; softer demand discounts and surrender premiums.
- **Standard** (new-campaign default): normal interest strength.
- **Strict:** twice the Standard strength; unwanted incoming terms are discounted more and wanted assets cost more to surrender. It is not a promise that every treaty costs exactly twice as much.

**Whose interest?** The table evaluates your negotiating partner. Under **You offer**, the percentage measures their interest in receiving; under **They offer**, it measures their willingness to surrender. Your own character's simulated preferences do not force you to accept an AI letter. A percentage is never the probability of acceptance.

**What changes?** Gold, prestige, piety and eligible influence use current stocks and useful spending needs: extra units may become less useful, while giving away useful reserves costs more. Land, vassals, fealty, independence, courtiers, hostages, artifacts, promised hooks, marriages and contract changes use their relevant context. Examples include domain or vassal capacity, court vacancies, equipped alternatives, protection and autonomy. Existing intrinsic prices and Classic/Scaled still apply; the rule does not unlock a forbidden term or replace fame, faith, resource or transfer restrictions.

**Reading the calculation.** At 100%, a term retains its base point value. Receiving interest discounts the benefit; willingness to surrender divides the base cost. Thus a 100-point term at 50% is worth **50** when received but costs **200** when surrendered. More incoming currency is priced across the useful-demand bands it crosses, not by applying the final unit's percentage to the whole offer. The badge summarizes the complete selected amount. The central **Interest** line deducts the difference once, including the associated relationship and bargaining changes.

**Mild and Strict are strength settings, not flat price multipliers.** For a single raw interest score `x` between 0 and 1, the effective score is `x / (s + (1 - s) × x)`, with strength `s = 0.5 / 1 / 2`. A raw 50% score therefore becomes about **66.67% / 50% / 33.33%**. Currency bands are adjusted before being combined. A genuinely unwanted incoming term can remain at 0%; surrender calculations have a numerical floor rather than dividing by zero.

**Before selecting anything,** the badge shows a preliminary preview for the current context. A currency preview describes the next marginal unit, not a selected quantity or a zero-sized treaty. Selecting an amount or object replaces it with that actual selection's evaluation; clearing the row restores the preview. Hover separates percentage-point reasons from the **Useful stock target (resource units)** and current stock. That resource target is an input, not extra treaty points. Rounded badges and more precise tooltip totals can differ slightly.

**AI and Auto-balance.** Manual negotiations, incoming offers and Auto-balance use the revised table quote, with ordinary acceptance checked again before settlement. Existing voluntary AI-to-AI deal types also apply interest to both rulers and recheck at execution, while retaining that system's own relationship and bargaining baseline. This does not add new AI deal types or guarantee a profitable offer on a schedule. Auto-balance can report that available payments cannot reach agreement.

**Pressure stays separate.** A threat or a called-in hook is not an unwanted gift and receives no interest percentage. The assets demanded in return still have their normal interest-adjusted value. Threat strength, eligibility, refusal consequences and cooldowns retain their own rules; a human may still choose to pay a valid coercive demand.

The model uses live needs, not a forecast of future income after every possible territorial or court change. Multi-object rows give an aggregate contextual score, not a separate interest breakdown for every selected object. It is not a guarantee against every profitable exchange or a universal difficulty setting.

#### 4. Prestige trading

- **Available** (default): prestige may be offered or requested from any eligible partner.
- **Same faith only**: both rulers must follow exactly the same faith. Belonging to the same broader religion is not enough.
- **Lower fame only**: prestige can move only from a ruler with a **strictly higher level of fame** to one with a lower level. Equal levels are excluded.
- **Peers and lesser only**: the giver's fame level may be equal to or higher than the receiver's.
- **Disabled**: prestige cannot be traded.

The directional rules compare **level of fame**, not stored prestige, title rank or who initiated negotiations. With fame levels 4 and 2, **Lower fame only** permits 4 → 2, but not 2 → 4. At equal levels, neither direction is allowed in strict mode; **Peers and lesser only** permits both. The giver must still have enough spendable prestige.

#### 5. Piety trading

- **Available** (default): piety may be offered or requested regardless of faith.
- **Same faith only**: both rulers must follow exactly the same faith; devotion levels do not restrict the direction.
- **Same faith: less devout**: both rulers must follow the same faith, and the giver's **level of devotion must be strictly higher** than the receiver's. Equal levels are excluded.
- **Different faiths only**: the rulers must follow different faiths, including different faiths within the same religion.
- **Same religion only**: the rulers must belong to the same broader religion, even if their faiths differ.
- **Disabled**: piety cannot be traded.

For example, Catholic and Orthodox rulers have different faiths within Christianity. They qualify under **Different faiths only** and **Same religion only**, but not **Same faith only**. A Catholic and an Ash'ari ruler qualify under **Different faiths only**, not **Same religion only**.

The strict-devotion option compares **level of devotion**, not the amount of piety in the treasury. A same-faith ruler at devotion level 4 can give to one at level 2, but cannot receive piety from them under that rule.

#### How currency restrictions affect a deal

Each direction's trading permission is checked separately; a prestige or piety row may be available on only one side, and unavailable rows disappear. **Auto-balance and AI proposals use the same restrictions**, including when pricing a counteroffer. Gold is unaffected by these two permission rules.

**New in 1.3.0: gold, prestige and piety can each have a positive amount on only one side of a treaty.** Selecting one direction locks the opposite direction's add buttons and amount presets. Reducing the selected amount to zero, choosing **None**, or clearing the draft restores the opposite direction when trading permission allows it. This safeguard also applies with Negotiation interests **Off**. Old drafts with both directions selected cannot be sent or settled; Auto-balance converts the opposing amounts into one net transfer before solving. Influence retains net valuation with both full transfers checked for permission and affordability.

The final agreement is checked again before execution. If a ruler's faith or fame/devotion level changes and a positive currency term is no longer permitted, an old draft cannot bypass the rule: revise or reopen the deal. Restrictions govern negotiated payments, not unrelated resource gains, costs or consequences such as the prestige loss for refusing a threat.

The prestige and piety rules are separate choices. For the faith-based exchange suggested by the community, choose **Prestige: Same faith only** and **Piety: Different faiths only**. Compliance does not mean the AI must include prestige or piety in every offer; a gold-only proposal is still valid.

#### 6. Threat strength

These labels adjust **how much pressure military superiority provides**, not a guaranteed schedule of incoming demands:

- **Weak**: coefficient 2.5; at equal fame and dread, the military-strength ratio needed is 41:1.
- **Normal** (default): coefficient 5; at equal fame and dread, the ratio needed is 21:1.
- **Strong**: coefficient 7.5; at equal fame and dread, the ratio needed is about 14.34:1.
- **Very strong**: coefficient 10; at equal fame and dread, the ratio needed is 11:1.

Every option requires **at least 100 threat points**, for both player and AI. Under **Normal**, a 2:1 military advantage at equal fame and dread gives only 5 points: it is not enough to threaten. The comparison uses maximum military strength, not just the troops currently raised. Higher fame and dread can lower the military advantage needed; being a full fame level below the target makes the threat worth zero regardless of army size.

The target must be an independent ruler, cannot be your ally, and neither ruler may hold a hostage from the other's home court. Other eligibility checks still apply. A completed treaty signed under threat causes a **-100 opinion modifier that decays over 15 years**; while that modifier remains, the same ruler cannot threaten that target again.

Threatening adds pressure to negotiations; it is not an automatic declaration of war. A large army does not guarantee a demand letter or the annexation of neighbors. This rule has no **Disabled** option; incoming demands can instead be silenced with the incoming-offer rule or the embassy decision below.

#### 7. Threat frequency

Choose **0 years** (default), **1 year**, **5 years** or **10 years** between uses. This is a **global cooldown on the ruler making the threat**, applying equally to the player and AI: changing targets cannot bypass it. It does not change the pressure calculation or stop ordinary diplomacy.

The cooldown starts when a treaty using a threat is concluded. An AI demand consumes its use when a valid demand is paid or refused; a stale, invalid demand does not. Merely ticking the threat box, auto-balancing or abandoning a draft does not start it. Successful AI-to-AI extortion and coerced fealty use the same cooldown. Already-open drafts and demand letters are checked again before execution.

**0 years** means no additional global cooldown, not unlimited threats against the same victim. The existing **15-year same-pair restriction**, incoming-letter limits and AI-to-AI bargain cooldown remain separate. A timed cooldown belongs to the individual character and survives saving/reloading or closing the table; it is not inherited by a successor.

#### 8. AI-to-AI treaties

- **Disabled**: stops the autonomous system for bargains between AI rulers. It does not stop you opening talks or receiving AI offers.
- **Occasional**: fewer opportunities for autonomous bargains.
- **Frequent** (default): more opportunities, still subject to eligible partners and workable terms.

This separate system can arrange payments, favors, artifacts, eligible land transfers, marriages and fealty. Overwhelming rulers can force submission when the threat conditions are met. Concluded world bargains impose a three-year per-ruler cooldown. You receive notices about relevant bargains involving a border neighbor, ally or current opponent.

Frequency changes opportunities, not a guaranteed number of treaties per year, and it does not make the AI's prices more generous. **Advanced terms** is not a universal switch for this system.

#### 9. Offers sent to you

- **Never**: stops unsolicited AI offers and demands. You can still initiate negotiations; AI-to-AI treaties retain their own setting.
- **Rare**: a three-year recipient quiet period after a visible letter; an individual proposer has a six-year attempt cooldown.
- **Normal**: a one-year recipient quiet period; a three-year proposer attempt cooldown.
- **Frequent** (default): a six-month recipient quiet period; a one-year proposer attempt cooldown.

These periods are limits, **not delivery deadlines**. A suitable proposer, meaningful package and eligible game state are still needed. A year without a letter is not, by itself, proof that the system is inactive.

Demand letters have an additional recipient lock: **20 years on Rare, 10 on Normal, 3 on Frequent**, plus the separate 15-year same-pair threat memory after a response. Ordinary offer frequency therefore does not imply repeated demands at the same rate.

During a campaign, **Receive No More Embassies** silences incoming treaty envoys; **Receive Embassies Again** reverses that choice. Neither prevents you from opening negotiations yourself.

#### Suggested combinations

- **Start with the defaults** for the full negotiating table, Standard interests and unrestricted prestige/piety trading permissions.
- **Earlier valuation:** negotiation interests **Off**, advanced term valuation **Classic**. The one-direction currency safeguard remains active.
- **Stronger needs-based bargaining:** negotiation interests **Strict**. Use **Mild** for a gentler adjustment; neither changes trading permissions.
- **Territory-sensitive expansion:** advanced term valuation **Scaled**. Large realms cost more; ordinary courtiers no longer all start at 10 points.
- **Less frequent extortion:** threat frequency **5 years** or **10 years**. A ruler must wait before threatening another target, even with overwhelming dread and military strength.
- **Faith-based exchange:** prestige **Same faith only**, piety **Different faiths only**.
- **Strict downward transfers:** prestige **Lower fame only**, piety **Same faith: less devout**.
- **You initiate diplomacy:** incoming offers **Never**. Disable AI-to-AI treaties separately only if you also want to stop autonomous world bargains.

These are suggested combinations of the existing rules, not additional built-in presets.
<!-- full-game-rules-guide:end -->

While acting for a puppet, the opener and marriage picker are hidden. Personal Rites set marriage defaults and lineality prices; native marriage eligibility still applies.

## Compatibility and load order

**Vanilla file replacements: none.** Overhaul changes to treaty mechanics may need compatibility work.

**Optional vanilla load order:**

1. Parley: The Negotiating Table
2. Marriage Calculation Assistant

**AGOT is unsupported on CK3 1.20.** Integration is disabled pending its update and checks. Both marriage assistants are optional, not general compatibility patches.

**Submods and companion mods:**

- [Marriage Calculation Assistant]({{MCA_STEAM_URL}}): marriage-candidate scores, breakdowns and sorting.
- [AGOT: Marriage Calculation Assistant]({{AGOT_MCA_GITHUB_URL}}): AGOT scoring for MCA; current compatibility is on hold.

Use one copy per mod; no other patches included.

## Saves and known limits

To remove: use **Fold Away the Negotiating Table** under **Mod Removal Decisions**, save, then disable Parley. Negotiation/AI state clears; completed marriages, payments and transfers persist. Close MCA's picker before saving or removing MCA.

Title transfers exclude fealty/independence; courtier/hostage overlap can invalidate a package.

With interests enabled, refused manual offers lack consequence previews; refusal and retry still work.

Captions identify older **CK3 1.19.0.6** captures. **Multiplayer and long campaigns remain unverified.**

## Feedback and support

Report versions, load order, UI scale, steps and a screenshot; try this family alone.

[Report an issue on GitHub]({{PARLEY_GITHUB_URL}}/issues)

Email: {{CONTACT_EMAIL}}

### [Want to support my work? Donate on Ko-fi 💛]({{DONATION_URL}})

## Find this mod elsewhere

- [Steam Workshop]({{PARLEY_STEAM_URL}})
- [Paradox Mods]({{PARLEY_PARADOX_URL}})
- [Nexus Mods]({{PARLEY_NEXUS_URL}})
- [GitHub]({{PARLEY_GITHUB_URL}})

## My other mods

### Standalone mods

- [Marriage Calculation Assistant](https://steamcommunity.com/sharedfiles/filedetails/?id=3811100163) — compare and sort marriage candidates.
- [Your Own Hegemony](https://steamcommunity.com/sharedfiles/filedetails/?id=3811201582) — found a custom hegemony.
- [Vassalization Extended](https://steamcommunity.com/sharedfiles/filedetails/?id=3813943691) — choose Forced Vassalization terms without a county limit.
- [Court Automation](https://steamcommunity.com/sharedfiles/filedetails/?id=3814028714) — automate court positions and recruit courtiers or knights.
- [Nomad Autorefill](https://steamcommunity.com/sharedfiles/filedetails/?id=3814793283) — automatically reinforce nomadic Men-at-Arms using herd or gold.
- [Tax Collection Automation](https://steamcommunity.com/sharedfiles/filedetails/?id=3815381275) — automatically assign tax collectors and optimize tax jurisdictions.
- [Council Assignment Automation](https://steamcommunity.com/sharedfiles/filedetails/?id=3815689627) — automate council appointments and optimize councillor assignments.

### Compatibility patches

- [[compatch] CAA + CA](https://steamcommunity.com/sharedfiles/filedetails/?id=3816373375) — use Council Assignment Automation and Council Autopilot together.
