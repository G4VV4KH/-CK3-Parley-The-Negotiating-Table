"""Compact ledger coverage and actual gift-floor arithmetic regressions.

The GUI checks are structural; text fit and hover behavior require native CK3.
The arithmetic executes shipped script values with explicit relationship inputs.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import unittest

from test_autobalance import DEFAULT_SOURCE, D, TOKEN, World


SOURCE = DEFAULT_SOURCE


def named_gui_block(text, widget, name):
    """Extract a unique named GUI body; quoted braces/comments are not syntax."""
    pattern = rf'\b{re.escape(widget)}\s*=\s*\{{\s*name\s*=\s*"{re.escape(name)}"'
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise AssertionError(f"expected one {widget} {name}, got {len(matches)}")
    start = text.index("{", matches[0].start())
    depth = 0
    for token in TOKEN.finditer(text, start):
        if token.group() == "{":
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if not depth:
                return text[start + 1:token.start()]
    raise AssertionError(f"unclosed GUI block {name}")


class LedgerFloorTests(unittest.TestCase):
    def gui(self):
        return (SOURCE / "gui/tnt_types.gui").read_text(encoding="utf-8-sig")

    def fixture(self, opinion=-124, threshold=4):
        return World(SOURCE, opinion=opinion, threshold=threshold,
                     lumpy_p=332, lumpy_r=0)

    def test_pressure_and_floor_share_an_always_visible_row(self):
        row = named_gui_block(self.gui(), "hbox", "tnt_figure_row_threat")
        self.assertNotRegex(row.split("tnt_balance_figure", 1)[0], r"\b(?:visible|enabled)\s*=")
        for name in ("threat", "floor"):
            child = named_gui_block(row, "tnt_balance_figure", "tnt_figure_" + name)
            self.assertNotRegex(child, r"\b(?:visible|enabled)\s*=")
        self.assertNotIn("tnt_show_threat_p", row)
        names = re.findall(r'name\s*=\s*"(tnt_figure_[^\"]+)"', row)
        self.assertEqual(names, ["tnt_figure_row_threat", "tnt_figure_threat", "tnt_figure_floor"])
        self.assertIn("TntSV('tnt_display_pressure_p_value')|+=0", row)
        self.assertIn("TntSV('tnt_display_deal_floor_value')|+=0", row)
        interest_row = named_gui_block(self.gui(), "hbox", "tnt_figure_row_interest")
        self.assertIn("TntPos('tnt_interests_enabled_value')", interest_row)
        interest = named_gui_block(interest_row, "tnt_balance_figure", "tnt_figure_interest")
        self.assertIn("TntPos('tnt_interests_enabled_value')", interest)
        self.assertIn("TntSV('tnt_interest_penalty_display_value')|+=0", interest)

    def test_floor_has_a_short_label_and_hover_explanation(self):
        floor = named_gui_block(self.gui(), "tnt_balance_figure", "tnt_figure_floor")
        for fragment in ('alwaystransparent = no', 'using = tooltip_es',
                         'tooltip = "tnt_bd_floor"', 'text = "tnt_bd_floor_panel"'):
            self.assertIn(fragment, floor)

    def test_fractional_adjustments_use_display_only_rounding(self):
        gui = self.gui()
        for name, value in (
            ("relation", "tnt_display_relation_mod_value"),
            ("threshold", "tnt_display_threshold_delta_value"),
            ("threat", "tnt_display_pressure_p_value"),
            ("floor", "tnt_display_deal_floor_value"),
        ):
            row = named_gui_block(gui, "tnt_balance_figure", "tnt_figure_" + name)
            self.assertIn(f"TntSV('{value}')|+=0", row)

    def test_hostile_free_gift_exposes_the_missing_positive_correction(self):
        world = self.fixture()
        self.assertEqual(world.value("tnt_gain_total_value"), 332)
        self.assertEqual(world.value("tnt_relation_mod_value"), -412)
        self.assertEqual(world.value("tnt_threshold_delta_value"), -13)
        self.assertEqual(world.value("tnt_deal_floor_value"), D("92.96"))
        self.assertEqual(world.value("tnt_display_deal_floor_value"), 93)
        self.assertEqual(world.value("tnt_ai_accept_value"), 0)
        # UI-only change: zero remains zero, not a newly accepted gift.
        self.assertFalse(world.value("tnt_ai_accept_value") > 0)

    def test_peaceful_and_empty_offers_keep_the_floor_visible_at_zero(self):
        world = self.fixture(opinion=25)
        self.assertEqual(world.value("tnt_deal_floor_value"), 0)
        self.assertEqual(world.value("tnt_display_deal_floor_value"), 0)
        world = self.fixture()
        world.leaves["tnt_val_vassal_p_value"] = D(0)
        self.assertEqual(world.value("tnt_deal_floor_value"), 0)
        self.assertEqual(world.value("tnt_ai_accept_value"), 0)

    def test_hook_only_pressure_survives_without_a_selected_threat(self):
        world = self.fixture()
        world.leaves["tnt_val_threat_p_value"] = D(0)
        world.leaves["tnt_val_usehook_p_value"] = D(45)
        self.assertEqual(world.value("tnt_val_pressure_p_value"), 45)
        self.assertEqual(world.value("tnt_display_pressure_p_value"), 45)
        self.assertEqual(world.value("tnt_ai_accept_value"), 45)

    def test_partner_hook_is_included_without_changing_player_pressure(self):
        world = self.fixture()
        world.leaves["tnt_val_usehook_p_value"] = D(45)
        world.leaves["tnt_val_usehook_r_value"] = D(-120)
        self.assertEqual(world.value("tnt_val_pressure_p_value"), 45)
        self.assertEqual(world.value("tnt_display_pressure_p_value"), -75)
        self.assertEqual(world.value("tnt_ai_accept_value"), -75)
        # Combine raw fractional pressure components before display rounding.
        world.leaves["tnt_val_usehook_p_value"] = D("45.5")
        world.leaves["tnt_val_usehook_r_value"] = D("-45.5")
        self.assertEqual(world.value("tnt_display_pressure_p_value"), 0)
        self.assertEqual(world.value("tnt_ai_accept_value"), 0)


def main():
    global SOURCE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    SOURCE = parser.parse_args().source
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(LedgerFloorTests))
    raise SystemExit(not result.wasSuccessful())


if __name__ == "__main__":
    main()
