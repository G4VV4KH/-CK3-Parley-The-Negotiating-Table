"""Package subsets in temporary fixtures; never modify pinned release inputs."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "tools/release"
SPEC = importlib.util.spec_from_file_location("subset_builder", TOOLS / "build_game.py")
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)
VANILLA = ("parley", "marriage_calc_assistant")


class ReleaseSubsetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dev = self.root / "dev"
        self.output = self.root / "game"
        self.build_id = "test-vanilla-subset"
        self.inputs = {}
        self.lock = {"schema": 1, "purpose": "TEST FIXTURE ONLY", "mods": {}}

    def add_mca_fixture(self):
        mod = "marriage_calc_assistant"
        files = {"descriptor.mod": b'version="1.0.0"\n',
                 "common/script_values/test_values.txt": b"fixture_value = { value = 1 }\n"}
        for language in builder.LANGUAGES:
            text = f"l_{language}:\n" + "".join(f' fixture_{i}:0 "Text {i}"\n' for i in range(22))
            files[f"localization/{language}/fixture_l_{language}.yml"] = text.encode("utf-8-sig")
        self.add_mod(mod, files)

    def add_parley_fixture(self):
        # Copy this repository's real transform input to a disposable fixture.
        # Its dynamically pinned hashes certify this test copy only, not a release.
        source = REPO / "mod/parley"
        files = {path.relative_to(source).as_posix(): path.read_bytes()
                 for path in source.rglob("*") if path.is_file()
                 and path.relative_to(source).parts[0] in builder.RUNTIME_ROOTS}
        self.add_mod("parley", files)

    def add_adapter_fixture(self):
        files = {"descriptor.mod": b'version="1.0.0"\n',
                 "common/script_values/test_adapter.txt": b"fixture_adapter = { value = 30 }\n"}
        for language in builder.LANGUAGES:
            text = f"l_{language}:\n" + "".join(f' fixture_{i}:0 "Text {i}"\n' for i in range(5))
            files[f"localization/{language}/fixture_l_{language}.yml"] = text.encode("utf-8-sig")
        self.add_mod("agot_marriage_calc_assistant", files)

    def add_mod(self, mod, files):
        self.inputs[mod] = files
        self.lock["mods"][mod] = {"files": builder.inventory(files)}
        for name, data in files.items():
            path = self.dev / mod / "mod" / mod / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def run_tool(self, name, *args, succeeds=True):
        result = subprocess.run([sys.executable, str(TOOLS / name), *map(str, args)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, succeeds, result.stdout + result.stderr)
        return result

    def build(self, mods=None, *flags, succeeds=True):
        lock_path = self.root / "test-only-lock.json"
        lock_path.write_text(json.dumps(self.lock), encoding="utf-8")
        selection = ["--mods", *mods] if mods is not None else []
        return self.run_tool("build_game.py", "--dev-root", self.dev, "--output-root", self.output,
                             "--lock", lock_path, "--build-id", self.build_id, *selection, *flags,
                             succeeds=succeeds)

    def test_vanilla_pair_build_package_verify_omits_adapter(self):
        self.add_parley_fixture()
        self.add_mca_fixture()
        self.build(VANILLA)
        self.build(VANILLA, "--verify")
        build = self.output / self.build_id
        manifest = json.loads((build / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["mods"]), set(VANILLA))
        self.assertFalse((build / "agot_marriage_calc_assistant").exists())
        self.assertEqual((build / "marriage_calc_assistant/descriptor.mod").read_bytes(),
                         self.inputs["marriage_calc_assistant"]["descriptor.mod"])
        distribution = self.root / "distribution"
        self.run_tool("package_game.py", "--build-dir", build, "--output-dir", distribution)
        self.run_tool("package_game.py", "--build-dir", build, "--output-dir", distribution, "--verify")
        archives = json.loads((distribution / "archive-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(archives["archives"]), set(VANILLA))
        self.assertEqual(len(list(distribution.glob("*.zip"))), 2)
        (build / "agot_marriage_calc_assistant").mkdir()
        self.run_tool("package_game.py", "--build-dir", build, "--output-dir", distribution,
                      "--verify", succeeds=False)
        self.build(VANILLA, "--verify", succeeds=False)

    def test_single_mod_controls_and_default_still_requires_full_family(self):
        self.add_mca_fixture()
        result = self.build(succeeds=False)
        self.assertIn("use explicit --mods", result.stderr)
        self.assertFalse(self.output.exists())
        self.build(("marriage_calc_assistant",))
        report = json.loads((self.output / self.build_id / "transform-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["public_rate_projection"]["status"], "NOT_APPLICABLE")
        self.assertEqual(len(report["negative_controls"]), 5)
        self.assertEqual(set(report["transform_totals"].values()), {0})

    def test_default_selection_keeps_full_three_mod_fixture(self):
        self.add_parley_fixture()
        self.add_mca_fixture()
        self.add_adapter_fixture()
        self.build()
        self.build(None, "--verify")
        build = self.output / self.build_id
        manifest = json.loads((build / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["mods"]), set(builder.MODS))
        distribution = self.root / "distribution"
        self.run_tool("package_game.py", "--build-dir", build, "--output-dir", distribution)
        self.run_tool("package_game.py", "--build-dir", build, "--output-dir", distribution, "--verify")
        self.assertEqual(len(list(distribution.glob("*.zip"))), 3)

    def test_full_lock_can_select_subset_without_reading_omitted_sources(self):
        self.add_mca_fixture()
        for mod in ("parley", "agot_marriage_calc_assistant"):
            self.lock["mods"][mod] = {"files": {"missing.txt": {"sha256": "0" * 64, "bytes": 0}}}
        self.build(("marriage_calc_assistant",), "--check")
        self.assertFalse(self.output.exists())

    def test_reject_invalid_subsets_and_missing_lock_member(self):
        for mods in ([], ["foreign_mod"], ["parley", "parley"]):
            with self.subTest(mods=mods), self.assertRaises(builder.ReleaseError):
                builder.selected_mods(mods)
        self.add_mca_fixture()
        with self.assertRaisesRegex(builder.ReleaseError, "does not include every selected mod"):
            builder.validate_lock_inputs(self.inputs, {"mods": {"parley": {"files": {}}}})
        self.lock["mods"]["foreign_mod"] = {"files": {}}
        self.build(("marriage_calc_assistant",), "--check", succeeds=False)

    def test_packager_rejects_empty_and_unknown_manifest_selection(self):
        self.add_mca_fixture()
        self.build(("marriage_calc_assistant",))
        build = self.output / self.build_id
        path = build / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for mods in ({}, {"foreign_mod": {}}):
            manifest["mods"] = mods
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.run_tool("package_game.py", "--build-dir", build,
                          "--output-dir", self.root / "distribution", succeeds=False)
            self.assertFalse((self.root / "distribution").exists())


if __name__ == "__main__":
    unittest.main()
