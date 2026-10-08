"""Production-AST checks for AI-world bilateral interest adapters and commit gates.

Native relations/archetypes/inventory are explicit fixture facts. Effect tests
execute the real branch guards and record commit-leg calls; engine settlement,
fixed-point precision and whole-deal prospective context remain native gates.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import subprocess
import unittest

import test_interest_currency as currency_tests
from test_autobalance import DEFAULT_SOURCE, one, parse
from test_interest_currency import D, InterestWorld
from test_scaled_valuation import Scope, Unsupported

SOURCE = DEFAULT_SOURCE
LANES = {
    "hook_low": "tnt_ai_gold_low_value", "hook_high": "tnt_ai_gold_high_value",
    "ultimatum": "tnt_ai_demand_gold_value", "hookcall": "tnt_ai_hookcall_gold_value",
    "title": "tnt_ai_title_gold_value", "vassal": "tnt_ai_vassal_gold_value",
    "artifact": "tnt_ai_artifact_gold_value", "wed": "tnt_ai_wed_gold_value",
}


def walk(nodes):
    for node in nodes:
        yield node
        if isinstance(node[2], list):
            yield from walk(node[2])


class AiWorld(InterestWorld):
    def __init__(self, policy="standard"):
        super().__init__(policy)
        self.actor, self.recipient = self.root, self.partner
        self.root = Scope("unrelated_root")
        self.scopes.update(actor=self.actor, recipient=self.recipient)
        faith = Scope("same_faith", "faith", stats={"doctrine_parameters": set()})
        culture = Scope("same_culture", "culture")
        for character in (self.actor, self.recipient):
            character.links.update(faith=faith, culture=culture)
            character.stats.update(gold=D(1000), yearly_character_income=D(100),
                                   current_military_strength=D(1000), domain_size=D(1),
                                   domain_limit=D(3), vassal_limit_available=D(5),
                                   ai_greed=D(0), ai_rationality=D(0), ai_boldness=D(0),
                                   opinions={}, is_ruler=True)
        self.actor.stats["opinions"][self.recipient.name] = D(100)
        self.recipient.stats["opinions"][self.actor.name] = D(100)

    def operand(self, atom, current):
        if isinstance(atom, str) and atom.startswith("opinion("):
            target = self.scope(atom[len("opinion("):-1], current)
            return current.stats["opinions"].get(target.name, D(0))
        return super().operand(atom, current)

    def condition(self, nodes, current):
        translated = []
        for key, op, body in nodes:
            if key == "has_same_culture_as":
                result = current.links.get("culture") is self.scope(body, current).links.get("culture")
            elif key == "faith_hostility_level":
                result = False  # This fixture uses exactly one common faith.
            elif key in ("is_close_or_extended_family_of", "is_allied_to", "has_weak_hook", "has_strong_hook"):
                result = self.scope(body, current) in current.lists.get(key, [])
            elif key == "is_ruler":
                result = bool(current.stats.get("is_ruler", False)) == (body == "yes")
            elif key == "any_equipped_character_artifact":
                result = any(self.condition(body, item) for item in current.lists.get("equipped_artifacts", []))
            elif key == "artifact_slot_type":
                result = current.stats.get(key) == body
            elif key == "is_equipped":
                result = bool(current.stats.get(key, False)) == (body == "yes")
            elif key == "variable_list_size":
                compare_op, number = next((operator, value) for name, operator, value in body if name == "value")
                result = self.compare(D(len(current.lists.get(one(body, "name"), []))), compare_op, D(number))
            else:
                translated.append((key, op, body))
                continue
            translated.append(("always", "=", "yes" if result else "no"))
        return super().condition(translated, current)


class GateWitness:
    """Execute ordinary production branches; record, never pretend native mutations."""
    COMMIT_LEGS = {"tnt_ai_send_gold_effect", "tnt_ai_grant_hook_effect",
                   "tnt_ai_transfer_title_effect", "tnt_ai_world_apply_vassal_effect",
                   "tnt_ai_transfer_artifact_effect", "tnt_wed_plain_pair_effect"}

    def __init__(self, world):
        self.world = world
        self.calls = []

    def run(self, nodes, current=None):
        current = current or self.world.root
        index = 0
        while index < len(nodes):
            key, _, body = nodes[index]
            index += 1
            if key == "if":
                chain = [(key, body)]
                while index < len(nodes) and nodes[index][0] in ("else_if", "else"):
                    branch, _, contents = nodes[index]
                    chain.append((branch, contents)); index += 1
                for branch, contents in chain:
                    if branch == "else" or self.world.condition(one(contents, "limit", []), current):
                        self.run([node for node in contents if node[0] != "limit"], current)
                        break
            elif key.startswith("scope:"):
                self.run(body, self.world.scope(key, current))
            elif key in self.COMMIT_LEGS:
                self.calls.append(key)
            elif key.startswith("tnt_log_") or key in ("tnt_ai_world_notify_effect", "tnt_ai_world_cooldown_effect",
                                                         "tnt_start_threat_cooldown_effect", "add_opinion", "use_hook"):
                pass  # Named observability/native side effects outside this branch witness.
            else:
                raise Unsupported(f"Unmodeled effect {key}")


class InterestAiWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = {key: body for key, _, body in parse((SOURCE / "common/scripted_effects/tnt_38_ai_world.txt").read_text(encoding="utf-8-sig"))}

    def test_off_branches_are_exact_previous_ast_and_retired_lanes_unchanged(self):
        repo = SOURCE.parents[1]
        path = "mod/parley/common/script_values/tnt_56_ai_values.txt"
        baseline = {key: body for key, _, body in parse(subprocess.check_output(
            ["git", "show", f"HEAD:{path}"], cwd=repo).decode("utf-8-sig"))}
        live = AiWorld("off").defs
        for lane in LANES:
            name = f"tnt_ai_deal_{lane}_value"
            self.assertEqual(one(live[name], "else"), baseline[name])
        for lane in ("truce_low", "truce_high", "ally_low", "ally_high"):
            name = f"tnt_ai_deal_{lane}_value"
            self.assertEqual(live[name], baseline[name])
        live_keys = {key for body in self.effects.values() for key, _, _ in walk(body)}
        self.assertNotIn("tnt_ai_world_do_truce_effect", live_keys)
        self.assertNotIn("tnt_ai_world_do_ally_effect", live_keys)

    def test_all_gold_interval_adapters_match_table_curve_in_both_directions(self):
        for policy in ("mild", "standard", "strict"):
            world = AiWorld(policy)
            table = InterestWorld(policy)
            table.partner.stats.update(world.recipient.stats)
            for lane, amount_name in LANES.items():
                for stock in (-100, 0, 75, 300, 600, 10000):
                    for amount in (D("0.001"), D(10), D(250), D(10000)):
                        world.recipient.stats.update({"gold": D(stock), amount_name: amount})
                        for direction, side in (("receive", "p"), ("surrender", "r")):
                            actual = world.value(f"tnt_interest_ai_{lane}_gold_{direction}_factor_value", world.recipient)
                            expected = table.quote("gold", side, stock, amount)
                            self.assertEqual(actual, expected, (lane, direction, stock, amount))

    def test_character_advanced_adapters_match_single_object_table_policy(self):
        for policy in ("mild", "standard", "strict"):
            world = AiWorld(policy)
            item = Scope("artifact", "artifact", stats={"artifact_slot_type": "armor", "is_equipped": True})
            world.scopes["tnt_deal_artifact"] = item
            world.recipient.lists["equipped_artifacts"] = [item]
            world.root.variables["tnt_partner"] = world.recipient
            world.root.stats["is_ruler"] = True
            for term, table_term in (("title", "title"), ("vassal", "vassal"), ("artifact", "artifact"), ("hook", "hook"), ("wed", "marriage")):
                for direction, side in (("receive", "p"), ("surrender", "r")):
                    selected = f"tnt_interest_{table_term}_{side}_selected_value"
                    world.root.stats[selected] = D(1)
                    world.root.stats["tnt_domain_titles_p_value"] = D(1 if side == "p" else 0)
                    world.root.stats["tnt_domain_titles_r_value"] = D(1 if side == "r" else 0)
                    world.root.stats["tnt_count_sel_artifact_p_value"] = D(1 if side == "p" else 0)
                    world.root.stats["tnt_count_sel_artifact_r_value"] = D(1 if side == "r" else 0)
                    world.root.lists["tnt_sel_artifact_p"] = [item] if side == "p" else []
                    world.root.lists["tnt_sel_artifact_r"] = [item] if side == "r" else []
                    actual = world.value(f"tnt_interest_ai_{term}_{direction}_factor_value", world.recipient)
                    expected = world.value(f"tnt_interest_{table_term}_{side}_factor_value")
                    self.assertEqual(actual, expected, (term, side, policy))

    def test_independent_actor_relation_and_threshold_do_not_reuse_recipient_affinity(self):
        world = AiWorld()
        world.actor.stats["opinions"][world.recipient.name] = D(-80)
        world.recipient.stats["opinions"][world.actor.name] = D(80)
        world.actor.stats["ai_greed"] = D(90)
        self.assertEqual(world.value("tnt_ai_relation_value"), 65)
        self.assertEqual(world.value("tnt_interest_ai_actor_relation_value"), -55)
        self.assertEqual(world.value("tnt_ai_threshold_value"), 0)
        self.assertEqual(world.value("tnt_interest_ai_actor_threshold_value"), 9)

    def test_voluntary_gate_requires_both_parties_and_stale_quote_is_recomputed(self):
        world = AiWorld()
        world.recipient.stats["gold"] = D(0)
        world.actor.stats["gold"] = D(1000)
        self.assertGreater(world.value("tnt_ai_deal_hook_low_value"), 0)
        accepted = GateWitness(world)
        accepted.run(self.effects["tnt_ai_world_do_hook_effect"])
        self.assertEqual(accepted.calls, ["tnt_ai_send_gold_effect", "tnt_ai_grant_hook_effect"])

        # The original quote is no longer usable once the recipient is saturated.
        world.recipient.stats["gold"] = D(10000)
        self.assertLessEqual(world.value("tnt_ai_deal_hook_low_value"), 0)
        rejected = GateWitness(world)
        rejected.run(self.effects["tnt_ai_world_do_hook_effect"])
        self.assertEqual(rejected.calls, [])

        world.recipient.stats["gold"] = D(0)
        world.actor.stats["opinions"][world.recipient.name] = D(-100)
        self.assertGreater(world.value("tnt_interest_ai_hook_low_recipient_score_value"), 0)
        self.assertLess(world.value("tnt_interest_ai_hook_low_actor_score_value"), 0)
        rejected = GateWitness(world)
        rejected.run(self.effects["tnt_ai_world_do_hook_effect"])
        self.assertEqual(rejected.calls, [])

    def test_unwanted_currency_has_no_positive_relation_side_payment(self):
        world = AiWorld()
        for lane in ("hook_low", "hook_high", "title", "vassal", "artifact", "wed"):
            world.recipient.stats["gold"] = D(100000)
            # Amount/base leaves are fixtures; the full quote and relation AST execute.
            for character in (world.actor, world.recipient, world.root):
                character.stats[LANES[lane]] = D(100)
            self.assertEqual(world.value(f"tnt_interest_ai_{lane}_recipient_relation_value"), 0)

    def test_pressure_terms_stay_exact_while_reserve_losses_change_cost(self):
        world = AiWorld()
        world.actor.stats["gold"] = D(0)
        world.recipient.stats["gold"] = D(100)
        for character in (world.root, world.actor, world.recipient):
            character.stats.update(tnt_ai_threat_points_value=D(100), tnt_ai_demand_gold_value=D(60),
                                   tnt_ai_hookcall_points_value=D(45), tnt_ai_hookcall_gold_value=D(60))
        for lane, pressure in (("ultimatum", D(100)), ("hookcall", D(45))):
            factor = world.value(f"tnt_interest_ai_{lane}_gold_surrender_factor_value", world.recipient)
            score = world.value(f"tnt_interest_ai_{lane}_recipient_score_value")
            self.assertEqual(score, pressure - (D(60) / 15) * factor + 80)
            self.assertGreater(factor, 1)
        world.actor.stats["gold"] = D(100000)
        self.assertEqual(world.value("tnt_interest_ai_ultimatum_actor_score_value"), 0)
        self.assertEqual(world.value("tnt_interest_ai_hookcall_actor_score_value"), 0)

    def test_submission_uses_explicit_target_and_rechecks_before_mutation(self):
        world = AiWorld()
        target = deepcopy(world.recipient)
        target.stats["is_at_war"] = False
        world.scopes["tnt_submission_target"] = target
        world.root.stats["tnt_ai_threat_points_value"] = D(120)
        self.assertEqual(world.value("tnt_interest_ai_submission_score_value"), -5)
        world.recipient.stats["is_at_war"] = True  # Irrelevant stale generic recipient.
        self.assertEqual(world.value("tnt_interest_ai_submission_score_value"), -5)
        world.root.stats["tnt_ai_threat_points_value"] = D(200)
        self.assertGreater(world.value("tnt_interest_ai_submission_score_value"), 0)
        world.policy = "off"
        self.assertEqual(world.value("tnt_interest_ai_submission_score_value"), 1)
        gate = one(one(self.effects["tnt_ai_world_do_submission_effect"], "if"), "limit")
        self.assertIn(("tnt_interest_ai_submission_score_value", ">", "0"), gate)

    def test_new_adapter_is_pure_and_every_active_world_lane_calls_the_live_quote(self):
        adapter = parse((SOURCE / "common/script_values/tnt_64_interest_ai_values.txt").read_text(encoding="utf-8-sig"))
        for key, _, body in walk(adapter):
            self.assertNotIn(key, {"set_variable", "save_scope_value_as", "save_temporary_scope_as", "move_budget_gold", "random"})
            self.assertFalse(key.startswith("var:"), key)
            if isinstance(body, str):
                self.assertNotIn("var:tnt_partner", body)
                self.assertNotIn("root", body)
        for lane in LANES:
            effect_name = "hook" if lane in ("hook_low", "hook_high") else lane
            guard_nodes = list(walk(self.effects[f"tnt_ai_world_do_{effect_name}_effect"]))
            self.assertIn((f"tnt_ai_deal_{lane}_value", ">", "0"), guard_nodes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args, remaining = parser.parse_known_args()
    SOURCE = args.source.resolve()
    currency_tests.SOURCE = SOURCE
    unittest.main(argv=[__file__, *remaining], verbosity=2)
