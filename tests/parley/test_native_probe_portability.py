"""External inputs are explicit; these tests never install or launch CK3."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


NATIVE = Path(__file__).parent / "native_interest"
sys.path.insert(0, str(NATIVE))
import probe_configuration as config
import prepare_interest_probe as base
import inspect_interest_probe as inspector

PREPARERS = {
    "prepare_interest_probe": lambda module, run: module.prepare_plan(run, "standard"),
    "prepare_window_open_probe": lambda module, run: module.prepare(run, "standard"),
    "prepare_final_window_probe": lambda module, run: module.prepare(run),
    "prepare_currency_ui_probe": lambda module, run: module.prepare(run),
    "prepare_badge_layout_probe": lambda module, run: module.prepare(run),
    "prepare_hover_content_probe": lambda module, run: module.prepare(run),
    "prepare_hover_content_probe_v2": lambda module, run: module.prepare(run),
}


class NativeProbePortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {}, clear=True).start()
        patch.object(config, "_cli", {}).start()

    def test_all_entrypoints_import_without_installation_and_expose_same_cli(self):
        for name in PREPARERS:
            with self.subTest(name=name):
                result = subprocess.run([sys.executable, "-B", str(NATIVE / (name + ".py")), "--help"],
                                        cwd=self.root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                for flag, _ in config.OPTIONS.values():
                    self.assertIn(flag, result.stdout)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_missing_dependency_fails_before_any_preparer_creates_output(self):
        for name, invoke in PREPARERS.items():
            with self.subTest(name=name):
                destination = self.root / name
                with self.assertRaisesRegex(ValueError, "reload-helper"):
                    invoke(importlib.import_module(name), destination)
                self.assertFalse(destination.exists())

    def test_pure_fixture_does_not_require_any_external_paths(self):
        event, values, controls, labels = base.fixture("standard")
        self.assertTrue(event and values and controls and labels)

    def test_cli_environment_conflict_and_relative_inputs_fail(self):
        first, second = self.root / "first", self.root / "second"
        first.mkdir()
        second.mkdir()
        os.environ["PARLEY_QA_EVIDENCE_ROOT"] = str(first)
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            config.configure(argparse.Namespace(evidence_root=second))
        config._cli = {}
        os.environ["PARLEY_QA_EVIDENCE_ROOT"] = "relative"
        with self.assertRaisesRegex(ValueError, "absolute"):
            config.resolve("evidence_root")

    def test_lazy_paths_share_configuration_and_hash_readonly_inputs(self):
        helper = self.root / "build_reload_probe.py"
        helper.write_bytes(b"# test-only external helper\n")
        settings = self.root / "input-profile" / "pdx_settings.txt"
        settings.parent.mkdir()
        settings.write_bytes(b"test-only settings\n")
        os.environ.update(PARLEY_QA_RELOAD_HELPER=str(helper), CK3_USER_SETTINGS=str(settings),
                          PARLEY_QA_EVIDENCE_ROOT=str(self.root))
        self.assertEqual(Path(base.RELOAD_HELPER), helper)
        self.assertEqual(Path(base.EVIDENCE / "probe"), self.root / "probe")
        record = config.inputs("reload_helper", "settings_source")
        self.assertEqual(record["reload_helper"]["files"]["file"]["sha256"],
                         hashlib.sha256(helper.read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError, "input user profile"):
            config.validate_run(settings.parent / "probe", "reload_helper")
        self.assertEqual(helper.read_bytes(), b"# test-only external helper\n")
        self.assertEqual(settings.read_bytes(), b"test-only settings\n")

    def test_freeze_missing_inputs_fails_before_output(self):
        helper = self.root / "helper.py"
        helper.write_bytes(b"# read only\n")
        os.environ["PARLEY_QA_RELOAD_HELPER"] = str(helper)
        destination = self.root / "run"
        with self.assertRaisesRegex(ValueError, "game-root"):
            base.freeze(destination)
        self.assertFalse(destination.exists())

    def test_baseline_members_are_cwd_independent_and_fail_closed(self):
        review = json.loads((NATIVE / "diagnostic-review.json").read_text())
        self.assertEqual(review["schema_version"], 2)
        baseline = self.root / "baseline"
        for index, entry in enumerate(review["entries"]):
            path = baseline / entry["baseline_member"]
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = f"fixture baseline {index}".encode()
            path.write_bytes(payload)
            fixture = dict(entry, sha256=hashlib.sha256(payload).hexdigest())
            self.assertEqual(config.baseline_member(fixture, 2, baseline), path)
            with self.assertRaisesRegex(ValueError, "hash differs"):
                config.baseline_member(entry, 2, baseline)
            for member in ("../escape", "/absolute", chr(88) + ":/drive",
                           "\\" * 2 + "server" + "\\" + "share", "common/../escape"):
                with self.subTest(member=member), self.assertRaises(ValueError):
                    config.baseline_member(dict(fixture, baseline_member=member), 2, baseline)
            with self.assertRaises(ValueError):
                config.baseline_member(fixture, 2, self.root / "missing")
            with self.assertRaisesRegex(ValueError, "absolute"):
                config.baseline_member(fixture, 2, Path("relative"))

    def test_both_pinned_historical_hashes_resolve_from_fixture_baseline(self):
        review = json.loads((NATIVE / "diagnostic-review.json").read_text())
        for entry in review["entries"]:
            source = base.SOURCE / entry["runtime_file"]
            target = self.root / "baseline" / entry["baseline_member"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            self.assertEqual(config.baseline_member(entry, 2, self.root / "baseline"), target)

    def test_v2_review_cannot_waive_missing_or_wrong_baseline(self):
        entry = json.loads((NATIVE / "diagnostic-review.json").read_text())["entries"][0]
        review = self.root / "review.json"
        review.write_text(json.dumps({"schema_version": 2, "entries": [entry]}))
        message = "[12:00:00]" + entry["exact_message_without_timestamp"]
        reviewed, remaining, issues, _ = inspector.review_diagnostics(
            [message], self.root, {"runtime_sha256": {}}, review)
        self.assertFalse(reviewed)
        self.assertEqual(remaining, [message])
        self.assertTrue(issues)

    def test_v2_review_accepts_only_full_matching_baseline_runtime_and_merged(self):
        entry = dict(json.loads((NATIVE / "diagnostic-review.json").read_text())["entries"][0])
        payload = b"review fixture bytes, not CK3 evidence"
        entry["sha256"] = hashlib.sha256(payload).hexdigest()
        for tree in ("baseline", "runtime", "merged"):
            path = self.root / tree / entry["runtime_file"]
            path.parent.mkdir(parents=True)
            path.write_bytes(payload)
        review = self.root / "review.json"
        review.write_text(json.dumps({"schema_version": 2, "entries": [entry]}))
        message = "[12:00:00]" + entry["exact_message_without_timestamp"]
        manifest = {"runtime_sha256": {entry["runtime_file"]: entry["sha256"]}}
        reviewed, remaining, issues, _ = inspector.review_diagnostics(
            [message], self.root, manifest, review, self.root / "baseline")
        self.assertEqual((len(reviewed), remaining, issues), (1, [], []))
        self.assertEqual(Path(reviewed[0]["baseline_file"]),
                         self.root / "baseline" / entry["runtime_file"])
        (self.root / "baseline" / entry["runtime_file"]).write_bytes(b"changed")
        reviewed, remaining, issues, _ = inspector.review_diagnostics(
            [message], self.root, manifest, review, self.root / "baseline")
        self.assertEqual((reviewed, remaining), ([], [message]))
        self.assertTrue(issues)


if __name__ == "__main__":
    unittest.main()
