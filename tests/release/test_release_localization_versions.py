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

    def test_versions_do_not_accept_each_others_counts(self):
        for version, wrong_count in (("1.1.0", 632), ("1.2.0", 622)):
            with self.subTest(version=version), self.assertRaises(builder.ReleaseError):
                builder.project(fixture(version, wrong_count))

    def test_unknown_or_duplicate_version_rejected(self):
        for descriptor in (b'version="1.3.0"\n', b'version="1.2.0"\nversion="1.1.0"\n', b'name="Parley"\n'):
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
