"""Execute production currency locks and solver ASTs, not a CK3 certification.

Native GUI execution, actual resource conservation and rendering are verified by
the separate isolated native gate. Commit tests below inspect routing and execute
the extracted pure package guard; they do not simulate the native executor.
"""
from copy import deepcopy
from itertools import product
import unittest

from test_autobalance import DEFAULT_SOURCE, D, World, one, parse
from test_currency_trade_rules import definitions, walk
from currency_exclusivity_baseline import without_currency_exclusivity


CUR = ("gold", "prestige", "piety")
SIDES = ("p", "r")
ADDITIONS = ("add", "add_big", "add_huge", "std", "half", "max")
REDUCTIONS = ("sub", "sub_big", "sub_huge", "none")
POLICIES = ("off", "mild", "standard", "strict")


class ExclusivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guis = {}
        for file in ("tnt_20_scripted_guis.txt", "tnt_22_v2.txt"):
            cls.guis.update(definitions(DEFAULT_SOURCE, "common/scripted_guis/" + file))
        cls.gates = definitions(DEFAULT_SOURCE, "common/scripted_triggers/tnt_41_gates.txt")

    def world(self, policy="off", **kwargs):
        defaults = dict(player=(5000, 5000, 5000, 5000), partner=(5000, 5000, 5000, 5000),
                        traits=(), opinion=0, lumpy_p=0, lumpy_r=0)
        defaults.update(kwargs)
        world = World(**defaults)
        # Native income is an explicit fixture input for the gold standard preset.
        for side in SIDES:
            world.stats[side]["yearly_character_income"] = D(120)
        world.defs = {**world.defs, **self.gates}
        world.game_rules.add("tnt_interests_" + policy)
        return world

    def exclusive(self, world):
        return world.scripted_trigger("tnt_currencies_exclusive_trigger")

    def execute(self, world, currency, side, action):
        world.effect_block(one(self.guis[f"tnt_{currency}_{side}_{action}"], "effect"))

    def test_all_36_additions_lock_at_validation_and_callback_time(self):
        for currency, side, action, policy in product(CUR, SIDES, ADDITIONS, POLICIES):
            world = self.world(policy)
            other = "r" if side == "p" else "p"
            world.vars[f"tnt_{currency}_{other}"] = D("0.001")
            gui = self.guis[f"tnt_{currency}_{side}_{action}"]
            with self.subTest(currency=currency, side=side, action=action, policy=policy):
                self.assertFalse(world.trigger(one(gui, "is_valid")))
                # Direct Execute is intentionally tested without consulting IsValid.
                before = dict(world.vars)
                world.effect_block(one(gui, "effect"))
                self.assertEqual(world.vars, before)
                # An already-malformed legacy row cannot grow either.
                world.vars[f"tnt_{currency}_{side}"] = D(200)
                before = dict(world.vars)
                world.effect_block(one(gui, "effect"))
                self.assertEqual(world.vars, before)

    def test_zero_or_absent_opposite_and_other_currency_do_not_lock(self):
        for currency, side, action, absent in product(CUR, SIDES, ADDITIONS, (False, True)):
            world = self.world()
            other = "r" if side == "p" else "p"
            if not absent:
                world.vars[f"tnt_{currency}_{other}"] = D(0)
            for other_currency in set(CUR) - {currency}:
                world.vars[f"tnt_{other_currency}_{other}"] = D(100)
            gui = self.guis[f"tnt_{currency}_{side}_{action}"]
            with self.subTest(currency=currency, side=side, action=action, absent=absent):
                self.assertTrue(world.trigger(one(gui, "is_valid")))
                world.effect_block(one(gui, "effect"))
                self.assertGreater(world.vars[f"tnt_{currency}_{side}"], 0)
                self.assertTrue(self.exclusive(world))

    def test_all_24_reductions_and_clears_repair_conflict_then_unlock(self):
        for currency, side, action, policy in product(CUR, SIDES, REDUCTIONS, POLICIES):
            world = self.world(policy)
            other = "r" if side == "p" else "p"
            world.vars[f"tnt_{currency}_{side}"] = D(10)
            world.vars[f"tnt_{currency}_{other}"] = D(100)
            gui = self.guis[f"tnt_{currency}_{side}_{action}"]
            with self.subTest(currency=currency, side=side, action=action, policy=policy):
                self.assertTrue(world.trigger(one(gui, "is_valid", [])))
                world.effect_block(one(gui, "effect"))
                self.assertEqual(world.vars.get(f"tnt_{currency}_{side}", 0), 0)
                self.assertTrue(self.exclusive(world))
                self.assertTrue(world.trigger(one(self.guis[f"tnt_{currency}_{other}_add"], "is_valid")))
                self.execute(world, currency, other, "add")
                self.assertEqual(world.vars[f"tnt_{currency}_{other}"], 110)

    def test_generic_helpers_cannot_bypass_but_signed_negative_steps_work(self):
        for currency, side in product(CUR, SIDES):
            world = self.world()
            other = "r" if side == "p" else "p"
            variable = f"tnt_{currency}_{side}"
            world.vars[variable] = D(100)
            world.vars[f"tnt_{currency}_{other}"] = D(200)
            for kind, extra in (("step", {"DELTA": 500}), ("set", {"AMOUNT": 500}),
                                ("frac", {"MULT": "0.5"})):
                world.effect(f"tnt_cur_{kind}_{side}_effect", {"VAR": variable, "FIELD": currency, **extra})
                self.assertEqual(world.vars[variable], 100)
            world.effect(f"tnt_cur_step_{side}_effect", {"VAR": variable, "FIELD": currency, "DELTA": -100})
            self.assertEqual(world.vars[variable], 0)
            self.assertTrue(self.exclusive(world))

    def test_package_guard_is_unconditional_and_influence_is_out_of_scope(self):
        preflight = definitions(DEFAULT_SOURCE, "common/scripted_triggers/tnt_43_preflight.txt")["tnt_deal_preflight_trigger"]
        players = [body for key, _, body in one(preflight, "trigger_if") if key == "$PLAYER$"]
        guard = ("tnt_currencies_exclusive_trigger", "=", "yes")
        self.assertEqual(sum(guard in body for body in players), 1)
        send = one(self.guis["tnt_send_offer"], "is_valid")
        self.assertEqual(sum(guard in body for key, _, body in send if key == "custom_tooltip"), 1)
        for currency, policy, p, r in product(CUR, POLICIES, (None, 0, "0.001", 50), (None, 0, "0.001", 50)):
            world = self.world(policy)
            for side, amount in (("p", p), ("r", r)):
                if amount is not None:
                    world.vars[f"tnt_{currency}_{side}"] = D(amount)
            world.vars.update(tnt_influence_p=D(200), tnt_influence_r=D(200))
            expected = not (p is not None and D(p) > 0 and r is not None and D(r) > 0)
            self.assertEqual(world.trigger([guard]), expected)
        world = self.world(influence=True)
        world.vars.update(tnt_influence_p=D(100), tnt_influence_r=D(100))
        self.assertTrue(self.exclusive(world))
        for side in SIDES:
            gui = self.guis[f"tnt_influence_{side}_add"]
            self.assertTrue(world.trigger(one(gui, "is_valid", [])))
            world.effect_block(one(gui, "effect"))
            self.assertGreater(world.vars[f"tnt_influence_{side}"], 100)

    def test_solver_and_incoming_pricebalance_repair_then_never_recreate_conflict(self):
        for currency, p, r, lumpy_p, lumpy_r, ai in product(CUR, (0, 200, 1200), (0, 100, 800),
                                                          (0, 100), (0, 100), (False, True)):
            # The solver runs the Off branch here; lock policy independence is
            # separately exhaustive above. Native enabled pricing is a separate gate.
            world = self.world(lumpy_p=lumpy_p, lumpy_r=lumpy_r)
            world.vars[f"tnt_{currency}_p"] = D(p)
            world.vars[f"tnt_{currency}_r"] = D(r)
            world.vars["tnt_ai_offer_arch"] = D(1)
            world.press(ai=ai)
            self.assertTrue(self.exclusive(world), (currency, p, r, ai))
            world.press(ai=ai)
            self.assertTrue(self.exclusive(world))

    def test_search_additions_check_opposite_even_when_called_directly(self):
        for currency in CUR:
            world = self.world(lumpy_p=200)
            world.vars.update(tnt_ab_margin=D(1), tnt_ab_ceiling=D(1), tnt_ab_search_target=D(1))
            world.vars[f"tnt_{currency}_p"] = D(100)
            world.vars[f"tnt_{currency}_r"] = D(0)
            world.effect("tnt_ab_pay_currency_effect", {"VAR": f"tnt_{currency}_r", "P": f"tnt_{currency}_p", "CAP": 2000})
            self.assertEqual(world.vars[f"tnt_{currency}_r"], 0)
            world.leaves["tnt_val_vassal_p_value"] = D(0)
            world.leaves["tnt_val_vassal_r_value"] = D(200)
            world.vars[f"tnt_{currency}_p"] = D(0)
            world.vars[f"tnt_{currency}_r"] = D(100)
            world.effect("tnt_ab_add_offer_currency_effect", {"P": f"tnt_{currency}_p", "R": f"tnt_{currency}_r", "CAP": 2000})
            self.assertEqual(world.vars[f"tnt_{currency}_p"], 0)

    def test_incoming_normalizes_before_quote_and_composer_only_stages_single_demand_currency(self):
        world = self.world()
        pricebalance = world.defs["tnt_ai_pricebalance_effect"]
        self.assertEqual([key for key, _, _ in pricebalance[:2]],
                         ["tnt_ab_sanitize_currencies_effect", "tnt_ab_net_effect"])
        composer = definitions(DEFAULT_SOURCE, "common/scripted_effects/tnt_37_ai_offer.txt")["tnt_ai_compose_offer_effect"]
        writes = [one(body, "name") for key, _, body in walk(composer)
                  if key in ("set_variable", "change_variable") and one(body, "name") in
                  {f"tnt_{currency}_{side}" for currency, side in product(CUR, SIDES)}]
        self.assertEqual(writes, ["tnt_gold_p"])
        self.assertEqual(sum(key == "tnt_ai_offer_settle_effect" for key, _, _ in walk(composer)), 1)
        dispatcher = definitions(DEFAULT_SOURCE, "events/tnt_ai_events.txt")["tnt_ai_offer.0001"]
        immediate = one(dispatcher, "immediate")
        keys = [key for key, _, _ in immediate]
        self.assertLess(keys.index("tnt_reset_offer_effect"), keys.index("tnt_ai_compose_offer_effect"))

    def test_send_manual_commit_incoming_accept_demand_and_master_retain_preflight(self):
        def guarded_preflight(body):
            return any(key == "if" and any(k == "tnt_deal_preflight_trigger" for k, _, _ in walk(one(value, "limit", [])))
                       for key, _, value in walk(body))
        self.assertTrue(guarded_preflight(one(self.guis["tnt_send_offer"], "effect")))
        master = definitions(DEFAULT_SOURCE, "common/scripted_effects/tnt_32_apply.txt")["tnt_apply_deal_effect"]
        self.assertEqual([key for key, _, _ in master], ["if"])
        self.assertIsNotNone(one(one(one(master, "if"), "limit"), "tnt_deal_preflight_trigger"))
        for filename, event, option in (
                ("events/tnt_events.txt", "tnt_diplomacy.0001", "tnt_confirm_opt_yes"),
                ("events/tnt_ai_events.txt", "tnt_ai_offer.0002", "tnt_ai_offer_opt_accept"),
                ("events/tnt_ai_events.txt", "tnt_ai_offer.0003", "tnt_ai_demand_opt_pay")):
            event_body = definitions(DEFAULT_SOURCE, filename)[event]
            body = next(v for k, _, v in event_body if k == "option" and one(v, "name") == option)
            self.assertTrue(guarded_preflight(body), option)

    def test_lock_test_detects_effect_guard_removal(self):
        world = self.world()
        world.vars["tnt_gold_r"] = D(100)
        effect = deepcopy(one(self.guis["tnt_gold_p_add"], "effect"))
        self.assertEqual([key for key, _, _ in effect], ["if"])
        weakened = [node for node in one(effect, "if") if node[0] != "limit"]
        world.effect_block(weakened)
        self.assertGreater(world.vars["tnt_gold_p"], 0)
        self.assertFalse(self.exclusive(world))

    def test_baseline_projection_rejects_weakened_or_misplaced_guards(self):
        effects = definitions(DEFAULT_SOURCE, "common/scripted_effects/tnt_39_autobalance.txt")
        for name in ("tnt_cur_step_p_effect", "tnt_cur_set_r_effect", "tnt_ab_pay_currency_effect",
                     "tnt_ab_solve_effect", "tnt_ai_pricebalance_effect"):
            ast = [(name, "=", deepcopy(effects[name]))]
            without_currency_exclusivity(ast)
            if name == "tnt_cur_step_p_effect":
                value = one(one(ast[0][2], "set_variable"), "value")
                delta = one(value, "add")
                one(delta, "if")[-1] = ("max", "=", "10")
            elif name == "tnt_cur_set_r_effect":
                one(one(ast[0][2], "if"), "limit")[:] = parse("tnt_currency_p_unlocked_trigger = { CURRENCY = $FIELD$ }")
            elif name == "tnt_ab_pay_currency_effect":
                one(one(ast[0][2], "if"), "limit")[:] = parse("tnt_ab_surplus_value > 0")
            elif name == "tnt_ab_solve_effect":
                call = next(value for key, _, value in walk(ast) if key == "tnt_ab_pay_currency_effect")
                call[:] = [(key, op, "tnt_gold_r" if key == "P" else value) for key, op, value in call]
            else:
                ast[0][2].pop(1)
            with self.subTest(name=name), self.assertRaises(AssertionError):
                without_currency_exclusivity(ast)

        source = definitions(DEFAULT_SOURCE, "common/scripted_triggers/tnt_43_preflight.txt")
        ast = [("tnt_deal_preflight_trigger", "=", source["tnt_deal_preflight_trigger"])]
        without_currency_exclusivity(ast)
        player = next(value for key, _, value in one(ast[0][2], "trigger_if")
                      if key == "$PLAYER$" and ("tnt_currencies_exclusive_trigger", "=", "yes") in value)
        player.remove(("tnt_currencies_exclusive_trigger", "=", "yes"))
        with self.assertRaises(AssertionError):
            without_currency_exclusivity(ast)


if __name__ == "__main__":
    unittest.main()
