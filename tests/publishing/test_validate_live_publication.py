"""Isolated DOM mutations: native wrappers/text nodes must not hide drift."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

TOOLS = Path(__file__).resolve().parents[4] / 'tools/publishing'


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(
    all((TOOLS / (name + '.py')).is_file() for name in
        ('validate_live_publication', 'validate_publication_copy')),
    'Release workspace publication validators unavailable')
class LiveSemanticTests(unittest.TestCase):
    def setUp(self):
        self.gate = load('validate_live_publication')
        self.copy = load('validate_publication_copy')
        self.config = {'workshop_ids': {'self': '1', 'other': '2'}, 'links': {'DONATION_URL': 'https://ko-fi.com/g4vv4kh'}}
        self.identity = {'steam': 'https://steamcommunity.com/sharedfiles/filedetails/?id=1',
                         'paradox': 'https://mods.paradoxplaza.com/mods/1/Any',
                         'nexus': 'https://www.nexusmods.com/crusaderkings3/mods/1',
                         'github': 'https://github.com/owner/self'}
        self.label = self.gate.LABEL
        self.feedback = f'Report details. Report an issue on GitHub Email: g4vv4kh@gmail.com {self.label}'
        self.family = 'Other — role. These mods are optional.'
        self.platform_pairs = list(zip(('Steam Workshop', 'Paradox Mods', 'Nexus Mods', 'GitHub'), self.identity.values()))
        self.expected = {'feedback': {'text': self.feedback, 'links': [('Report an issue on GitHub', self.identity['github'] + '/issues'), (self.label, self.config['links']['DONATION_URL'])]},
                         'family': {'text': self.family, 'links': [('Other', 'https://steamcommunity.com/sharedfiles/filedetails/?id=2')]},
                         'platforms': {'text': 'Steam Workshop Paradox Mods Nexus Mods GitHub', 'links': self.platform_pairs}}

    def receipt(self, style='steam'):
        wrappers = {'steam': ('<div class="bb_h1">', '</div>'), 'nexus': ('<font size="5"><strong>', '</strong></font>'), 'github': ('<h2 class="heading-element">', '</h2>'), 'paradox': ('<h3>', '</h3>')}
        a, b = wrappers[style]
        heading = lambda value: a + value + b
        link = lambda label, url: f'<a href="{url}">{label}</a>'
        html = heading('Feedback and support') + '<br>Report details.<br>' + link('Report an issue on GitHub', self.identity['github'] + '/issues') + '<br>Email: g4vv4kh@gmail.com<br>'
        html += heading(link(self.label, self.config['links']['DONATION_URL'])) + '<br>' + heading('Find this mod elsewhere')
        html += '<ul>' + ''.join('<li>' + link(*pair) + '</li>' for pair in self.platform_pairs) + '</ul>'
        html += heading('My other mods') + '<ul><li>' + link('Other', self.expected['family']['links'][0][1]) + ' — role.</li></ul>These mods are optional.' + heading('Credits') + '<p>Credit.</p>'
        return {'description': {'html': html}, 'cta': [{'text': self.label, 'href': self.config['links']['DONATION_URL'], 'visible': True,
                'styles': [{'tag': 'A', 'fontSize': '22px'}, {'tag': 'DIV', 'fontSize': '14px'}]}]}

    def slots(self, receipt):
        return self.gate.captured_slots(receipt, self.expected, self.identity, self.copy, self.config, 'self')

    def test_all_native_heading_wrappers_preserve_raw_text_nodes(self):
        for style in ('steam', 'nexus', 'github', 'paradox'):
            self.assertTrue(all(slot['status'] == 'PASS' for slot in self.slots(self.receipt(style)).values()), style)

    def test_same_links_with_wrong_role_or_report_sentence_fail(self):
        for before, after, key in [('role.', 'wrong role.', 'family'), ('Report details.', 'Different details.', 'feedback'),
                                   ('Email: g4vv4kh@gmail.com', 'Email: wrong@example.com', 'feedback')]:
            receipt = self.receipt()
            receipt['description']['html'] = receipt['description']['html'].replace(before, after)
            self.assertEqual('FAIL', self.slots(receipt)[key]['status'])

    def test_wrong_tracker_old_heading_and_nonsteam_recommendation_fail(self):
        for before, after, key in [('/self/issues', '/self', 'feedback'), ('My other mods', 'My mods', 'family'),
                                   ('https://steamcommunity.com/sharedfiles/filedetails/?id=2', 'https://www.nexusmods.com/crusaderkings3/mods/2', 'family')]:
            receipt = self.receipt()
            receipt['description']['html'] = receipt['description']['html'].replace(before, after)
            self.assertEqual('FAIL', self.slots(receipt)[key]['status'])

    def test_global_links_cannot_hide_missing_scoped_entries(self):
        receipt = self.receipt()
        receipt['description']['html'] = receipt['description']['html'].replace('My other mods', 'Wrong section')
        receipt['anchors'] = [{'text': label, 'href': url} for label, url in self.expected['family']['links']]
        self.assertEqual('FAIL', self.slots(receipt)['family']['status'])

    def test_permalink_is_ignored_but_small_cta_fails(self):
        receipt = self.receipt('github')
        receipt['cta'].append({'text': '', 'href': self.identity['github'] + '#support', 'visible': True})
        self.assertEqual('PASS', self.slots(receipt)['support']['status'])
        receipt['cta'][0]['styles'][0]['fontSize'] = '14px'
        self.assertEqual('FAIL', self.slots(receipt)['support']['status'])

    def test_missing_description_remains_unverified(self):
        self.assertTrue(all(slot['status'] == 'NOT_VERIFIED' for slot in self.slots({}).values()))


if __name__ == '__main__':
    unittest.main()
