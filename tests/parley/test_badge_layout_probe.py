"""Static native-probe guards; localized witness fixtures are not engine proof."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / "native_interest"))
import prepare_badge_layout_probe as probe


class BadgeLayoutProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def prepare(self, language="l_russian"):
        run = self.directory / language
        with redirect_stdout(StringIO()):
            probe.prepare(run, language)
        return run, json.loads((run / "plan.json").read_text(encoding="utf-8"))

    def test_both_languages_keep_short_cycle_exact_tooltips_and_native_witnesses(self):
        before = probe.final.ordinary.base.inventory(probe.final.ordinary.base.SOURCE)
        helper_before = probe.helper_bindings()
        plans = []
        for language in probe.LANGUAGES:
            run, plan = self.prepare(language)
            plans.append(plan)
            self.assertEqual(plan["expected_count"], 17)
            self.assertEqual(plan["language"], language)
            self.assertEqual(plan["localized_witness_count"], 2)
            self.assertEqual(plan["localized_witnesses"], probe.localized_expectations(probe.final.ordinary.base.SOURCE, language))
            controls = (run / "probe" / probe.CONTROLS).read_text(encoding="utf-8-sig")
            self.assertEqual(controls.count("TNGUI_LOCALIZED|"), 2)
            for key in probe.WITNESS_KEYS:
                self.assertIn(f"TNGUI_LOCALIZED|{key}|[Localize('{key}')]|END", controls)
            self.assertNotIn("AddScope('observed'", controls)
            self.assertNotIn("gui/tnt_types.gui", plan["probe_sha256"])
            self.assertFalse((run / "runtime").exists())
            self.assertFalse((run / "userdata").exists())
        self.assertEqual(plans[0]["expected_labels"], plans[1]["expected_labels"])
        self.assertNotEqual(plans[0]["localized_witnesses"], plans[1]["localized_witnesses"])
        self.assertEqual(before, probe.final.ordinary.base.inventory(probe.final.ordinary.base.SOURCE))
        self.assertEqual(helper_before, probe.helper_bindings())

    def test_new_default_is_russian_and_existing_runs_are_never_reused(self):
        run = self.directory / "default"
        with redirect_stdout(StringIO()):
            probe.prepare(run)
        plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["language"], "l_russian")
        with self.assertRaises(FileExistsError), redirect_stdout(StringIO()):
            probe.prepare(run)

    def test_language_selection_is_finite_and_settings_replacement_is_exact(self):
        original = '"language"={ value="l_german" }\n"autosave"={ value="NEVER" }'
        for language in probe.LANGUAGES:
            self.assertEqual(probe.language_settings(original, language), original.replace("l_german", language))
        for original in ("missing language", '"language"={value="l_russian"}\n"language"={value="l_english"}'):
            with self.assertRaises(ValueError):
                probe.language_settings(original, "l_english")
        with self.assertRaises(ValueError):
            probe.prepare(self.directory / "unsupported", "l_french")
        self.assertFalse((self.directory / "unsupported").exists())

    def test_freezer_is_separate_and_records_actual_selected_profile_language(self):
        for language in probe.LANGUAGES:
            run, plan = self.prepare(language)

            def fake_base_freeze(target):
                self.assertEqual(target, run)
                (target / "userdata").mkdir()
                (target / "userdata/pdx_settings.txt").write_text('"language"={value="l_english"}', encoding="utf-8")
                (target / "frozen-manifest.json").write_text(json.dumps(plan), encoding="utf-8")

            with patch.object(probe.final.ordinary.base, "freeze", side_effect=fake_base_freeze) as base_freeze, patch.object(probe.final.ordinary, "freeze") as ordinary_freeze:
                probe.freeze(run)
                base_freeze.assert_called_once_with(run)
                ordinary_freeze.assert_not_called()
            manifest = json.loads((run / "frozen-manifest.json").read_text(encoding="utf-8"))
            settings = run / "userdata/pdx_settings.txt"
            self.assertIn('value="' + language + '"', settings.read_text(encoding="utf-8"))
            self.assertFalse(settings.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertEqual(manifest["prepared_settings_sha256"], probe.final.ordinary.base.sha(settings))
            self.assertEqual(manifest["freezer_sha256"], probe.final.ordinary.base.sha(Path(probe.__file__)))

    def test_changed_helper_or_source_blocks_freeze_before_any_snapshot(self):
        run, plan = self.prepare()
        with patch.object(probe, "helper_bindings", return_value={"changed": "hash"}), patch.object(probe.final.ordinary.base, "freeze") as freeze:
            with self.assertRaisesRegex(ValueError, "helper changed"):
                probe.freeze(run)
            freeze.assert_not_called()
        plan["runtime_source_at_plan_sha256"] = {"changed": "hash"}
        (run / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        with patch.object(probe.final.ordinary.base, "freeze") as freeze:
            with self.assertRaisesRegex(ValueError, "Production changed"):
                probe.freeze(run)
            freeze.assert_not_called()


class BadgeLocalizedWitnessTests(unittest.TestCase):
    def setUp(self):
        self.expected = {"one": "English one", "two": "Second string"}
        self.logs = ("TNGUI_TEST|BEGIN|production_window\n"
                     "TNGUI_LOCALIZED|one|English one|END\n"
                     "TNGUI_LOCALIZED|two|Second string|END\n"
                     "TNGUI_TEST|END|production_window\n")

    def test_exact_native_strings_pass(self):
        self.assertEqual(probe.validate_localized_witnesses(self.logs, self.expected), [])

    def test_missing_repeated_wrong_locale_unresolved_or_unknown_key_fails(self):
        for logs in (self.logs.replace("TNGUI_LOCALIZED|one|English one|END\n", ""),
                     self.logs + "TNGUI_LOCALIZED|one|English one|END\n",
                     self.logs.replace("English one", "Базовая склонность"),
                     self.logs.replace("English one", "[Localize('one')]"),
                     self.logs.replace("|one|", "|unknown|"),
                     self.logs + "TNGUI_LOCALIZED|malformed\n"):
            with self.subTest(logs=logs):
                self.assertTrue(probe.validate_localized_witnesses(logs, self.expected))

    def test_witnesses_without_cycle_or_outside_its_boundaries_fail(self):
        for logs in (self.logs.replace("TNGUI_TEST|BEGIN|production_window", "ignored"),
                     self.logs.replace("TNGUI_TEST|END|production_window", "ignored"),
                     self.logs.replace("TNGUI_TEST|BEGIN|production_window\n", "") + "TNGUI_TEST|BEGIN|production_window\n"):
            self.assertTrue(probe.validate_localized_witnesses(logs, self.expected))


if __name__ == "__main__":
    unittest.main()
