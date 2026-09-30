"""CK3 1.20 source regressions and bounded current-game dependency audit.

The fixture evaluator executes shipped ASTs for scope redirects, Rite decisions,
lineality prices, Jizya availability and the administrative noble-family gate.
It is not an engine simulation. The optional --game audit checks active token
coverage, named helper definitions and government rule/mechanic arguments;
it cannot establish native scope typing, GUI behavior or gameplay compatibility.
"""
from __future__ import annotations

import argparse
import json
import re
import unittest
from pathlib import Path

from test_autobalance import DEFAULT_SOURCE, TOKEN, one, parse

SOURCE = DEFAULT_SOURCE
GAME = None


def walk(nodes):
    for node in nodes:
        yield node
        if isinstance(node[2], list):
            yield from walk(node[2])


def definitions(source):
    result = {}
    for folder in ("common", "events"):
        for file in sorted((source / folder).rglob("*.txt")):
            for key, _, body in parse(file.read_text(encoding="utf-8-sig")):
                if isinstance(body, list):
                    result[key] = body
    return result


class Fixture:
    """Fail on unknown executed syntax; native state is explicit fixture data."""

    def __init__(self, defs):
        self.defs = defs
        self.people = {
            "player": {"matchmaker": "player", "is_ai": False, "is_landed": True,
                       "vars": {"tnt_open": 1, "tnt_partner": "partner"},
                       "faith": "faith_player", "rite": "rite_player"},
            "partner": {"matchmaker": "partner", "is_ai": True, "is_landed": True,
                        "is_ruler": True, "is_female": False, "dynasty": "house",
                        "faith": "faith_partner", "rite": "rite_partner"},
            "left": {"matchmaker": "player", "is_female": True},
            "right": {"matchmaker": "partner", "is_female": True},
            "puppet": {"matchmaker": "puppet", "vars": {}},
            "faith_player": {}, "faith_partner": {},
            "rite_player": {}, "rite_partner": {},
        }
        self.scopes = {"actor": "player", "puppet_or_actor": "player",
                       "recipient": "partner", "tnt_me": "player", "tnt_p": "partner",
                       "tnt_sp": "left", "tnt_sr": "partner"}
        # These two unchanged mechanisms have their own source checks; the
        # fixtures isolate the compatibility decision's inputs, not its output.
        self.leaves = {"tnt_pair_is_matri_trigger": True, "tnt_ob_feudal_value": 1}

    def resolve(self, name, current):
        if name == "this":
            return current
        if name.startswith("scope:"):
            head, *tail = name[6:].split(".")
            value = self.scopes.get(head)
        elif name.startswith("var:"):
            return self.people[current].get("vars", {}).get(name[4:])
        else:
            head, *tail = name.split(".")
            value = self.people[current].get(head)
        for field in tail:
            value = self.people.get(value, {}).get(field)
        return value

    def condition(self, key, op, value, current):
        if key == "NOT":
            return not self.trigger(value, current)
        if key in ("OR", "NOR"):
            answer = any(self.condition(k, o, v, current) for k, o, v in value)
            return not answer if key == "NOR" else answer
        if key == "AND":
            return self.trigger(value, current)
        if key == "exists":
            return self.resolve(value, current) is not None
        if key == "always":
            return value == "yes"
        if key == "trigger_if":
            return (not self.trigger(one(value, "limit"), current)
                    or self.trigger([n for n in value if n[0] != "limit"], current))
        if key in ("has_realm_law", "has_doctrine", "has_doctrine_parameter",
                   "rite_has_doctrine", "rite_has_parameter"):
            field = {"has_realm_law": "laws", "has_doctrine": "doctrines",
                     "rite_has_doctrine": "doctrines", "has_doctrine_parameter": "parameters",
                     "rite_has_parameter": "parameters"}[key]
            return value in self.people[current].get(field, set())
        if key in ("is_female", "is_male"):
            female = self.people[current].get("is_female", False)
            return (female if key == "is_female" else not female) == (value == "yes")
        if key in ("is_ai", "is_landed", "is_ruler"):
            return self.people[current].get(key, False) == (value == "yes")
        if key == "government_has_mechanic":
            return value in self.people[current].get("mechanics", set())
        if key == "any_held_title":
            return any(self.trigger(value, title) for title in self.people[current].get("titles", ()))
        if key == "is_noble_family_title":
            return self.people[current].get(key, False) == (value == "yes")
        if key == "sex_opposite_of":
            return (self.people[current].get("is_female", False)
                    != self.people[self.resolve(value, current)].get("is_female", False))
        if key == "player_heir_position":
            return self.people[current].get("heirs", {}).get(int(one(value, "value"))) == self.resolve(one(value, "target"), current)
        if key in self.leaves:
            left = self.leaves[key]
            right = value == "yes" if value in ("yes", "no") else int(value)
        elif key in ("this", "faith", "dynasty") or key.startswith(("scope:", "var:")) or key == "rite":
            left = self.resolve(key, current)
            if isinstance(value, list):
                return left is not None and self.trigger(value, left)
            right = self.resolve(value, current)
            if right is None and value.lstrip("-").isdigit():
                right = int(value)
        else:
            raise AssertionError(f"unimplemented condition {key}")
        if op in ("=", "?="):
            return left is not None and left == right
        if op == ">":
            return left is not None and left > right
        raise AssertionError(f"unimplemented comparison {op}")

    def trigger(self, nodes, current="player"):
        return all(self.condition(k, o, v, current) for k, o, v in nodes)

    def execute(self, nodes, current="player", numeric=False, total=0):
        i = 0
        while i < len(nodes):
            key, op, value = nodes[i]
            i += 1
            if key == "if":
                chain = [(key, value)]
                while i < len(nodes) and nodes[i][0] in ("else_if", "else"):
                    chain.append((nodes[i][0], nodes[i][2]))
                    i += 1
                for branch, body in chain:
                    if branch == "else" or self.trigger(one(body, "limit"), current):
                        total = self.execute(body, current, numeric, total)
                        break
            elif key == "limit":
                continue
            elif key in ("save_scope_as", "save_temporary_scope_as"):
                self.scopes[value] = current
            elif key == "remove_variable":
                self.people[current].setdefault("vars", {}).pop(value, None)
            elif key == "set_variable":
                self.people[current].setdefault("vars", {})[one(value, "name")] = int(one(value, "value"))
            elif numeric and key in ("value", "add"):
                operand = self.execute(value, current, True) if isinstance(value, list) else int(value)
                total = operand if key == "value" else total + operand
            elif key.startswith(("scope:", "var:")) or key == "matchmaker":
                target = self.resolve(key, current)
                if target is None and op == "?=":
                    continue
                if target is None:
                    raise AssertionError(f"missing scope {key}")
                total = self.execute(value, target, numeric, total)
            else:
                raise AssertionError(f"unimplemented command {key}")
        return total


class CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.defs = definitions(SOURCE)

    def setUp(self):
        self.world = Fixture(self.defs)

    def test_default_line_uses_personal_rite_over_faith(self):
        w = self.world
        w.people["rite_player"]["parameters"] = {"female_dominated_law"}
        w.execute(self.defs["tnt_marriage_default_line_effect"])
        self.assertEqual(w.people["player"]["vars"]["tnt_marriage_matri"], 1)
        w.people["rite_player"]["parameters"] = set()
        w.people["faith_player"]["parameters"] = {"female_dominated_law"}
        w.execute(self.defs["tnt_marriage_default_line_effect"])
        self.assertNotIn("tnt_marriage_matri", w.people["player"]["vars"])

    def test_female_realm_laws_still_set_default_line(self):
        for law in ("female_only_law", "female_preference_law"):
            with self.subTest(law=law):
                self.world.people["player"]["laws"] = {law}
                self.world.execute(self.defs["tnt_marriage_default_line_effect"])
                self.assertEqual(self.world.people["player"]["vars"]["tnt_marriage_matri"], 1)

    def test_lineality_price_uses_partners_rite_in_both_gender_directions(self):
        for female in (False, True):
            with self.subTest(female=female):
                w = Fixture(self.defs)
                w.people["partner"]["is_female"] = female
                w.people["left"]["is_female"] = not female
                w.leaves["tnt_pair_is_matri_trigger"] = not female
                doctrine = "doctrine_gender_female_dominated" if female else "doctrine_gender_male_dominated"
                w.people["rite_partner"]["doctrines"] = {doctrine}
                body = self.defs["tnt_marriage_lineality_cost_value"]
                self.assertEqual(w.execute(body, numeric=True), 1000)
                w.people["rite_partner"]["doctrines"] = set()
                w.people["faith_partner"]["doctrines"] = {doctrine}
                self.assertEqual(w.execute(body, numeric=True), 100)
                w.leaves["tnt_pair_is_matri_trigger"] = female
                self.assertEqual(w.execute(body, numeric=True), 0)

    def test_same_sex_lineality_remains_free(self):
        w = self.world
        w.people["partner"]["is_female"] = True
        w.people["rite_partner"]["doctrines"] = {"doctrine_gender_female_dominated"}
        w.leaves["tnt_pair_is_matri_trigger"] = False
        self.assertEqual(w.execute(self.defs["tnt_marriage_lineality_cost_value"], numeric=True), 0)

    def test_jizya_follows_contract_faith_in_both_fealty_directions(self):
        for side, liege in (("p", "partner"), ("r", "player")):
            for same_faith in (False, True):
                with self.subTest(side=side, same_faith=same_faith):
                    w = Fixture(self.defs)
                    w.people["player"]["vars"][f"tnt_vassal_{side}"] = 1
                    if same_faith:
                        w.people["partner"]["faith"] = "faith_player"
                    w.people[w.people[liege]["faith"]]["parameters"] = {"unlock_jizya_contract"}
                    body = self.defs["tnt_ob_revoke_ok_value"]
                    self.assertEqual(w.execute(body, numeric=True), int(same_faith))
                    w.people[w.people[liege]["faith"]]["parameters"] = set()
                    w.people[w.people[liege]["rite"]]["parameters"] = {"unlock_jizya_contract"}
                    self.assertEqual(w.execute(body, numeric=True), 1)

    def test_picker_redirect_normalizes_both_aliases_and_is_idempotent(self):
        w = self.world
        w.scopes.update(actor="left", puppet_or_actor="left", recipient="right")
        body = one(self.defs["tnt_stage_marriage_interaction"], "redirect")
        w.execute(body)
        expected = {"actor": "player", "puppet_or_actor": "player", "recipient": "partner",
                    "secondary_actor": "left", "secondary_recipient": "right"}
        for key, value in expected.items():
            self.assertEqual(w.scopes[key], value)
        w.execute(body)
        for key, value in expected.items():
            self.assertEqual(w.scopes[key], value)
        self.assertEqual(w.people["player"]["vars"]["tnt_partner"], "partner")
        self.assertNotIn("vars", w.people["left"])

    def test_picker_refuses_proxy_and_wrong_partner_without_writing_state(self):
        w = self.world
        shown = one(self.defs["tnt_stage_marriage_interaction"], "is_shown")
        self.assertTrue(w.trigger(shown))
        w.scopes["puppet_or_actor"] = "puppet"
        self.assertFalse(w.trigger(shown))
        self.assertEqual(w.people["puppet"]["vars"], {})
        w.scopes.pop("puppet_or_actor")
        self.assertTrue(w.trigger(shown))
        w.scopes["recipient"] = "puppet"
        self.assertFalse(w.trigger(shown))

    def test_picker_keeps_right_ruler_pick_and_existing_secondary(self):
        w = self.world
        redirect = one(self.defs["tnt_stage_marriage_interaction"], "redirect")
        w.execute(redirect)
        self.assertEqual(w.scopes["secondary_recipient"], "partner")
        w.scopes["secondary_recipient"] = "right"
        w.execute(redirect)
        self.assertEqual(w.scopes["secondary_recipient"], "right")
        self.assertEqual(w.scopes["recipient"], "partner")

    def test_front_door_has_same_proxy_guard(self):
        picker = one(one(self.defs["tnt_stage_marriage_interaction"], "is_shown"), "trigger_if")
        opener = one(one(self.defs["tnt_open_negotiations"], "is_shown"), "trigger_if")
        self.assertEqual(opener, picker)

    def test_administrative_noble_family_gate_uses_actual_mechanic(self):
        gates = [body for key, _, body in walk(self.defs["tnt_subject_candidate_trigger"])
                 if key == "trigger_if" and any(k in ("government_allows", "government_has_mechanic")
                                                for k, _, _ in walk(one(body, "limit")))]
        self.assertEqual(len(gates), 1)
        w = self.world
        w.people["noble_house"] = {"is_noble_family_title": True}
        w.people["county"] = {"is_noble_family_title": False}
        for mechanics, titles, expected in (
                ({"administrative"}, ("noble_house",), False),
                ({"administrative"}, ("noble_house", "county"), True),
                ({"administrative"}, (), False),
                ({"feudal"}, ("noble_house",), True)):
            with self.subTest(mechanics=mechanics, titles=titles):
                w.people["player"].update(mechanics=mechanics, titles=titles)
                self.assertEqual(w.condition("trigger_if", "=", gates[0], "player"), expected)

    def test_government_audit_distinguishes_rule_and_mechanic_enums(self):
        if not GAME:
            self.skipTest("pass --game for typed government-argument audit")
        rules, mechanics = government_contract(GAME)
        self.assertIn("administrative", mechanics)
        self.assertNotIn("administrative", rules)
        self.assertIn("create_cadet_branches", rules)
        self.assertEqual(audit_government_arguments(
            [("government_allows", "=", "administrative")], rules, mechanics),
            [{"trigger": "government_allows", "argument": "administrative"}])
        self.assertEqual(audit_government_arguments(
            [("government_has_mechanic", "=", "administrative"),
             ("government_allows", "=", "create_cadet_branches")], rules, mechanics), [])

    def test_native_marriage_owns_legality_but_staging_does_not_marry(self):
        picker = self.defs["tnt_stage_marriage_interaction"]
        self.assertEqual(one(picker, "interface"), "marriage")
        self.assertIsNone(one(picker, "special_interaction"))
        for name in ("tnt_can_stage_pair_trigger", "tnt_stage_pair_available_trigger", "tnt_wed_one_pair_effect"):
            self.assertIn("can_marry_character_trigger", {k for k, _, _ in walk(self.defs[name])})
        for name in ("populate_actor_list", "populate_recipient_list", "on_accept"):
            self.assertIsNotNone(one(one(picker, name), "scope:actor"))

    def test_runtime_dependencies_present_in_installed_game(self):
        if not GAME:
            self.skipTest("pass --game for current-upstream dependency audit")
        audit = audit_upstream(SOURCE, GAME)
        self.assertEqual(audit["unresolved_runtime_keys"], [])
        self.assertEqual(audit["unresolved_named_helpers"], [])
        self.assertEqual(audit["helper_parameter_mismatches"], [])
        self.assertEqual(audit["unresolved_government_arguments"], [])
        print(json.dumps(audit, indent=2))


def government_contract(game):
    """Read typed rules from their declaration block, not arbitrary token hits.

    Government files include typed color literals outside the supported script
    parser. Tokenize those files, brace-match only government_rules, and parse
    that narrow block; collect mechanic_type separately from real definitions.
    """
    rules, mechanics = set(), set()
    directory = game / "common/governments"
    for path in [directory / "_governments.info", *sorted(directory.glob("*.txt"))]:
        tokens = [m.group() for m in TOKEN.finditer(path.read_text(encoding="utf-8-sig"))
                  if not m.group().startswith("#")]
        for index in range(len(tokens) - 2):
            if tokens[index:index + 2] == ["mechanic_type", "="] and path.suffix == ".txt":
                mechanics.add(tokens[index + 2].strip('"'))
            if tokens[index:index + 3] != ["government_rules", "=", "{"]:
                continue
            depth, end = 1, index + 3
            while end < len(tokens) and depth:
                depth += (tokens[end] == "{") - (tokens[end] == "}")
                end += 1
            if depth:
                raise ValueError(f"Unclosed government_rules block in {path}")
            rules.update(k for k, _, _ in parse(" ".join(tokens[index + 3:end - 1])))
    return rules, mechanics


def audit_government_arguments(nodes, rules, mechanics):
    expected = {"government_allows": rules, "government_disallows": rules,
                "government_has_mechanic": mechanics}
    return [{"trigger": key, "argument": value} for key, _, value in nodes
            if key in expected and (not isinstance(value, str) or value not in expected[key])]


def audit_upstream(source, game):
    runtime = []
    for folder in ("common", "events"):
        for path in sorted((source / folder).rglob("*.txt")):
            runtime.extend(walk(parse(path.read_text(encoding="utf-8-sig"))))
    keys = {k for k, _, _ in runtime if re.fullmatch("[a-z][a-z0-9_]*", k) and not k.startswith("tnt_")}
    named = set()
    for key, _, value in runtime:
        for token in (key, value):
            if isinstance(token, str) and re.fullmatch(r"[a-z][a-z0-9_]*(?:_trigger|_effect|_value)", token) and not token.startswith("tnt_"):
                named.add(token)
    named.discard("hidden_effect")  # Native control block, not a scripted helper.
    tokens, helpers = set(), {}
    for folder in ("common", "events"):
        for path in sorted((game / folder).rglob("*.txt")):
            content = path.read_text(encoding="utf-8-sig", errors="replace")
            tokens.update(m.group().strip('"') for m in TOKEN.finditer(content) if not m.group().startswith("#"))
            if path.parent.name in ("scripted_triggers", "scripted_effects", "script_values", "scripted_modifiers"):
                for key, _, value in parse(content):
                    if key in named:
                        helpers[key] = value
    mismatches = []
    for key, _, value in runtime:
        if key in helpers and isinstance(value, list):
            required = set(re.findall(r"\$([A-Z_0-9]+)\$", str(helpers[key])))
            supplied = {k for k, _, _ in value}
            if required != supplied:
                mismatches.append({"helper": key, "required": sorted(required), "supplied": sorted(supplied)})
    government_rules, government_mechanics = government_contract(game)
    government_reads = [{"trigger": key, "argument": value} for key, _, value in runtime
                        if key in ("government_allows", "government_disallows", "government_has_mechanic")]
    return {"game": str(game), "runtime_plain_key_count": len(keys),
            "named_helpers": sorted(named), "unresolved_runtime_keys": sorted(keys - tokens),
            "unresolved_named_helpers": sorted(named - helpers.keys()),
            "helper_parameter_mismatches": mismatches,
            "government_reads": government_reads,
            "native_government_rule_count": len(government_rules),
            "native_government_mechanics": sorted(government_mechanics),
            "unresolved_government_arguments": audit_government_arguments(runtime, government_rules, government_mechanics),
            "limit": "Token presence and helper parameters do not prove native scope typing or engine behavior."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--game", type=Path)
    args, extra = parser.parse_known_args()
    SOURCE, GAME = args.source, args.game
    unittest.main(argv=[__file__, *extra])
