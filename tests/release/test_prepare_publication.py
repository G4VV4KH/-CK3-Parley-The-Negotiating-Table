"""Pure/temp-file checks; never build into the owner's release workspace."""
import importlib.util
import json
from pathlib import Path
import tempfile
import io
import struct
import unittest
import zipfile
from unittest import mock
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[2] / "tools/release/prepare_publication.py"
SPEC = importlib.util.spec_from_file_location("prepare_publication", SCRIPT)
kit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kit)


class PreparationTests(unittest.TestCase):
    @staticmethod
    def runtime_fixture(version, public=False):
        names = kit.PARLEY_RUNTIME_FILES[version] - ({kit.LOGGER_FILE} if public else set())
        files = dict.fromkeys(names, b'fixture=yes\n')
        files['descriptor.mod'] = f'version="{version}"\n'.encode()
        return files

    def test_runtime_inventory_has_exact_historical_base_and_seven_new_helpers(self):
        original = json.loads((SCRIPT.parent / 'release-inputs.json').read_text(encoding='utf-8'))
        self.assertEqual(kit.PARLEY_120_RUNTIME_FILES, set(original['mods']['parley']['files']))
        self.assertEqual(kit.PARLEY_121_ADDITIONS, {
            'common/customizable_localization/tnt_90_cooldown_loc.txt',
            'common/script_values/tnt_5b_scaled_land_values.txt',
            'common/script_values/tnt_5c_scaled_person_values.txt',
            'common/script_values/tnt_5d_scaled_strategic_values.txt',
            'common/script_values/tnt_5e_display_values.txt',
            'common/script_values/tnt_5e_valuation_policy.txt',
            'common/script_values/tnt_5f_scaled_balance_values.txt',
        })
        for version, dev_count, game_count in [('1.2.0', 76, 75), ('1.2.1', 83, 82), ('1.2.2', 83, 82)]:
            for public, count in [(False, dev_count), (True, game_count)]:
                with self.subTest(version=version, public=public):
                    files = self.runtime_fixture(version, public)
                    self.assertEqual(len(files), count)
                    kit.validate_runtime_inventory(files, public=public)

    def test_each_missing_or_substituted_121_helper_fails_closed(self):
        for helper in kit.PARLEY_121_ADDITIONS:
            for public in [False, True]:
                files = self.runtime_fixture('1.2.1', public)
                del files[helper]
                with self.subTest(helper=helper, public=public, replacement=False), self.assertRaises(kit.PreparationError):
                    kit.validate_runtime_inventory(files, public=public)
                files['common/script_values/unreviewed.txt'] = b'unknown=yes\n'
                with self.subTest(helper=helper, public=public, replacement=True), self.assertRaises(kit.PreparationError):
                    kit.validate_runtime_inventory(files, public=public)

    def test_version_drift_and_logger_in_public_inventory_are_rejected(self):
        source = self.runtime_fixture('1.2.0')
        for descriptor in [b'version="1.2.1"\n', b'version="1.2.2"\n',
                           b'version="1.2.0"\nversion="1.2.1"\n', b'name="Parley"\n']:
            with self.subTest(descriptor=descriptor), self.assertRaises(kit.PreparationError):
                kit.validate_runtime_inventory({**source, 'descriptor.mod': descriptor})
        with self.assertRaises(kit.PreparationError):
            kit.validate_runtime_inventory(self.runtime_fixture('1.2.1'), public=True)
        with self.assertRaises(kit.PreparationError):
            kit.validate_runtime_inventory(self.runtime_fixture('1.2.1', True))

    def test_frozen_rc2_inventory_requires_its_pinned_preparation_tool(self):
        for public, old_count in [(False, 81), (True, 80)]:
            files = self.runtime_fixture('1.2.1', public)
            del files['common/customizable_localization/tnt_90_cooldown_loc.txt']
            del files['common/script_values/tnt_5e_display_values.txt']
            self.assertEqual(len(files), old_count)
            with self.subTest(public=public), self.assertRaises(kit.PreparationError):
                kit.validate_runtime_inventory(files, public=public)

    def test_legacy_preparer_rejects_current_130_authoring_runtime(self):
        repo = SCRIPT.parents[2]
        with self.assertRaisesRegex(kit.PreparationError, "Unreviewed Parley version"):
            kit.runtime_inputs(repo)
        # The historical 1.2.2 profile remains accepted without adding 1.3.0 to
        # this deliberately frozen release route.
        files = self.runtime_fixture('1.2.2')
        self.assertEqual(len(files), 83)
        kit.validate_runtime_inventory(files)

    def test_steam_identity_overlay_is_only_descriptor_delta(self):
        source = {"descriptor.mod": b'version="1.2.0"\nname="Parley: The Negotiating Table"\n', "common/x.txt": b'x=yes\n'}
        steam, wrapper, portable = kit.platform_payloads(source)
        self.assertEqual(steam["common/x.txt"], source["common/x.txt"])
        self.assertEqual(steam["descriptor.mod"], source["descriptor.mod"] + b'remote_file_id="3811090081"\n')
        self.assertIn(b'path="mod/parley"', wrapper)
        self.assertNotIn(b"remote_file_id", portable)
        self.assertNotIn(b"remote_file_id", source["descriptor.mod"])

    def test_existing_identity_overlay_fails_closed(self):
        with self.assertRaises(kit.PreparationError):
            kit.platform_payloads({"descriptor.mod": b'remote_file_id="999"\n'})

    def test_descriptor_public_name_version_and_supported_target(self):
        good = b'version="1.2.0"\nname="Parley: The Negotiating Table"\nsupported_version="1.20.*"\n'
        kit.descriptor_check(good, "1.2.0")
        for bad in (good.replace(b'1.2.0', b'1.1.0'), good.replace(b'Parley:', b'[DEV] Parley:'), good+b'path="mod/parley"\n'):
            with self.assertRaises(kit.PreparationError):
                kit.descriptor_check(bad, "1.2.0")

    def test_known_source_path_becomes_portable(self):
        sample = ('GAME = "' + 'D:' + '/SteamLibrary/steamapps/common/Crusader Kings III/game"\n').encode()
        result, changes = kit.sanitize_source("test.py", sample)
        self.assertEqual(result, b'GAME = "./game"\n')
        self.assertEqual(len(changes), 1)

    def test_unclassified_path_rejected(self):
        with self.assertRaises(kit.PreparationError):
            kit.sanitize_source("note.md", ('private ' + 'C:' + '/Users/Someone/secret').encode())

    def test_url_and_non_text_asset_retained(self):
        data = b'https://example.invalid/item\n'
        self.assertEqual(kit.sanitize_source("notes.md", data), (data, []))
        self.assertEqual(kit.sanitize_source("a.png", b'\x00\xff'), (b'\x00\xff', []))

    def test_relative_member_validation(self):
        for name in ("../outside", "/absolute", "a/../b", "a\\b", "C:" + "/outside"):
            with self.assertRaises(kit.PreparationError):
                kit.safe_relative(name)

    def test_write_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kit.write_new(root, "a/b", b"old")
            with self.assertRaises(FileExistsError):
                kit.write_new(root, "a/b", b"new")
            self.assertEqual((root / "a/b").read_bytes(), b"old")

    def test_guide_is_honest_and_uses_distinct_platform_shapes(self):
        guide = kit.guide("1.2.2", "test", "a" * 40)
        for expected in ("PREPARED_LOCAL_GATES_PASS_PUBLICATION_PENDING", "NOT_UPLOADED", "03-PARADOX/parley-1.2.2-PARADOX.zip", "04-NEXUS/parley-1.2.2-NEXUS-MANUAL.zip", "AGOT integration remains on hold"):
            self.assertIn(expected, guide)

    def test_known_backslash_path_and_utf8_bom_are_preserved(self):
        text = '# ' + 'D:' + '\\SteamLibrary\\steamapps\\common\\Crusader Kings III\\game\n'
        data = b'\xef\xbb\xbf' + text.encode()
        actual, changes = kit.sanitize_source("script.txt", data)
        self.assertEqual(actual, b'\xef\xbb\xbf# ./game\n')
        self.assertTrue(changes)

    def test_png_dimensions_are_read_from_native_header(self):
        data = b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\rIHDR' + struct.pack('>II', 512, 512)
        self.assertEqual(kit.image_size(data), (512, 512))
        with self.assertRaises(kit.PreparationError):
            kit.image_size(b'not an image')

    def test_distinct_archive_shapes_and_exact_members(self):
        packager = kit.load_module(SCRIPT.parent / 'package_game.py')
        runtime = {'descriptor.mod': b'version="1.2.0"\n', 'common/test.txt': b'test=yes\n'}
        _, _, wrapper = kit.platform_payloads(runtime)
        nexus = {'parley/' + name: data for name, data in runtime.items()}
        nexus.update({'parley.mod': wrapper, 'INSTALL.txt': b'Install the mod.\n'})
        with tempfile.TemporaryDirectory() as directory:
            for name, files in [('paradox.zip', runtime), ('nexus.zip', nexus)]:
                path = Path(directory) / name
                stream = io.BytesIO()
                packager.write_zip(stream, files)
                path.write_bytes(stream.getvalue())
                result = packager.verify_zip(path, files)
                self.assertEqual(result['member_count'], len(files))
                with zipfile.ZipFile(path) as archive:
                    self.assertIsNone(archive.testzip())
            with self.assertRaises(packager.PackageError):
                packager.verify_zip(Path(directory) / 'nexus.zip', runtime)

    def test_legitimate_generated_readme_footer_and_steam_utf8_budget(self):
        generated = {name: b'text' for name in ('steam.bbcode', 'paradox.txt', 'paradox.html', 'nexus.bbcode', 'github.md', 'preview.html', 'render-status.json', 'metadata.json')}
        label = 'Want to support my work? Donate on Ko-fi 💛'
        generated['nexus.bbcode'] = f'[size=5][b][url=https://ko-fi.com/g4vv4kh]{label}[/url][/b][/size]'.encode()
        generated['paradox.html'] = f'<h3><a href="https://ko-fi.com/g4vv4kh">{label}</a></h3>'.encode()
        generated['metadata.json'] = json.dumps({'nexus_file_version': '1.2.0', 'target_game_version': kit.TARGET, 'nexus_file_description': f'For CK3 {kit.TARGET}'}).encode()
        readme = generated['github.md'] + kit.CONTRIBUTING_FOOTER
        kit.validate_copy(generated, readme, b'Version 1.2.0', '1.2.0')
        with self.assertRaises(kit.PreparationError):
            kit.validate_copy(generated, generated['github.md'], b'Version 1.2.0', '1.2.0')
        valid_nexus = generated['nexus.bbcode']
        for invalid in (b'', valid_nexus.replace(b'[size=5]', b'[size=3]'), valid_nexus * 2):
            generated['nexus.bbcode'] = invalid
            with self.assertRaises(kit.PreparationError):
                kit.validate_copy(generated, readme, b'Version 1.2.0', '1.2.0')
        generated['nexus.bbcode'] = valid_nexus
        valid_metadata = generated['metadata.json']
        generated['metadata.json'] = valid_metadata.replace(kit.TARGET.encode(), b'1.20.0.2')
        with self.assertRaises(kit.PreparationError):
            kit.validate_copy(generated, readme, b'Version 1.2.0', '1.2.0')
        generated['metadata.json'] = valid_metadata
        generated['steam.bbcode'] = b'x\n' * 100 + b'x' * 7701
        with self.assertRaises(kit.PreparationError):
            kit.validate_copy(generated, readme, b'Version 1.2.0', '1.2.0')
        generated['steam.bbcode'] = ('я' * 4001).encode()
        with self.assertRaises(kit.PreparationError):
            kit.validate_copy(generated, readme, b'Version 1.2.0', '1.2.0')

    def test_missing_native_acceptance_blocks_before_outputs(self):
        # Exercise the real release guard. Candidate/source proof is a separate
        # preflight; this test proves packaging cannot replace native acceptance.
        actual_guards = kit.load_module(SCRIPT.parent / 'candidate_release_guards.py')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = SimpleNamespace(workspace=root, version='1.2.2',
                candidate_manifest=root / 'unused.json', candidate_receipt=None,
                check_candidate_only=False, localization_acceptance=None)
            with mock.patch.multiple(actual_guards,
                    candidate_proof=mock.Mock(return_value=({}, {})),
                    assert_projection=mock.Mock(return_value={})):
                with mock.patch.multiple(kit, load_module=mock.Mock(return_value=actual_guards),
                        runtime_inputs=mock.Mock(return_value={})):
                    with self.assertRaisesRegex(ValueError, 'localization acceptance'):
                        kit.prepare(args)
            for path in ('game', 'distribution', 'deploy', 'verification-evidence'):
                self.assertFalse((root / path).exists())

    def test_failed_external_media_preflight_creates_no_output_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / 'dev/parley'
            changelog = root / 'changelog.md'
            changelog.write_bytes(b'Version 1.2.2')
            revision_path = root / 'revision.json'
            revision = {'source_projection': str(repo),
                'canonical_description': str(repo / 'publishing/description.en.md'),
                'rendered_outputs': {k: str(repo / 'publishing/generated' / v) for k, v in
                    {'steam':'steam.bbcode','paradox_rich':'paradox.html','nexus':'nexus.bbcode',
                     'github':'github.md','metadata':'metadata.json'}.items()}}
            args = SimpleNamespace(workspace=root, version='1.2.2', build_id='fixture', bundle=None,
                verify=False, changelog=changelog, candidate_manifest=None, candidate_receipt=None,
                check_candidate_only=False, localization_acceptance=root / 'gate.json',
                publication_revision=revision_path, family_config=repo / 'publishing/family-links.json',
                copy_validator=root / 'validator.py', contract_dir=root / 'contract', media_workspace=root)
            guards = SimpleNamespace(candidate_proof=mock.Mock(return_value=({}, {})),
                assert_projection=mock.Mock(return_value={}), acceptance=mock.Mock(return_value={}))
            validator = SimpleNamespace(validate=mock.Mock(return_value={'status':'PASS', 'mod':'parley',
                'mod_version':'1.2.2', 'target_game_version':kit.TARGET}))
            def module(path):
                if path.name == 'candidate_release_guards.py': return guards
                if path.name == 'validator.py': return validator
                return None
            def read(path):
                if path == revision_path: return json.dumps(revision).encode()
                if path == changelog: return b'Version 1.2.2'
                return b'fixture'
            with mock.patch.multiple(kit, load_module=mock.Mock(side_effect=module),
                    run=mock.Mock(side_effect=['', 'a'*40]), runtime_inputs=mock.Mock(return_value={'descriptor.mod':b'fixture'}),
                    source_snapshot=mock.Mock(return_value=({}, {})), tree=mock.Mock(return_value={}),
                    read_file=mock.Mock(side_effect=read), descriptor_check=mock.Mock(), validate_copy=mock.Mock(),
                    media_inputs=mock.Mock(side_effect=kit.PreparationError('media mismatch'))):
                with self.assertRaisesRegex(kit.PreparationError, 'media mismatch'):
                    kit.prepare(args)
            for path in ('game', 'distribution', 'deploy', 'verification-evidence'):
                self.assertFalse((root / path).exists())


if __name__ == "__main__":
    unittest.main()
