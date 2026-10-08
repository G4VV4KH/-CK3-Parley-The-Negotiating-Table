"""Focused safety tests for the new native-interest diagnostic gate."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).parent / "native_interest"
spec = importlib.util.spec_from_file_location("interest_native_inspector", ROOT / "inspect_interest_probe.py")
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)
court_spec = importlib.util.spec_from_file_location("interest_court", ROOT / "review_court_diagnostics.py")
court = importlib.util.module_from_spec(court_spec)
court_spec.loader.exec_module(court)


class NativeInterestDiagnosticReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        self.relative = "common/character_interactions/tnt_10_interaction.txt"
        self.content = b"tnt_open_negotiations = { ai_frequency = 0 }\n"
        self.baseline = self.run / "baseline.txt"
        self.baseline.write_bytes(self.content)
        for tree in ("runtime", "merged"):
            path = self.run / tree / self.relative
            path.parent.mkdir(parents=True)
            path.write_bytes(self.content)
        self.entry = dict(json.loads((ROOT / "diagnostic-review.json").read_text(encoding="utf-8"))["entries"][0])
        self.entry.update(baseline_file=str(self.baseline), sha256=inspector.sha(self.baseline))
        self.review = self.run / "review.json"
        self.save_review()
        self.message = "[12:00:00]" + self.entry["exact_message_without_timestamp"]
        self.manifest = {"runtime_sha256": {self.relative: inspector.sha(self.baseline)}}

    def save_review(self):
        self.review.write_text(json.dumps({"schema_version": 1, "entries": [self.entry]}), encoding="utf-8")

    def evaluate(self, records=None):
        return inspector.review_diagnostics(records or [self.message], self.run, self.manifest, self.review)

    def test_exact_verified_warning_only(self):
        reviewed, remaining, issues, identity = self.evaluate()
        self.assertEqual(len(reviewed), 1)
        self.assertEqual((remaining, issues), ([], []))
        self.assertEqual(identity["sha256"], inspector.sha(self.review))

    def test_unknown_or_changed_message_is_not_allowed(self):
        reviewed, remaining, issues, _ = self.evaluate([self.message + " new error"])
        self.assertEqual(reviewed, [])
        self.assertEqual(len(remaining), 1)
        self.assertEqual(issues, [])

    def test_duplicate_warning_blocks(self):
        reviewed, remaining, _, _ = self.evaluate([self.message, self.message])
        self.assertEqual((len(reviewed), len(remaining)), (1, 1))

    def test_changed_runtime_or_test_override_blocks(self):
        for tree in ("runtime", "merged"):
            with self.subTest(tree=tree):
                path = self.run / tree / self.relative
                path.write_bytes(b"changed")
                reviewed, remaining, issues, _ = self.evaluate()
                self.assertEqual(reviewed, [])
                self.assertEqual(len(remaining), 1)
                self.assertTrue(issues)
                path.write_bytes(self.content)

    def test_changed_baseline_blocks(self):
        self.baseline.write_bytes(b"changed")
        reviewed, remaining, issues, _ = self.evaluate()
        self.assertEqual(reviewed, [])
        self.assertEqual(len(remaining), 1)
        self.assertTrue(issues)

    def test_wildcard_or_different_classification_blocks(self):
        self.entry["exact_message_without_timestamp"] = ".*"
        self.entry["classification"] = "IGNORE_ALL"
        self.save_review()
        reviewed, remaining, issues, _ = self.evaluate()
        self.assertEqual(reviewed, [])
        self.assertEqual(len(remaining), 1)
        self.assertTrue(issues)

    def test_no_review_never_suppresses(self):
        reviewed, remaining, issues, identity = inspector.review_diagnostics([self.message], self.run, self.manifest)
        self.assertEqual((reviewed, remaining, issues, identity), ([], [self.message], [], None))


class NativeInterestCourtReviewTests(unittest.TestCase):
    def setUp(self):
        self.burst = ["[12:00:00]" + court.TRIGGER + name
                      for name, count in court.SCENES.items() for _ in range(count)]
        self.burst.append("[12:00:00]" + court.MANAGER)

    def test_only_timestamp_is_normalized(self):
        self.assertTrue(court.exact_burst(self.burst))
        self.assertTrue(court.exact_burst([item.replace("[12:00:00]", "[13:24:59]", 1) for item in self.burst]))

    def test_count_identity_path_and_control_chars_fail_closed(self):
        variants = [self.burst[:-1], self.burst + [self.burst[0]]]
        for original, replacement in (("4294967295", "1"), ("line: 9", "line: 8"),
                                      ("\x15weak", "weak"), ("untyped trigger", "different trigger")):
            variants.append([item.replace(original, replacement) for item in self.burst])
        for changed in variants:
            with self.subTest(changed=changed[-1]):
                self.assertFalse(court.exact_burst(changed))

    def test_initial_load_requires_before_fixture(self):
        self.assertEqual(court.phase_of_burst(self.burst, "[12:00:01] TNI_TEST|BEGIN|interest"),
                         "INITIAL_WORLD_LOAD_BEFORE_FIXTURE")
        self.assertEqual(court.phase_of_burst(self.burst, "[11:59:59] TNI_TEST|BEGIN|interest"), "UNVERIFIED")

    def test_native_load_has_exact_temporal_boundaries(self):
        debug = ("[11:59:50] TNI_TEST|BEGIN|interest\n"
                 "[11:59:59] TNI_RELOAD|native_exact_local_load|probe\n"
                 "[12:00:01] TNI_RELOAD|loaded_state_observed_before_recovery|yes")
        self.assertEqual(court.phase_of_burst(self.burst, debug), "NATIVE_DISK_LOAD_BEFORE_RESTORED_CALLBACK")
        self.assertEqual(court.phase_of_burst(self.burst, debug.replace("[12:00:01]", "[11:59:59]")), "UNVERIFIED")

    def test_second_burst_is_not_one_startup_event(self):
        changed = list(self.burst)
        changed[0] = changed[0].replace("[12:00:00]", "[12:00:01]")
        self.assertEqual(court.phase_of_burst(changed, "[12:00:02] TNI_TEST|BEGIN|interest"), "UNVERIFIED")

    def test_v2_exact_startup_and_disk_load_pair(self):
        reload_burst = [item.replace("[12:00:00]", "[12:00:04]") for item in self.burst]
        debug = ("[12:00:01] TNI_TEST|BEGIN|interest\n"
                 "[12:00:03] TNI_RELOAD|native_exact_local_load|probe\n"
                 "[12:00:05] TNI_RELOAD|loaded_state_observed_before_recovery|yes")
        bursts, issues = court.validate_target_bursts(self.burst + reload_burst, debug, self.burst)
        self.assertEqual(len(bursts), 2)
        self.assertEqual(issues, [])

    def test_v2_duplicate_phase_extra_burst_and_body_drift_block(self):
        debug = ("[12:00:02] TNI_TEST|BEGIN|interest\n"
                 "[12:00:03] TNI_RELOAD|native_exact_local_load|probe\n"
                 "[12:00:05] TNI_RELOAD|loaded_state_observed_before_recovery|yes")
        second_startup = [item.replace("[12:00:00]", "[12:00:01]") for item in self.burst]
        reload_burst = [item.replace("[12:00:00]", "[12:00:04]") for item in self.burst]
        cases = [self.burst + second_startup, self.burst + second_startup + reload_burst,
                 self.burst + [item.replace("4294967295", "12345") for item in reload_burst],
                 self.burst + reload_burst + [reload_burst[0]]]
        for case in cases:
            with self.subTest(records=len(case)):
                self.assertTrue(court.validate_target_bursts(case, debug, self.burst)[1])

    def test_forged_pass_json_cannot_suppress_arbitrary_58_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            report = run / "forged.json"
            errors = ["[12:00:00] unrelated production failure"] * 58
            report.write_text(json.dumps({"schema_version": 1,
                "classification": "EXACT_INHERITED_NATIVE_COURT_INITIALIZATION_BURST",
                "status": "SCOPED_REVIEW_PASS", "control_run": str(run), "target_run": str(run),
                "accepted_diagnostics": errors, "bound_files": [{"path": str(report), "sha256": "fake"}]}), encoding="utf-8")
            reviewed, remaining, issues, _ = inspector.apply_court_review(errors, run, report)
            self.assertEqual(reviewed, [])
            self.assertEqual(remaining, errors)
            self.assertTrue(issues)


if __name__ == "__main__":
    unittest.main()
