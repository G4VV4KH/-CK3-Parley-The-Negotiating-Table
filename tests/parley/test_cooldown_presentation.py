"""Read-only cooldown presentation; native rendering still requires game smoke."""
from pathlib import Path
import re
import unittest

from test_autobalance import DEFAULT_SOURCE, one, parse
from test_threat_frequency import ThreatWorld, VARIABLE, CONSUME


SOURCE = DEFAULT_SOURCE
LOC_FILE = 'common/customizable_localization/tnt_90_cooldown_loc.txt'
# Native data_types_script.txt: GetVarTimeRemaining returns int32. Render the
# day count directly; calendar-relative duration strings can turn 365 into 13 months.
DAYS = "[GetVarTimeRemaining(tnt_cooldown_actor.MakeScope, 'tnt_threat_cooldown')|0]"
EXPIRY_DATE = "[GetCurrentDateWithDiff(GetVarTimeRemaining(tnt_cooldown_actor.MakeScope, 'tnt_threat_cooldown'))]"


class CooldownPresentationTests(unittest.TestCase):
    def definitions(self):
        return {k: v for k, _, v in parse((SOURCE / LOC_FILE).read_text(encoding='utf-8-sig'))}

    def selected(self, name, world, actor='p'):
        for k, _, branch in self.definitions()[name]:
            if k != 'text':
                continue
            trigger = one(branch, 'trigger')
            if trigger is None or world.trigger(trigger, actor):
                return one(branch, 'localization_key')
        self.fail('Missing fallback')

    def test_existing_rc2_timer_is_read_without_restart_or_migration(self):
        world = ThreatWorld(setting='1_year')
        # The only pre-existing state required is the RC2 variable + its native expiry.
        world.character_vars['p'][VARIABLE] = 1
        world.expiries['p', VARIABLE] = 1
        before = dict(world.expiries)
        self.assertEqual(self.selected('TntThreatCooldownStatus', world), 'tnt_threat_cooldown_status')
        self.assertEqual(self.selected('TntThreatRowSubtitle', world), 'tnt_threat_cooldown_short')
        self.assertEqual(world.expiries, before)

    def test_none_and_missing_rule_hide_a_retained_old_timer(self):
        for setting in ('unlimited', None):
            world = ThreatWorld(setting=setting)
            world.character_vars['p'][VARIABLE] = 1
            self.assertEqual(self.selected('TntThreatCooldownStatus', world), 'tnt_threat_cooldown_empty')
            self.assertEqual(self.selected('TntThreatRowSubtitle', world), 'tnt_threat_cooldown_empty')

    def test_duration_options_and_expiry_select_actual_state(self):
        for setting, years in (('1_year', 1), ('5_years', 5), ('10_years', 10)):
            world = ThreatWorld(setting=setting)
            world.effect(CONSUME)
            world.advance(years - 0.5)
            self.assertEqual(self.selected('TntThreatCooldownStatus', world), 'tnt_threat_cooldown_status')
            world.advance(0.5)
            self.assertEqual(self.selected('TntThreatCooldownStatus', world), 'tnt_threat_cooldown_empty')

    def test_scope_is_actual_actor_not_partner(self):
        world = ThreatWorld(setting='1_year')
        world.effect(CONSUME, current='r')
        self.assertEqual(self.selected('TntThreatCooldownStatus', world, 'p'), 'tnt_threat_cooldown_empty')
        self.assertEqual(self.selected('TntThreatCooldownStatus', world, 'r'), 'tnt_threat_cooldown_status')

    def test_subtitle_preserves_selected_pressure_and_prioritizes_block(self):
        world = ThreatWorld(setting='1_year')
        world.character_vars['p']['tnt_threat_p'] = 1
        self.assertEqual(self.selected('TntThreatRowSubtitle', world), 'tnt_threat_sub')
        world.effect(CONSUME)
        self.assertEqual(self.selected('TntThreatRowSubtitle', world), 'tnt_threat_cooldown_short')

    def test_custom_loc_has_only_readonly_native_interface_setup(self):
        for definition in self.definitions().values():
            for k, _, branch in definition:
                if k == 'text' and one(branch, 'setup_scope'):
                    self.assertEqual(one(branch, 'setup_scope'),
                                     [('save_scope_as', '=', 'tnt_cooldown_actor')])
        live = '\n'.join(x for x in (SOURCE / LOC_FILE).read_text().splitlines()
                         if not x.lstrip().startswith('#'))
        self.assertNotRegex(live, r'\b(?:set_variable|change_variable|add_character_modifier|remove_variable)\s*=')

    def test_three_ui_surfaces_and_no_dynamic_buildtooltip_reason(self):
        gui = (SOURCE / 'gui/tnt_diplomacy_window.gui').read_text(encoding='utf-8-sig')
        self.assertIn("[TntTip('tnt_threat_p_toggle')][GetPlayer.Custom('TntThreatCooldownStatus')]", gui)
        self.assertIn("[GetPlayer.Custom('TntThreatRowSubtitle')]", gui)
        subtitle = gui.split("[GetPlayer.Custom('TntThreatRowSubtitle')]", 1)[0][-130:]
        self.assertIn('visible = yes', subtitle)
        required = {'NOT_tnt_err_hatred', 'tnt_bd_floor_panel', 'tnt_threat_cooldown_status',
                    'tnt_threat_cooldown_short', 'tnt_threat_cooldown_empty'}
        files = list((SOURCE / 'localization').glob('*/tnt_l_*.yml'))
        self.assertEqual(len(files), 9)
        for path in files:
            text = path.read_text(encoding='utf-8-sig')
            pairs = re.findall(r'^\s*([^\s:#]+):\d*\s+"(.*)"\s*$', text, re.M)
            loc = dict(pairs)
            self.assertEqual(len(pairs), len(loc), path)
            self.assertTrue(required <= loc.keys(), path)
            self.assertIn("[actor.Custom('TntThreatCooldownStatus')]", loc['tnt_open_negotiations_desc'])
            self.assertNotRegex(loc['tnt_err_threat_cooldown'], r'[\[\]$#]')
            self.assertIn(DAYS, loc['tnt_threat_cooldown_status'])
            self.assertIn(EXPIRY_DATE, loc['tnt_threat_cooldown_status'])
            self.assertEqual(loc['NOT_tnt_err_hatred'], loc['tnt_err_hatred'])
            self.assertEqual(loc['tnt_threat_cooldown_empty'], '')
            if path.parent.name == 'russian':
                self.assertEqual(loc['setting_tnt_threat_frequency_unlimited'], 'нету')

    def test_all_locales_display_integer_days_and_keep_the_expiry_date(self):
        units = {'english': ' d.', 'russian': ' д.', 'german': ' T.',
                 'french': ' j', 'spanish': ' d.', 'polish': ' d.',
                 'japanese': '日', 'korean': '일', 'simp_chinese': '天'}
        files = list((SOURCE / 'localization').glob('*/tnt_l_*.yml'))
        self.assertEqual({path.parent.name for path in files}, set(units))
        for path in files:
            with self.subTest(language=path.parent.name):
                data = path.read_bytes()
                self.assertTrue(data.startswith(b'\xef\xbb\xbf'))
                self.assertFalse(data[3:].startswith(b'\xef\xbb\xbf'))
                loc = dict(re.findall(r'^\s*([^\s:#]+):\d*\s+"(.*)"\s*$',
                                      data.decode('utf-8-sig'), re.M))
                long = loc['tnt_threat_cooldown_status']
                short = loc['tnt_threat_cooldown_short']
                self.assertEqual(long.count(DAYS), 1)
                self.assertEqual(short.count(DAYS), 1)
                self.assertEqual(long.count(EXPIRY_DATE), 1)
                self.assertNotIn(EXPIRY_DATE, short)
                self.assertTrue(short.endswith(DAYS + units[path.parent.name]))
                for text in (long, short):
                    self.assertNotIn('GetTimeDifferenceWithDays', text)
                    self.assertNotIn('GetGameTimeDifferenceForDiffDays', text)
                    self.assertNotIn('.VarRemaining(', text)

    def test_russian_labels_use_explicit_days_without_month_conversion(self):
        path = SOURCE / 'localization/russian/tnt_l_russian.yml'
        loc = dict(re.findall(r'^\s*([^\s:#]+):\d*\s+"(.*)"\s*$',
                              path.read_text(encoding='utf-8-sig'), re.M))
        self.assertEqual(loc['tnt_threat_cooldown_short'], 'Перезарядка: ' + DAYS + ' д.')
        self.assertEqual(loc['tnt_threat_cooldown_status'],
                         r'\n\n#high Перезарядка угрозы#!\nОсталось дней: '
                         + DAYS + ' (до ' + EXPIRY_DATE + ').')


if __name__ == '__main__':
    unittest.main(verbosity=2)
