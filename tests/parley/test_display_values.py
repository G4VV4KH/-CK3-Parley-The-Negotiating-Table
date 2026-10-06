"""Exercise shipped display wrappers without moving rounding into prices.

Native GUI text/layout still needs a CK3 smoke check. Arithmetic uses the shared
strict AST interpreter, whose half-away rounding matches the observed .5 totals.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import unittest

import test_scaled_valuation as shared
from test_autobalance import one, parse
from test_scaled_people import PeopleWorld, claim, person
from test_scaled_valuation import D, Scope, ValuationWorld, realm


DISPLAY_FILE = "common/script_values/tnt_5e_display_values.txt"
GUI_FILES = ("gui/tnt_panels.gui", "gui/tnt_panel_people.gui",
             "gui/tnt_panel_multiselect.gui")


class DisplayValueTests(unittest.TestCase):
    def test_native_presentation_helpers_are_utf8_with_one_bom(self):
        for relative in (DISPLAY_FILE, "common/customizable_localization/tnt_90_cooldown_loc.txt"):
            with self.subTest(path=relative):
                data = (shared.SOURCE / relative).read_bytes()
                self.assertTrue(data.startswith(b"\xef\xbb\xbf"), "CK3 requires UTF-8 BOM")
                self.assertFalse(data[3:].startswith(b"\xef\xbb\xbf"), "Duplicate UTF-8 BOM")
                data[3:].decode("utf-8", errors="strict")

    def definitions(self):
        return dict((key, body) for key, _, body in parse(
            (shared.SOURCE / DISPLAY_FILE).read_text(encoding="utf-8-sig")))

    def table(self):
        world = PeopleWorld()
        player = realm(world, "player", 12, D("18.75"), nested=True)
        partner = realm(world, "partner", 12, D("18.75"), nested=True)
        world.root = player
        world.scopes.update(tnt_me=player, tnt_p=partner, actor=player, recipient=partner)
        player.variables["tnt_partner"] = partner
        return world, player, partner

    def maria(self, donor):
        candidate = person("Maria", diplomacy=12, traits={"beauty_good_2"})
        candidate.links["dynasty"] = Scope("dynasty", "dynasty", {"dynasty_prestige_level": D(3)})
        candidate.lists["is_close_or_extended_family_of"] = [donor]
        candidate.lists["claims"] = [claim("county", "tier_county", Scope("outsider"), pressed=False)]
        return candidate

    def test_all_wrappers_only_round_after_the_original_value(self):
        world = ValuationWorld()
        definitions = self.definitions()
        self.assertEqual(len(definitions), 28)
        for name, body in definitions.items():
            raw = one(body, "value")
            self.assertIn(raw, world.defs)
            expected_body = [("value", "=", raw), ("round", "=", "yes")]
            if name == "tnt_display_pressure_p_value":
                # The compact pressure figure also includes the partner's
                # signed hook contribution already present in the headline.
                expected_body.insert(1, ("add", "=", "tnt_val_usehook_r_value"))
                world.root.stats["tnt_val_usehook_r_value"] = D(0)
            self.assertEqual(body, expected_body)
            for value, expected in (("18.49", 18), ("18.5", 19), ("18.51", 19),
                                    ("472.5", 473), ("-18.5", -19), ("0", 0)):
                with self.subTest(wrapper=name, value=value):
                    # The input is a fixture only for this boundary test. Actual
                    # courtier/realm prices execute below without leaf overrides.
                    world.root.stats[raw] = D(value)
                    self.assertEqual(world.value(name), expected)
                    self.assertEqual(world.value(raw), D(value))
                    del world.root.stats[raw]

    def test_display_values_have_no_gameplay_consumers(self):
        for path in (shared.SOURCE / "common").rglob("*.txt"):
            if path == shared.SOURCE / DISPLAY_FILE:
                continue
            live = "\n".join(line for line in path.read_text(encoding="utf-8-sig").splitlines()
                             if not line.lstrip().startswith("#"))
            self.assertNotRegex(live, r"\btnt_display_", str(path))
        for path in (shared.SOURCE / "events").rglob("*.txt"):
            self.assertNotIn("tnt_display_", path.read_text(encoding="utf-8-sig"), str(path))

    def test_raw_point_labels_use_display_wrappers_and_net_labels_stay_net(self):
        for relative in GUI_FILES:
            text = (shared.SOURCE / relative).read_text(encoding="utf-8-sig")
            live = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
            self.assertNotRegex(live, r"TntSV\('tnt_val_[^']+'\)\|(?:\+=)?0", relative)
            for name in re.findall(r"TntSV\('(tnt_display_[^']+)'\)", live):
                self.assertIn(name, self.definitions())
        panels = (shared.SOURCE / GUI_FILES[0]).read_text(encoding="utf-8-sig")
        for term in ("courtier", "subject"):
            self.assertIn(f"TntSV('tnt_shown_{term}_multi_p_value')|0", panels)

    def test_native_maria_half_point_and_multi_sum(self):
        world, player, partner = self.table()
        first, second = self.maria(partner), self.maria(partner)
        player.lists["tnt_sel_courtier_r"] = [first]
        self.assertEqual(world.value("tnt_val_courtier_multi_r_value"), D("18.5"))
        self.assertEqual(world.value("tnt_display_courtier_multi_r_value"), 19)
        player.lists["tnt_sel_courtier_r"] = [first, second]
        self.assertEqual(world.value("tnt_val_courtier_multi_r_value"), 37)
        self.assertEqual(world.value("tnt_display_courtier_multi_r_value"), 37)
        # NOT 38: the fractional per-person prices are never rounded before sum.
        player.lists["tnt_sel_courtier_p"] = [self.maria(player)]
        player.stats["tnt_deal_mult_value"] = D("0.375")
        self.assertEqual(world.value("tnt_val_courtier_multi_p_value"), D("18.5"))
        self.assertEqual(world.value("tnt_shown_courtier_multi_p_value"), 7)

    def test_independence_half_points_both_directions_stay_raw_underneath(self):
        world, player, _ = self.table()
        player.variables.update(tnt_indep_p=D(1), tnt_indep_r=D(1))
        for side in ("p", "r"):
            self.assertEqual(world.value(f"tnt_val_indep_{side}_value"), D("472.5"))
            self.assertEqual(world.value(f"tnt_display_indep_{side}_value"), 473)
            self.assertEqual(world.value(f"tnt_val_indep_{side}_value"), D("472.5"))

    def test_whole_deal_aggregates_keep_rounding_after_raw_term_sums(self):
        world = ValuationWorld()
        for name, side in (("tnt_gain_total_value", "p"), ("tnt_loss_total_value", "r")):
            body = world.defs[name]
            self.assertEqual(body[-1], ("round", "=", "yes"))
            for key, op, value in body:
                if key == "add":
                    self.assertIsInstance(value, str)
                    self.assertNotIn("display", value)
                    world.root.stats[value] = D(0)
            world.root.stats[f"tnt_val_indep_{side}_value"] = D("472.5")
            world.root.stats[f"tnt_val_hostage_{side}_value"] = D("18.5")
            self.assertEqual(world.value(name), 491)  # not 473 + 19 = 492
            world.root.stats.clear()

    def test_landless_title_label_has_native_validity_gate(self):
        text = (shared.SOURCE / "gui/tnt_panel_multiselect.gui").read_text(encoding="utf-8-sig")
        body = text.split('name = "tnt_multi_row_rank"', 1)[1].split("\n\t\t\t}", 1)[0]
        self.assertIn('visible = "[Character.GetPrimaryTitle.IsValid]"', body)
        self.assertIn('text = "[Character.GetPrimaryTitle.GetNameNoTooltip]"', body)
        self.assertNotIn('text = "None"', body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=shared.SOURCE)
    args, remaining = parser.parse_known_args()
    shared.SOURCE = args.source.resolve()
    unittest.main(argv=[__file__, *remaining], verbosity=2)
