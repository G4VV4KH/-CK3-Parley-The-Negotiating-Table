"""Pure/temp-file checks; never build into the owner's release workspace."""
import importlib.util
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
        guide = kit.guide("1.2.0", "test", "a" * 40)
        for expected in ("PREPARED_RUNTIME_SMOKE_PENDING", "NOT_UPLOADED", "03-PARADOX/parley-1.2.0-PARADOX.zip", "04-NEXUS/parley-1.2.0-NEXUS-MANUAL.zip", "AGOT integration remains on hold"):
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
        generated = {name: b'text' for name in ('steam.bbcode', 'paradox.txt', 'nexus.bbcode', 'github.md', 'preview.html', 'render-status.json')}
        readme = generated['github.md'] + kit.CONTRIBUTING_FOOTER
        kit.validate_copy(generated, readme, b'Version 1.2.0', '1.2.0')
        with self.assertRaises(kit.PreparationError):
            kit.validate_copy(generated, generated['github.md'], b'Version 1.2.0', '1.2.0')
        generated['steam.bbcode'] = ('я' * 4001).encode()
        with self.assertRaises(kit.PreparationError):
            kit.validate_copy(generated, readme, b'Version 1.2.0', '1.2.0')

    def test_failed_external_media_preflight_creates_no_output_directories(self):
        generated = {name: b'text' for name in ('steam.bbcode', 'paradox.txt', 'nexus.bbcode', 'github.md', 'preview.html', 'render-status.json')}
        descriptor = b'version="1.2.0"\nname="Parley: The Negotiating Table"\nsupported_version="1.20.*"\n'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            changelog = root / 'changelog.md'
            changelog.write_bytes(b'Version 1.2.0')
            repo = root / 'dev/parley'
            reads = {repo / 'README.md': b'text' + kit.CONTRIBUTING_FOOTER,
                     repo / 'publishing/description.en.md': b'Version 1.2.0', changelog: b'Version 1.2.0'}
            args = SimpleNamespace(workspace=root, version='1.2.0', build_id='fixture', bundle=None, verify=False, changelog=changelog)
            with mock.patch.multiple(kit, load_module=mock.Mock(return_value=None),
                    run=mock.Mock(side_effect=['', 'a'*40]), runtime_inputs=mock.Mock(return_value={'descriptor.mod': descriptor}),
                    source_snapshot=mock.Mock(return_value=({}, {})), tree=mock.Mock(return_value=generated),
                    read_file=mock.Mock(side_effect=lambda path: reads[path]),
                    media_inputs=mock.Mock(side_effect=kit.PreparationError('media mismatch'))):
                with self.assertRaisesRegex(kit.PreparationError, 'media mismatch'):
                    kit.prepare(args)
            for path in ('game', 'distribution', 'deploy', 'verification-evidence'):
                self.assertFalse((root / path).exists())


if __name__ == "__main__":
    unittest.main()
