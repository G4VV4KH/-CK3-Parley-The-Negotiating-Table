"""Mutation checks for the reusable local publication gate."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
VALIDATOR = ROOT / 'tools/publishing/validate_publication_copy.py'


@unittest.skipUnless(VALIDATOR.is_file(), 'Release workspace validator unavailable')
class PublicationGateTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('publication_gate', VALIDATOR)
        self.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gate)
        spec = importlib.util.spec_from_file_location('test_renderer', ROOT / 'dev/parley/tools/render-publication.py')
        self.renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.renderer)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        links = {'DONATION_URL': 'https://ko-fi.com/g4vv4kh', 'CONTACT_EMAIL': 'g4vv4kh@gmail.com'}
        ids, remotes = {}, {}
        for i, slug in enumerate(('parley', 'marriage_calc_assistant', 'custom_hegemony', 'vassalization_extended', 'court_automation')):
            prefix = slug.upper()
            for site in ('STEAM', 'PARADOX', 'NEXUS', 'GITHUB'):
                links[f'{prefix}_{site}_URL'] = f'https://example.org/{slug}/{site.lower()}'
            links[f'{prefix}_STEAM_URL'] = f'https://steamcommunity.com/sharedfiles/filedetails/?id={i + 1}'
            ids[slug] = str(i + 1)
            remotes[slug] = links[prefix + '_GITHUB_URL'] + '.git'
        self.config = self.root / 'links.json'
        self.config.write_text(json.dumps({'links': links, 'workshop_ids': ids, 'github_remotes': remotes}), encoding='utf-8')
        self.contract = self.root / 'contract.json'
        self.contract.write_text(json.dumps({'published_family_catalog': {
            slug: {'label': slug, 'role': 'role.', 'steam_url': links[slug.upper() + '_STEAM_URL']} for slug in ids},
            'semantic_common_blocks': {'exact_headings': ['At a glance', 'Getting started', 'Compatibility and load order', 'Saves and known limits', 'Feedback and support', 'Find this mod elsewhere', 'My other mods']}}), encoding='utf-8')
        source = '# Parley\n\n## At a glance\n\nVersion 1.2.0 · Targets CK3 1.20.0.3.\n\n'
        source += 'Languages: English.\n\n## Getting started\n\nStart.\n\n## Compatibility and load order\n\nNo dependency.\n\n## Saves and known limits\n\nBack up saves.\n\n'
        source += '## Feedback and support\n\n[Report an issue on GitHub](https://example.org/parley/github/issues)\n\nEmail: g4vv4kh@gmail.com\n\n'
        source += f'### [{self.gate.LABEL}]({links["DONATION_URL"]})\n\n## Find this mod elsewhere\n\n'
        for label, platform in [('Steam Workshop', 'STEAM'), ('Paradox Mods', 'PARADOX'), ('Nexus Mods', 'NEXUS'), ('GitHub', 'GITHUB')]:
            source += f'- [{label}]({links["PARLEY_" + platform + "_URL"]})\n'
        source += '\n## My other mods\n\n'
        for other in list(ids)[1:]:
            source += f'- [{other}]({links[other.upper() + "_STEAM_URL"]}) — role.\n'
        source += '\nThese mods are optional.\n'
        canonical = self.root / 'description.en.md'
        canonical.write_text(source, encoding='utf-8')
        outputs = {'github': source, 'steam': self.renderer.bbcode(source, 'steam'),
                   'nexus': self.renderer.bbcode(source, 'nexus'), 'paradox_rich': self.renderer.paradox_html(source),
                   'metadata': json.dumps(self.renderer.publication_metadata(source))}
        self.paths = {}
        for surface, content in outputs.items():
            path = self.root / surface
            path.write_text(content, encoding='utf-8')
            self.paths[surface] = path
        self.revision = self.root / 'revision.json'
        self.revision.write_text(json.dumps({'mod': 'parley', 'version': '1.2.0', 'game_target': '1.20.0.3',
            'canonical_description': str(canonical), 'canonical_sha256': hashlib.sha256(canonical.read_bytes()).hexdigest(),
            'source_projection': str(self.root), 'rendered_outputs': {k: str(v) for k, v in self.paths.items()},
            'nexus_file_version': '1.2.0', 'nexus_file_description': 'For CK3 1.20.0.3'}), encoding='utf-8')

    def validate(self):
        return self.gate.validate(self.revision, self.config, self.contract)

    def test_valid_copy_passes_without_claiming_public_verification(self):
        result = self.validate()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['public_verification'], 'NOT_VERIFIED')

    def test_wrong_destination_and_self_catalog_rejected(self):
        path = self.paths['steam']
        original = path.read_text(encoding='utf-8')
        for wrong in ('https://wrong.example/', 'https://steamcommunity.com/sharedfiles/filedetails/?id=1'):
            path.write_text(original.replace('https://steamcommunity.com/sharedfiles/filedetails/?id=3', wrong), encoding='utf-8')
            result = self.validate()
            self.assertEqual(next(c for c in result['checks'] if c['name'] == 'steam:family_catalog')['status'], 'FAIL')

    def test_small_missing_duplicate_or_wrongly_linked_cta_rejected(self):
        path = self.paths['nexus']
        original = path.read_text(encoding='utf-8')
        for invalid in (original.replace('[size=5]', '[size=3]'), original.replace(self.gate.LABEL, ''),
                        original + self.gate.LABEL, original.replace('https://ko-fi.com/g4vv4kh', 'https://wrong.example/')):
            path.write_text(invalid, encoding='utf-8')
            result = self.validate()
            self.assertEqual(next(c for c in result['checks'] if c['name'] == 'nexus:support_heading')['status'], 'FAIL')

    def test_old_nexus_file_target_rejected(self):
        path = self.paths['metadata']
        path.write_text(path.read_text(encoding='utf-8').replace('For CK3 1.20.0.3', 'For CK3 1.20.0.2'), encoding='utf-8')
        result = self.validate()
        self.assertEqual(next(c for c in result['checks'] if c['name'] == 'nexus_file_game_target')['status'], 'FAIL')

    def test_missing_fifth_mod_nonsteam_and_old_heading_are_rejected(self):
        path = self.paths['github']
        original = path.read_text(encoding='utf-8')
        variants = [original.replace('My other mods', 'My mods'),
                    original.replace('https://steamcommunity.com/sharedfiles/filedetails/?id=5', 'https://example.org/court_automation/nexus'),
                    '\n'.join(line for line in original.splitlines() if '[court_automation]' not in line)]
        for invalid in variants:
            path.write_text(invalid, encoding='utf-8')
            self.assertEqual('FAIL', self.validate()['status'])

    def test_feedback_variations_wrong_issue_repo_and_email_are_rejected(self):
        path = self.paths['steam']
        original = path.read_text(encoding='utf-8')
        for before, after in [('Report an issue on GitHub', 'Source and issue reports'),
                              ('https://example.org/parley/github/issues', 'https://example.org/court_automation/github/issues'),
                              ('Email: g4vv4kh@gmail.com', 'Email: someone@example.com')]:
            path.write_text(original.replace(before, after), encoding='utf-8')
            self.assertEqual('FAIL', self.validate()['status'])

    def test_same_links_but_different_role_text_is_not_faithful(self):
        path = self.paths['nexus']
        path.write_text(path.read_text(encoding='utf-8').replace(' — role.', ' — altered role.', 1), encoding='utf-8')
        result = self.validate()
        self.assertEqual('FAIL', next(c for c in result['checks'] if c['name'] == 'nexus:family_matches_canonical')['status'])

    def test_new_contract_member_rejects_previous_complete_catalog(self):
        contract = json.loads(self.contract.read_text(encoding='utf-8'))
        contract['published_family_catalog']['sixth_mod'] = {'label': 'Sixth mod', 'role': 'Another role.', 'steam_url': 'https://steamcommunity.com/sharedfiles/filedetails/?id=6'}
        self.contract.write_text(json.dumps(contract), encoding='utf-8')
        result = self.validate()
        self.assertEqual('FAIL', result['status'])
        self.assertEqual('FAIL', next(c for c in result['checks'] if c['name'] == 'canonical:complete_current_published_catalog')['status'])


if __name__ == '__main__':
    unittest.main()
