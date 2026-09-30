"""Execute marriage edit callbacks and verify their owner-scoped verdict lifecycle.

Pricing and native pair-record cleanup are explicit mocks here; the engine
harness exercises production staging and repricing. Unknown executed syntax fails.
"""
import unittest

from test_autobalance import DEFAULT_SOURCE, one
from test_compatibility_120 import definitions, walk


class Edits:
    def __init__(self, defs):
        self.defs = defs
        self.vars = {"player": {"tnt_ab_state": 2, "tnt_wed_principal": "left"},
                     "left": {"tnt_wed_partner": "right"}, "right": {}}
        self.scopes = {"tnt_picked": "left"}
        self.lists = {"tnt_wed_list": ["left"]}
        self.reprices = 0
        self.params = {}

    def expand(self, value):
        if isinstance(value, str):
            for key, replacement in self.params.items():
                value = value.replace(f"${key}$", replacement)
        return value

    def ref(self, value, current):
        value = self.expand(value)
        if value == "this": return current
        if value.startswith("scope:"): return self.scopes.get(value[6:])
        if value.startswith("var:"): return self.vars[current].get(value[4:])
        return int(value)

    def trigger(self, body, current):
        return all(self.condition(k, o, v, current) for k, o, v in body)

    def condition(self, key, op, val, current):
        key, val = self.expand(key), self.expand(val)
        if key == "NOT": return not self.trigger(val, current)
        if key in ("OR", "NOR"):
            result = any(self.condition(k, o, v, current) for k, o, v in val)
            return not result if key == "NOR" else result
        if key == "exists": return self.ref(val, current) is not None
        if key == "is_alive": return val == "yes"
        if key == "has_variable_list": return val in self.lists
        if key == "variable_list_size":
            return len(self.lists.get(one(val, "name"), [])) > int(one(val, "value"))
        if key == "is_target_in_variable_list":
            return self.ref(one(val, "target"), current) in self.lists.get(one(val, "name"), [])
        if key.startswith(("scope:", "var:")) and isinstance(val, list):
            target = self.ref(key, current)
            return target is not None and self.trigger(val, target)
        raise AssertionError((key, op, val))

    def effect(self, name, current="player", params=None):
        if name == "tnt_wed_reprice_all_effect":
            self.reprices += 1
            return
        if name == "tnt_wed_strip_effect":
            self.vars[current].pop("tnt_wed_partner", None)
            return
        previous = self.params
        self.params = {**previous, **(params or {})}
        body = self.defs[name]
        self.run(one(body, "effect", body), current)
        self.params = previous

    def run(self, nodes, current):
        i = 0
        while i < len(nodes):
            key, op, value = nodes[i]
            key, value = self.expand(key), self.expand(value)
            i += 1
            if key == "if":
                chain = [(key, value)]
                while i < len(nodes) and nodes[i][0] in ("else_if", "else"):
                    chain.append((nodes[i][0], nodes[i][2]))
                    i += 1
                for branch, body in chain:
                    if branch == "else" or self.trigger(one(body, "limit"), current):
                        self.run(body, current)
                        break
            elif key in ("limit", "variable"):
                continue
            elif key == "remove_variable":
                self.vars[current].pop(value, None)
            elif key == "set_variable":
                self.vars[current][self.expand(one(value, "name"))] = self.ref(one(value, "value"), current)
            elif key == "clear_variable_list":
                self.lists.pop(value, None)
            elif key == "every_in_list":
                for member in list(self.lists.get(one(value, "variable"), [])):
                    if self.trigger(one(value, "limit", []), member): self.run(value, member)
            elif key.startswith(("scope:", "var:")):
                target = self.ref(key, current)
                if target is not None: self.run(value, target)
                elif op != "?=": raise AssertionError(key)
            elif key == "save_temporary_scope_as":
                self.scopes[value] = current
            elif key.endswith("_effect"):
                params = {k: self.expand(v) for k, _, v in value} if isinstance(value, list) else None
                self.effect(key, current, params)
            else:
                raise AssertionError((key, op, value))


class VerdictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.defs = definitions(DEFAULT_SOURCE)

    def test_existing_pair_edits_clear_only_the_owners_verdict(self):
        for callback in ("tnt_wed_sync_effect", "tnt_wed_clear_all_effect", "tnt_wed_row_line_flip",
                         "tnt_wed_set_principal", "tnt_wed_grand_toggle", "tnt_wed_grand_clear"):
            with self.subTest(callback=callback):
                model = Edits(self.defs)
                model.vars["left"]["tnt_ab_state"] = 4  # Another character's independent state.
                model.effect(callback)
                self.assertNotIn("tnt_ab_state", model.vars["player"])
                self.assertEqual(model.vars["left"]["tnt_ab_state"], 4)

    def test_line_flip_reprices_on_both_directions(self):
        model = Edits(self.defs)
        model.effect("tnt_wed_row_line_flip")
        self.assertEqual(model.vars["left"]["tnt_wed_matri"], 1)
        self.assertEqual(model.reprices, 1)
        model.vars["player"]["tnt_ab_state"] = 2
        model.effect("tnt_wed_row_line_flip")
        self.assertNotIn("tnt_wed_matri", model.vars["left"])
        self.assertEqual(model.reprices, 2)
        self.assertNotIn("tnt_ab_state", model.vars["player"])

    def test_missing_row_does_not_change_line_or_verdict(self):
        model = Edits(self.defs)
        model.scopes.clear()
        model.effect("tnt_wed_row_line_flip")
        self.assertEqual(model.vars["player"]["tnt_ab_state"], 2)
        self.assertEqual(model.reprices, 0)

    def closure(self, name, seen=None):
        seen = set() if seen is None else seen
        if name in seen: return seen
        seen.add(name)
        for key, _, _ in walk(self.defs[name]):
            if key in self.defs and key.endswith("_effect"): self.closure(key, seen)
        return seen

    def test_all_pair_add_remove_and_gc_routes_reach_shared_invalidation(self):
        for entry in ("tnt_wed_stage_pair_effect", "tnt_wed_add_pair_effect", "tnt_wed_drop_pair_effect",
                      "tnt_wed_add", "tnt_wed_remove", "tnt_wed_gc_effect"):
            with self.subTest(entry=entry):
                self.assertTrue({"tnt_wed_sync_effect", "tnt_wed_clear_all_effect"} & self.closure(entry))

    def test_balancer_does_not_reach_marriage_invalidation(self):
        reached = self.closure("tnt_autobalance_effect")
        self.assertNotIn("tnt_wed_sync_effect", reached)
        self.assertNotIn("tnt_wed_clear_all_effect", reached)


if __name__ == "__main__": unittest.main(verbosity=2)
