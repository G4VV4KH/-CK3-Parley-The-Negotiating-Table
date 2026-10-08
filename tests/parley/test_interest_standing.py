"""Production-AST parity and work-count tests for exact zero-product bypasses.

The baseline is reconstructed from the same shipped rows by removing only the
new zero guards. No algebraic regrouping or cached gameplay value is permitted.
Named evaluation counts measure script work, not native frame time.
"""
from copy import deepcopy
from decimal import Decimal as D
import random
import unittest

from test_autobalance import one
from test_interest_fixedpoint import Fixed
from test_interest_ledger import LedgerWorld


MODIFIERS = tuple(f"tnt_relmod_{name}_value" for name in
                  ("opinion", "faith", "culture", "kin", "relation", "war", "ally"))


class FixedLedger(LedgerWorld):
    """.001 truncation sensitivity, not an assertion about native C++ precision."""
    def value(self, item, current="p"):
        value = super().value(item, current)
        return Fixed(value) if isinstance(value, D) else value

    def numeric(self, nodes, current="p", acc=D(0)):
        return Fixed(super().numeric(nodes, current, Fixed(acc)))


def unguarded(world):
    world.defs = deepcopy(world.defs)  # World shares the parsed immutable cache.
    for kind in ("base", "adjusted"):
        name = f"tnt_interest_gain_{kind}_standing_value"
        body = []
        for row in world.defs[name]:
            if row[0] == "if":
                body.extend(node for node in row[2] if node[0] != "limit")
            else:
                body.append(row)
        world.defs[name] = body
    return world


class InterestStandingTests(unittest.TestCase):
    def test_every_original_nonzero_operation_and_order_is_preserved(self):
        world = LedgerWorld()
        for kind in ("base", "adjusted"):
            unit = f"tnt_interest_gain_{kind}_unit_value"
            actual = world.defs[f"tnt_interest_gain_{kind}_standing_value"]
            self.assertEqual(actual[0], ("value", "=", f"tnt_interest_gain_{kind}_value"))
            self.assertEqual(len(actual), 10)
            for row, field in zip(actual[1:9], (*MODIFIERS, "tnt_threshold_value")):
                self.assertEqual(row[0], "if")
                self.assertEqual(one(row[2], "limit"), [("NOT", "=", [(field, "=", "0")])])
                operation = "subtract" if field == "tnt_threshold_value" else "add"
                self.assertEqual([x for x in row[2] if x[0] != "limit"], [
                    (operation, "=", [("value", "=", field), ("multiply", "=", unit)])])
            floor = actual[9]
            self.assertEqual(one(floor[2], "limit"), [("tnt_deal_mod_sum_value", "<", "-100")])
            self.assertEqual(one(floor[2], "add"), [
                ("value", "=", "100"), ("add", "=", "tnt_deal_mod_sum_value"),
                ("multiply", "=", "-1"), ("min", "=", "0"), ("multiply", "=", unit)])

    def test_signed_obligations_floor_and_fractional_modifiers_are_exactly_equal(self):
        rng = random.Random(146072)
        for world_type in (LedgerWorld, FixedLedger):
            for policy in ("off", "mild", "standard", "strict"):
                for index in range(12):
                    live = world_type(policy, opinion=0, lumpy_p=100, lumpy_r=80)
                    old = unguarded(world_type(policy, opinion=0, lumpy_p=100, lumpy_r=80))
                    inputs = {field: (D(0) if index % 3 == 0 else D(rng.randrange(-200000, 100000)) / 1000)
                              for field in MODIFIERS}
                    inputs.update(tnt_threshold_value=D(rng.randrange(40000)) / 1000,
                                  tnt_val_ob_tax_value=D(rng.randrange(-180, 180)))
                    quantities = dict(tnt_gold_p=D(rng.randrange(1000)), tnt_gold_r=D(rng.randrange(1000)))
                    for world in (live, old):
                        world.leaves.update(inputs)
                        world.leaves["tnt_interest_ob_tax_p_factor_value"] = D("0.6")
                        world.leaves["tnt_interest_ob_tax_r_factor_value"] = D("2.5")
                        world.vars.update(quantities)
                    for value in ("tnt_interest_gain_base_standing_value", "tnt_interest_gain_adjusted_standing_value",
                                  "tnt_interest_penalty_value", "tnt_ai_accept_value"):
                        self.assertEqual(live.value(value), old.value(value), (world_type, policy, index, value))

    def test_zero_rows_avoid_aggregate_recomputation_without_caching(self):
        for opinion, expected_base, expected_adjusted in ((0, 11, 1), (55, 12, 2), (-200, 13, 3)):
            live = LedgerWorld(opinion=opinion, threshold=0, lumpy_p=100, lumpy_r=80)
            old = unguarded(LedgerWorld(opinion=opinion, threshold=0, lumpy_p=100, lumpy_r=80))
            for world in (live, old):
                world.vars["tnt_gold_p"] = D(500)
            self.assertEqual(live.value("tnt_ai_accept_value"), old.value("tnt_ai_accept_value"))
            self.assertEqual(live.value_evaluations["tnt_interest_gain_base_value"], expected_base)
            self.assertEqual(live.value_evaluations["tnt_interest_gain_adjusted_value"], expected_adjusted)
            self.assertEqual(old.value_evaluations["tnt_interest_gain_base_value"], 20)
            self.assertEqual(old.value_evaluations["tnt_interest_gain_adjusted_value"], 10)
            self.assertLess(sum(live.value_evaluations.values()), sum(old.value_evaluations.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
