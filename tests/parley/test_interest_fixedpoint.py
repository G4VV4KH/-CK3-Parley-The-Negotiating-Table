"""Conservative .001 arithmetic sensitivity tests over the production AST.

Every scalar operation truncates toward zero here. This is deliberately not a
claim about CK3's C++ implementation; root's native probe is the final authority.
It detects the catastrophic ratio-first loss independently of Decimal precision.
"""
from decimal import Decimal as D, ROUND_DOWN
import unittest

from test_interest_currency import CURRENCIES, InterestWorld, STRENGTHS
from test_interest_ai_world import AiWorld, LANES, walk


class Fixed(D):
    def __new__(cls, value=0):
        return super().__new__(cls, D(value).quantize(D("0.001"), rounding=ROUND_DOWN))

    def __add__(self, other): return Fixed(D(self) + D(other))
    def __sub__(self, other): return Fixed(D(self) - D(other))
    def __mul__(self, other): return Fixed(D(self) * D(other))
    def __truediv__(self, other): return Fixed(D(self) / D(other))
    def __radd__(self, other): return Fixed(D(other) + D(self))
    def __rsub__(self, other): return Fixed(D(other) - D(self))
    def __rmul__(self, other): return Fixed(D(other) * D(self))
    def __rtruediv__(self, other): return Fixed(D(other) / D(self))


class QuantizedMixin:
    def operand(self, atom, current):
        value = super().operand(atom, current)
        return Fixed(value) if isinstance(value, D) else value

    def numeric(self, nodes, current, initial=D(0)):
        return Fixed(super().numeric(nodes, current, Fixed(initial)))


class FixedTable(QuantizedMixin, InterestWorld):
    pass


class FixedAi(QuantizedMixin, AiWorld):
    pass


class InterestFixedPointTests(unittest.TestCase):
    def table(self, policy="standard"):
        world = FixedTable(policy)
        world.root.variables.update(tnt_infl_ok_p=D(1), tnt_infl_ok_r=D(1))
        return world

    def test_quantization_really_occurs_at_each_operation(self):
        world = self.table()
        world.defs["quantum_probe"] = [("value", "=", "1"), ("divide", "=", "3000"), ("multiply", "=", "3000")]
        self.assertEqual(world.value("quantum_probe"), 0)

    def test_large_offer_keeps_finite_demand_and_never_reprices_downward(self):
        for policy in STRENGTHS:
            for currency in CURRENCIES:
                world = self.table(policy)
                capacity = world.value(f"tnt_interest_{currency}_capacity_value")
                for side in ("p", "r"):
                    world.partner.stats[currency] = capacity / 2
                    points = []
                    amounts = [D("0.001"), D(1), capacity / 4, capacity, capacity * 2,
                               capacity * 1000, capacity * 100000]
                    for amount in amounts:
                        world.root.variables[f"tnt_{currency}_{side}"] = amount
                        points.append(world.value(f"tnt_interest_{currency}_{side}_net_adjusted_points_value"))
                    self.assertEqual(points, sorted(points), (policy, currency, side, points))
                    if side == "p":
                        self.assertEqual(points[-1], points[-2])
                        self.assertGreater(points[-1], 0)
                        # Old base*ratio would have erased this useful demand.
                        self.assertEqual(world.value(f"tnt_interest_{currency}_p_factor_value"), 0)
                    world.root.variables.pop(f"tnt_{currency}_{side}")

    def test_raw_currency_is_netted_before_any_point_conversion(self):
        for currency in CURRENCIES:
            world = self.table()
            for side, opposite in (("p", "r"), ("r", "p")):
                world.root.variables.update({f"tnt_{currency}_{side}": D("1000000.101"),
                                             f"tnt_{currency}_{opposite}": D(1000000)})
                net = [world.value(f"tnt_interest_{currency}_{side}_net_{mode}_points_value") for mode in ("base", "adjusted")]
                world.root.variables.update({f"tnt_{currency}_{side}": D("0.101"), f"tnt_{currency}_{opposite}": D(0)})
                direct = [world.value(f"tnt_interest_{currency}_{side}_net_{mode}_points_value") for mode in ("base", "adjusted")]
                self.assertEqual(net, direct)

    def test_existing_rates_and_traits_apply_once_and_off_keeps_gross(self):
        for currency in CURRENCIES:
            for traits in (set(), {"arrogant", "zealous", "ambitious"}, {"humble", "content"}):
                world = self.table()
                world.partner.stats["traits"] = traits
                for side in ("p", "r"):
                    world.root.variables[f"tnt_{currency}_{side}"] = D(90)
                    raw = world.value(f"tnt_val_{currency}_{side}_value")
                    self.assertEqual(world.value(f"tnt_interest_{currency}_{side}_net_base_points_value"), raw)
                    world.policy = "off"
                    world.root.variables[f"tnt_{currency}_{'r' if side == 'p' else 'p'}"] = D(90)
                    for mode in ("base", "adjusted"):
                        self.assertEqual(world.value(f"tnt_interest_{currency}_{side}_net_{mode}_points_value"), raw)
                    world.policy = "standard"
                    world.root.variables.pop(f"tnt_{currency}_{'r' if side == 'p' else 'p'}")
                    world.root.variables.pop(f"tnt_{currency}_{side}")

    def test_weighted_currency_splitting_has_only_quantum_residue(self):
        for policy in STRENGTHS:
            for currency in CURRENCIES:
                world = self.table(policy)
                capacity = world.value(f"tnt_interest_{currency}_capacity_value")
                for side, sign in (("p", 1), ("r", -1)):
                    stock, first, second = capacity * D("0.6"), capacity * D("0.7"), capacity * D("2.37")
                    def quote(balance, amount):
                        world.partner.stats[currency] = balance
                        world.root.variables[f"tnt_{currency}_{side}"] = amount
                        return world.value(f"tnt_interest_{currency}_{side}_weighted_amount_value")
                    whole = quote(stock, first + second)
                    split = quote(stock, first) + quote(stock + sign * first, second)
                    if side == "p": self.assertLessEqual(split, whole)
                    self.assertLessEqual(abs(split - whole), D("0.002"))
                    world.root.variables.pop(f"tnt_{currency}_{side}")

    def test_quantized_same_currency_roundtrip_has_no_inventory_profit(self):
        for policy in STRENGTHS:
            for currency in CURRENCIES:
                world = self.table(policy)
                for stock in (D(0), D("19.999"), D(150), D(100000)):
                    for amount in (D("0.001"), D("11.999"), D(500), D(1000000)):
                        world.partner.stats[currency] = stock
                        world.root.variables[f"tnt_{currency}_p"] = amount
                        receive = world.value(f"tnt_interest_{currency}_p_net_adjusted_points_value")
                        world.root.variables.pop(f"tnt_{currency}_p")
                        world.partner.stats[currency] = stock + amount
                        world.root.variables[f"tnt_{currency}_r"] = amount
                        surrender = world.value(f"tnt_interest_{currency}_r_net_adjusted_points_value")
                        world.root.variables.pop(f"tnt_{currency}_r")
                        self.assertLessEqual(receive, surrender, (policy, currency, stock, amount))

    def test_ai_and_table_weighted_amounts_match_with_quantized_operations(self):
        for policy in STRENGTHS:
            world, table = FixedAi(policy), self.table(policy)
            table.partner.stats.update(world.recipient.stats)
            for lane, amount_name in LANES.items():
                for stock in (D(-100), D(0), D(150), D(300), D(600)):
                    for amount in (D("0.001"), D("19.999"), D(300), D(10000000)):
                        world.recipient.stats.update(gold=stock, **{amount_name: amount})
                        table.partner.stats["gold"] = stock
                        for direction, side in (("receive", "p"), ("surrender", "r")):
                            table.root.variables[f"tnt_gold_{side}"] = amount
                            self.assertEqual(world.value(f"tnt_interest_ai_{lane}_gold_{direction}_weighted_amount_value", world.recipient),
                                             table.value(f"tnt_interest_gold_{side}_weighted_amount_value"))
                            table.root.variables.pop(f"tnt_gold_{side}")

    def test_production_ai_gold_scores_never_multiply_by_rounded_ratios(self):
        world = FixedAi()
        for lane in LANES:
            for party in ("actor", "recipient"):
                nodes = world.defs[f"tnt_interest_ai_{lane}_{party}_score_value"]
                for _, _, body in walk(nodes):
                    if isinstance(body, str):
                        self.assertNotIn(f"{lane}_gold_receive_factor_value", body)
                        self.assertNotIn(f"{lane}_gold_surrender_factor_value", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
