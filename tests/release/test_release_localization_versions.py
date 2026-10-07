"""Version-specific Parley localization projections; no release files are edited."""
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "tools/release/build_game.py"
SPEC = importlib.util.spec_from_file_location("versioned_builder", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


def fixture(version, public_count):
    files = {"descriptor.mod": f'version="{version}"\n'.encode()}
    keys = [f"public_key_{index}" for index in range(public_count)] + sorted(builder.REMOVED_LOC)
    for language in builder.LANGUAGES:
        text = f"l_{language}:\n" + "".join(f' {key}:0 "Text"\n' for key in keys)
        files[f"localization/{language}/tnt_l_{language}.yml"] = text.encode("utf-8-sig")
    return {"parley": files}


class LocalizationVersionTests(unittest.TestCase):
    def test_110_profile_preserves_reviewed_counts(self):
        source = fixture("1.1.0", 622)
        self.assertEqual(builder.parley_localization_counts(source["parley"]), (632, 622))
        output, changes = builder.project(source)
        self.assertEqual(builder.validate_localizations(output)["parley"]["keys_per_language"], 622)
        self.assertEqual(len(changes["parley"]), 9)

    def test_120_adds_ten_public_keys_and_removes_same_diagnostics(self):
        source = fixture("1.2.0", 632)
        self.assertEqual(builder.parley_localization_counts(source["parley"]), (642, 632))
        output, changes = builder.project(source)
        self.assertEqual(builder.validate_localizations(output)["parley"]["keys_per_language"], 632)
        for report in changes["parley"].values():
            self.assertEqual(set(report["localization_keys_removed"]), builder.REMOVED_LOC)

    def test_121_adds_valuation_frequency_and_presentation_keys(self):
        source = fixture("1.2.1", 652)
        self.assertEqual(builder.parley_localization_counts(source["parley"]), (662, 652))
        output, changes = builder.project(source)
        self.assertEqual(builder.validate_localizations(output)["parley"]["keys_per_language"], 652)
        self.assertEqual(len(changes["parley"]), 9)
        for report in changes["parley"].values():
            self.assertEqual(set(report["localization_keys_removed"]), builder.REMOVED_LOC)

    def test_122_translation_patch_keeps_121_counts_and_diagnostic_boundary(self):
        source = fixture("1.2.2", 652)
        self.assertEqual(builder.parley_localization_counts(source["parley"]), (662, 652))
        output, changes = builder.project(source)
        self.assertEqual(builder.validate_localizations(output)["parley"]["keys_per_language"], 652)
        self.assertEqual(len(changes["parley"]), 9)
        for report in changes["parley"].values():
            self.assertEqual(set(report["localization_keys_removed"]), builder.REMOVED_LOC)

    def test_actual_current_localizations_keep_valuation_frequency_and_presentation_keys(self):
        root = SCRIPT.parents[2] / "mod/parley"
        files = {"descriptor.mod": (root / "descriptor.mod").read_bytes()}
        for language in builder.LANGUAGES:
            name = f"localization/{language}/tnt_l_{language}.yml"
            files[name] = (root / name).read_bytes()
        output, _ = builder.project({"parley": files})
        evidence = builder.validate_localizations(output)["parley"]
        self.assertEqual(evidence["keys_per_language"], 652)
        expected = {"rule_tnt_advanced_valuation", "setting_tnt_advanced_valuation_classic",
                    "setting_tnt_advanced_valuation_classic_desc", "setting_tnt_advanced_valuation_scaled",
                    "setting_tnt_advanced_valuation_scaled_desc", "rule_tnt_threat_frequency",
                    "tnt_err_threat_cooldown", "NOT_tnt_err_hatred", "tnt_bd_floor_panel",
                    "tnt_threat_cooldown_status", "tnt_threat_cooldown_short",
                    "tnt_threat_cooldown_empty"}
        for setting in ("unlimited", "1_year", "5_years", "10_years"):
            expected.add(f"setting_tnt_threat_frequency_{setting}")
            expected.add(f"setting_tnt_threat_frequency_{setting}_desc")
        for name, data in output["parley"].items():
            if name.endswith(".yml"):
                with self.subTest(language=name):
                    self.assertEqual(len(builder.localization_keys(files[name], name)), 662)
                    self.assertTrue(expected <= builder.localization_keys(data, name))

    def test_versions_do_not_accept_each_others_counts(self):
        profiles = {"1.1.0": 622, "1.2.0": 632, "1.2.1": 652, "1.2.2": 652}
        for version, expected in profiles.items():
            for wrong_count in set(profiles.values()) - {expected}:
                with self.subTest(version=version, wrong_count=wrong_count), self.assertRaises(builder.ReleaseError):
                    builder.project(fixture(version, wrong_count))

    def test_old_121_candidate_counts_require_their_pinned_builder(self):
        for old_game_count in (637, 647):
            with self.subTest(old_game_count=old_game_count), self.assertRaises(builder.ReleaseError):
                builder.project(fixture("1.2.1", old_game_count))

    def test_actual_current_projection_preserves_cooldown_runtime_and_cleanup(self):
        root = SCRIPT.parents[2] / "mod/parley"
        files = {path.relative_to(root).as_posix(): path.read_bytes()
                 for path in root.rglob("*") if path.is_file()}
        self.assertEqual(len(files), 83)
        output, transforms = builder.project({"parley": files})
        projected = output["parley"]
        self.assertEqual(len(projected), 82)
        self.assertEqual(builder.validate_localizations(output)["parley"]["keys_per_language"], 652)
        builder.transform_totals(transforms)
        for path in (
            "common/game_rules/tnt_80_game_rules.txt",
            "common/script_values/tnt_57_threat_values.txt",
            "common/scripted_triggers/tnt_41_gates.txt",
            "common/scripted_guis/tnt_20_scripted_guis.txt",
            "common/customizable_localization/tnt_90_cooldown_loc.txt",
            "common/script_values/tnt_5e_display_values.txt",
        ):
            self.assertEqual(projected[path], files[path], path)
        for path, count in (
            ("common/scripted_effects/tnt_32_apply.txt", 1),
            ("common/scripted_effects/tnt_37_ai_offer.txt", 2),
            ("common/scripted_effects/tnt_38_ai_world.txt", 2),
        ):
            self.assertEqual(projected[path].count(b"tnt_start_threat_cooldown_effect = yes"), count)
        cleanup = projected["common/decisions/tnt_86_uninstall.txt"]
        self.assertEqual(cleanup.count(b"remove_variable = tnt_threat_cooldown"), 2)
        self.assertEqual(cleanup.count(b"exists = var:tnt_threat_cooldown"), 2)
        self.assertIn(b"tnt_threat_cooldown_available_trigger = { A = scope:tnt_deal_partner }",
                      projected["events/tnt_ai_events.txt"])

    def test_unknown_or_duplicate_version_rejected(self):
        for descriptor in (b'version="1.2.3"\n', b'version="1.3.0"\n', b'version="1.2.1"\nversion="1.2.0"\n', b'name="Parley"\n'):
            with self.subTest(descriptor=descriptor), self.assertRaises(builder.ReleaseError):
                builder.parley_localization_counts({"descriptor.mod": descriptor})

    def test_same_drift_in_all_languages_still_rejected(self):
        output, _ = builder.project(fixture("1.2.0", 632))
        for name in output["parley"]:
            if name.endswith(".yml"):
                output["parley"][name] += b' leaked_key:0 "Drift"\n'
        with self.assertRaises(builder.ReleaseError):
            builder.validate_localizations(output)


if __name__ == "__main__":
    unittest.main()
