"""Source-backed global threat-frequency regressions.

Executes the shipped policy, cooldown effect, common gates, GUI toggle, selected
threat value and paid/refused demand ASTs in a constrained character-scope model.
Native relation/army facts and raw pressure are explicit fixtures. Timed-variable
expiry uses simulated years: it proves our duration/ownership wiring, not CK3's
calendar, save serialization or engine execution. Whole-deal/world settlement
boundaries are checked structurally; these are not engine-smoke certification.
Unknown executed syntax raises instead of silently passing.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from test_autobalance import DEFAULT_SOURCE, D, Unsupported, World, one, parse


VARIABLE = "tnt_threat_cooldown"
POLICY = "tnt_threat_cooldown_years_value"
AVAILABLE = "tnt_threat_cooldown_available_trigger"
CONSUME = "tnt_start_threat_cooldown_effect"
OPTIONS = {"unlimited": 0, "1_year": 1, "5_years": 5, "10_years": 10}
FILES = (
    "common/game_rules/tnt_80_game_rules.txt",
    "common/script_values/tnt_57_threat_values.txt",
    "common/scripted_triggers/tnt_40_triggers.txt",
    "common/scripted_triggers/tnt_41_gates.txt",
    "common/scripted_triggers/tnt_43_preflight.txt",
    "common/scripted_guis/tnt_20_scripted_guis.txt",
    "common/scripted_effects/tnt_30_effects.txt",
    "common/scripted_effects/tnt_32_apply.txt",
    "common/scripted_effects/tnt_37_ai_offer.txt",
    "common/scripted_effects/tnt_38_ai_world.txt",
    "common/opinion_modifiers/tnt_61_opinions.txt",
    "common/decisions/tnt_86_uninstall.txt",
    "events/tnt_ai_events.txt",
)


def definitions(source, filename):
    return {key: body for key, _, body in parse((source / filename).read_text(encoding="utf-8-sig"))
            if isinstance(body, list)}


def walk(nodes, ancestors=()):
    for node in nodes:
        yield node, ancestors
        if isinstance(node[2], list):
            yield from walk(node[2], ancestors + (node,))


def named_nodes(nodes, name):
    return [(node, parents) for node, parents in walk(nodes) if node[0] == name]


class ThreatWorld(World):
    """World's strict AST evaluator plus scoped variables and named native facts."""

    def __init__(self, source=DEFAULT_SOURCE, setting="5_years"):
        super().__init__(source)
        self.defs = dict(self.defs)  # Never mutate World's shared definition cache.
        for filename in FILES:
            self.defs.update(definitions(self.source, filename))
        self.game_rules = set()
        if setting is not None:
            self.game_rules.add("tnt_threat_frequency_" + setting)
        self.character_vars = {"p": self.vars, "r": {}, "x": {}}
        self.expiries = {}
        self.opinions = {}
        self.now = D(0)
        self.scopes.update(third="x", actor="r", recipient="x", tnt_deal_partner="r")
        self.stats["x"] = deepcopy(self.stats["r"])
        self.identities["x"] = deepcopy(self.identities["r"])
        self.traits["x"] = set()
        self.governments["x"] = False
        for side in self.stats:
            self.stats[side].update(max_military_strength=D(10000), dread=D(50))
        self.leaves.update(tnt_threat_points_value=D(500), minor_dread_gain=D(10),
                           minor_dread_loss=D(-10), minor_prestige_loss=D(-75),
                           medium_prestige_loss=D(-150))
        self.leaves.pop("tnt_val_threat_p_value", None)
        self.independent = {side: True for side in self.stats}
        self.attack_allowed = True

    @contextmanager
    def current_vars(self, current):
        old = self.vars
        self.vars = self.character_vars[current]
        try:
            yield
        finally:
            self.vars = old

    def scope(self, token, current="p"):
        token = self.expand(token)
        if token == "this":
            return current
        if token.startswith("var:"):
            value = self.character_vars[current].get(token[4:])
            return value if value in self.character_vars else None
        return super().scope(token, current)

    def value(self, item, current="p"):
        with self.current_vars(current):
            return super().value(item, current)

    def exists(self, name, current):
        if self.expand(name) == "this":
            return current in self.character_vars
        with self.current_vars(current):
            return super().exists(name, current)

    def trigger(self, block, current="p"):
        with self.current_vars(current):
            return super().trigger(block, current)

    def condition(self, key, op, val, current):
        key = self.expand(key)
        if key == "this" and isinstance(val, list):
            return self.trigger(val, current)
        if key == "save_temporary_scope_as":
            self.scopes[self.expand(val)] = current
            return True
        if key == "has_variable":
            return self.expand(val) in self.character_vars[current]
        if key == "is_independent_ruler":
            return self.independent[current] == (val == "yes")
        if key == "is_allied_to":
            self.assert_scope(val, current)
            return False  # Explicit fixture: no allies.
        if key == "any_warden_hostage":
            if val != parse("home_court ?= $B$") and val != parse("home_court ?= $A$"):
                raise Unsupported("unexpected hostage fixture predicate")
            return False  # Explicit fixture: neither ruler has hostages.
        if key == "can_attack_in_hierarchy":
            self.assert_scope(val, current)
            return self.attack_allowed
        if key == "has_opinion_modifier":
            target = self.assert_scope(one(val, "target"), current)
            return (current, target, one(val, "modifier")) in self.opinions
        with self.current_vars(current):
            return super().condition(key, op, val, current)

    def assert_scope(self, token, current):
        target = self.scope(token, current)
        if target is None:
            raise Unsupported(f"missing fixture character {token}")
        return target

    def effect_block(self, block, current="p"):
        # Consume ordinary AST rows through the existing evaluator. Only these
        # engine-native state writes need character/timer-aware implementations.
        i = 0
        with self.current_vars(current):
            while i < len(block):
                key, op, body = block[i]
                key = self.expand(key)
                if key == "if":
                    i, _ = self.branch(block, i, current, "effect")
                    continue
                i += 1
                if key == "set_variable":
                    allowed = {"name", "value", "years"}
                    if any(k not in allowed for k, _, _ in body):
                        raise Unsupported("unsupported variable lifetime syntax")
                    name = self.expand(one(body, "name"))
                    self.vars[name] = self.value(one(body, "value"), current)
                    years = one(body, "years")
                    if years is not None:
                        self.expiries[current, name] = self.now + self.value(years, current)
                elif key == "remove_variable":
                    self.vars.pop(self.expand(body), None)
                    self.expiries.pop((current, self.expand(body)), None)
                elif key in ("add_dread", "add_prestige"):
                    self.stats[current][key[4:]] += self.value(body, current)
                elif key == "add_opinion":
                    modifier = one(body, "modifier")
                    if modifier != "tnt_threat_opinion":
                        raise Unsupported(f"unmodeled opinion {modifier}")
                    target = self.assert_scope(one(body, "target"), current)
                    self.opinions[current, target, modifier] = self.now + D(one(self.defs[modifier], "years"))
                else:
                    super().effect_block([(key, op, body)], current)

    def advance(self, years):
        self.now += D(str(years))
        for (holder, variable), expiry in list(self.expiries.items()):
            if expiry <= self.now:
                self.character_vars[holder].pop(variable, None)
                del self.expiries[holder, variable]
        self.opinions = {pair: expiry for pair, expiry in self.opinions.items() if expiry > self.now}

    def available(self, actor="root"):
        return self.scripted_trigger(AVAILABLE, {"A": actor})

    def can_threaten(self, actor="root", victim="scope:third", demand=False):
        return self.scripted_trigger("tnt_can_demand_trigger" if demand else "tnt_can_threat_trigger",
                                     {"A": actor, "B": victim})


class ThreatFrequencyTests(unittest.TestCase):
    source = DEFAULT_SOURCE

    def world(self, setting="5_years"):
        return ThreatWorld(self.source, setting)

    def test_four_options_default_zero_and_unchanged_strength_identifiers(self):
        defs = definitions(self.source, FILES[0])
        rule = defs["tnt_threat_frequency"]
        self.assertEqual(one(rule, "default"), "tnt_threat_frequency_unlimited")
        self.assertEqual({key for key, _, value in rule if isinstance(value, list) and key != "categories"},
                         {"tnt_threat_frequency_" + option for option in OPTIONS})
        strength = defs["tnt_threat_scale"]
        self.assertEqual(one(strength, "default"), "tnt_threat_scale_normal")
        for option, expected in (("rare", "2.5"), ("normal", "5"), ("frequent", "7.5"), ("constant", "10")):
            self.assertIsNotNone(one(strength, "tnt_threat_scale_" + option))
            world = self.world()
            world.game_rules.add("tnt_threat_scale_" + option)
            self.assertEqual(world.value("tnt_threat_scale_value"), D(expected))

    def test_actual_policy_durations_and_missing_setting_fallback(self):
        for option, years in {**OPTIONS, None: 0, "unknown_future_setting": 0}.items():
            with self.subTest(option=option):
                world = self.world(option)
                self.assertEqual(world.value(POLICY), years)
                self.assertTrue(world.available())

    def test_actor_scoped_timer_expiry_and_victim_not_charged(self):
        for option, years in OPTIONS.items():
            for actor in ("p", "r"):
                with self.subTest(option=option, actor=actor):
                    world = self.world(option)
                    world.effect(CONSUME, current=actor)
                    self.assertEqual(VARIABLE in world.character_vars[actor], years > 0)
                    for other in set(world.character_vars) - {actor}:
                        self.assertNotIn(VARIABLE, world.character_vars[other])
                    if years:
                        self.assertEqual(world.expiries[actor, VARIABLE], years)
                        handle = "root" if actor == "p" else "scope:actor"
                        self.assertFalse(world.available(handle))
                        world.advance(D(years) - D("0.001"))
                        self.assertFalse(world.available(handle))
                        world.advance("0.001")
                        self.assertTrue(world.available(handle))
                        self.assertNotIn(VARIABLE, world.character_vars[actor])

    def test_zero_or_missing_setting_ignores_preexisting_timer(self):
        for option in ("unlimited", None):
            world = self.world(option)
            world.character_vars["p"][VARIABLE] = D(1)
            world.expiries["p", VARIABLE] = D(10)
            self.assertTrue(world.available())
            self.assertTrue(world.can_threaten())
            self.assertTrue(world.can_threaten(demand=True))

    def test_cooldown_blocks_every_target_and_both_player_ai_gates(self):
        for option in ("1_year", "5_years", "10_years"):
            world = self.world(option)
            for victim in ("var:tnt_partner", "scope:third"):
                for demand in (False, True):
                    self.assertTrue(world.can_threaten(victim=victim, demand=demand))
            world.effect(CONSUME)
            for victim in ("var:tnt_partner", "scope:third"):
                for demand in (False, True):
                    self.assertFalse(world.can_threaten(victim=victim, demand=demand))
            self.assertTrue(world.can_threaten("scope:actor", "scope:third", demand=True))

    def test_fifteen_year_pair_memory_survives_shorter_global_timer(self):
        world = self.world("1_year")
        world.effect(CONSUME)
        world.effect_block(parse("add_opinion = { target = root modifier = tnt_threat_opinion }"), "r")
        world.advance(1)
        self.assertTrue(world.can_threaten(victim="scope:third"))
        self.assertFalse(world.can_threaten(victim="var:tnt_partner"))
        world.game_rules = {"tnt_threat_frequency_unlimited"}
        self.assertFalse(world.can_threaten(victim="var:tnt_partner"))
        world.advance(14)
        self.assertTrue(world.can_threaten(victim="var:tnt_partner"))

    def test_stale_selected_threat_has_zero_pressure_and_fails_preflight_guard(self):
        world = self.world()
        world.character_vars["p"]["tnt_threat_p"] = D(1)
        world.params = {"PLAYER": "root", "PARTNER": "var:tnt_partner"}
        guards = [node for node, _ in named_nodes(world.defs["tnt_deal_preflight_trigger"], "trigger_if")
                  if one(node[2], "tnt_can_threat_trigger") is not None]
        self.assertEqual(len(guards), 1)
        self.assertTrue(world.trigger(guards))
        self.assertEqual(world.value("tnt_val_threat_p_value"), 500)
        world.effect(CONSUME)
        self.assertFalse(world.trigger(guards))
        self.assertEqual(world.value("tnt_val_threat_p_value"), 0)
        world.character_vars["p"].pop("tnt_threat_p")
        self.assertTrue(world.trigger(guards), "ordinary diplomacy must remain permitted")

    def test_blocked_gui_can_deselect_but_cannot_select_or_consume_a_draft(self):
        world = self.world()
        gui = world.defs["tnt_threat_p_toggle"]
        # The native checkbox enables selected rows independently of is_valid,
        # which must continue to describe the unmet cooldown condition.
        window = (self.source / "gui/tnt_diplomacy_window.gui").read_text(encoding="utf-8-sig")
        self.assertIn('enabled = "[Or(TntOn(\'tnt_threat_p\'), TntValid(\'tnt_threat_p_toggle\'))]"', window)
        self.assertTrue(world.trigger(one(gui, "is_valid")))
        world.effect_block(one(gui, "effect"))
        self.assertIn("tnt_threat_p", world.character_vars["p"])
        self.assertNotIn(VARIABLE, world.character_vars["p"])
        world.effect(CONSUME)
        self.assertFalse(world.trigger(one(gui, "is_valid")))
        self.assertTrue("tnt_threat_p" in world.character_vars["p"] or world.trigger(one(gui, "is_valid")))
        world.effect_block(one(gui, "effect"))
        self.assertNotIn("tnt_threat_p", world.character_vars["p"])
        self.assertFalse(world.trigger(one(gui, "is_valid")))
        world.effect_block(one(gui, "effect"))
        self.assertNotIn("tnt_threat_p", world.character_vars["p"], "stale UI execution must not add a blocked threat")
        self.assertEqual(world.expiries["p", VARIABLE], 5)

    def test_manual_commit_consumes_only_selected_successful_threat_on_root(self):
        world = self.world()
        body = world.defs["tnt_apply_deal_effect"]
        outer = one(body, "if")
        self.assertEqual(one(one(outer, "limit"), "tnt_deal_preflight_trigger"),
                         parse("PLAYER = root PARTNER = scope:tnt_deal_partner"))
        calls = named_nodes(body, CONSUME)
        self.assertEqual(len(calls), 1)
        _, parents = calls[0]
        branch = next(node for node in reversed(parents) if node[0] == "if")
        self.assertEqual(one(branch[2], "limit"), parse("exists = var:tnt_threat_p var:tnt_threat_p > 0"))
        world.effect_block([branch])
        self.assertNotIn(VARIABLE, world.character_vars["p"])
        world.character_vars["p"]["tnt_threat_p"] = D(1)
        world.effect_block([branch])
        self.assertIn(VARIABLE, world.character_vars["p"])
        self.assertNotIn(VARIABLE, world.character_vars["r"])
        self.assertIn(("r", "p", "tnt_threat_opinion"), world.opinions)

    def test_incoming_paid_and_valid_refused_demand_consume_ai_not_player(self):
        for name in ("tnt_demand_paid_effect", "tnt_demand_refused_effect"):
            world = self.world()
            world.character_vars["p"]["tnt_demand_pts"] = D(500)
            before = world.stats["p"]["prestige"]
            world.effect(name)
            self.assertIn(VARIABLE, world.character_vars["r"])
            self.assertNotIn(VARIABLE, world.character_vars["p"])
            self.assertIn(("p", "r", "tnt_threat_opinion"), world.opinions)
            self.assertEqual(world.stats["p"]["prestige"] - before,
                             -150 if name == "tnt_demand_refused_effect" else 0)

    def test_invalid_refusal_does_not_start_or_extend_global_timer(self):
        world = self.world()
        world.attack_allowed = False
        world.effect("tnt_demand_refused_effect")
        self.assertNotIn(VARIABLE, world.character_vars["r"])
        world = self.world()
        world.effect(CONSUME, current="r")
        world.advance(1)
        world.effect("tnt_demand_refused_effect")
        self.assertEqual(world.expiries["r", VARIABLE], 5, "stale response must not restart the timer")

    def test_pending_ai_pay_checks_actor_cooldown_before_any_transfer(self):
        events = definitions(self.source, "events/tnt_ai_events.txt")
        options = [node[2] for event in events.values() for node, _ in named_nodes(event, "option")
                   if one(node[2], "name") == "tnt_ai_demand_opt_pay"]
        self.assertEqual(len(options), 1)
        pay = one(options[0], "if")
        limit = one(pay, "limit")
        self.assertEqual(one(limit, AVAILABLE), parse("A = scope:tnt_deal_partner"))
        self.assertIsNotNone(one(limit, "tnt_deal_preflight_trigger"))
        self.assertIsNotNone(one(pay, "tnt_apply_deal_effect"))
        self.assertIsNotNone(one(pay, "tnt_demand_paid_effect"))
        stale = one(options[0], "else")
        self.assertFalse(named_nodes(stale, "tnt_apply_deal_effect"))
        self.assertFalse(named_nodes(stale, CONSUME))

    def test_all_five_settlement_sites_own_correct_actor_and_no_draft_site_consumes(self):
        expected = {
            "tnt_apply_deal_effect": None,
            "tnt_demand_paid_effect": "scope:tnt_deal_partner",
            "tnt_demand_refused_effect": "scope:tnt_deal_partner",
            "tnt_ai_world_do_submission_effect": "scope:actor",
            "tnt_ai_world_do_ultimatum_effect": "scope:actor",
        }
        actual = {}
        for file in (self.source / "common/scripted_effects").glob("*.txt"):
            for name, body in definitions(self.source, file.relative_to(self.source)).items():
                for _, parents in named_nodes(body, CONSUME):
                    scopes = [key for key, _, _ in parents if key == "root" or key.startswith(("scope:", "var:"))]
                    self.assertNotIn(name, actual, "cooldown consumed twice at one settlement")
                    actual[name] = scopes[-1] if scopes else None
        self.assertEqual(actual, expected)
        world = self.world()
        cash = one(world.defs["tnt_ai_world_do_ultimatum_effect"], "if")
        self.assertEqual(one(one(cash, "limit"), AVAILABLE), parse("A = scope:actor"))
        submission = one(world.defs["tnt_ai_world_do_submission_effect"], "if")
        self.assertIsNotNone(one(one(submission, "limit"), "tnt_ai_coercive_fealty_pair_trigger"))
        calls = named_nodes(world.defs["tnt_ai_coercive_fealty_pair_trigger"], "tnt_can_threat_trigger")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][2], parse("A = $A$ B = $B$"))

    def test_one_duration_read_family_one_timed_writer_and_uninstall_only_removal(self):
        writers, removals, rule_readers = [], [], []
        for file in (self.source / "common").rglob("*.txt"):
            relative = file.relative_to(self.source).as_posix()
            for node, _ in walk(parse(file.read_text(encoding="utf-8-sig"))):
                key, _, body = node
                if key == "set_variable" and one(body, "name") == VARIABLE:
                    writers.append((relative, body))
                if key == "remove_variable" and body == VARIABLE:
                    removals.append(relative)
                if key == "has_game_rule" and isinstance(body, str) and body.startswith("tnt_threat_frequency_"):
                    rule_readers.append(relative)
        self.assertEqual(len(writers), 1)
        self.assertEqual(one(writers[0][1], "years"), POLICY)
        self.assertEqual(one(writers[0][1], "value"), "1")
        self.assertEqual(set(rule_readers), {"common/script_values/tnt_57_threat_values.txt"})
        self.assertEqual(len(rule_readers), 3)
        self.assertGreaterEqual(len(removals), 2, "root and other living characters must be swept")
        self.assertEqual(set(removals), {"common/decisions/tnt_86_uninstall.txt"})
        uninstall = definitions(self.source, "common/decisions/tnt_86_uninstall.txt")["tnt_uninstall_decision"]
        walks = named_nodes(uninstall, "every_living_character")
        self.assertEqual(len(walks), 1)
        self.assertTrue(any(node[0] == "exists" and node[2] == "var:" + VARIABLE for node, _ in walk(walks[0][0][2])))
        self.assertTrue(any(node[0] == "remove_variable" and node[2] == VARIABLE for node, _ in walk(walks[0][0][2])))

    def test_regression_detects_missing_global_guard_and_unknown_syntax(self):
        world = self.world()
        world.effect(CONSUME)
        self.assertFalse(world.can_threaten())
        world.defs = deepcopy(world.defs)
        world.defs[AVAILABLE] = parse("always = yes")
        with self.assertRaises(AssertionError):
            self.assertFalse(world.can_threaten(), "a different target must still be blocked")
        with self.assertRaises(Unsupported):
            world.trigger(parse("invented_threat_condition = yes"))
        with self.assertRaises(Unsupported):
            world.effect_block(parse("set_variable = { name = x value = 1 invented_lifetime = 5 }"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()
    ThreatFrequencyTests.source = args.source
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ThreatFrequencyTests))
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps({
            "tests_run": result.testsRun, "success": result.wasSuccessful(),
            "failures": [(str(test), trace) for test, trace in result.failures],
            "errors": [(str(test), trace) for test, trace in result.errors],
            "source": str(args.source),
            "source_sha256": {filename: hashlib.sha256((args.source / filename).read_bytes()).hexdigest()
                              for filename in (*FILES, "gui/tnt_diplomacy_window.gui")},
            "limitations": __doc__,
        }, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())


if __name__ == "__main__":
    main()
