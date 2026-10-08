"""Synthetic rejection checks; these unit cases are never native evidence."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent / "native_interest"))
import review_stable_ui_diagnostics as review


def startup(court=True):
    expected = review.window.expected_english() if court else review.window.DISCOVERY
    return "\n\n".join("[12:00:01]" + body if body in review.window.DISCOVERY else "[12:00:02]" + body
                        for body, count in expected.items() for _ in range(count))


def native_result(records):
    return {"blockers": [review.DIAGNOSTIC_BLOCKER], "status": "FAIL", "language": "l_english",
            "classification": "PRODUCTION_BADGE_LAYOUT_LANGUAGE_CYCLE", "native_window_assertions": "PASS",
            "localized_witnesses": "PASS", "pass_count": 17, "expected_count": 17,
            "localized_witness_count": 2, "source_exact_current": True,
            "visual_status": "NOT_VERIFIED", "physical_hover_status": "NOT_VERIFIED",
            "unreviewed_diagnostics": records}


class StableUIDiagnosticTests(unittest.TestCase):
    debug = "[12:00:03] TNGUI_TEST|BEGIN|production_window\n"

    def test_exact_english_two_or_sixty_only(self):
        for count, error in ((2, startup(False)), (60, startup())):
            phase, issues = review.validate_startup(error, self.debug)
            self.assertEqual(issues, [])
            self.assertEqual(phase["record_count"], count)

    def test_russian_punctuation_not_accepted_as_english(self):
        error = startup().replace(review.window.ENGLISH_DISPLAY, review.window.RUSSIAN_DISPLAY)
        self.assertTrue(review.validate_startup(error, self.debug)[1])

    def test_unknown_gui_new_identity_path_wording_or_count_rejected(self):
        items = review.window.court.records(startup())
        variants = [startup() + "\n[12:00:02][E][pdx_gui_container.cpp:142]: layout error",
                    "\n".join(items[:-1]), "\n".join(items + [items[-1]]),
                    startup().replace("4294967295", "42", 1),
                    startup().replace("line: 9 ", "line: 10 ", 1),
                    startup().replace("is not valid", "is invalid", 1)]
        for error in variants:
            with self.subTest(error=error[:100]):
                self.assertTrue(review.validate_startup(error, self.debug)[1])

    def test_after_begin_split_burst_missing_timestamp_or_extra_begin_rejected(self):
        for error, debug in ((startup().replace("12:00:02", "12:00:03"), self.debug),
                             (startup().replace("[12:00:02]", "[12:00:01]", 1), self.debug),
                             (startup().replace("[12:00:01]", "", 1), self.debug),
                             (startup(), self.debug * 2),
                             (startup(False).replace("12:00:01", "12:00:03"), self.debug)):
            self.assertTrue(review.validate_startup(error, debug)[1])

    def test_older_only_exact_expected_objections_replaced(self):
        for count in (2, 60):
            expected = review.anticipated_old_objections(Path("target"), count)
            self.assertEqual(review.retain_old_problems(expected, expected), [])
            self.assertTrue(review.retain_old_problems(expected[:-1], expected))
            self.assertTrue(review.retain_old_problems(expected + [expected[0]], expected))
            self.assertIn("source changed", review.retain_old_problems(expected + ["source changed"], expected))

    def test_native_source_locale_and_visual_contract_remain_mandatory(self):
        result = native_result([])
        self.assertEqual(review.validate_badge_gate(result), [])
        for key, value in (("language", "l_russian"), ("native_window_assertions", "FAIL"),
                           ("localized_witnesses", "FAIL"), ("source_exact_current", False),
                           ("expected_count", 16), ("pass_count", 16), ("localized_witness_count", 1),
                           ("visual_status", "PASS"), ("physical_hover_status", "PASS")):
            changed = result | {key: value}
            self.assertTrue(review.validate_badge_gate(changed), key)

    def test_other_blocker_cannot_be_removed(self):
        for blockers in ([], [review.DIAGNOSTIC_BLOCKER] * 2, [review.DIAGNOSTIC_BLOCKER, "source drift"]):
            self.assertTrue(review.validate_badge_gate(native_result([]) | {"blockers": blockers}))

    def consumer_fixture(self):
        target = Path("target").resolve()
        records = review.window.court.records(startup())
        saved = {"schema_version": 1, "classification": review.CLASSIFICATION, "status": "SCOPED_REVIEW_PASS",
                 "target_run": str(target), "generator_sha256": review.window.court.sha(Path(review.__file__)),
                 "accepted_diagnostics": records, "target_phase": {"record_count": 60},
                 "bound_files": [{"path": "control", "sha256": "bound"}], "limits": ["NOT_VERIFIED"],
                 "recorded_utc": "old"}
        return target, native_result(records), saved, saved | {"recorded_utc": "new"}

    def test_consumer_recomputed_equal_accepts_only_diagnostic_blocker(self):
        target, native, saved, verified = self.consumer_fixture()
        result = review.apply_review(native, saved, verified, target, Path("review.json"), "hash")
        self.assertEqual(result["status"], "PASS_WITH_SCOPED_DIAGNOSTICS_REVIEW")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(len(result["reviewed_diagnostics"]), 60)
        self.assertEqual(result["visual_status"], "NOT_VERIFIED")
        self.assertEqual(native["blockers"], [review.DIAGNOSTIC_BLOCKER])

    def test_saved_report_forgery_helper_hash_or_binding_drift_fails(self):
        for key, value in (("status", "SCOPED_REVIEW_FAIL"), ("classification", "wildcard"),
                           ("generator_sha256", "drift"), ("bound_files", []),
                           ("accepted_diagnostics", []), ("target_run", "other")):
            target, native, saved, verified = self.consumer_fixture()
            saved[key] = value
            result = review.apply_review(native, saved, verified, target, Path("review.json"), "hash")
            self.assertEqual(result["status"], "FAIL", key)
            self.assertTrue(result["unreviewed_diagnostics"])

    def test_recomputed_failure_native_failure_or_extra_record_fails(self):
        for case in ("review", "native", "record", "blocker"):
            target, native, saved, verified = self.consumer_fixture()
            if case == "review":
                verified["status"] = "SCOPED_REVIEW_FAIL"
            elif case == "native":
                native["native_window_assertions"] = "FAIL"
            elif case == "record":
                native["unreviewed_diagnostics"] = native["unreviewed_diagnostics"] + ["GUI failure"]
            else:
                native["blockers"].append("crash")
            self.assertEqual(review.apply_review(native, saved, verified, target, Path("review.json"), "hash")["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
