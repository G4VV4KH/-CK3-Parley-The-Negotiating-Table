"""Execute production currency-interest AST against explicit native input facts.

This verifies the actual shipped piecewise arithmetic, netting, policies, scope
direction and tooltip totals. Native archetype/budget values remain fixture facts;
CK3 engine execution, cross-resource context and GUI behavior are separate gates.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
import random
import unittest

from test_autobalance import DEFAULT_SOURCE, parse
from test_scaled_valuation import D, Scope, Unsupported, ValuationWorld

SOURCE = DEFAULT_SOURCE
CURRENCIES = ("gold", "prestige", "piety", "influence")
STRENGTHS = {"mild": D("0.5"), "standard": D(1), "strict": D(2)}


class InterestWorld(ValuationWorld):
    NATIVE_PREDICATES = {
        "has_treasury", "is_at_war", "is_landed",
        "ai_has_warlike_personality", "ai_has_cautious_personality",
        "ai_has_conqueror_personality", "ai_has_economical_boom_personality",
        "ai_has_pious_builder_personality", "ai_should_focus_on_building_in_their_capital",
        "can_use_conquest_cbs_trigger",
    }

    def __init__(self, policy="standard"):
        super().__init__(source=SOURCE)
        self.policy = policy
        self.root = character("owner")
        self.partner = character("partner")
        self.root.variables["tnt_partner"] = self.partner
        self.scopes["tnt_me"] = self.root

    def condition(self, nodes, current):
        translated = []
        for key, op, body in nodes:
            if key == "has_game_rule":
                result = self.policy is not None and body == f"tnt_interests_{self.policy}"
            elif key == "government_has_flag":
                result = body in current.stats.get("government_flags", set())
            elif key == "has_doctrine_parameter":
                result = body in current.stats.get("doctrine_parameters", set())
            elif key == "has_perk":
                result = body in current.stats.get("perks", set())
            elif key == "has_trait":
                result = body in current.stats.get("traits", set())
            elif key in self.NATIVE_PREDICATES:
                result = bool(current.stats.get(key, False)) == (body == "yes")
            else:
                translated.append((key, op, body))
                continue
            translated.append(("always", "=", "yes" if result else "no"))
        return super().condition(translated, current)

    def numeric(self, nodes, current, initial=D(0)):
        # Descriptions annotate UI rows and never participate in arithmetic.
        return super().numeric([row for row in nodes if row[0] != "desc"], current, initial)

    def quote(self, currency, side, stock, amount, opposite=0):
        self.partner.stats[currency] = D(stock)
        self.root.variables[f"tnt_{currency}_{side}"] = D(amount)
        self.root.variables[f"tnt_{currency}_{'r' if side == 'p' else 'p'}"] = D(opposite)
        return self.value(f"tnt_interest_{currency}_{side}_factor_value")


def character(name):
    stats = {currency: D(0) for currency in CURRENCIES}
    stats.update({
        "yearly_character_income": D(0), "war_chest_gold_maximum": D(0),
        "reserved_gold_maximum": D(0), "monthly_character_expenses": D(0),
        "monthly_character_men_at_arms_expense_prestige": D(0),
        "highest_held_title_tier": D(3),
        "government_flags": {"government_has_influence"},
        "perks": set(),
    })
    return Scope(name, stats=stats, links={"faith": Scope("faith", "faith", stats={"doctrine_parameters": set()})})


def benefit_potential(stock, capacity, strength):
    return min(stock, capacity) + min(max(stock - capacity, D(0)), capacity) / (1 + strength)


def cost_potential(stock, capacity, strength):
    return stock + strength * min(stock, capacity) + 2 * strength * min(stock, capacity / 4)


class InterestCurrencyTests(unittest.TestCase):
    def assert_decimal_close(self, first, second):
        self.assertLessEqual(abs(first - second), D("0.00000000000000000001"), (first, second))

    def test_policy_absent_and_off_are_exact_neutral_without_native_inputs(self):
        for policy in (None, "off"):
            world = InterestWorld(policy)
            world.root = Scope("empty_owner")
            self.assertEqual(world.value("tnt_interests_enabled_value"), 0)
            self.assertEqual(world.value("tnt_interest_strength_value"), 0)
            for currency in CURRENCIES:
                for side in ("p", "r"):
                    self.assertEqual(world.value(f"tnt_interest_{currency}_{side}_factor_value"), 1)
                    self.assertEqual(world.value(f"tnt_interest_{currency}_{side}_percent_value"), 100)

    def test_native_capacity_facts_have_correct_resource_scope(self):
        world = InterestWorld()
        native = world.partner
        native.stats.update(yearly_character_income=D(120), war_chest_gold_maximum=D(200),
                            reserved_gold_maximum=D(50), monthly_character_expenses=D(10))
        gold = lambda: world.value("tnt_interest_gold_native_capacity_value", native)
        self.assertEqual(gold(), 590)
        native.stats["ai_has_cautious_personality"] = True
        self.assertEqual(gold(), 790)
        native.stats["is_at_war"] = True
        self.assertEqual(gold(), 910)
        native.stats["ai_has_economical_boom_personality"] = True
        self.assertEqual(gold(), 1030)
        native.stats["has_treasury"] = True
        self.assertEqual(gold(), 460)  # Treasury-funded state reserve is not personal gold demand.
        native.stats["yearly_character_income"] = D(100000000)
        self.assertLessEqual(gold(), 100000)

        native.stats.update(monthly_character_men_at_arms_expense_prestige=D(10),
                            can_use_conquest_cbs_trigger=True, ai_has_conqueror_personality=True)
        native.stats["government_flags"].add("government_is_tribal")
        self.assertEqual(world.value("tnt_interest_prestige_native_capacity_value", native), 2790)
        native.stats["is_landed"] = True
        self.assertEqual(world.value("tnt_interest_piety_native_capacity_value", native), 750)
        native.stats["perks"].add("sanctioned_loopholes_perk")
        self.assertEqual(world.value("tnt_interest_piety_native_capacity_value", native), 1250)
        native.links["faith"].stats["doctrine_parameters"].add("holy_wars_forbidden")
        self.assertEqual(world.value("tnt_interest_piety_native_capacity_value", native), 750)
        self.assertEqual(world.value("tnt_interest_influence_native_capacity_value", native), 400)

    def test_actual_ast_matches_continuous_potential_differences(self):
        for policy, strength in STRENGTHS.items():
            world = InterestWorld(policy)
            self.assertEqual(world.value("tnt_interest_strength_value"), strength)
            for currency in CURRENCIES:
                capacity = world.value(f"tnt_interest_{currency}_native_capacity_value", world.partner)
                for stock in (-capacity, D(0), capacity / 4, capacity / 2, capacity, capacity * 2, capacity * 100):
                    for amount in (D("0.001"), D("0.5"), D(1), capacity / 3, capacity, capacity * 3, capacity * 1000):
                        receive = world.quote(currency, "p", stock, amount)
                        expected = (benefit_potential(stock + amount, capacity, strength)
                                    - benefit_potential(stock, capacity, strength)) / amount
                        self.assert_decimal_close(receive, expected)
                        surrender = world.quote(currency, "r", stock, amount)
                        expected = (cost_potential(stock, capacity, strength)
                                    - cost_potential(stock - amount, capacity, strength)) / amount
                        self.assert_decimal_close(surrender, expected)
                        self.assertTrue(0 <= receive <= 1)
                        self.assertTrue(1 <= surrender <= 7)

    def test_saturation_and_reserve_costs_are_distinct(self):
        world = InterestWorld()
        for currency in CURRENCIES:
            capacity = world.value(f"tnt_interest_{currency}_native_capacity_value", world.partner)
            self.assertEqual(world.quote(currency, "p", capacity * 2, 100), 0)
            self.assertEqual(world.quote(currency, "r", capacity * 3, 100), 1)
            self.assertEqual(world.quote(currency, "p", 0, capacity), 1)
            self.assertEqual(world.quote(currency, "r", capacity / 4, capacity / 4), 4)

    def test_net_scoring_does_not_value_reciprocal_gross_legs(self):
        world = InterestWorld()
        for currency in CURRENCIES:
            for side in ("p", "r"):
                direct = world.quote(currency, side, 150, 125)
                net = world.quote(currency, side, 150, 10125, opposite=10000)
                self.assertEqual(direct, net)
                world.quote(currency, side, 150, 10000, opposite=10000)
                self.assertEqual(world.value(f"tnt_interest_{currency}_{side}_amount_value"), 0)
                self.assertEqual(world.value(f"tnt_interest_{currency}_{side}_factor_value"), 1)

    def test_splitting_same_context_cannot_improve_either_direction(self):
        randomizer = random.Random(9128)
        for policy in STRENGTHS:
            world = InterestWorld(policy)
            for currency in CURRENCIES:
                capacity = world.value(f"tnt_interest_{currency}_native_capacity_value", world.partner)
                for _ in range(30):
                    stock = D(randomizer.randrange(-500, 4000))
                    first, second = D(randomizer.randrange(1, 4000)), D(randomizer.randrange(1, 4000))
                    for side, sign in (("p", 1), ("r", -1)):
                        whole = (first + second) * world.quote(currency, side, stock, first + second)
                        split = first * world.quote(currency, side, stock, first)
                        split += second * world.quote(currency, side, stock + sign * first, second)
                        self.assert_decimal_close(whole, split)
                    self.assertEqual(capacity, world.value(f"tnt_interest_{currency}_native_capacity_value", world.partner))

    def test_same_resource_roundtrip_never_produces_subjective_profit(self):
        for policy in STRENGTHS:
            world = InterestWorld(policy)
            for currency in CURRENCIES:
                for stock in (D(0), D(100), D(500), D(10000)):
                    for amount in (D(1), D(250), D(1000)):
                        received = amount * world.quote(currency, "p", stock, amount)
                        surrendered = amount * world.quote(currency, "r", stock + amount, amount)
                        self.assertLessEqual(received, surrendered)

    def test_tooltip_percent_reconciles_and_higher_strength_never_helps(self):
        for currency in CURRENCIES:
            for side in ("p", "r"):
                percentages = []
                for policy in ("mild", "standard", "strict"):
                    world = InterestWorld(policy)
                    capacity = world.value(f"tnt_interest_{currency}_native_capacity_value", world.partner)
                    factor = world.quote(currency, side, capacity, capacity * 2)
                    percent = world.value(f"tnt_interest_{currency}_{side}_percent_value")
                    self.assert_decimal_close(percent, factor * 100 if side == "p" else 100 / factor)
                    percentages.append(percent)
                self.assertGreaterEqual(percentages[0], percentages[1])
                self.assertGreaterEqual(percentages[1], percentages[2])

    def test_partner_is_always_evaluator_and_scope_alias_cannot_override_it(self):
        world = InterestWorld()
        world.root.stats["prestige"] = D(0)
        world.partner.stats["prestige"] = D(10000)
        world.root.variables["tnt_prestige_p"] = D(100)
        world.scopes["tnt_p"] = world.root  # A stale alias from another call must not leak.
        self.assertEqual(world.value("tnt_interest_prestige_p_factor_value"), 0)
        world.root.variables["tnt_prestige_r"] = D(200)
        self.assertEqual(world.value("tnt_interest_prestige_r_factor_value"), 1)

    def test_influence_requires_both_actual_governments(self):
        world = InterestWorld()
        self.assertEqual(world.quote("influence", "p", 100000, 100), 0)
        for party in (world.root, world.partner):
            party.stats["government_flags"].remove("government_has_influence")
            self.assertEqual(world.quote("influence", "p", 100000, 100), 1)
            self.assertEqual(world.quote("influence", "r", 1, 100), 1)
            party.stats["government_flags"].add("government_has_influence")

    def test_values_have_no_persistent_mutations_or_duplicate_trait_prices(self):
        forbidden = {"set_variable", "change_variable", "add_character_flag", "random",
                     "move_budget_gold", "move_budget_treasury", "add_gold", "add_prestige",
                     "add_piety", "change_influence", "ai_greed", "ai_rationality", "ai_boldness"}
        def keys(nodes):
            for key, _, body in nodes:
                yield key
                if isinstance(body, list):
                    yield from keys(body)
        for filename in ("tnt_60_interest_policy.txt", "tnt_61_interest_currency_values.txt"):
            ast = parse((SOURCE / "common/script_values" / filename).read_text(encoding="utf-8-sig"))
            self.assertFalse(forbidden.intersection(keys(ast)))
            for name, _, body in ast:
                # Trait prices are owned only by the one final conversion, not
                # by the capacity or usefulness layer a second time.
                if not name.endswith(("_net_base_points_value", "_net_adjusted_points_value")):
                    self.assertNotIn("has_trait", set(keys(body)), name)
        world = InterestWorld()
        before = deepcopy(world.root.variables)
        for currency in CURRENCIES:
            world.value(f"tnt_interest_{currency}_p_percent_value")
            world.value(f"tnt_interest_{currency}_r_percent_value")
        self.assertEqual(set(before), set(world.root.variables))
        world.defs["bad"] = [("unsupported_command", "=", "yes")]
        with self.assertRaises(Unsupported):
            world.value("bad")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args, remaining = parser.parse_known_args()
    SOURCE = args.source.resolve()
    unittest.main(argv=[__file__, *remaining], verbosity=2)
