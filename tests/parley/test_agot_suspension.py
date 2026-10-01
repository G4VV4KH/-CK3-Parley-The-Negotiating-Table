"""Keep the CK3 1.20 Parley payload free of the suspended AGOT integration.

The optional --baseline argument proves a narrow source delta: after removing
the explicitly retired AGOT nodes from RC9, every common/events AST must equal
the candidate AST. This is a source preservation check, not an engine test.
Historical documentation and build locks are deliberately outside the scan.
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import re
import unittest

from test_autobalance import DEFAULT_SOURCE, TOKEN, one, parse

SOURCE = DEFAULT_SOURCE
BASELINE = None
HELPERS = {
    "tnt_person_is_beast_trigger",
    "tnt_person_is_sworn_brother_trigger",
    "tnt_vassalage_pair_allowed_trigger",
    "tnt_not_the_watch_trigger",
}
MARKERS = {
    "living_dragons", "wildling_culture", "government_is_nw",
    "government_is_uninteractable", "agot_pwl_direct",
    "nights_watch_government", "nightswatch", "nightswatch_temp",
    "nightswatch_historical", "tnt_err_vassal_wall",
}
FORBIDDEN = re.compile(
    r"\b(?:agot\w*|" + "|".join(sorted(HELPERS | MARKERS)) + r")\b", re.I)
TEXT_SUFFIXES = {".txt", ".gui", ".yml", ".mod"}


def forbidden_references(text):
    # TOKEN preserves quoted strings as one token, including CK3 '#low' markup.
    # Do not let that markup hide an active expression later on the same line.
    return sorted({match.group() for token in TOKEN.finditer(text.lstrip("\ufeff"))
                   if not token.group().startswith("#")
                   for match in FORBIDDEN.finditer(token.group())})


def suspended_nodes_removed(nodes):
    """Remove only the reviewed AGOT nodes, preserving all vanilla decisions."""
    result = []
    for key, op, value in nodes:
        if key in HELPERS:
            continue
        if key == "NOT" and value == [("has_variable", "=", "agot_pwl_direct")]:
            continue
        if key == "custom_tooltip" and isinstance(value, list) and one(value, "text") == "tnt_err_vassal_wall":
            continue
        if key == "if" and one(value, "limit") == [("always", "=", "no")]:
            body = [n for n in value if n[0] != "limit"]
            dragon_writer = [("add_to_global_variable_list", "=", [
                ("name", "=", "living_dragons"), ("target", "=", "this")])]
            wildling_writer = [("culture", "=", [("set_variable", "=", [
                ("name", "=", "wildling_culture"), ("value", "=", "0")])])]
            if body in (dragon_writer, wildling_writer):
                continue
        if isinstance(value, list):
            filtered = suspended_nodes_removed(value)
            # Only newly empty wrappers disappear. A trigger_if with only its
            # limit left also has no remaining decision and must be removed.
            if value and not filtered:
                continue
            if key == "trigger_if" and len(filtered) == 1 and filtered[0][0] == "limit" and len(value) > 1:
                continue
            value = filtered
        result.append((key, op, value))
    return result


def script_inventory(source):
    return {p.relative_to(source).as_posix(): parse(p.read_text(encoding="utf-8-sig"))
            for folder in ("common", "events")
            for p in sorted((source / folder).rglob("*.txt"))}


class AgotSuspension(unittest.TestCase):
    def test_payload_has_no_active_agot_markers_calls_or_localization(self):
        self.assertTrue((SOURCE / "descriptor.mod").is_file(), "Missing Parley source")
        problems = {}
        for path in sorted(SOURCE.rglob("*")):
            if path.is_file() and path.suffix in TEXT_SUFFIXES:
                refs = forbidden_references(path.read_text(encoding="utf-8-sig"))
                if refs:
                    problems[path.relative_to(SOURCE).as_posix()] = refs
        self.assertEqual(problems, {})

    def test_reintroduced_integration_is_rejected(self):
        examples = [f"{name} = yes" for name in sorted(HELPERS)]
        examples += [f"has_variable = {name}" for name in sorted(MARKERS)]
        examples += [
            'text = "[GetScriptedGui(\'agot_future_adapter\')]"',
            'text = "#low ordinary tooltip#!" government_has_flag = government_is_nw',
            'if = { limit = { always = no } set_variable = { name = living_dragons value = 0 } }',
        ]
        for code in examples:
            with self.subTest(code=code):
                self.assertTrue(forbidden_references(code))

    def test_archival_comments_do_not_activate_integration(self):
        self.assertEqual(forbidden_references(
            '# government_has_flag = government_is_nw\n'
            'always = yes # tnt_not_the_watch_trigger = { WHO = this }\n'
            'text = "#low native tooltip#!" # living_dragons\n'), [])

    def test_remaining_runtime_matches_baseline_after_only_agot_removal(self):
        if BASELINE is None:
            self.skipTest("pass --baseline with immutable RC9 Parley for bounded delta audit")
        old = script_inventory(BASELINE)
        new = script_inventory(SOURCE)
        self.assertEqual(set(old), set(new), "Unexpected runtime script inventory change")
        changed = []
        for name in old:
            with self.subTest(path=name):
                expected = suspended_nodes_removed(old[name])
                self.assertEqual(new[name], expected)
                if new[name] != old[name]:
                    changed.append(name)
        print("Reviewed AGOT-only AST changes: " + ", ".join(changed))

    def test_baseline_normalizer_does_not_erase_vanilla_safety(self):
        # A dropped war restriction or an accidental AI/player switch must
        # remain visible to the bounded delta check.
        original = parse('pair = { is_ai = yes is_alive = yes is_at_war = no '
                         'NOT = { has_variable = agot_pwl_direct } '
                         'tnt_vassalage_pair_allowed_trigger = { A = root B = this } }')
        good = parse('pair = { is_ai = yes is_alive = yes is_at_war = no }')
        self.assertEqual(suspended_nodes_removed(original), good)
        for mutation in (
                parse('pair = { is_ai = yes is_alive = yes }'),
                parse('pair = { is_ai = no is_alive = yes is_at_war = no }')):
            self.assertNotEqual(suspended_nodes_removed(original), mutation)
        # An arbitrary always=no body is not one of the retired suppressors.
        native = parse('if = { limit = { always = no } add_gold = 1 }')
        self.assertEqual(suspended_nodes_removed(copy.deepcopy(native)), native)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--baseline", type=Path)
    args, extra = parser.parse_known_args()
    SOURCE, BASELINE = args.source, args.baseline
    unittest.main(argv=[__file__, *extra], verbosity=2)
