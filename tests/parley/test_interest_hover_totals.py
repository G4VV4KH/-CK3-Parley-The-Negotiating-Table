"""Static hover contracts; native row materialization and pixels are separate gates."""
import re
import unittest

from test_interest_layout_refresh import BADGES, badge_rendering_prefix, blocks, clean, override, single_block, visible
from test_interest_ui import SOURCE, body_containing, text


class InterestHoverTotalsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.types = clean(text(SOURCE / "gui/tnt_types.gui"))
        cls.instances = blocks(clean(text(SOURCE / "gui/tnt_diplomacy_window.gui") + "\n"
                                    + text(SOURCE / "gui/tnt_panel_contract.gui")),
                               r"\btnt_interest_badge\s*=")

    def test_effective_total_is_outside_selected_only_price_group(self):
        tooltip = single_block(self.types, r"\btype\s+tnt_interest_tooltip\s*=\s*container")
        total = body_containing(tooltip, "tnt_interest_total")
        points = body_containing(tooltip, "tnt_interest_points")
        self.assertIn('block "tnt_interest_points_effective" {}', total)
        self.assertNotRegex(total, r"\bvisible\s*=")
        self.assertNotIn("tnt_interest_points_effective", points)
        self.assertIn('block "tnt_interest_points" { visible = no }', points)
        self.assertIn('block "tnt_interest_points_base" {}', points)
        self.assertIn('block "tnt_interest_points_adjusted" {}', points)

    def test_all_35_totals_use_unrounded_state_aware_display_value(self):
        self.assertEqual(len(self.instances), 35)
        observed = set()
        for badge in self.instances:
            prefix = badge_rendering_prefix(override(badge, "tnt_interest_value"))
            observed.add(prefix)
            total = override(badge, "tnt_interest_points_effective")
            self.assertNotRegex(total, r"\bvisible\s*=")
            self.assertIn("[Localize('tnt_interest_effective_percent')]", total)
            self.assertIn(f"[TntSV('{prefix}_display_percent_value')|2]%", total)
            self.assertNotIn("_badge_percent_value", total)
            self.assertNotIn(f"'{prefix}_percent_value'", total)
        self.assertEqual(observed, BADGES)

    def test_all_35_breakdowns_prices_and_preview_notes_follow_the_same_state(self):
        for badge in self.instances:
            prefix = badge_rendering_prefix(override(badge, "tnt_interest_value"))
            compact = lambda value: re.sub(r"\s+", "", value)
            term = prefix.removeprefix("tnt_interest_")
            if term.rsplit("_", 1)[0] in ("gold", "prestige", "piety", "influence"):
                selected_condition = f"[TntOn('tnt_{term}')]"
            else:
                selected_condition = f"[TntPos('{prefix}_selected_value')]"
            empty_condition = "[Not(" + selected_condition[1:-1] + ")]"
            for block_name, suffix, expected in (
                    ("tnt_interest_breakdown", "_percent_value", selected_condition),
                    ("tnt_interest_preview_breakdown", "_preview_percent_value", empty_condition)):
                body = override(badge, block_name)
                self.assertEqual(compact(visible(body)), expected, prefix)
                self.assertIn(f"[TntBreakdown('{prefix}{suffix}')]", body)
            self.assertEqual(compact(visible(override(badge, "tnt_interest_points"))), selected_condition)
            note = override(badge, "tnt_interest_empty_state")
            self.assertEqual(compact(visible(note)), empty_condition)
            self.assertRegex(note, r'text\s*=\s*"tnt_interest_preview_(?:currency|context|contract)"')


if __name__ == "__main__":
    unittest.main()
