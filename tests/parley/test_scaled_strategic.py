"""Bounded execution tests for Scaled strategic terms and AI-world seams.

Production price ASTs execute in explicit character/title fixtures. Native hook
ownership, contract legality and marriage legality are input facts, not simulated
CK3 behavior. The coercion test executes the production pressure gates; it does
not certify the engine's threat or realm-iterator implementation.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import subprocess
import unittest

import test_scaled_valuation as shared
from test_autobalance import DEFAULT_SOURCE, one, parse
from test_scaled_valuation import CLASSIC_BASELINE, D, Scope, ValuationWorld, realm

SOURCE = DEFAULT_SOURCE


class StrategicWorld(ValuationWorld):
    def __init__(self, rule="scaled"):
        super().__init__(source=SOURCE, rule=rule)

    def condition(self, nodes, current):
        # Only fixture-backed native relations/containers are added here. All
        # remaining syntax passes through the strict shared interpreter.
        converted, index = [], 0
        while index < len(nodes):
            key, op, body = nodes[index]
            index += 1
            if key == "trigger_if":
                chain = [(key, op, body)]
                while index < len(nodes) and nodes[index][0] in ("trigger_else_if", "trigger_else"):
                    chain.append(nodes[index]); index += 1
                for branch, _, branch_body in chain:
                    if branch == "trigger_else" or self.condition(one(branch_body, "limit", []), current):
                        chosen = [row for row in branch_body if row[0] != "limit"]
                        converted.append(("always", "=", "yes" if self.condition(chosen, current) else "no"))
                        break
            elif key in ("has_weak_hook", "has_strong_hook"):
                answer = self.scope(body, current) in current.stats.get(key, set())
                converted.append(("always", "=", "yes" if answer else "no"))
            elif key == "variable_list_size":
                target_op, target = next((o, b) for k, o, b in body if k == "value")
                answer = self.compare(D(len(current.lists.get(one(body, "name"), []))),
                                      target_op, self.operand(target, current))
                converted.append(("always", "=", "yes" if answer else "no"))
            else:
                converted.append((key, op, body))
        return super().condition(converted, current)


def table(world, player_count=1, partner_count=30):
    player = realm(world, "player", player_count, tier="tier_county", nested=True)
    partner = realm(world, "partner", partner_count, tier="tier_county", nested=True)
    player.variables["tnt_partner"] = partner
    world.root = player
    world.scopes.update(actor=player, recipient=partner, tnt_me=player, tnt_p=partner)
    return player, partner


def substitute(nodes, replacements):
    result = []
    for key, op, body in nodes:
        for old, new in replacements.items():
            key = key.replace(old, new)
        if isinstance(body, list):
            body = substitute(body, replacements)
        else:
            for old, new in replacements.items():
                body = body.replace(old, new)
        result.append((key, op, body))
    return result


class ScaledStrategicTests(unittest.TestCase):
    def test_hook_actual_debtor_direction_and_shared_world_price(self):
        world = StrategicWorld()
        player, partner = table(world)
        player.variables.update(tnt_hook_p=D(2), tnt_hook_r=D(2),
                                tnt_usehook_p=D(1), tnt_usehook_r=D(1))
        player.stats["has_strong_hook"] = {partner}
        partner.stats["has_strong_hook"] = {player}
        # Player land20 -> factor1.05; partner land600 -> boundedfactor2.
        self.assertEqual(world.value("tnt_val_hook_tier_p_value"), D("52.5"))
        self.assertEqual(world.value("tnt_val_hook_tier_r_value"), 100)
        self.assertEqual(world.value("tnt_val_usehook_p_value"), 240)
        self.assertEqual(world.value("tnt_val_usehook_r_value"), -126)
        self.assertEqual(world.value("tnt_ai_hook_cost_value"), 40)
        self.assertEqual(world.value("tnt_ai_hookcall_points_value"), 240)

    def test_hook_strength_and_cap_do_not_inherit_a_courtiers_liege(self):
        world = StrategicWorld()
        liege = realm(world, "emperor", 200, tier="tier_empire")
        courtier = Scope("courtier", links={"liege": liege})
        self.assertEqual(world.value("tnt_scaled_hook_leverage_factor_value", courtier), 1)
        self.assertEqual(world.value("tnt_scaled_hook_leverage_factor_value", liege), 2)
        player, partner = table(world)
        player.variables.update(tnt_hook_p=D(1), tnt_usehook_p=D(1))
        player.stats["has_weak_hook"] = {partner}
        self.assertEqual(world.value("tnt_val_hook_tier_p_value"), 21)
        self.assertEqual(world.value("tnt_val_usehook_p_value"), 90)
        self.assertEqual(world.value("tnt_ai_hookcall_points_value"), 90)

    def contract_facts(self, player):
        # Native eligibility is a fixture input. Production amount/sign and
        # subject-direction definitions are deliberately not mocked.
        for gate in ("feudal", "fort_ok", "coin_ok", "relig_ok", "revoke_ok", "succ_ok"):
            player.stats[f"tnt_ob_{gate}_value"] = D(1)
        player.stats["tnt_ob_clan_value"] = D(0)

    def test_economic_contract_scaling_subject_sign_and_personal_rights(self):
        world = StrategicWorld()
        player, partner = table(world)
        self.contract_facts(player)
        player.variables.update(tnt_vassal_r=D(1), tnt_ob_tax=D(1), tnt_ob_levy=D(1),
                                tnt_ob_fort=D(1), tnt_ob_coin=D(1), tnt_ob_relig=D(1),
                                tnt_ob_council=D(1), tnt_ob_revoke=D(1), tnt_ob_war=D(1),
                                tnt_ob_succ=D(1))
        # Partner subject600land -> cap3, applied exactly once; existing sign+.
        for term, amount in (("tax",60),("levy",30),("fort",60),("coin",60),
                             ("relig",60),("council",30),("revoke",20),("war",20),("succ",-20)):
            self.assertEqual(world.value(f"tnt_val_ob_{term}_value"), amount, term)
        player.variables["tnt_ob_tax"] = D(3)
        self.assertEqual(world.value("tnt_val_ob_tax_value"), -75)
        player.variables["tnt_vassal_r"] = D(0)
        player.variables["tnt_vassal_p"] = D(1)
        # Actual player subject20land -> factor1.1; no partner-realm leak.
        self.assertEqual(world.value("tnt_val_ob_tax_value"), D("27.5"))
        player.variables["tnt_ob_tax"] = D(2)
        self.assertEqual(world.value("tnt_val_ob_tax_value"), 0)
        player.variables["tnt_vassal_p"] = D(0)
        self.assertEqual(world.value("tnt_contract_economic_scale_value"), 1)
        self.assertEqual(world.value("tnt_val_ob_coin_value"), 0)

    def test_empty_hooks_and_default_contract_do_not_walk_either_realm(self):
        world = StrategicWorld()
        player, _ = table(world, player_count=100, partner_count=100)
        self.contract_facts(player)
        player.variables.update(tnt_hook_p=D(0), tnt_hook_r=D(0), tnt_vassal_r=D(1),
                                tnt_ob_tax=D(2), tnt_ob_levy=D(2),
                                tnt_ob_fort=D(0), tnt_ob_coin=D(0))
        for value in ("tnt_val_hook_tier_p_value", "tnt_val_hook_tier_r_value",
                      "tnt_val_usehook_p_value", "tnt_val_usehook_r_value",
                      "tnt_val_ob_tax_value", "tnt_val_ob_levy_value",
                      "tnt_val_ob_fort_value", "tnt_val_ob_coin_value"):
            self.assertEqual(world.value(value), 0, value)
        self.assertEqual(world.iterator_visits, 0)

    def test_world_fealty_bill_has_no_scaled_cap_and_checks_real_purse(self):
        world = StrategicWorld()
        player, partner = table(world, partner_count=100)
        # Only relationship policy is a fixture. Asset cost and conversion
        # execute the exact production script, including the absent 1,200 cap.
        player.stats.update(tnt_ai_relation_value=D(20), tnt_ai_threshold_value=D(5))
        amount = world.value("tnt_ai_vassal_gold_value")
        self.assertEqual(world.value("tnt_ai_vassal_cost_value"), 2100)
        self.assertEqual(amount, 21000)
        self.assertEqual(world.value("tnt_ai_vassal_gold_points_value"), 2100)
        effects = dict((k,b) for k,_,b in parse((SOURCE / "common/scripted_effects/tnt_38_ai_world.txt").read_text(encoding="utf-8-sig")))
        gate = one(one(effects["tnt_ai_world_do_vassal_effect"], "if"), "limit")
        player.stats["gold"] = amount - 1
        self.assertFalse(world.condition(gate, player))
        player.stats["gold"] = amount
        self.assertTrue(world.condition(gate, player))

    def test_coercion_keeps_minimum_and_requires_scaled_territorial_pressure(self):
        triggers = dict((k,b) for k,_,b in parse((SOURCE / "common/scripted_triggers/tnt_40_triggers.txt").read_text(encoding="utf-8-sig")))
        pair = one(triggers["tnt_ai_coercive_fealty_pair_trigger"], "trigger_if")
        pressure_rows = [row for row in pair if row[0] == "trigger_if" or
                         (row[0] == "$A$" and any(k.startswith("tnt_threat_") for k,_,_ in row[2]))]
        self.assertEqual(len(pressure_rows), 3)
        pressure_rows = substitute(pressure_rows, {"$A$":"scope:actor", "$B$":"scope:recipient"})
        for rule in (None, "classic", "scaled"):
            world = StrategicWorld(rule)
            player, partner = table(world, partner_count=1)
            player.stats.update(tnt_threat_ratio_value=D(4), tnt_threat_points_value=D(150))
            self.assertTrue(world.condition(pressure_rows, player))
            large = realm(world, "large", 100, tier="tier_county")
            world.scopes["recipient"] = large
            self.assertEqual(world.condition(pressure_rows, player), rule != "scaled")
            player.stats["tnt_threat_points_value"] = D(99)
            self.assertFalse(world.condition(pressure_rows, player))

    def marriage(self, world):
        player, partner = table(world)
        player.variables.update(tnt_marriage_p=D(1), tnt_marriage_r=D(1))
        # Independent native consequences mocked at their seams; stored pair
        # prices and aggregate taper/caps remain production computations.
        player.stats.update(tnt_marriage_dread_value=D(0), tnt_marriage_grand_value=D(0))
        player.lists["tnt_wed_list"] = []
        for index in range(7):
            bride = Scope(f"bride{index}", stats={"is_alive":True})
            groom = Scope(f"groom{index}", stats={"is_alive":True})
            bride.variables.update(tnt_wed_partner=groom, tnt_wed_gain=D(1000), tnt_wed_loss=D(1000))
            player.lists["tnt_wed_list"].append(bride)
        return player

    def test_marriage_scaled_cost_linear_beyond_six_vetoes_gain_stays_capped(self):
        for rule, loss in ((None,6000),("classic",6000),("scaled",7000)):
            world = StrategicWorld(rule)
            self.marriage(world)
            self.assertEqual(world.value("tnt_marriage_offer_r_value"), loss)
            self.assertEqual(world.value("tnt_marriage_offer_p_value"), 2000)

    def test_classic_semantic_results_match_pinned_120_source(self):
        repo = SOURCE.parent.parent
        filenames = ("tnt_52_marriage_values.txt", "tnt_55_hc_values.txt",
                     "tnt_56_ai_values.txt", "tnt_59_usehook_values.txt")
        old_defs = {}
        for filename in filenames:
            relative = (SOURCE / "common/script_values" / filename).relative_to(repo).as_posix()
            raw = subprocess.check_output(["git","show",f"{CLASSIC_BASELINE}:{relative}"],cwd=repo)
            old_defs.update((k,b) for k,_,b in parse(raw.decode("utf-8-sig")))
        names = ["tnt_val_hook_tier_p_value","tnt_val_hook_tier_r_value","tnt_val_usehook_p_value",
                 "tnt_val_usehook_r_value","tnt_ai_hook_cost_value","tnt_ai_hookcall_points_value",
                 "tnt_ai_vassal_cost_value","tnt_ai_vassal_gold_value"]
        names += [f"tnt_val_ob_{term}_value" for term in ("tax","levy","fort","coin")]
        for rule in (None,"classic"):
            for count in (1,30,100):
                world = StrategicWorld(rule)
                player, partner = table(world, partner_count=count)
                self.contract_facts(player)
                player.variables.update(tnt_hook_p=D(3),tnt_hook_r=D(2),tnt_usehook_p=D(1),
                                        tnt_usehook_r=D(1),tnt_vassal_r=D(1),tnt_ob_tax=D(3),
                                        tnt_ob_levy=D(1),tnt_ob_fort=D(1),tnt_ob_coin=D(1))
                player.stats["has_strong_hook"] = {partner}
                partner.stats["has_weak_hook"] = {player}
                expected = deepcopy(world)
                expected.defs.update(old_defs)
                for name in names:
                    self.assertEqual(world.value(name), expected.value(name), (rule,count,name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=DEFAULT_SOURCE)
    args, remaining = parser.parse_known_args()
    SOURCE = args.source.resolve()
    shared.SOURCE = SOURCE
    unittest.main(argv=[__file__, *remaining],verbosity=2)
