"""Fail-closed tests for the separate GUI-supplied-boolean diagnostic review."""
from collections import Counter
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_interest_window_diagnostics import diagnostic_fixture, native_fixture

sys.path.insert(0, str(Path(__file__).parent / "native_interest"))
import review_currency_ui_diagnostics as review
import inspect_window_open_probe as inspector


class CurrencyDiagnosticPhaseTests(unittest.TestCase):
    def setUp(self):
        _, self.debug = native_fixture()
        self.debug = self.debug.replace("12:00:03", "12:00:06")
        self.full = diagnostic_fixture().replace("12:00:02", "12:00:05")
        self.short = "\n".join("[12:00:01]" + body for body in review.window.DISCOVERY)
        self.warnings = "\n".join(f"[{time}]" + review.WARNING for time in ("12:00:02", "12:00:03"))

    def test_only_exact_four_records_pass(self):
        phase, issues = review.validate_startup(self.short + "\n" + self.warnings, self.debug)
        self.assertEqual(issues, [])
        self.assertEqual(phase["record_count"], 4)
        self.assertEqual(phase["dynamic_bool_warning_count"], 2)
        self.assertTrue(review.validate_startup(self.full + "\n" + self.warnings, self.debug)[1])

    def test_missing_duplicate_new_target_or_changed_wording_fail(self):
        for warnings in (self.warnings.splitlines()[0], self.warnings + "\n" + self.warnings.splitlines()[0],
                         self.warnings.replace("'observed'", "'other'"), self.warnings.replace("never set", "not set"),
                         self.warnings.replace("1162", "1163")):
            self.assertTrue(review.validate_startup(self.short + "\n" + warnings, self.debug)[1])

    def test_post_begin_before_discovery_or_same_time_warnings_fail(self):
        for warnings in (self.warnings.replace("12:00:03", "12:00:06"),
                         self.warnings.replace("12:00:02", "12:00:00"),
                         self.warnings.replace("12:00:03", "12:00:02")):
            self.assertTrue(review.validate_startup(self.short + "\n" + warnings, self.debug)[1])

    def test_any_gui_or_partial_court_diagnostic_fails(self):
        gui = "[12:00:04][E][pdx_gui_container.cpp:142]: gui/tnt_types.gui:159 - layout error"
        partial = next(item for item in review.window.court.records(self.full) if "4294967295" in item)
        for extra in (gui, partial, self.full):
            self.assertTrue(review.validate_startup(self.short + "\n" + self.warnings + "\n" + extra, self.debug)[1])


class CurrencyDiagnosticClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.probe_run = Path(cls.temp.name) / "probe"
        with redirect_stdout(StringIO()):
            review.fixture.prepare(cls.probe_run)
        cls.plan = json.loads((cls.probe_run / "plan.json").read_text(encoding="utf-8"))
        cls.manifest = deepcopy(cls.plan)
        cls.manifest["preparer_sha256"] = review.window.court.sha(Path(review.fixture.ordinary.__file__))
        cls.probe_texts = {path.relative_to(cls.probe_run / "probe").as_posix(): path.read_text(encoding="utf-8-sig")
                           for path in (cls.probe_run / "probe").rglob("*") if path.is_file() and path.suffix in review.TEXT_SUFFIXES}
        cls.runtime_texts = {path.relative_to(review.fixture.ordinary.base.SOURCE).as_posix(): path.read_text(encoding="utf-8-sig")
                             for path in review.fixture.ordinary.base.SOURCE.rglob("*") if path.is_file() and path.suffix in review.TEXT_SUFFIXES}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def issues(self, runtime=None, probe=None, manifest=None, plan=None):
        return review.validate_fixture(self.runtime_texts if runtime is None else runtime,
                                       self.probe_texts if probe is None else probe,
                                       self.manifest if manifest is None else manifest,
                                       self.plan if plan is None else plan)

    def test_current_generated_probe_has_exact_closed_boolean_calls(self):
        self.assertEqual(len(review.expected_calls()), 34)
        self.assertEqual(self.issues(), [])

    def test_runtime_comments_are_not_event_targets_but_live_token_is_rejected(self):
        self.assertEqual(self.issues(runtime={"comment.txt": "# observed is a historical prose word\n"}), [])
        for text in ("scope:observed = yes", "save_scope_as = observed", "set_variable = { name = observed value = yes }"):
            self.assertTrue(self.issues(runtime={"script.txt": text}))

    def test_dummy_assignment_existence_or_changed_polarity_is_rejected(self):
        path = "common/scripted_guis/tnwqa_controls.txt"
        for old, new in (("scope:observed = no", "scope:observed = yes"),
                         ("scope:observed = yes", "exists = scope:observed"),
                         ("scope:observed = yes", "scope:observed = yes save_scope_as = observed")):
            texts = dict(self.probe_texts)
            texts[path] = texts[path].replace(old, new, 1)
            self.assertTrue(self.issues(probe=texts))

    def test_missing_extra_plain_or_changed_gui_producer_is_rejected(self):
        path = "gui/tnuq_driver.gui"
        for addition in ("on_finish = \"[GetScriptedGui('tnuq_bool_true').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]\"",
                         "on_finish = \"[GetScriptedGui('tnuq_bool_true').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).AddScope('observed',MakeScopeBool(IsGamePaused)).End)]\""):
            texts = dict(self.probe_texts)
            texts[path] += "\n" + addition
            self.assertTrue(self.issues(probe=texts))
        for old, new in (("MakeScopeBool(Not(IsGamePaused))", "MakeScopeBool(IsGamePaused)"),
                         ("'tnuq_bool_true'", "'tnuq_unreviewed'")):
            texts = dict(self.probe_texts)
            texts[path] = texts[path].replace(old, new)
            self.assertTrue(self.issues(probe=texts))

    def test_extra_probe_script_scope_and_generator_or_count_drift_fail(self):
        texts = self.probe_texts | {"common/scripted_effects/unrelated.txt": "save_scope_as = observed"}
        self.assertTrue(self.issues(probe=texts))
        for key, value in (("preparer_sha256", "wrong"), ("expected_count", 156), ("currency_ui_preview_lock_cycle", False)):
            self.assertTrue(self.issues(plan=self.plan | {key: value}))
            self.assertTrue(self.issues(manifest=self.manifest | {key: value}))


class CurrencyDiagnosticConsumerTests(unittest.TestCase):
    def test_saved_pass_is_recomputed_and_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            path = run / "review.json"
            records = ["one", "two", "three", "four"]
            saved = {"schema_version": 1, "classification": review.CLASSIFICATION,
                     "status": "SCOPED_REVIEW_PASS", "off_control_run": str(run / "off"),
                     "window_control_run": str(run / "window"), "target_run": str(run),
                     "generator_sha256": review.window.court.sha(Path(review.__file__)),
                     "accepted_diagnostics": records, "target_phase": {"record_count": 4},
                     "limits": [], "recorded_utc": "old"}
            path.write_text(json.dumps(saved), encoding="utf-8")
            with patch.object(review, "review", return_value=saved | {"recorded_utc": "new"}) as recompute:
                reviewed, remaining, issues, identity = inspector.apply_currency_ui_review(records, run, path)
                recompute.assert_called_once()
                self.assertEqual(len(reviewed), 4)
                self.assertEqual(remaining, [])
                self.assertEqual(issues, [])
                self.assertTrue(identity["recomputed"])
            for changed in ({"status": "SCOPED_REVIEW_FAIL"}, {"bound_files": ["changed"]},
                            {"target_phase": {"record_count": 62}}, {"accepted_diagnostics": records[:-1]}):
                with patch.object(review, "review", return_value=saved | changed):
                    reviewed, remaining, issues, _ = inspector.apply_currency_ui_review(records, run, path)
                    self.assertEqual(reviewed, [])
                    self.assertEqual(remaining, records)
                    self.assertTrue(issues)


if __name__ == "__main__":
    unittest.main()
