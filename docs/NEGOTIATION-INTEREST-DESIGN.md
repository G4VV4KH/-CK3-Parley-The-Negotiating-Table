# Parley negotiation interest design

Implementation candidate, 8 October 2026. This feature gives each negotiating ruler a
purpose-sensitive valuation of receiving and surrendering each term. Native
personality, economic archetypes and budgets provide inputs; Parley owns the
conversion to treaty points and its explanation. The intended outcome is that
surplus prestige cannot automatically purchase another ruler's entire treasury.

Status: implemented in active DEV; source-bound functional native matrix passes
with scoped diagnostics review. Release acceptance remains separate.
Runtime prices, rule presets, UI explanations, commit guards and existing AI
routes are integrated. No version bump or external publication is implied.
The design goals below are distinguished from current coverage in the final
section; coefficients are not yet long-campaign balance measurements.

## Rule and compatibility

Use one independent rule, **Parley: Negotiation interests**, with four settings:
**Off / Mild / Standard / Strict**. Russian labels: **Заинтересованность в
переговорах — Выключено / Мягко / Обычно / Строго**. Avoid an additional enable
switch or a free-form numerical slider: four named presets are reproducible,
explainable and practical in CK3's existing rules screen.

The implemented new-campaign default is Standard. The policy resolves an absent
setting to Off, but whether the engine fills a missing old-save rule with the
new default remains a native migration gate; do not promise old-save Off until
that load is measured. Explicit Off dispatches to the existing evaluation and auto-balance paths,
without new interest restrictions or misleading 100% badges. It necessarily
retains the legacy economic weaknesses.

This rule does not unlock advanced terms, change Classic versus Scaled, change
currency-trading permissions, or replace threat strength/frequency. Do not
assume a version number until a release candidate is actually selected.

## Whose interest the window displays

The ordinary window answers whether the **partner** accepts. Under “You offer”,
the badge means the partner's interest in receiving. Under “They offer”, it
means the partner's willingness to surrender. The tooltip names the evaluator,
giver, receiver and selected object or amount. It is never an acceptance chance.

Both are computed independently: little desire for additional gold does not
mean willingness to surrender one's existing gold. Human decisions are not
overruled by a simulated personality preference. AI-to-AI voluntary negotiations
require both AI evaluations; incoming AI offers use the same evaluator for the
AI author, without forcing a human recipient to obey their character's score.

## Native inputs and ownership of reasons

The native inputs are available in the installed game under
`./game/`:

- `common/script_values/00_ai_values.txt`: personality axes and numeric budget
  uses, including `war_chest_gold` and `war_chest_gold_maximum`.
- `common/scripted_triggers/00_ai_value_triggers.txt`: warlike, cautious,
  economical, pious-builder and conqueror checks incorporating government,
  culture, faith, house and contract conditions.
- `common/scripted_effects/00_ai_budget_effects.txt`: budget priorities and
  contextual reactions; these are inputs and precedents, not effects to invoke
  during a read-only quote.
- `common/character_interactions/00_courtier_and_guest_interactions.txt`:
  examples of usefulness based on council vacancies and skills.

`ai_will_do` is an interaction sending probability and `ai_accept` concerns a
specific interaction. Neither is a universal exchange-price API. Activity
weights may reward fame/devotion gained by that activity; do not borrow those
benefits if Parley's actual resource transfer does not confer them. A reserve
shortfall is observable; a hidden, complete future AI war plan is not assumed.

Use a fixed motive ledger: practical use, personality/strategy, relationships
to this object, and offer volume/consequences. Emit each reason once. Existing
greed/rationality/boldness bargaining thresholds, de-jure bonuses, faith/culture
preferences, skills and kinship prices must be classified before adding new
weights. Preserve already-priced evidence in the base layer until an explicit
migration replaces it; do not silently price it again as interest. “Already
included in base price” belongs in the tooltip where needed.

| Terms | Interest-specific evidence | Interface explanation |
| --- | --- | --- |
| Gold | Actual income, budget shortfall, military maintenance, war and construction priorities; prospective income coupling is deferred | War reserve; money available beyond needs; loss of financial safety |
| Prestige | Real spending opportunities, government and military needs, saturation | Useful for army; no current use for this surplus |
| Piety | Real religious spending, faith context, zeal and saturation | Religious plans; demand already satisfied |
| Influence where available | Actual government-specific uses and existing permissions | Political spending need; unavailable outside eligible government |
| Counties and vassals | Domain/vassal capacity after settlement, strategic cohesion and actual gain/loss | Domain would be over limit; loss of useful vassal |
| Fealty and independence | Security, autonomy, lost power and changed obligations | Gains protection; gives up independence |
| Courtiers and hostages | Vacancies, marginal skill improvement, replacement cost, family/heir exposure | Fills council vacancy; heir placed at risk |
| Marriage and obligations | Concrete alliance, succession, family and contract consequences not already priced | Useful alliance; contract burden |
| Artifacts and promised hooks | Usability, equipped alternatives, religious/owner attachment and usable leverage | Can equip; duplicate; political leverage |
| Threats and called-in hooks | Keep existing pressure/cooldown/legality treatment | Pressure remains separately itemized, never discounted as an unwanted gift |

Never revive retired terms. “All aspects” includes explicit exclusions rather
than indiscriminately multiplying every signed value.

## Meaning of percentages and strength

For an ordinary positive base price B, receiving interest I discounts benefit:
`benefit = B * I`. Willingness to surrender W increases the required value:
`cost = B / W`. Both displayed percentages are **effective for this rule and
the complete selected amount**, not raw personality values. A higher percentage
is always more favorable to reaching agreement; the direction is named.

Use a smooth prototype strength transform for a raw normalized score x:

`f(x, s) = x / (s + (1 - s) * x)`

Mild s=0.5, Standard s=1, Strict s=2. Off bypasses the feature, rather than
passing s=0. This keeps zero receiving interest at zero in every enabled mode,
keeps 100% at 100%, and avoids Strict suddenly deleting all interests below a
threshold. For surrender costs, this doubles the extra cost in Strict compared
with Standard at the same raw W, before numerical safeguards.

Receiving I can equal zero. Do not divide by a zero surrender value. The draft
uses an explicit 1% numerical floor on effective W (maximum 100 times base cost),
shown in the breakdown if it binds. This is not an economic guarantee and must
be calibrated against CK3 fixed-point limits. A genuinely unavailable or illegal
term displays a reason and a dash, not a fabricated percentage. Economic
reluctance is not silently turned into a new hard legal prohibition.

The feature penalizes departures from fully useful terms; it does not inflate
incoming benefit above the existing base at 100%. Positive and negative motive
contributions move the interest score within this bounded range. Native AI axes
are not themselves percentages. Exact motive weights and thresholds remain to
be calibrated, separately from the preset transform.

## Quantities and whole-deal consistency

Price fungible resources over the interval from pre-deal stock to post-deal
stock, using nonnegative marginal values and useful-demand saturation. Do not
apply one final-stock coefficient to the whole amount. After saturation, more
of an unwanted resource contributes no benefit, even with positive relations.
Cost of surrendered gold rises as useful reserves are depleted.

For quantity bands, sum effective benefits and costs first, then derive badges:
`I_display = total_benefit / total_base` and
`W_display = total_base / total_cost`. Never arithmetically average surrender
percentages or use rounded badge values in settlement. At each motive stage,
recompute the aggregate and show the percentage-point difference from the
previous stage, in a fixed order. Thus tooltip +/- entries reconcile even when
the aggregation is nonlinear. They explain sequential adjustments, not
independent causal experiments.

Normalize identical resources to net transfers for scoring only, AFTER checking
each gross leg's existing directional permissions and affordability. Preserve
existing atomic settlement semantics and do not let netting legalize a forbidden
leg. Duplicate objects and family bundles retain their current guards.

Deferred whole-deal coupling: changing territory or a useful courtier can change prospective income, costs
and needs for other terms. Freeze one consistent hypothetical post-deal context
per draft revision and recalculate affected terms. Requirements include stable
results under row permutation, no inventory-only profit from split or reversed
trades, and bounded search. Independent per-resource curves alone do not prove
these properties when cross-resource context changes. That coupling is a native
gate, not an assumed solution. Retain a bounded fallback when monotonic search
cannot be demonstrated; never loop Auto-balance indefinitely.

## Acceptance and the central ledger

The current gain/loss/relationship/threshold/gift-floor/pressure logic is the
baseline. Let E0 be its unrounded result without interest and E1 the result
using interest-adjusted gain and loss through the same relationship/floor
function. Show `interest_penalty = E0 - E1`, not a separately approximated sum.
For ordinary positive terms and fixed clamped relation multiplier M:

`penalty = M * (G0 - G1) + (L1 - L0)`

Applying the receiving discount only after a positive opinion bonus would leave
valuable “friendship points” on completely unwanted prestige. Applying the same
relationship function to G1 prevents that leakage. Signed contract rights,
negative obligations and gift-floor paths require the exact before/after
calculation, not unconditional use of this simplified identity.

Keep these visible ledger concepts: base received/given points; relationship
and bargaining adjustments; **Interest penalty**; pressure; and final answer.
The interest line expands into discounted incoming benefit and increased
surrender cost, including the associated relationship change. Existing floor
correction stays explainable. Strictly positive acceptance remains required;
zero is not accepted. Keep rounding at the existing aggregate boundary and
expose exact decimals or a named rounding adjustment when integer rows do not
sum to the headline. Do not reuse display-rounded values in gameplay.

## Interface behavior

Place an independently hoverable percent badge beside the term name in the
existing 56-pixel row. Preserve the selected-object subtitle and amount controls.
Do not add a fixed column that squeezes the already narrow currency labels.
The tooltip contains: whose evaluation; direction; base propensity; named
positive/negative percentage-point adjustments; rule-strength adjustment;
numerical clamp if any; effective percentage; base and effective point cost.

For an unselected term show a dash and “Choose a term to calculate”; a quantity
preview, if later added, must explicitly name its preview amount. A multi-object
row shows its aggregate and links to per-object detail in the selector. Opposite
directions and differing family bundles never share a generic percentage.

Central deal rows show base and adjusted points through a consistent contract,
with the full calculation on hover. The compact figure area can fit one extra
interest row by reorganizing existing figures rather than making the central
scroll region shorter. Off hides badges and the interest row. Do not overload
red/green with acceptance probability; label receiving versus surrendering.

The illustrative interface in this task uses hypothetical point prices. It
demonstrates presets, hover explanations and ledger arithmetic, not final game
art, pixel-fit verification, native state extraction or live currency rates.

## Implementation sequence and acceptance gates

1. Inventory baseline contributors and define one unrounded per-term ledger.
   Preserve stresses derived from actual transfers rather than subjective
   interest. Add native read-only probes for profiles, budgets and quote inputs.
2. Implement the rule and pure evaluators for gold/prestige/piety first. Add
   percentage breakdowns and central penalty simultaneously, then route manual
   evaluation and Auto-balance through the same ledger. Do not publish this
   partial stage as covering every term.
3. Extend land, people, artifacts, hooks, marriage and obligations, with explicit
   no-double-counting ownership and post-deal dependencies. Keep pressure apart.
4. Connect incoming offers, AI-world voluntary deals and coercive paths. A
   credible threat can counter reluctance through existing pressure; it must
   never bypass physical availability, permissions or existing cooldowns.
5. Use isolated native fixtures and source-bound reports for Off exact parity,
   Classic/Scaled combinations, all presets/directions, role reversal, native
   archetypes/budgets, saturation, reserve depletion, money conservation,
   duplicate/netting rejection, split/reverse transactions, stale pending
   offers, reload and complete atomic settlement. AI must be enabled for AI
   paths. Recheck quotes on commit before mutation.
6. Verify every shipping locale, actual hover targets, narrow currency names,
   long tooltips, multi-select and marriage displays, empty-table zero, and
   central arithmetic. Measure large-realm and AI-world costs. Separate native
   correctness, visual acceptance, multiplayer and long-campaign balance.

No all-character heartbeat is planned. Quote snapshots are derived, invalidated
by draft/partner/state changes, and never trusted after reload or at settlement.
Avoid modifying AI budgets merely to price an offer. Native safe snapshot and
invalidation coverage must be established before introducing persistent caches.

## Integration map and evidence boundary

Active authoring: this repository (`.`),
resolved from `release-workflow.json`. Frozen public baseline is 1.2.2,
`2026-10-07-parley-1.2.2-rc1`; it is not the full current DEV snapshot. Existing
dirty edits are preserved. The registry's localization gate PASS applies only
to its recorded 1.2.2 payload, not to this proposed feature.

Primary seams beneath `mod/parley/`:

- `common/script_values/tnt_50_values.txt`: base totals, relations, threshold,
  floor and authoritative acceptance.
- `tnt_53_currency_values.txt` in that directory and
  `common/scripted_effects/tnt_39_autobalance.txt`: acceptance probing/search;
  acquisition bounds must be re-audited with nonlinear prices.
- `tnt_54_multiselect_values.txt`, `tnt_58_person_values.txt`,
  `tnt_52_marriage_values.txt`, `tnt_5e_display_values.txt`: currently differing
  raw versus globally adjusted row displays must be normalized.
- `tnt_5a_stress_values.txt`: preserve actual-transfer stress semantics.
- `gui/tnt_types.gui`: shared rows, native breakdown tooltip and center figures;
  `gui/tnt_diplomacy_window.gui`: actual directional bindings;
  `gui/tnt_panels.gui` and `gui/tnt_panel_multiselect.gui`: both deal-row families.
- `events/tnt_ai_events.txt` and `common/scripted_effects/tnt_37_ai_offer.txt`:
  AI proposal gates must share the revised quote semantics.

New feature native status: **PASS_WITH_SCOPED_DIAGNOSTICS_REVIEW** for the
four-preset functional matrix, 352 assertions, exact current 88-file runtime.
This is not a clean-log or release verdict. Visual CK3 status: **NOT_VERIFIED**.
Current work modifies the active DEV runtime only, never the frozen published
payload. New pure evaluators live in `tnt_60_interest_policy.txt`,
`tnt_61_interest_currency_values.txt`, `tnt_62_interest_advanced_values.txt`,
`tnt_63_interest_ledger_values.txt` and `tnt_64_interest_ai_values.txt`.

## Implemented behavior and remaining gates

- Four currencies use finite useful-demand bands and reserve-sensitive surrender
  costs. Production points integrate actual amounts before conversion; rounded
  display ratios never price large transfers. Fixed-context splitting telescopes;
  this is not a proof of arbitrary cross-resource no-arbitrage.
- Nine ordinary advanced families and nine signed obligation families have
  separate receiving/surrendering contextual evaluations. Existing intrinsic
  prices, legality and Classic/Scaled remain authoritative. Signed concessions
  preserve their direction. Advanced multi-object badges use aggregate contextual
  scores, not a per-object harmonic ledger or per-object interest drill-down.
- Threats and spent hooks remain pressure outside interest. Voluntary execution
  is repriced before mutation. Only the existing human Pay action on a coercive
  demand has a transient exemption from voluntary consent; physical preflight
  and cooldown checks still apply.
- Manual tables, incoming letters and Auto-balance share the central ledger.
  AI-world voluntarily trades only when both AI evaluations are positive, and
  rechecks its production helper at settlement. It shares native-informed
  interest curves but deliberately retains its existing additive relationship
  and threshold baseline, not the manual table's percentage-based baseline.
  This does not create new autonomous AI deal families.
- Currency hover separates percentage-point adjustments from the native useful
  stock target in resource units. Archetypes and native budget values are read
  as pricing inputs; no quote rewrites the engine's AI budgets.

Not implemented: hypothetical land/courtier income changes feeding currency
capacity, persistent quote caches, all-character polling, or guaranteed prevention
of every split/reversal exploit across changing contexts. The aggregate score is
recomputed from live state. Zero modifier products bypass expensive aggregate
evaluation without changing nonzero arithmetic or fixed-point operation order.

Acceptance boundaries: hidden native runs cannot establish pixel fit, actual
hover readability, multiplayer determinism or long-campaign balance. Synchronous
AI helper tests do not prove autonomous scheduler selection. Cached marriage
adapter tests do not prove full MCA selection/settlement. The master live-consent
guard currently suppresses consequence previews for already-refused manual
offers; refusal and retry remain available. A preview fix must not add a live
execution bypass.

Native evidence and the exact current-source verdict are recorded separately in
`docs/NEGOTIATION-INTEREST-VERIFICATION.md`; do not treat illustrative prototype
assertions or an obsolete smoke snapshot as release acceptance.
