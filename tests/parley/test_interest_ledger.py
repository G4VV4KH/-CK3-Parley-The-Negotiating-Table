"""Execute production interest ledger and auto-balance against explicit inputs.

Currency interval arithmetic and authoritative acceptance are real AST. Advanced
term intrinsic prices/context factors are controlled leaves here and have their
own production-AST tests. This is not native CK3 acceptance.
"""
from decimal import Decimal as D, ROUND_HALF_UP
import random
import unittest

from test_autobalance import DEFAULT_SOURCE, World

CURRENCIES = ("gold", "prestige", "piety", "influence")
TERMS = ("title", "subject", "courtier", "artifact", "vassal", "indep", "hostage", "hook", "marriage")
OBS = ("tax", "levy", "fort", "coin", "relig", "council", "revoke", "war", "succ")


class LedgerWorld(World):
    def __init__(self, policy="standard", **kwargs):
        kwargs.setdefault("lumpy_r", 0)
        super().__init__(DEFAULT_SOURCE, **kwargs)
        if policy:
            self.game_rules.add("tnt_interests_" + policy)
        for currency in CURRENCIES:
            self.leaves[f"tnt_interest_{currency}_native_capacity_value"] = D(100)
            # The character-scoped stock helpers use actual fixture wallets.
        for term in TERMS:
            for side in ("p", "r"):
                self.leaves[f"tnt_interest_{term}_{side}_factor_value"] = D(1)
        for term in OBS:
            for side in ("p", "r"):
                self.leaves[f"tnt_interest_ob_{term}_{side}_factor_value"] = D(1)

    def scope(self, token, current="p"):
        if token == "this":
            return current
        return super().scope(token, current)

    def adjusted_oracle(self):
        gain = self.value("tnt_interest_gain_adjusted_value")
        loss = self.value("tnt_interest_loss_adjusted_value")
        multiplier = max(D(0), 1 + self.value("tnt_deal_mod_sum_value") / 100)
        return ((gain * multiplier if gain > 0 else gain) - loss
                + self.value("tnt_val_threat_p_value")
                + self.value("tnt_val_usehook_p_value")
                + self.value("tnt_val_usehook_r_value")).to_integral_value(rounding=ROUND_HALF_UP)


class InterestLedgerTests(unittest.TestCase):
    def test_off_and_missing_preserve_legacy_score_and_gross_quotes(self):
        for policy in (None, "off"):
            world = LedgerWorld(policy, opinion=55, lumpy_p=81, lumpy_r=40)
            world.vars.update(tnt_gold_p=D(90), tnt_gold_r=D(90))
            self.assertEqual(world.value("tnt_interest_penalty_value"), 0)
            self.assertEqual(world.value("tnt_interest_quote_gain_value"), world.value("tnt_gain_total_value"))
            self.assertEqual(world.value("tnt_interest_quote_loss_value"), world.value("tnt_loss_total_value"))
            self.assertEqual(world.value("tnt_ai_accept_value"), world.independent_score())

    def test_empty_and_opposing_currency_cannot_manufacture_relationship_points(self):
        for policy in ("mild", "standard", "strict"):
            for currency in CURRENCIES:
                world = LedgerWorld(policy, opinion=125, influence=True)
                self.assertEqual(world.value("tnt_ai_accept_value"), 0)
                world.vars.update({f"tnt_{currency}_p": D(999), f"tnt_{currency}_r": D(999)})
                self.assertEqual(world.value("tnt_interest_quote_gain_value"), 0)
                self.assertEqual(world.value("tnt_interest_quote_loss_value"), 0)
                self.assertEqual(world.value("tnt_interest_penalty_value"), 0)
                self.assertEqual(world.value("tnt_ai_accept_value"), 0)

    def test_netting_does_not_mutate_the_physical_package(self):
        world = LedgerWorld(opinion=0)
        world.vars.update(tnt_gold_p=D(310), tnt_gold_r=D(300))
        before = dict(world.vars)
        base = world.value("tnt_interest_quote_gain_value")
        score = world.value("tnt_ai_accept_value")
        self.assertEqual(world.vars, before)
        self.assertGreater(world.value("tnt_gain_total_value"), base)
        del world.vars["tnt_gold_r"]
        world.vars["tnt_gold_p"] = D(10)
        self.assertEqual(world.value("tnt_ai_accept_value"), score)

    def test_signed_obligations_and_standing_floor_reconcile(self):
        for opinion in (-200, -100, -50, 0, 125):
            for obligation in (-150, -50, 0, 50, 150):
                world = LedgerWorld(opinion=opinion, threshold=4, lumpy_p=100)
                world.leaves["tnt_val_ob_tax_value"] = D(obligation)
                world.leaves["tnt_interest_ob_tax_p_factor_value"] = D("0.5")
                world.leaves["tnt_interest_ob_tax_r_factor_value"] = D(3)
                world.leaves["tnt_interest_vassal_p_factor_value"] = D("0.4")
                self.assertGreaterEqual(world.value("tnt_interest_penalty_value"), 0)
                self.assertEqual(world.value("tnt_ai_accept_value"), world.adjusted_oracle())

    def test_each_advanced_family_is_priced_once_in_each_direction(self):
        for term in TERMS:
            for side in ("p", "r"):
                world = LedgerWorld(opinion=0, threshold=0)
                multi = "_multi" if term in ("title", "artifact", "subject", "courtier") else ""
                world.leaves[f"tnt_val_{term}{multi}_{side}_value"] = D(100)
                world.leaves[f"tnt_interest_{term}_{side}_factor_value"] = D("0.5" if side == "p" else "2")
                self.assertEqual(world.value("tnt_ai_accept_value"), D(50 if side == "p" else -200), (term, side))

    def test_threat_and_spent_hook_pressure_do_not_receive_interest_factor(self):
        for policy in (None, "off", "mild", "standard", "strict"):
            world = LedgerWorld(policy, opinion=-200, lumpy_p=100, lumpy_r=20)
            before = world.value("tnt_ai_accept_value")
            world.leaves.update(tnt_val_threat_p_value=D(312), tnt_val_usehook_p_value=D(45), tnt_val_usehook_r_value=D(-120))
            self.assertEqual(world.value("tnt_ai_accept_value") - before, 237)

    def test_saturated_prestige_cannot_buy_a_low_gold_reserve(self):
        world = LedgerWorld(opinion=0, threshold=0, player=(0, 10000, 0, 0), partner=(100, 2000, 0, 0))
        world.stats["r"]["prestige"] = D(2000)
        world.vars.update(tnt_prestige_p=D(10000), tnt_gold_r=D(100))
        self.assertEqual(world.value("tnt_interest_prestige_p_factor_value"), 0)
        self.assertGreater(world.value("tnt_interest_gold_r_factor_value"), 1)
        self.assertLess(world.value("tnt_ai_accept_value"), 0)

    def test_randomized_conservation_and_stricter_policy_never_improves_same_quote(self):
        rng = random.Random(87123)
        for _ in range(60):
            scores = []
            quantities = {f"tnt_{c}_{s}": D(rng.randrange(1500)) for c in CURRENCIES for s in ("p", "r")}
            opinion = rng.randrange(-200, 126)
            for policy in ("mild", "standard", "strict"):
                world = LedgerWorld(policy, opinion=opinion, influence=True)
                world.vars.update(quantities)
                self.assertEqual(world.value("tnt_ai_accept_value"), world.adjusted_oracle())
                scores.append(world.value("tnt_ai_accept_value"))
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_autobalance_uses_live_nonlinear_score(self):
        for policy in ("mild", "standard", "strict"):
            world = LedgerWorld(policy, opinion=0, threshold=0, lumpy_r=8, player=(1000, 0, 0, 0), partner=(0, 0, 0, 0),
                                prestige=False, piety=False, influence=False)
            world.effect("tnt_autobalance_effect", {"MARGIN": "1", "CEILING": "1"})
            self.assertEqual(world.value("tnt_ai_accept_value"), 1)
            self.assertGreater(world.vars["tnt_gold_p"], 0)
            self.assertLessEqual(world.vars["tnt_gold_p"], 800)


if __name__ == "__main__":
    unittest.main(verbosity=2)
