"""Explicit Hegemony input/output routing; no writes to live publication trees."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RELEASE_ROOT = Path(__file__).resolve().parents[4]
BUILDER = RELEASE_ROOT / 'tools/hegemony/build_publication_copy.py'
LABEL = 'Want to support my work? Donate on Ko-fi 💛'


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


@unittest.skipUnless(BUILDER.is_file(), 'Release workspace Hegemony renderer unavailable')
class HegemonyRendererTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / 'input'
        self.source = self.root / 'authoring'
        self.inputs.mkdir()
        self.source.mkdir()
        description = ('# Your Own Hegemony [1.20]\n\n## At a glance\n\n'
                       '- 🟢 **Version 0.1.3** · Targets CK3 **1.20.0.3**.\n\n'
                       '## An empire is only the beginning\n\nMake late-game rule easier.\n\n'
                       '## Feedback and support\n\n### [' + LABEL + ']({{DONATION_URL}})\n\n'
                       '## My mods\n\n- [Other](https://example.org/other)\n')
        (self.inputs / 'description.en.md').write_text(description, encoding='utf-8')
        (self.inputs / '10-GITHUB-DEV.md').write_text('Contributor notes input\n', encoding='utf-8')
        (self.inputs / '11-PUBLICATION-LINKS.json').write_text(json.dumps({'public_urls': {site: f'https://example.org/{site}' for site in ('github', 'steam', 'paradox', 'nexus')}}), encoding='utf-8')
        self.links = self.root / 'links.json'
        self.links.write_text(json.dumps({'links': {'DONATION_URL': 'https://ko-fi.com/g4vv4kh'}}), encoding='utf-8')
        for name in ('mod/custom_hegemony/README.md', 'mod/custom_hegemony/descriptor.mod',
                     'mod/custom_hegemony/common/decisions/chg_decisions.txt',
                     'mod/custom_hegemony/common/scripted_effects/chg_effects.txt',
                     'mod/custom_hegemony/common/scripted_triggers/chg_triggers.txt',
                     'mod/custom_hegemony/common/script_values/chg_values.txt',
                     'mod/custom_hegemony/events/chg_events.txt',
                     'mod/custom_hegemony/localization/english/chg_l_english.yml',
                     'tests/custom_hegemony/SMOKE.md'):
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Unchanged claims fixture\n', encoding='utf-8')

    def run_builder(self, output, *extra):
        return subprocess.run([sys.executable, '-B', str(BUILDER), '--input-dir', str(self.inputs),
                               '--output-dir', str(output), '--source-root', str(self.source),
                               '--family-links', str(self.links), *extra], capture_output=True, text=True, encoding='utf-8')

    def test_deterministic_fresh_outputs_preserve_inputs_and_runtime(self):
        before_inputs, before_source = snapshot(self.inputs), snapshot(self.source)
        one, two = self.root / 'one', self.root / 'two'
        for output in (one, two):
            result = self.run_builder(output)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot(one), snapshot(two))
        self.assertEqual(snapshot(self.inputs), before_inputs)
        self.assertEqual(snapshot(self.source), before_source)
        metadata = json.loads((one / '08-METADATA.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['nexus_file_version'], '0.1.3')
        self.assertEqual(metadata['nexus_file_description'], 'For CK3 1.20.0.3')
        self.assertIn(f'<h3><a href="https://ko-fi.com/g4vv4kh">{LABEL}</a></h3>', (one / '05-PARADOX-DESCRIPTION.html').read_text(encoding='utf-8'))
        self.assertIn(f'[size=5][b][url=https://ko-fi.com/g4vv4kh]{LABEL}[/url][/b][/size]', (one / '04-NEXUS-DESCRIPTION.bbcode.txt').read_text(encoding='utf-8'))
        for name in ('00-START-HERE.txt', '00-START-HERE.html'):
            self.assertIn('For CK3 1.20.0.3', (one / name).read_text(encoding='utf-8'))

    def test_existing_or_input_output_refused_without_writes(self):
        output = self.root / 'frozen'
        output.mkdir()
        (output / 'sentinel.txt').write_text('Historical evidence', encoding='utf-8')
        for destination in (output, self.inputs / 'generated', self.source / 'generated'):
            before = snapshot(self.root)
            result = self.run_builder(destination)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(snapshot(self.root), before)

    def test_mismatched_target_rejected_before_output(self):
        output = self.root / 'rejected'
        result = self.run_builder(output, '--target-game-version', '1.20.0.2')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())

    def test_explicit_paths_required(self):
        result = subprocess.run([sys.executable, '-B', str(BUILDER)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--input-dir', result.stderr)


if __name__ == '__main__':
    unittest.main()
