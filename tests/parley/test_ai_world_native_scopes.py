"""Execute the AI-world native-call adapter against the current CK3 scope contract.

The model executes only scope/value saves and the shared vassal adapter. Native
title mutations are not simulated: their actual liege, opinion and catalyst
expressions are read from the installed helper and resolved against the adapter's
output. A focused engine run must still prove the resulting vassal relationship.
"""
import argparse
import copy
from pathlib import Path
import unittest

from test_autobalance import DEFAULT_SOURCE, one, parse
from test_compatibility_120 import walk


SOURCE = DEFAULT_SOURCE
GAME = Path("D:/SteamLibrary/steamapps/common/Crusader Kings III/game")
ADAPTER = "tnt_ai_world_apply_vassal_effect"
NATIVE = "offer_vassalization_interaction_effect"
OPTIONS = {"high_obligations", "low_obligations", "religious_exemption",
           "religious_exemption_clan"}


class NativeCall:
    def __init__(self, native, stale=None):
        self.scopes = {"actor": "new_liege", "recipient": "new_vassal"}
        if stale is not None:
            self.scopes["puppet_or_actor"] = stale
        self.native = native
        self.observed = []

    def resolve(self, atom):
        if not atom.startswith("scope:"):
            raise AssertionError(f"Unexpected native reference {atom}")
        return self.scopes[atom[6:]]

    def run(self, nodes, current):
        for key, op, value in nodes:
            if key.startswith("scope:") and isinstance(value, list):
                self.run(value, self.resolve(key))
            elif key == "save_temporary_scope_as":
                self.scopes[value] = current
            elif key == "save_scope_value_as":
                literal = one(value, "value")
                if literal not in ("yes", "no"):
                    raise AssertionError("Native option must be a boolean")
                self.scopes[one(value, "name")] = literal == "yes"
            elif key == NATIVE and value == "yes":
                # Read the mutation's actual character scope and destinations.
                owner, body = next((k, v) for k, _, v in self.native
                                   if isinstance(v, list) and one(v, "change_liege") is not None)
                catalyst = next(v for k, _, v in walk(self.native)
                                if k == "fp3_struggle_apply_independent_vassalage_catalyst_effect")
                self.observed.append({
                    "vassal": self.resolve(owner),
                    "liege": self.resolve(one(one(body, "change_liege"), "liege")),
                    "opinion_target": self.resolve(one(one(body, "add_opinion"), "target")),
                    "catalyst_liege": self.resolve(one(catalyst, "NEW_LIEGE")),
                    "catalyst_vassal": self.resolve(one(catalyst, "NEW_VASSAL")),
                    "options": {name: self.scopes[name] for name in OPTIONS},
                })
            else:
                raise AssertionError(f"Unsupported adapter operation {(key, op, value)}")


class AiWorldNativeScopes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.defs = {key: body for key, _, body in parse(
            (SOURCE / "common/scripted_effects/tnt_38_ai_world.txt").read_text(encoding="utf-8-sig"))}
        native_defs = {key: body for key, _, body in parse(
            (GAME / "common/scripted_effects/00_interaction_effects.txt").read_text(encoding="utf-8-sig"))}
        cls.native = native_defs[NATIVE]

    def assert_native_roles(self, adapter, current="unrelated_caller", stale=None):
        call = NativeCall(self.native, stale)
        call.run(adapter, current)
        self.assertEqual(call.observed, [{
            "vassal": "new_vassal", "liege": "new_liege",
            "opinion_target": "new_liege", "catalyst_liege": "new_liege",
            "catalyst_vassal": "new_vassal",
            "options": {name: False for name in OPTIONS},
        }])
        self.assertEqual(call.scopes["actor"], "new_liege")
        self.assertEqual(call.scopes["recipient"], "new_vassal")

    def test_missing_native_alias_is_supplied_before_call(self):
        self.assert_native_roles(self.defs[ADAPTER])

    def test_stale_proxy_alias_is_replaced_with_ai_actor(self):
        for stale in ("unrelated_puppet", "new_vassal"):
            with self.subTest(stale=stale):
                self.assert_native_roles(self.defs[ADAPTER], stale=stale)

    def test_recipient_caller_does_not_become_the_liege(self):
        self.assert_native_roles(self.defs[ADAPTER], current="new_vassal")

    def test_both_world_lanes_share_the_native_adapter(self):
        callers = {name for name, body in self.defs.items()
                   if isinstance(body, list) and any(key == ADAPTER for key, _, _ in walk(body))}
        self.assertEqual(callers, {"tnt_ai_world_do_submission_effect", "tnt_ai_world_do_vassal_effect"})
        native_callers = {name for name, body in self.defs.items()
                          if isinstance(body, list) and any(key == NATIVE for key, _, _ in walk(body))}
        self.assertEqual(native_callers, {ADAPTER})
        submission = one(self.defs["tnt_ai_world_do_submission_effect"], "if")
        rebind = next(i for i, (key, _, _) in enumerate(submission) if key == "scope:tnt_submission_target")
        invoke = next(i for i, (key, _, _) in enumerate(submission) if key == ADAPTER)
        self.assertLess(rebind, invoke)
        self.assertEqual(one(submission[rebind][2], "save_temporary_scope_as"), "recipient")
        paid = one(self.defs["tnt_ai_world_do_vassal_effect"], "if")
        gold = one(paid, "tnt_ai_send_gold_effect")
        self.assertEqual(one(gold, "PAYER"), "scope:actor")
        self.assertEqual(one(gold, "RECEIVER"), "scope:recipient")

    def test_missing_late_and_wrong_owner_alias_mutations_fail(self):
        good = copy.deepcopy(self.defs[ADAPTER])
        index = next(i for i, (key, _, body) in enumerate(good)
                     if key == "scope:actor" and one(body, "save_temporary_scope_as") == "puppet_or_actor")
        binding = good[index]
        missing = good[:index] + good[index + 1:]
        late = missing + [binding]
        wrong = copy.deepcopy(good)
        wrong[index] = ("scope:recipient", binding[1], binding[2])
        for label, mutation in (("missing", missing), ("late", late), ("recipient", wrong)):
            with self.subTest(mutation=label), self.assertRaises((KeyError, AssertionError)):
                self.assert_native_roles(mutation)

    def test_direct_native_effect_inventory_is_bounded(self):
        # A new native effect needs its own scope-contract review before it can
        # silently enter the AI-world path. Built-in mutation commands are separate.
        calls = {key for body in self.defs.values() if isinstance(body, list)
                 for key, _, _ in walk(body)
                 if key.endswith("_effect") and not key.startswith("tnt_") and key != "hidden_effect"}
        self.assertEqual(calls, {"add_hook_if_possible_default_length_effect", NATIVE})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--game", type=Path, default=GAME)
    args, extra = parser.parse_known_args()
    SOURCE, GAME = args.source, args.game
    unittest.main(argv=[__file__, *extra], verbosity=2)
