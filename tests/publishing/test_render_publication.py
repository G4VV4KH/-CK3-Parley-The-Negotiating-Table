"""Publication projections and single-mod wrapper checks; all writes are temporary."""
import contextlib
import hashlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[2]
RENDERER = REPO / 'tools/render-publication.py'
WRAPPER = REPO.parents[1] / 'tools/publishing/render_mod_publication.py'
spec = importlib.util.spec_from_file_location('publication_renderer', RENDERER)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
MARKERS = renderer.GUIDE_MARKERS
GUIDE = '\n'.join((
    '# Parley', '', '## Getting started', '', 'Keep these ordinary steps.', '',
    MARKERS[0], 'SHORT GUIDE: [Full guide]({{PARLEY_GITHUB_URL}}#game-rules-guide)', MARKERS[1], '',
    MARKERS[2], '### Game rules guide', '', 'FULL GUIDE: detailed rules.', MARKERS[3], '',
    '## Compatibility and load order', '', 'Keep this restriction.', '',
))


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob('*') if path.is_file()}


class PublicationRendererTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dev = self.root / 'dev'
        self.repo = self.dev / 'parley'
        for slug in renderer.SLUGS:
            repo = self.dev / slug
            (repo / 'publishing/generated').mkdir(parents=True)
            (repo / 'README.md').write_text('UNCHANGED README', encoding='utf-8')
            (repo / 'publishing/description.en.md').write_text(GUIDE if slug == 'parley' else 'SIBLING CANONICAL', encoding='utf-8')
            (repo / 'publishing/generated/sentinel.txt').write_text('UNCHANGED GENERATED', encoding='utf-8')
        self.config = self.repo / 'publishing/family-links.json'
        self.config.write_text(json.dumps({'links': {'PARLEY_GITHUB_URL': 'https://example.org/parley'}}), encoding='utf-8')

    def render(self, source=None):
        if source is not None:
            (self.repo / 'publishing/description.en.md').write_text(source, encoding='utf-8')
        with patch.object(renderer, 'SLUGS', ('parley',)), patch.object(sys, 'argv', [str(RENDERER), '--dev-root', str(self.dev)]), contextlib.redirect_stdout(io.StringIO()):
            renderer.main()
        return {path.name: path.read_text(encoding='utf-8') for path in (self.repo / 'publishing/generated').iterdir()}

    def test_platform_projection_and_anchor(self):
        files = self.render()
        for name in ('steam.bbcode', 'paradox.txt'):
            self.assertIn('SHORT GUIDE', files[name])
            self.assertIn('https://example.org/parley#game-rules-guide', files[name])
            self.assertNotIn('FULL GUIDE', files[name])
        for name in ('github.md', 'nexus.bbcode', 'preview.html'):
            self.assertIn('FULL GUIDE', files[name])
            self.assertNotIn('SHORT GUIDE', files[name])
        self.assertIn('### Game rules guide', files['github.md'])
        for name in ('steam.bbcode', 'github.md', 'nexus.bbcode', 'paradox.txt', 'preview.html'):
            self.assertIn('Keep these ordinary steps.', files[name])
            self.assertIn('Keep this restriction.', files[name])
            self.assertNotIn('<!--', files[name])
            self.assertNotIn('{{', files[name])

    def test_no_markers_keep_source_exactly(self):
        source = '# Mod\r\n\r\nText with Unicode: 🟢.\r\n'
        for platform in ('steam', 'github', 'nexus', 'paradox', 'preview'):
            self.assertEqual(renderer.platform_source(source, platform), source)

    def test_fourth_level_guide_heading_in_all_formats(self):
        source = GUIDE.replace('FULL GUIDE: detailed rules.', '#### Piety trading\n\nFULL GUIDE: detailed rules.')
        files = self.render(source)
        self.assertIn('#### Piety trading', files['github.md'])
        self.assertIn('<h4>Piety trading</h4>', files['preview.html'])
        self.assertIn('[size=5][b]Piety trading[/b][/size]', files['nexus.bbcode'])
        self.assertNotIn('Piety trading', files['paradox.txt'])
        self.assertNotIn('Piety trading', files['steam.bbcode'])
        self.assertEqual(renderer.bbcode('#### Piety trading\n', 'steam'), '[h1]Piety trading[/h1]\n')
        for name in ('steam.bbcode', 'nexus.bbcode', 'paradox.txt', 'preview.html'):
            self.assertNotIn('####', files[name])

    def test_no_markers_keep_legacy_outputs_exactly(self):
        files = self.render('# Mod\n\n## Getting started\n\n1. Open it.\n2. Use **rules**.\n\n[Link](https://example.org)\n')
        self.assertEqual(files['steam.bbcode'], '[h1]Mod[/h1]\n\n[h1]Getting started[/h1]\n\n[olist]\n[*]Open it.\n[*]Use [b]rules[/b].\n[/olist]\n\n[url=https://example.org]Link[/url]\n')
        self.assertEqual(files['nexus.bbcode'], '[size=5][b]Mod[/b][/size]\n\n[size=5][b]Getting started[/b][/size]\n\n[list=1]\n[*]Open it.\n[*]Use [b]rules[/b].\n[/list]\n\n[url=https://example.org]Link[/url]\n')
        self.assertEqual(files['paradox.txt'], 'Mod\n\nGetting started\n\n1. Open it.\n2. Use rules.\n\nLink: https://example.org\n')
        self.assertEqual(files['github.md'], '# Mod\n\n## Getting started\n\n1. Open it.\n2. Use **rules**.\n\n[Link](https://example.org)\n')
        self.assertEqual((self.repo / 'README.md').read_text(encoding='utf-8'), files['github.md'] + '\n## Contributing\n\nSee [dev.md](dev.md) for the source layout, checks and pull-request workflow.\n')

    def test_each_missing_marker_is_rejected_before_output_writes(self):
        for marker in MARKERS:
            with self.subTest(marker=marker):
                self.assert_bad_without_writes(GUIDE.replace(marker, ''))

    def test_duplicate_markers_rejected(self):
        for marker in MARKERS:
            with self.subTest(marker=marker):
                self.assert_bad_without_writes(GUIDE + marker + '\n')

    def test_reversed_and_nested_markers_rejected(self):
        for order in ((1, 0, 2, 3), (2, 3, 0, 1), (0, 2, 1, 3), (0, 1, 3, 2)):
            with self.subTest(order=order):
                self.assert_bad_without_writes('\n'.join(MARKERS[i] for i in order))

    def test_inline_and_unknown_marker_suffix_rejected(self):
        for source in (GUIDE.replace(MARKERS[0], 'prefix ' + MARKERS[0]), GUIDE + '<!-- full-game-rules-guide:typo -->\n'):
            self.assert_bad_without_writes(source)

    def assert_bad_without_writes(self, source):
        (self.repo / 'publishing/description.en.md').write_text(source, encoding='utf-8')
        before = snapshot(self.dev)
        with self.assertRaises(ValueError):
            self.render()
        self.assertEqual(snapshot(self.dev), before)

    def test_steam_limit_is_utf8_bytes_not_characters(self):
        # 2,001 emoji plus LF is only 2,002 characters but exceeds 8,000 bytes.
        self.assert_bad_without_writes('🟢' * 2001)

    def test_exact_steam_byte_limit_allowed_and_reported(self):
        files = self.render('x' * 7999)
        report = json.loads(files['render-status.json'])
        self.assertEqual(report['steam_bytes'], 8000)
        self.assertEqual(report['steam_characters'], 8000)
        self.assertTrue(report['steam_under_8000'])
        self.assertTrue(report['steam_under_8000_bytes'])

    def test_multibyte_report_retains_character_fields(self):
        files = self.render('🟢')
        report = json.loads(files['render-status.json'])
        self.assertEqual(report['steam_characters'], 2)
        self.assertEqual(report['steam_bytes'], 5)
        self.assertTrue(report['steam_under_8000'])
        self.assertTrue(report['steam_under_8000_bytes'])
        self.assertEqual(report['paradox_characters'], 3)
        self.assertEqual(report['paradox_html_characters'], 9)

    def test_full_guide_can_exceed_steam_limit(self):
        files = self.render(GUIDE.replace('FULL GUIDE: detailed rules.', 'FULL GUIDE: ' + 'x' * 12000))
        self.assertGreater(len(files['github.md'].encode('utf-8')), 10000)
        self.assertLess(len(files['steam.bbcode'].encode('utf-8')), 8000)
        self.assertLess(len(files['paradox.txt']), 10000)

    def test_paradox_limit_includes_escaped_html_overhead(self):
        # 2,500 ampersands pass Steam and plain-text limits but exceed the
        # Paradox cap after HTML escaping. Failure must precede every write.
        self.assert_bad_without_writes('&' * 2500)

    def test_paradox_limit_rejects_plain_text_without_writes(self):
        with patch.object(renderer, 'STEAM_BYTE_LIMIT', 20000):
            self.assert_bad_without_writes('x' * 10000)

    def test_exact_paradox_html_limit_allowed_and_reported(self):
        with patch.object(renderer, 'STEAM_BYTE_LIMIT', 20000):
            files = self.render('x' * 9993)
        report = json.loads(files['render-status.json'])
        self.assertEqual(report['paradox_characters'], 9994)
        self.assertEqual(report['paradox_html_characters'], 10000)
        self.assertTrue(report['paradox_under_10000'])

    def test_paradox_html_preserves_plain_content_and_escapes_markup(self):
        self.assertEqual(renderer.paradox_html('First & <second>\nnext\n\nhttps://example.org\n'),
                         '<p>First &amp; &lt;second&gt;<br>next</p><p>https://example.org</p>')

    def test_required_support_heading_retained_on_every_platform(self):
        url = 'https://ko-fi.com/g4vv4kh'
        label = renderer.DONATION_TEXT
        self.config.write_text(json.dumps({'links': {'PARLEY_GITHUB_URL': 'https://example.org/parley', 'DONATION_URL': url}}), encoding='utf-8')
        source = GUIDE + f'\n### [{label}]({{{{DONATION_URL}}}})\n'
        files = self.render(source)
        self.assertIn(f'[size=5][b][url={url}]{label}[/url][/b][/size]', files['nexus.bbcode'])
        self.assertIn(f'[h1][url={url}]{label}[/url][/h1]', files['steam.bbcode'])
        self.assertIn(f'<h3><a href="{url}">{label}</a></h3>', files['paradox.html'])
        self.assertEqual(json.loads(files['render-status.json'])['required_support_local'], 'PASS')
        self.assertEqual(json.loads(files['render-status.json'])['required_support_public'], 'NOT_VERIFIED')
        for name in ('steam.bbcode', 'nexus.bbcode', 'github.md', 'paradox.html'):
            self.assertEqual(files[name].count(label), 1)
        first = snapshot(self.repo)
        self.render()
        self.assertEqual(snapshot(self.repo), first)
        self.assert_bad_without_writes(source.replace('### [', '['))
        self.assert_bad_without_writes(source + f'\n### [{label}]({url})\n')

    def test_rich_paradox_preserves_link_pairs_and_native_headings(self):
        source = '# Title\n\nText **bold** & `code`.\n\n### [Support](https://example.org/?a=1&b=2)\n\n- [Other](https://example.org/other)\n- Plain item\n\n1. Open.\n2. Review.\n'
        rich = renderer.paradox_html(source)
        self.assertIn('<h3><a href="https://example.org/?a=1&amp;b=2">Support</a></h3>', rich)
        self.assertIn('<ul><li><a href="https://example.org/other">Other</a></li><li>Plain item</li></ul>', rich)
        self.assertIn('<ol><li>Open.</li><li>Review.</li></ol>', rich)
        import html
        self.assertEqual(renderer.LINK.findall(source), [(html.unescape(label), html.unescape(url))
                         for url, label in re.findall(r'<a href="([^"]+)">([^<]+)</a>', rich)])

    def test_nexus_file_metadata_uses_approved_game_target_not_mod_version(self):
        for target in ('1.20.0.3', '1.20.0.4'):
            source = f'# Mod\n\n- 🟢 **Version 3.1.0** · Targets CK3 **{target}**.\n'
            files = self.render(source)
            metadata = json.loads(files['metadata.json'])
            self.assertEqual(metadata['nexus_file_version'], '3.1.0')
            self.assertEqual(metadata['nexus_file_description'], 'For CK3 ' + target)
            self.assertEqual(metadata['target_game_version'], target)
        with self.assertRaises(ValueError):
            renderer.publication_metadata(source, target_game_version='1.20.0.2')
        with self.assertRaises(ValueError):
            renderer.publication_metadata(source, mod_version='3.0.0')

    def test_scoped_wrapper_changes_only_selected_mod_in_isolated_copy(self):
        if not WRAPPER.is_file():
            self.skipTest('Release workspace wrapper unavailable in standalone checkout')
        renderer_copy = self.repo / 'tools/render-publication.py'
        renderer_copy.parent.mkdir()
        renderer_copy.write_bytes(RENDERER.read_bytes())
        wrapper_copy = self.root / 'tools/publishing/render_mod_publication.py'
        wrapper_copy.parent.mkdir(parents=True)
        # Review the changed renderer against the unchanged wrapper behavior in
        # isolation before accepting its new fingerprint in the real wrapper.
        wrapper_text = WRAPPER.read_text(encoding='utf-8')
        new_hash = hashlib.sha256(RENDERER.read_bytes()).hexdigest()
        wrapper_text, count = re.subn(r'RENDERER_SHA256 = "[a-f0-9]{64}"', f'RENDERER_SHA256 = "{new_hash}"', wrapper_text)
        self.assertEqual(count, 1)
        wrapper_copy.write_text(wrapper_text, encoding='utf-8')
        sibling_before = {slug: snapshot(self.dev / slug) for slug in renderer.SLUGS if slug != 'parley'}
        result = subprocess.run([sys.executable, '-B', str(wrapper_copy), '--mod', 'parley', '--dev-root', str(self.dev)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        reports = json.loads(result.stdout)
        self.assertEqual([report['mod'] for report in reports], ['parley'])
        self.assertEqual({slug: snapshot(self.dev / slug) for slug in sibling_before}, sibling_before)
        self.assertIn('FULL GUIDE', (self.repo / 'README.md').read_text(encoding='utf-8'))
        self.assertIn('SHORT GUIDE', (self.repo / 'publishing/generated/steam.bbcode').read_text(encoding='utf-8'))
        self.assertIn('SHORT GUIDE', (self.repo / 'publishing/generated/paradox.txt').read_text(encoding='utf-8'))
        # A public metadata revision need not have the live dev-root layout.
        projection = self.root / 'metadata-revision/parley/source'
        shutil.copytree(self.repo, projection)
        live_before = snapshot(self.dev)
        result = subprocess.run([sys.executable, '-B', str(wrapper_copy), '--mod', 'parley', '--source-dir', str(projection), '--config', str(self.config)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot(self.dev), live_before)
        self.assertIn('FULL GUIDE', (projection / 'README.md').read_text(encoding='utf-8'))
        result = subprocess.run([sys.executable, '-B', str(wrapper_copy), '--mod', 'parley', '--source-dir', str(projection), '--dev-root', str(self.dev)], capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(result.returncode, 0)

    def test_live_wrapper_fingerprint_matches_reviewed_renderer(self):
        if not WRAPPER.is_file():
            self.skipTest('Release workspace wrapper unavailable in standalone checkout')
        pinned = re.search(r'RENDERER_SHA256 = "([a-f0-9]{64})"', WRAPPER.read_text(encoding='utf-8'))
        self.assertIsNotNone(pinned)
        self.assertEqual(pinned[1], hashlib.sha256(RENDERER.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
