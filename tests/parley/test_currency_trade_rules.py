"""Source-backed currency permission and directional solver regressions.

Executes the actual currency trigger, solver, row-gate and control ASTs using
test_autobalance.World. Native character facts are explicit fixtures; arithmetic
and scope behavior remain a constrained model, not CK3 runtime certification.
Send/preflight tests execute their extracted currency guards, not whole packages.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import unittest
from itertools import product
from pathlib import Path

from test_autobalance import CURRENCIES, DEFAULT_SOURCE, D, Unsupported, World, one, parse


def walk(nodes):
    for node in nodes:
        yield node
        if isinstance(node[2], list):
            yield from walk(node[2])


def definitions(source, filename):
    return {key: body for key, _, body in parse((source / filename).read_text(encoding="utf-8-sig"))
            if isinstance(body, list)}


FAITH_PAIRS = (
    ("catholic", "catholic", "christianity", "christianity"),
    ("catholic", "orthodox", "christianity", "christianity"),
    ("catholic", "ashari", "christianity", "islam"),
)
SETTINGS = {
    "prestige": ("off", "on", "peer", "faith", "lower"),
    "piety": ("off", "on", "faith", "religion", "different_faith", "faith_lower"),
}
GUI_SOURCE = "common/scripted_guis/tnt_22_v2.txt"
GATE_SOURCE = "common/scripted_triggers/tnt_41_gates.txt"


class CurrencyRuleTests(unittest.TestCase):
    source = DEFAULT_SOURCE
    metrics = {}

    def world(self, **kwargs):
        return World(self.source, **kwargs)

    def permitted(self, world, currency, side):
        args = {"A": "root", "B": "var:tnt_partner"} if side == "p" else {"A": "var:tnt_partner", "B": "root"}
        return world.scripted_trigger(f"tnt_trade_{currency}_trigger", args)

    def ui_world(self, **kwargs):
        world = self.world(**kwargs)
        # The cached numerical model definitions must never be mutated by a
        # test that additionally loads UI-specific definitions.
        world.defs = {**world.defs, **definitions(self.source, GATE_SOURCE)}
        return world

    def test_defaults_and_legacy_setting_identifiers_remain(self):
        rules = definitions(self.source, "common/game_rules/tnt_80_game_rules.txt")
        for currency, settings in SETTINGS.items():
            rule = rules[f"tnt_trade_{currency}"]
            self.assertEqual(one(rule, "default"), f"tnt_trade_{currency}_on")
            self.assertEqual({key for key, _, body in rule if isinstance(body, list) and key != "categories"},
                             {f"tnt_trade_{currency}_{setting}" for setting in settings})
            for side in ("p", "r"):
                self.assertTrue(self.permitted(self.world(), currency, side))

    def test_trigger_branch_interpreter_fails_on_unknown_executed_syntax(self):
        world = self.world()
        cases = (
            ("trigger_if = { limit = { always = no } always = no }", True),
            ("trigger_if = { limit = { always = no } always = no } trigger_else = { always = yes }", True),
            ("trigger_if = { limit = { always = yes } always = no } trigger_else = { always = yes }", False),
            ("trigger_if = { limit = { always = no } always = no } trigger_else_if = { limit = { always = yes } always = no } trigger_else = { always = yes }", False),
            ("trigger_if = { limit = { always = no } always = no } trigger_if = { limit = { always = yes } always = no }", False),
        )
        for source, expected in cases:
            self.assertEqual(world.trigger(parse(source)), expected, source)
        with self.assertRaises(Unsupported):
            world.trigger(parse("trigger_if = { limit = { always = yes } imaginary_trigger = yes }"))

    def test_prestige_rule_exhaustive_faith_and_fame_matrix(self):
        cases = 0
        for setting, pair, fame_p, fame_r, side in product(SETTINGS["prestige"], FAITH_PAIRS, range(6), range(6), ("p", "r")):
            faith_p, faith_r, religion_p, religion_r = pair
            world = self.world(prestige=setting, fame_p=fame_p, fame_r=fame_r,
                               faith_p=faith_p, faith_r=faith_r, religion_p=religion_p, religion_r=religion_r)
            giver, receiver = (fame_p, fame_r) if side == "p" else (fame_r, fame_p)
            expected = {"off": False, "on": True, "peer": giver >= receiver,
                        "faith": faith_p == faith_r, "lower": giver > receiver}[setting]
            with self.subTest(setting=setting, faiths=pair[:2], fame=(fame_p, fame_r), side=side):
                self.assertEqual(self.permitted(world, "prestige", side), expected)
            cases += 1
        self.metrics["prestige_rule_matrix_cases"] = cases

    def test_piety_rules_include_both_kinds_of_different_faith(self):
        cases = 0
        for setting, pair, devotion_p, devotion_r, side in product(
                SETTINGS["piety"], FAITH_PAIRS, range(6), range(6), ("p", "r")):
            faith_p, faith_r, religion_p, religion_r = pair
            world = self.world(piety=setting, faith_p=faith_p, faith_r=faith_r,
                               devotion_p=devotion_p, devotion_r=devotion_r,
                               religion_p=religion_p, religion_r=religion_r)
            giver, receiver = (devotion_p, devotion_r) if side == "p" else (devotion_r, devotion_p)
            expected = {"off": False, "on": True, "faith": faith_p == faith_r,
                        "religion": religion_p == religion_r,
                        "different_faith": faith_p != faith_r,
                        "faith_lower": faith_p == faith_r and giver > receiver}[setting]
            with self.subTest(setting=setting, faiths=pair[:2], devotion=(devotion_p, devotion_r), side=side):
                self.assertEqual(self.permitted(world, "piety", side), expected)
            cases += 1
        self.metrics["piety_rule_matrix_cases"] = cases

    def test_devotion_rule_reads_level_independent_of_spendable_piety_and_fame(self):
        for wallet_p, wallet_r in ((-500, 10000), (0, 0), (10000, -500)):
            world = self.world(piety="faith_lower", devotion_p=5, devotion_r=1,
                               fame_p=0, fame_r=5,
                               player=(0, 0, wallet_p, 0), partner=(0, 0, wallet_r, 0))
            self.assertTrue(self.permitted(world, "piety", "p"))
            self.assertFalse(self.permitted(world, "piety", "r"))

    def test_equal_devotion_regression_detects_strictness_mutation(self):
        original = self.world(piety="faith_lower", devotion_p=3, devotion_r=3)

        def rejects_equal_devotion(world):
            for side in ("p", "r"):
                self.assertFalse(self.permitted(world, "piety", side), "strict mode must reject equal devotion")

        rejects_equal_devotion(original)
        mutated = self.world(piety="faith_lower", devotion_p=3, devotion_r=3)
        mutated.defs = deepcopy(mutated.defs)
        changed = 0

        def weaken(nodes):
            nonlocal changed
            for index, (key, op, body) in enumerate(nodes):
                if key == "piety_level" and op == ">":
                    nodes[index] = (key, ">=", body)
                    changed += 1
                elif isinstance(body, list):
                    weaken(body)

        weaken(mutated.defs["tnt_trade_piety_trigger"])
        self.assertEqual(changed, 1)
        with self.assertRaisesRegex(AssertionError, "strict mode must reject equal devotion"):
            rejects_equal_devotion(mutated)
        rejects_equal_devotion(original)

    def test_fame_rule_reads_level_independent_of_spendable_prestige(self):
        for wallet_p, wallet_r in ((-500, 10000), (0, 0), (10000, -500)):
            world = self.world(prestige="lower", fame_p=5, fame_r=1,
                               player=(0, wallet_p, 0, 0), partner=(0, wallet_r, 0, 0))
            self.assertTrue(self.permitted(world, "prestige", "p"))
            self.assertFalse(self.permitted(world, "prestige", "r"))
        for currency in SETTINGS:
            for setting in SETTINGS[currency]:
                world = self.world(**{currency: setting})
                world.vars.pop("tnt_partner")
                self.assertFalse(self.permitted(world, currency, "p"))
                self.assertFalse(self.permitted(world, currency, "r"))

    def test_equal_fame_regression_detects_strictness_mutation(self):
        original = self.world(prestige="lower", fame_p=3, fame_r=3)

        def rejects_equal_fame(world):
            for side in ("p", "r"):
                self.assertFalse(self.permitted(world, "prestige", side), "strict mode must reject equal fame")

        rejects_equal_fame(original)
        mutated = self.world(prestige="lower", fame_p=3, fame_r=3)
        mutated.defs = deepcopy(mutated.defs)
        changed = 0

        def weaken(nodes):
            nonlocal changed
            for index, (key, op, body) in enumerate(nodes):
                if key == "prestige_level" and op == ">":
                    nodes[index] = (key, ">=", body)
                    changed += 1
                elif isinstance(body, list):
                    weaken(body)

        weaken(mutated.defs["tnt_trade_prestige_trigger"])
        self.assertEqual(changed, 1)
        with self.assertRaisesRegex(AssertionError, "strict mode must reject equal fame"):
            rejects_equal_fame(mutated)
        rejects_equal_fame(original)

    def test_surplus_regression_detects_solver_direction_mutation(self):
        def fixture():
            return self.world(prestige="lower", piety=False, fame_p=1, fame_r=3,
                              opinion=0, traits=(), lumpy_p=80, lumpy_r=0,
                              player=(0, 3000, 0, 0), partner=(0, 3000, 0, 0))

        def settles_partner_return(world):
            result = world.press()
            self.assertEqual(result["score"], 1, "partner-to-player prestige must settle the surplus")
            self.assertGreater(result["amounts"]["prestige_r"], 0)
            self.assertEqual(result["amounts"]["prestige_p"], 0)

        settles_partner_return(fixture())
        mutated = fixture()
        mutated.defs = deepcopy(mutated.defs)
        changed = 0
        for key, _, body in walk(mutated.defs["tnt_ab_solve_effect"]):
            if key != "if":
                continue
            payment = one(body, "tnt_ab_pay_currency_effect")
            if payment is None or one(payment, "VAR") != "tnt_prestige_r":
                continue
            limit = one(body, "limit")
            args = one(limit, "tnt_trade_prestige_trigger")
            self.assertEqual(dict((k, v) for k, _, v in args), {"A": "var:tnt_partner", "B": "root"})
            args[:] = [("A", "=", "root"), ("B", "=", "var:tnt_partner")]
            changed += 1
        self.assertEqual(changed, 1)
        with self.assertRaisesRegex(AssertionError, "partner-to-player prestige must settle the surplus"):
            settles_partner_return(mutated)
        settles_partner_return(fixture())

    def test_shared_solver_deficits_surpluses_reserves_and_repeated_clicks(self):
        # Every new/legacy setting, lower/equal/higher fame and devotion levels,
        # and both faith categories; independent expectations come from the rule
        # matrix above. Only the currency under test has a nonzero wallet.
        cases = 0
        for currency in SETTINGS:
            for setting, same_faith, fame_p, direction, enough, ai in product(
                    SETTINGS[currency], (False, True), (1, 3, 5), ("deficit", "surplus"), (False, True), (False, True)):
                wallet = [0, 0, 0, 0]
                wallet[CURRENCIES.index(currency)] = 3000 if enough else 1
                rules = {"prestige": False, "piety": False, currency: setting}
                world = self.world(opinion=0, traits=(), lumpy_p=80 if direction == "surplus" else 0,
                                   lumpy_r=80 if direction == "deficit" else 0, player=wallet, partner=wallet,
                                   fame_p=fame_p, fame_r=3,
                                   devotion_p=fame_p, devotion_r=3,
                                   faith_r="catholic" if same_faith else "orthodox", **rules)
                side = "p" if direction == "deficit" else "r"
                allowed = self.permitted(world, currency, side)
                before = dict(world.leaves)
                with self.subTest(currency=currency, setting=setting, same_faith=same_faith,
                                  fame_p=fame_p, direction=direction, enough=enough, ai=ai):
                    result = world.press(ai=ai)
                    self.assertEqual(D(str(result["score"])), world.independent_score())
                    self.assertEqual(world.leaves, before)
                    for cur, lane in product(CURRENCIES, ("p", "r")):
                        amount = result["amounts"][f"{cur}_{lane}"]
                        self.assertGreaterEqual(amount, 0)
                        self.assertLessEqual(D(str(amount)), D(wallet[CURRENCIES.index(cur)]) * D("0.8"))
                        if cur != currency or (cur in SETTINGS and not self.permitted(world, cur, lane)):
                            self.assertEqual(amount, 0)
                    self.assertEqual(result["amounts"][currency + ("_r" if side == "p" else "_p")], 0)
                    if allowed and enough:
                        self.assertEqual(result["score"], 1)
                        self.assertGreater(result["amounts"][currency + "_" + side], 0)
                    elif direction == "deficit":
                        self.assertLessEqual(result["score"], 0)
                        if not ai:
                            self.assertEqual(result["state"], 3)
                    else:
                        self.assertGreater(result["score"], 1)
                        if not ai:
                            self.assertEqual(result["state"], 4)
                    again = world.press(ai=ai)
                    self.assertEqual(again["score"], result["score"])
                    self.assertEqual(again["amounts"], result["amounts"])
                cases += 1
        self.metrics["solver_rule_matrix_cases"] = cases

    def test_deficit_reduces_legal_partner_return_when_player_cannot_pay_prestige(self):
        for setting, ai in product(("peer", "lower"), (False, True)):
            world = self.world(prestige=setting, piety=False, fame_p=1, fame_r=3,
                               opinion=0, traits=(), lumpy_p=80, lumpy_r=0,
                               player=(0, 3000, 0, 0), partner=(0, 3000, 0, 0))
            world.vars["tnt_prestige_r"] = D(2000)
            self.assertLess(world.independent_score(), 0)
            result = world.press(ai=ai)
            self.assertEqual(result["score"], 1)
            self.assertNotIn("tnt_prestige_p", world.vars)
            self.assertGreater(result["amounts"]["prestige_r"], 0)
            self.assertLess(result["amounts"]["prestige_r"], 2000)
            self.assertEqual(world.press(ai=ai)["amounts"], result["amounts"])

    def test_stale_denied_lane_is_removed_before_netting_legal_lane(self):
        for allowed_side, ai in product(("p", "r"), (False, True)):
            world = self.world(prestige="lower", piety=False, fame_p=5 if allowed_side == "p" else 1,
                               fame_r=3, opinion=0, traits=(), lumpy_p=0, lumpy_r=0)
            illegal = "r" if allowed_side == "p" else "p"
            world.vars[f"tnt_prestige_{allowed_side}"] = D(200)
            world.vars[f"tnt_prestige_{illegal}"] = D(150)
            world.effect("tnt_ab_sanitize_currencies_effect")
            world.effect("tnt_ab_net_effect")
            self.assertNotIn(f"tnt_prestige_{illegal}", world.vars)
            self.assertEqual(world.vars[f"tnt_prestige_{allowed_side}"], 200)
            # Entry points must reach the same table as a clean input; an
            # invalid opposite leg must not buy a discount or raise a gift cap.
            clean = self.world(prestige="lower", piety=False, fame_p=5 if allowed_side == "p" else 1,
                               fame_r=3, opinion=100, traits=(), lumpy_p=50, lumpy_r=50)
            stale = self.world(prestige="lower", piety=False, fame_p=5 if allowed_side == "p" else 1,
                               fame_r=3, opinion=100, traits=(), lumpy_p=50, lumpy_r=50)
            for fixture in (clean, stale):
                fixture.vars[f"tnt_prestige_{allowed_side}"] = D(200)
                fixture.vars["tnt_ai_offer_arch"] = D(1)
            stale.vars[f"tnt_prestige_{illegal}"] = D(150)
            good, repaired = clean.press(ai=ai), stale.press(ai=ai)
            self.assertEqual(repaired["amounts"], good["amounts"])
            self.assertEqual(repaired["score"], good["score"])
            self.assertNotIn(f"tnt_prestige_{illegal}", stale.vars)

    def test_all_denied_stale_currencies_disappear(self):
        for ai in (False, True):
            world = self.world(prestige=False, piety="different_faith", faith_r="catholic")
            for currency, side in product(SETTINGS, ("p", "r")):
                world.vars[f"tnt_{currency}_{side}"] = D(500)
            world.press(ai=ai)
            for currency, side in product(SETTINGS, ("p", "r")):
                self.assertNotIn(f"tnt_{currency}_{side}", world.vars)

    def test_devotion_rule_live_ui_controls_send_and_preflight(self):
        guis = definitions(self.source, GUI_SOURCE)
        send = one(definitions(self.source, "common/scripted_guis/tnt_20_scripted_guis.txt")["tnt_send_offer"], "is_valid")
        preflight = definitions(self.source, "common/scripted_triggers/tnt_43_preflight.txt")["tnt_deal_preflight_trigger"]
        guard_sets = []
        for body in (send, preflight):
            guards = [(key, op, branch) for key, op, branch in walk(body)
                      if key == "trigger_if" and any(k == "tnt_trade_piety_trigger" for k, _, _ in branch)]
            self.assertEqual(len(guards), 2)
            guard_sets.append(guards)
        covered = 0
        for side, same_faith, giver_level, receiver_level in product(
                ("p", "r"), (False, True), (1, 3, 5), (3,)):
            allowed = same_faith and giver_level > receiver_level
            levels = {"devotion_" + side: giver_level,
                      "devotion_" + ("r" if side == "p" else "p"): receiver_level}
            world = self.ui_world(piety="faith_lower", faith_r="catholic" if same_faith else "orthodox", **levels)
            # Stale bridge values cannot override the live direction/faith test.
            world.vars["tnt_trade_pty_on"] = D(1)
            world.params = {"PLAYER": "root", "PARTNER": "var:tnt_partner"}
            with self.subTest(side=side, same_faith=same_faith, giver_level=giver_level):
                self.assertEqual(world.scripted_trigger(f"tnt_show_piety_{side}_trigger", {"OTHER": "var:tnt_partner"}), allowed)
                self.assertEqual(world.trigger(one(guis[f"tnt_trade_piety_{side}_available"], "is_valid")), allowed)
                for action in ("add", "add_big", "add_huge", "sub", "sub_big", "sub_huge", "std", "half", "max"):
                    control = guis[f"tnt_piety_{side}_{action}"]
                    self.assertEqual(world.trigger(one(control, "is_valid")), allowed)
                    world.vars[f"tnt_piety_{side}"] = D(250)
                    before = dict(world.vars)
                    world.effect_block(one(control, "effect"))
                    if not allowed:
                        self.assertEqual(world.vars, before)
                    covered += 1
                world.vars[f"tnt_piety_{side}"] = D(100)
                for guards in guard_sets:
                    self.assertEqual(world.trigger(guards), allowed)
                clear = guis[f"tnt_piety_{side}_none"]
                self.assertTrue(world.trigger(one(clear, "is_valid", [])))
                world.effect_block(one(clear, "effect"))
                self.assertNotIn(f"tnt_piety_{side}", world.vars)
                for guards in guard_sets:
                    self.assertTrue(world.trigger(guards))
        self.metrics["devotion_control_permission_cases"] = covered

    def test_devotion_rule_repairs_stale_lanes_for_manual_and_incoming_ai(self):
        for allowed_side, ai in product(("p", "r"), (False, True)):
            kwargs = dict(prestige=False, piety="faith_lower",
                          devotion_p=5 if allowed_side == "p" else 1, devotion_r=3,
                          opinion=100, traits=(), lumpy_p=50, lumpy_r=50,
                          player=(0, 0, 3000, 0), partner=(0, 0, 3000, 0))
            illegal = "r" if allowed_side == "p" else "p"
            clean, stale = self.world(**kwargs), self.world(**kwargs)
            for world in (clean, stale):
                world.vars[f"tnt_piety_{allowed_side}"] = D(200)
                world.vars["tnt_ai_offer_arch"] = D(1)
            stale.vars[f"tnt_piety_{illegal}"] = D(150)
            good, repaired = clean.press(ai=ai), stale.press(ai=ai)
            self.assertEqual(repaired["amounts"], good["amounts"])
            self.assertEqual(repaired["score"], good["score"])
            self.assertNotIn(f"tnt_piety_{illegal}", stale.vars)
            # A faith change while an offer is staged invalidates both legs.
            stale.identities["r"]["faith"] = "orthodox"
            stale.press(ai=ai)
            self.assertNotIn("tnt_piety_p", stale.vars)
            self.assertNotIn("tnt_piety_r", stale.vars)

    def test_live_row_gates_follow_each_direction_and_ignore_bridge_cache(self):
        for currency, side, allowed, cached in product(SETTINGS, ("p", "r"), (False, True), (False, True)):
            kwargs = ({"prestige": "lower", "fame_p": 5 if allowed == (side == "p") else 1, "fame_r": 3}
                      if currency == "prestige" else {"piety": "different_faith", "faith_r": "orthodox" if allowed else "catholic"})
            world = self.ui_world(**kwargs)
            if cached:
                world.vars.update(tnt_trade_prest_on=D(1), tnt_trade_pty_on=D(1))
            with self.subTest(currency=currency, side=side, allowed=allowed, cached=cached):
                self.assertEqual(world.scripted_trigger(f"tnt_show_{currency}_{side}_trigger", {"OTHER": "var:tnt_partner"}), allowed)
                world.vars.pop("tnt_partner")
                self.assertFalse(world.scripted_trigger(f"tnt_show_{currency}_{side}_trigger", {"OTHER": "var:tnt_partner"}))

    def test_all_controls_have_live_permission_and_effect_guards(self):
        guis = definitions(self.source, GUI_SOURCE)
        actions = ("add", "add_big", "add_huge", "sub", "sub_big", "sub_huge", "std", "half", "max")
        covered = 0
        for currency, side in product(SETTINGS, ("p", "r")):
            availability = guis[f"tnt_trade_{currency}_{side}_available"]
            for allowed in (False, True):
                kwargs = ({"prestige": "lower", "fame_p": 5 if allowed == (side == "p") else 1, "fame_r": 3}
                          if currency == "prestige" else {"piety": "different_faith", "faith_r": "orthodox" if allowed else "catholic"})
                world = self.ui_world(**kwargs)
                self.assertEqual(world.trigger(one(availability, "is_valid", [])), allowed)
                for action in actions:
                    name = f"tnt_{currency}_{side}_{action}"
                    gui = guis[name]
                    with self.subTest(control=name, allowed=allowed):
                        self.assertIsNotNone(one(gui, "is_valid"))
                        self.assertEqual(world.trigger(one(gui, "is_valid")), allowed)
                        world.vars[f"tnt_{currency}_{side}"] = D(250)
                        before = dict(world.vars)
                        world.effect_block(one(gui, "effect"))
                        if not allowed:
                            self.assertEqual(world.vars, before, "stale GUI execution must not change the deal")
                    covered += 1
                clear = guis[f"tnt_{currency}_{side}_none"]
                self.assertTrue(world.trigger(one(clear, "is_valid", [])))
                world.effect_block(one(clear, "effect"))
                self.assertNotIn(f"tnt_{currency}_{side}", world.vars)
        self.metrics["control_permission_cases"] = covered

    def test_send_and_preflight_execute_positive_currency_guards(self):
        for file, definition, section in (
                ("common/scripted_guis/tnt_20_scripted_guis.txt", "tnt_send_offer", "is_valid"),
                ("common/scripted_triggers/tnt_43_preflight.txt", "tnt_deal_preflight_trigger", None)):
            body = definitions(self.source, file)[definition]
            if section:
                body = one(body, section)
            guards = [(key, op, branch) for key, op, branch in walk(body)
                      if key == "trigger_if" and any(k in ("tnt_trade_prestige_trigger", "tnt_trade_piety_trigger") for k, _, _ in branch)]
            self.assertEqual(len(guards), 4, file)
            for currency, side, positive, allowed in product(SETTINGS, ("p", "r"), (False, True), (False, True)):
                kwargs = ({"prestige": "lower", "fame_p": 5 if allowed == (side == "p") else 1, "fame_r": 3}
                          if currency == "prestige" else {"piety": "different_faith", "faith_r": "orthodox" if allowed else "catholic"})
                world = self.world(**kwargs)
                world.params = {"PLAYER": "root", "PARTNER": "var:tnt_partner"}
                world.vars[f"tnt_{currency}_{side}"] = D(100 if positive else 0)
                with self.subTest(file=file, currency=currency, side=side, positive=positive, allowed=allowed):
                    self.assertEqual(world.trigger(guards), not positive or allowed)

    def test_dormant_world_prestige_transfer_checks_rule_before_equal_debit_credit(self):
        body = definitions(self.source, "common/scripted_effects/tnt_38_ai_world.txt")["tnt_ai_send_prestige_effect"]
        # Both writes must share one gate and preserve the requested amount;
        # there is no fee, extra experience change, or ungated partial leg.
        self.assertEqual([key for key, _, _ in body], ["$GIVER$"])
        giver = one(body, "$GIVER$")
        self.assertEqual([key for key, _, _ in giver], ["if"])
        branch = one(giver, "if")
        self.assertEqual([key for key, _, _ in branch], ["limit", "add_prestige", "$RECEIVER$"])
        self.assertEqual(one(branch, "add_prestige"), parse("value = $AMOUNT$ multiply = -1"))
        self.assertEqual(one(branch, "$RECEIVER$"), parse("add_prestige = $AMOUNT$"))
        for side, enough in product(("p", "r"), (False, True)):
            world = self.world(prestige="lower", fame_p=5, fame_r=3,
                               player=(0, 100 if enough else 10, 0, 0),
                               partner=(0, 100 if enough else 10, 0, 0))
            world.scopes.update(currency_giver=side, currency_receiver="r" if side == "p" else "p")
            world.params = {"GIVER": "scope:currency_giver", "RECEIVER": "scope:currency_receiver", "AMOUNT": 20}
            self.assertEqual(world.trigger(one(branch, "limit"), current=side), side == "p" and enough)
            self.assertEqual(world.value(one(branch, "add_prestige"), side), -20)
            self.assertEqual(world.value(one(one(branch, "$RECEIVER$"), "add_prestige"), side), 20)

    def test_master_apply_preflight_protects_every_execution_leg(self):
        body = definitions(self.source, "common/scripted_effects/tnt_32_apply.txt")["tnt_apply_deal_effect"]
        # Source architecture check only: the complete native executor is not
        # simulated. Its sole outer branch must preflight the whole package
        # before telemetry, favor, currencies or any other persistent effect.
        self.assertEqual([key for key, _, _ in body], ["if"])
        branch = one(body, "if")
        self.assertEqual(branch[0][0], "limit")
        self.assertEqual(one(one(branch, "limit"), "tnt_deal_preflight_trigger"),
                         parse("PLAYER = root PARTNER = scope:tnt_deal_partner"))
        for currency in CURRENCIES:
            calls = [args for key, _, args in walk(branch) if key == f"tnt_exec_{currency}_effect"]
            self.assertEqual(len(calls), 2, currency)
            self.assertEqual({one(call, "SIDE") for call in calls}, {"p", "r"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()
    CurrencyRuleTests.source = args.source
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CurrencyRuleTests))
    if args.report_json:
        hashes = dict(World(args.source).hashes)
        for filename in (GUI_SOURCE, GATE_SOURCE, "common/game_rules/tnt_80_game_rules.txt",
                         "common/scripted_guis/tnt_20_scripted_guis.txt", "common/scripted_triggers/tnt_43_preflight.txt",
                         "common/scripted_effects/tnt_38_ai_world.txt", "common/scripted_effects/tnt_32_apply.txt"):
            hashes[filename] = hashlib.sha256((args.source / filename).read_bytes()).hexdigest()
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps({"tests_run": result.testsRun, "success": result.wasSuccessful(),
            "failures": [(str(test), trace) for test, trace in result.failures],
            "errors": [(str(test), trace) for test, trace in result.errors], "metrics": CurrencyRuleTests.metrics,
            "source": str(args.source), "source_sha256": hashes, "limitations": __doc__}, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())


if __name__ == "__main__":
    main()
