"""Fail-closed saved-review consumption and independent diagnostic gates."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent / "native_interest"))
import inspect_window_open_probe as inspector


class WindowReviewConsumerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / "target"
        self.review_path = Path(self.temp.name) / "review.json"
        self.records = [f"[12:00:01] exact bound record {index}" for index in range(60)]
        self.verified = {
            "schema_version": 1, "classification": "EXACT_RUSSIAN_WINDOW_STARTUP_60_RECORDS",
            "status": "SCOPED_REVIEW_PASS", "recorded_utc": "fresh timestamp",
            "off_control_run": str(Path(self.temp.name) / "off"),
            "window_control_run": str(Path(self.temp.name) / "window"),
            "target_run": str(self.run.resolve()),
            "generator_sha256": inspector.sha(Path(inspector.window_reviewer.__file__)),
            "bound_files": [{"path": "bound file", "sha256": "bound hash"}],
            "target_source_sha256": {"runtime": {"file": "bound"}},
            "target_phase": {"begin_times": [43203]},
            "accepted_diagnostics": self.records, "problems": [], "limits": ["Scoped only"],
            "current_source_acceptance": "NOT_ASSESSED_HISTORICAL_FROZEN_SOURCE_ONLY",
            "physical_hover_status": "NOT_VERIFIED",
        }
        self.saved = deepcopy(self.verified)
        self.saved["recorded_utc"] = "old timestamp"

    def apply(self, saved=None, verified=None, records=None):
        self.review_path.write_text(json.dumps(self.saved if saved is None else saved), encoding="utf-8")
        with mock.patch.object(inspector.window_reviewer, "review", return_value=self.verified if verified is None else verified) as recompute:
            result = inspector.apply_window_review(self.records if records is None else records, self.run, self.review_path)
        recompute.assert_called_once()
        return result

    def assert_rejected(self, result):
        reviewed, remaining, issues, identity = result
        self.assertEqual(reviewed, [])
        self.assertTrue(remaining)
        self.assertTrue(issues)
        self.assertIsNone(identity)

    def test_recomputes_and_ignores_only_generation_timestamp(self):
        reviewed, remaining, issues, identity = self.apply()
        self.assertEqual(len(reviewed), 60)
        self.assertEqual(remaining, [])
        self.assertEqual(issues, [])
        self.assertTrue(identity["recomputed"])

    def test_edited_records_bindings_phases_and_extra_claims_rejected(self):
        for key, value in (("accepted_diagnostics", ["unrelated error"] * 60),
                           ("bound_files", []), ("target_phase", {}),
                           ("target_source_sha256", {}), ("authoring_acceptance", True),
                           ("physical_hover_status", "PASS")):
            with self.subTest(key=key):
                edited = deepcopy(self.saved)
                edited[key] = value
                self.assert_rejected(self.apply(saved=edited))

    def test_new_source_or_log_binding_drift_rejected(self):
        for key, value in (("bound_files", [{"path": "bound file", "sha256": "changed"}]),
                           ("target_source_sha256", {"runtime": {"file": "changed"}})):
            with self.subTest(key=key):
                drift = deepcopy(self.verified)
                drift[key] = value
                self.assert_rejected(self.apply(verified=drift))

    def test_failed_recomputed_review_cannot_be_overridden_by_saved_pass(self):
        failed = deepcopy(self.verified)
        failed.update(status="SCOPED_REVIEW_FAIL", accepted_diagnostics=[])
        self.assert_rejected(self.apply(verified=failed))

    def test_same_non_scoped_status_or_classification_is_rejected(self):
        for key, value in (("status", "PASS"), ("classification", "IGNORE_ALL_GUI_ERRORS")):
            bad = deepcopy(self.verified)
            bad[key] = value
            self.assert_rejected(self.apply(saved=bad, verified=bad))

    def test_wrong_target_or_generator_rejected_even_if_recomputed_fields_match(self):
        for key, value in (("target_run", str(Path(self.temp.name) / "other")),
                           ("generator_sha256", "not the current reviewer")):
            bad = deepcopy(self.verified)
            bad[key] = value
            self.assert_rejected(self.apply(saved=bad, verified=bad))

    def test_missing_extra_or_changed_input_record_rejected(self):
        for records in (self.records[:-1], self.records + [self.records[0]],
                        self.records[:-1] + ["[12:00:01] new production error"]):
            self.assert_rejected(self.apply(records=records))

    def test_recompute_error_fails_closed_without_accepting_records(self):
        self.review_path.write_text(json.dumps(self.saved), encoding="utf-8")
        with mock.patch.object(inspector.window_reviewer, "review", side_effect=ValueError("source drift")):
            self.assert_rejected(inspector.apply_window_review(self.records, self.run, self.review_path))

    def test_missing_or_malformed_saved_review_fails_closed(self):
        self.assert_rejected(inspector.apply_window_review(self.records, self.run, self.review_path))
        self.review_path.write_text("{invalid", encoding="utf-8")
        self.assert_rejected(inspector.apply_window_review(self.records, self.run, self.review_path))


class WindowInspectorIndependentGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / "run"
        self.source = Path(self.temp.name) / "authoring"
        for tree in (self.source, self.run / "runtime", self.run / "probe", self.run / "merged"):
            tree.mkdir(parents=True)
            (tree / "payload.txt").write_text("unchanged", encoding="utf-8")
        profile = self.run / "userdata"
        (profile / "logs").mkdir(parents=True)
        (profile / "pdx_settings.txt").write_text("test settings", encoding="utf-8")
        labels = sorted(inspector.window_reviewer.OPEN_LABELS)
        debug = "TNGUI_TEST|BEGIN|production_window\nTNGUI_PHASE|BEFORE|production_open_effect\nTNGUI_PHASE|AFTER|production_open_effect\n"
        debug += "\n".join("TNGUI_TEST|PASS|" + label for label in labels)
        debug += "\nTNGUI_TEST|END|production_window\n"
        (profile / "logs/debug.log").write_text(debug, encoding="utf-8")
        (profile / "logs/error.log").write_text("[12:00:00] reviewed startup diagnostic", encoding="utf-8")
        manifest = {tree + "_sha256": inspector.inventory(self.run / tree) for tree in ("runtime", "probe", "merged")}
        manifest.update(runtime_source=str(self.source), prepared_settings_sha256=inspector.sha(profile / "pdx_settings.txt"),
                        expected_labels=labels, isolated_tooltip_flow_fix=False, final_actual_source_cycle=True,
                        game_version="test", preset="standard", language="l_russian", overrides={}, coverage_limits=[])
        (self.run / "frozen-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.run / "process-result.json").write_text(json.dumps({"status": "EXIT_CONFIRMED"}), encoding="utf-8")

    def inspect_with_valid_review(self):
        # Unit isolation: the dedicated consumer tests and reviewer tests verify
        # diagnostics. Here even an accepted review cannot override other gates.
        with mock.patch.object(inspector, "apply_window_review", return_value=([{"record": "reviewed"}], [], [], {"recomputed": True})):
            return inspector.inspect(self.run, window_diagnostic_review=Path("unit-only-review.json"))

    def test_scoped_pass_never_claims_broad_authoring_or_physical_hover_acceptance(self):
        report = self.inspect_with_valid_review()
        self.assertEqual(report["status"], "PASS_WITH_SCOPED_DIAGNOSTICS_REVIEW")
        self.assertEqual(report["classification"], "PRODUCTION_FINAL_SOURCE_WINDOW_TOOLTIP_CYCLE_DIAGNOSTIC")
        self.assertFalse(report["authoring_acceptance"])
        self.assertEqual(report["physical_hover_status"], "NOT_VERIFIED")

    def test_current_authoring_drift_blocks_despite_accepted_review(self):
        (self.source / "payload.txt").write_text("changed", encoding="utf-8")
        report = self.inspect_with_valid_review()
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["source_exact_current"])

    def test_crash_artifacts_block_despite_accepted_review(self):
        crash = self.run / "userdata/crashes/probe"
        crash.mkdir(parents=True)
        (crash / "exception.txt").write_text("stack overflow", encoding="utf-8")
        report = self.inspect_with_valid_review()
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(report["isolated_crash_files_sha256"])

    def test_frozen_source_drift_blocks_despite_accepted_review(self):
        (self.run / "merged/payload.txt").write_text("changed", encoding="utf-8")
        report = self.inspect_with_valid_review()
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("merged integrity" in blocker for blocker in report["blockers"]))


if __name__ == "__main__":
    unittest.main()
