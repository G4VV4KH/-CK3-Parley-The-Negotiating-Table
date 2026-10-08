"""Execute live interest commit guards; native settlement is a separate gate.

Acceptance scores and physical preflight outcomes are explicit inputs here.
The production guard AST determines branch selection, including stale letters,
legacy grace and the execution-local coercive payment exception.
"""
from pathlib import Path
import unittest

from test_autobalance import D, World, one, parse


SOURCE = Path(__file__).resolve().parents[2] / "mod/parley"


def definitions(relative):
    return {key: body for key, _, body in parse((SOURCE / relative).read_text(encoding="utf-8-sig"))
            if isinstance(body, list)}


def option(body, name):
    return next(value for key, _, value in body if key == "option" and one(value, "name") == name)


def calls(nodes):
    result = []
    for key, _, value in nodes:
        if key.endswith("_effect"):
            result.append(key)
        if isinstance(value, list):
            result.extend(calls(value))
    return result


class CommitWorld(World):
    def __init__(self, enabled, score, physical=True, coercive=None, arch=None, human=True):
        super().__init__(SOURCE)
        self.leaves.update(tnt_interests_enabled_value=D(enabled), tnt_ai_accept_value=D(score))
        self.vars["tnt_partner"] = "r"
        self.vars.pop("tnt_open", None)
        self.scopes["tnt_deal_partner"] = "r"
        self.physical, self.coercive, self.human = physical, coercive, human
        if arch is not None:
            self.vars["tnt_ai_offer_arch"] = D(arch)

    def exists(self, name, current):
        if name == "scope:tnt_deal_coercive_demand":
            return self.coercive is not None
        return super().exists(name, current)

    def value(self, value, current="p"):
        if value == "scope:tnt_deal_coercive_demand":
            return D(self.coercive)
        return super().value(value, current)

    def condition(self, key, op, value, current):
        if key == "tnt_deal_preflight_trigger":
            return self.physical
        if key == "is_ai":
            return (not self.human) == (value == "yes")
        if key == "is_alive":
            return value == "yes"
        if key == "this":
            return current == self.scope(value, current)
        return super().condition(key, op, value, current)


class InterestCommitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        events = definitions("events/tnt_ai_events.txt")
        cls.letter = option(events["tnt_ai_offer.0002"], "tnt_ai_offer_opt_accept")
        cls.pay = option(events["tnt_ai_offer.0003"], "tnt_ai_demand_opt_pay")
        cls.manual_event = definitions("events/tnt_events.txt")["tnt_diplomacy.0001"]
        cls.manual = option(cls.manual_event, "tnt_confirm_opt_yes")
        cls.master = definitions("common/scripted_effects/tnt_32_apply.txt")["tnt_apply_deal_effect"]

    def test_off_keeps_minus_fifteen_letter_grace(self):
        for score in (-16, -15, -14, -1, 0, 1):
            world = CommitWorld(0, score)
            self.assertEqual(world.trigger(one(self.letter, "trigger")), score > -15)
            self.assertTrue(world.trigger(one(one(self.letter, "if"), "limit")))
            self.assertTrue(world.trigger(one(one(self.master, "if"), "limit")))

    def test_enabled_stale_letter_click_expires_instead_of_transferring(self):
        for score in (-100, -1, 0, 1):
            world = CommitWorld(1, score)
            self.assertTrue(world.trigger(one(self.letter, "trigger")))
            accepted = world.trigger(one(one(self.letter, "if"), "limit"))
            self.assertEqual(accepted, score > 0)
            chosen = one(self.letter, "if" if accepted else "else")
            self.assertEqual("tnt_apply_deal_effect" in calls(chosen), score > 0)
            self.assertEqual("tnt_log_verdict_accept_effect" in calls(chosen), score > 0)
            if not accepted:
                self.assertIn("tnt_notify_stale_deal_effect", calls(chosen))
                self.assertIn("tnt_ai_offer_clear_effect", calls(chosen))

    def test_master_requires_positive_live_score_before_every_consequence(self):
        for score in (-1, 0, 1):
            world = CommitWorld(1, score)
            self.assertEqual(world.trigger(one(one(self.master, "if"), "limit")), score > 0)
        self.assertEqual([key for key, _, _ in self.master], ["if"])

    def test_coercive_exception_requires_explicit_human_pay_and_arch21(self):
        for marker, arch, human, expected in ((None, 21, True, False), (1, 20, True, False),
                                             (1, 21, False, False), (0, 21, True, False),
                                             (1, 21, True, True)):
            world = CommitWorld(1, -1, coercive=marker, arch=arch, human=human)
            self.assertEqual(world.trigger(one(one(self.master, "if"), "limit")), expected)
        body = one(self.pay, "if")
        marker = next(i for i, (key, _, value) in enumerate(body)
                      if key == "save_scope_value_as" and one(value, "name") == "tnt_deal_coercive_demand")
        apply = next(i for i, (key, _, _) in enumerate(body) if key == "tnt_apply_deal_effect")
        self.assertLess(marker, apply)
        self.assertNotIn("tnt_deal_coercive_demand", repr(self.letter))
        self.assertNotIn("tnt_deal_coercive_demand", repr(self.manual_event))

    def test_coercion_never_bypasses_physical_preflight(self):
        world = CommitWorld(1, -1, physical=False, coercive=1, arch=21)
        self.assertFalse(world.trigger(one(one(self.master, "if"), "limit")))
        self.assertNotIn("tnt_apply_deal_effect", calls(one(self.pay, "else")))

    def test_manual_commit_checks_live_score_before_window_close(self):
        for score in (-1, 0, 1):
            world = CommitWorld(1, score)
            accepted = world.trigger(one(one(self.manual, "if"), "limit"))
            self.assertEqual(accepted, score > 0)
            chosen = one(self.manual, "if" if accepted else "else")
            self.assertEqual("tnt_close_window_effect" in calls(chosen), score > 0)
        refused = next(body for key, _, body in self.manual_event
                       if key == "option" and one(body, "show_as_tooltip") is not None)
        self.assertIn("tnt_notify_rejected_effect", calls(refused))
        self.assertNotIn("tnt_close_window_effect", calls(refused))


if __name__ == "__main__":
    unittest.main()
