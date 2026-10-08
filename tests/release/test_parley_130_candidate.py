"""Separate 1.3 candidate checks; temp snapshots only, no native or publication."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools/release/prepare_parley_1_3_candidate.py"
SPEC = importlib.util.spec_from_file_location("parley_130_candidate", SCRIPT)
candidate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(candidate)


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = candidate.tree(REPO / "mod/parley")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "authoring"
        self.output = self.root / "candidate"
        for name, data in self.runtime.items():
            candidate.write_new(self.source / "mod/parley" / name, data)
        self.git = mock.patch.object(candidate, "git_state", return_value={
            "head": "a" * 40, "branch": "test-only", "porcelain": "?? mod/parley/common/script_values/tnt_65_interest_preview_values.txt\n"})
        self.git.start()
        self.addCleanup(self.git.stop)

    def check(self):
        return candidate.inspect_source(self.source)[2]

    def freeze(self):
        return candidate.freeze(self.source, self.output, "parley-1.3.0-test",
                                self.check()["source_fingerprint_sha256"])

    def test_exact_reviewed_inventory_and_profile(self):
        self.assertEqual(len(candidate.RUNTIME_PATHS), 89)
        self.assertEqual(set(self.runtime), candidate.RUNTIME_PATHS)
        evidence = self.check()
        self.assertEqual(len(evidence["game_runtime"]), 88)
        self.assertEqual(evidence["static_localization_coverage"]["parley"]["keys_per_language"], 720)
        self.assertEqual(len(evidence["static_localization_coverage"]["parley"]["languages"]), 9)
        self.assertFalse(evidence["acceptance"]["publication_ready"])
        self.assertIn("??", evidence["git_observation"]["porcelain"])
        self.assertFalse(self.output.exists())

    def test_check_preserves_source_and_has_no_outputs(self):
        before = candidate.tree(self.source)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(candidate.main(["--check", "--source-repo", str(self.source)]), 0)
        self.assertEqual(candidate.tree(self.source), before)
        self.assertFalse(self.output.exists())

    def test_missing_or_same_count_substituted_helper_is_rejected(self):
        for helper in (name for name in self.runtime if "tnt_6" in name and "script_values" in name):
            files = dict(self.runtime)
            del files[helper]
            with self.subTest(helper=helper), self.assertRaises(candidate.CandidateError):
                candidate.validate_runtime(files)
            files["common/script_values/substituted.txt"] = b"fake = 1"
            with self.subTest(helper=helper, substitution=True), self.assertRaises(candidate.CandidateError):
                candidate.validate_runtime(files)

    def test_descriptor_old_version_duplicate_name_and_remote_identity_rejected(self):
        good = self.runtime["descriptor.mod"]
        for bad in (good.replace(b'1.3.0', b'1.2.2'), good + b'\nversion="1.3.0"\n',
                    good.replace(b'Parley:', b'[DEV] Parley:'), good + b'\nremote_file_id="3811090081"\n',
                    good + b'\npath="mod/parley"\n', good.replace(b'1.20.*', b'1.19.*')):
            with self.subTest(bad=bad), self.assertRaises(candidate.CandidateError):
                candidate.validate_runtime({**self.runtime, "descriptor.mod": bad})

    def test_source_pin_required_and_drift_rejected_before_write(self):
        for pin in (None, "0" * 64):
            with self.assertRaisesRegex(candidate.CandidateError, "fingerprint drifted"):
                candidate.freeze(self.source, self.output, "test", pin)
            self.assertFalse(self.output.exists())

    def test_inventory_extra_file_rejected_before_output(self):
        candidate.write_new(self.source / "mod/parley/README.md", b"not runtime")
        with self.assertRaisesRegex(candidate.CandidateError, "Runtime inventory differs"):
            self.check()
        self.assertFalse(self.output.exists())

    def test_freeze_verify_and_exact_projection_without_publication_claim(self):
        result = self.freeze()
        self.assertEqual(result["status"], candidate.STATUS)
        self.assertFalse((self.output / "deploy").exists())
        self.assertFalse(list(self.output.rglob("*.zip")))
        manifest = json.loads((self.output / "candidate-manifest.json").read_bytes())
        self.assertEqual(set(manifest["source_runtime"]), set(self.runtime))
        self.assertEqual(manifest["acceptance"], candidate.PENDING)
        self.assertEqual(candidate.tree(self.source / "mod/parley"), self.runtime)
        verified = candidate.verify(self.output, result["manifest_sha256"])
        self.assertFalse(verified["acceptance"]["publication_ready"])
        self.assertIn("ACCEPTANCE_STILL_PENDING", verified["status"])

    def test_existing_or_overlapping_output_refused(self):
        self.output.mkdir()
        with self.assertRaisesRegex(candidate.CandidateError, "existing candidate"):
            candidate.safe_output(self.source, self.output)
        with self.assertRaisesRegex(candidate.CandidateError, "overlaps"):
            candidate.safe_output(self.source, self.source / "new-output")
        with self.assertRaises(candidate.CandidateError):
            candidate.freeze(self.source, self.root / "unsafe", "../outside", "0" * 64)

    def test_second_freeze_never_overwrites_candidate(self):
        self.freeze()
        before = candidate.tree(self.output)
        with self.assertRaisesRegex(candidate.CandidateError, "existing candidate"):
            self.freeze()
        self.assertEqual(candidate.tree(self.output), before)

    def test_manifest_wrong_pin_and_forged_acceptance_rejected(self):
        result = self.freeze()
        with self.assertRaisesRegex(candidate.CandidateError, "manifest hash"):
            candidate.verify(self.output, "0" * 64)
        path = self.output / "candidate-manifest.json"
        data = json.loads(path.read_bytes())
        data["acceptance"]["publication_ready"] = True
        raw = candidate.json_bytes(data)
        path.write_bytes(raw)
        with self.assertRaisesRegex(candidate.CandidateError, "cannot assert publication acceptance"):
            candidate.verify(self.output, candidate.sha(raw))

    def test_every_artifact_class_is_hash_bound_and_extra_file_is_rejected(self):
        result = self.freeze()
        for name in ("source/dev/parley/mod/parley/common/script_values/tnt_65_interest_preview_values.txt",
                     "tools/build_game.py", "tools/prepare_parley_1_3_candidate.py", "source-lock.json",
                     "builder-checks.json", "game/parley-1.3.0-test/parley/gui/tnt_types.gui"):
            path = self.output / name
            original = path.read_bytes()
            path.write_bytes(original + b"\n# drift\n")
            with self.subTest(name=name), self.assertRaisesRegex(candidate.CandidateError, "artifact inventory/bytes drift"):
                candidate.verify(self.output, result["manifest_sha256"])
            path.write_bytes(original)
        candidate.write_new(self.output / "extra.txt", b"not bound")
        with self.assertRaisesRegex(candidate.CandidateError, "artifact inventory/bytes drift"):
            candidate.verify(self.output, result["manifest_sha256"])

    def test_source_change_during_freeze_never_creates_success_manifest(self):
        original_run = candidate.run_builder
        calls = []
        def mutate_after_verify(*args):
            result = original_run(*args)
            calls.append(result)
            if len(calls) == 3:
                path = self.source / "mod/parley/common/script_values/tnt_65_interest_preview_values.txt"
                path.write_bytes(path.read_bytes() + b"\n# fixture-only race\n")
            return result
        with mock.patch.object(candidate, "run_builder", side_effect=mutate_after_verify):
            with self.assertRaisesRegex(candidate.CandidateError, "changed during freeze"):
                self.freeze()
        self.assertFalse((self.output / "candidate-manifest.json").exists())
        self.assertTrue(self.output.exists())  # Failed evidence is not erased/reused.

    def test_no_acceptance_bypass_or_upload_arguments(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            candidate.main(["--check", "--source-repo", str(self.source), "--skip-localization"])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            candidate.main(["--publish"])


if __name__ == "__main__":
    unittest.main()
