"""Static/AST tests for the native preview/locking probe, not engine evidence."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

from test_autobalance import parse
from test_interest_currency import InterestWorld
from test_scaled_valuation import D

sys.path.insert(0, str(Path(__file__).parent / "native_interest"))
import prepare_currency_ui_probe as probe


class CurrencyUiProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / "probe"
        self.before = probe.ordinary.base.inventory(probe.ordinary.base.SOURCE)
        with redirect_stdout(StringIO()):
            probe.prepare(self.run)
        self.plan = json.loads((self.run / "plan.json").read_text(encoding="utf-8"))
        self.controls = (self.run / "probe/common/scripted_guis/tnwqa_controls.txt").read_text(encoding="utf-8-sig")
        self.hosts = {path.stem: path.read_text(encoding="utf-8-sig") for path in (self.run / "probe/gui").glob("tnuq_*_host.gui")}

    def test_exact_independently_declared_assertion_count_and_boundaries(self):
        self.assertEqual(len(probe.CASE_LABELS), 24)
        self.assertEqual(len(probe.LEGACY_LABELS), 13)
        self.assertEqual(self.plan["expected_count"], 206)
        self.assertEqual(len(set(self.plan["expected_labels"])), 206)
        self.assertEqual(re.findall(r'TNGUI_TEST\|PASS\|([^"\s]+)', self.controls), self.plan["expected_labels"])
        self.assertEqual(re.findall(r'TNGUI_TEST\|FAIL\|([^"\s]+)', self.controls), self.plan["expected_labels"])
        self.assertEqual(self.controls.count("TNGUI_TEST|END|production_window"), 1)

    def test_real_opener_and_six_exact_production_tooltips(self):
        source = (probe.ordinary.base.SOURCE / probe.ordinary.WINDOW).read_text(encoding="utf-8-sig")
        self.assertEqual(len(self.hosts), 6)
        self.assertIn("tnt_open_window_effect = yes", self.controls)
        for currency in probe.CURRENCIES:
            for side in ("p", "r"):
                instance = probe.tooltip_instance(source, currency, side)
                host = self.hosts[f"tnuq_{currency}_{side}_host"]
                self.assertEqual(host.count(instance), 1)
                self.assertIn(f"tnt_interest_{currency}_{side}_preview_percent_value", instance)
                self.assertIn(f"tnt_interest_{currency}_{side}_percent_value", instance)
                self.assertEqual(host.count("duration = 3"), 5)
                self.assertIn(f"tnuq_{currency}_{side}_host_seen", host)

    def test_every_blocked_writer_is_executed_then_independently_asserted(self):
        for currency in probe.CURRENCIES:
            for side, other in (("p", "r"), ("r", "p")):
                host = self.hosts[f"tnuq_{currency}_{side}_host"]
                for writer in probe.WRITERS:
                    execute = f"GetScriptedGui('tnt_{currency}_{other}_{writer}').Execute"
                    observe = f"GetScriptedGui('tnuq_{currency}_{side}_blocked_{writer}').Execute"
                    self.assertIn(execute, host)
                    self.assertIn(observe, host)
                    self.assertLess(host.index(execute), host.index(observe))
                    self.assertIn(f"Not(GetScriptedGui('tnt_{currency}_{other}_{writer}').IsValid", host)
                for command in ("add", "sub", "max", "none"):
                    self.assertIn(f"GetScriptedGui('tnt_{currency}_{side}_{command}').Execute", host)

    def test_only_explicit_legacy_amount_writes_no_stock_or_pressure_writes(self):
        writes = re.findall(r"set_variable = \{ name = (tnt_(?:gold|prestige|piety|influence)_[pr]) value = ([0-9]+) \}", self.controls)
        expected = [(f"tnt_{currency}_{side}", amount) for currency in probe.CURRENCIES for _ in range(2)
                    for side, amount in (("p", "10"), ("r", "20"))]
        self.assertEqual(writes, expected)
        self.assertNotRegex(self.controls, r"\b(?:add|remove|set)_(?:gold|prestige|piety|influence)\s*=")
        self.assertNotRegex(self.controls, r"\btnt_(?:threat_p_toggle|usehook_[pr]_toggle)")
        self.assertEqual(self.controls.count("tnt_apply_deal_effect = yes"), 3)
        for name in ("tnt_threat_p", "tnt_usehook_p", "tnt_usehook_r"):
            self.assertIn("NOT = { has_variable = " + name + " }", self.controls)
        self.assertIn("scope:observed = yes gold > 20", self.controls)
        self.assertIn("MakeScopeBool(IsGamePaused)", (self.run / "probe/gui/tnuq_driver.gui").read_text(encoding="utf-8-sig"))

    def test_frozen_plan_binding_no_candidate_override_and_no_freeze(self):
        self.assertEqual(self.before, probe.ordinary.base.inventory(probe.ordinary.base.SOURCE))
        self.assertEqual(self.before, self.plan["runtime_source_at_plan_sha256"])
        self.assertEqual(self.plan["probe_sha256"], probe.ordinary.base.inventory(self.run / "probe"))
        self.assertNotIn("gui/tnt_types.gui", self.plan["probe_sha256"])
        self.assertFalse((self.run / "runtime").exists())
        self.assertFalse((self.run / "userdata").exists())
        self.assertFalse(self.plan["tooltip_materialization_contract"]["stock_or_formula_writes"])
        with self.assertRaises(FileExistsError):
            probe.prepare(self.run)

    def test_all_generated_script_values_and_commands_resolve(self):
        definitions = {}
        for directory in (probe.ordinary.base.SOURCE, self.run / "probe"):
            for path in (directory / "common/scripted_guis").glob("*.txt"):
                definitions.update({key: body for key, _, body in parse(path.read_text(encoding="utf-8-sig"))})
        self.assertIn("tnuq_finish", definitions)
        for host in self.hosts.values():
            for command in re.findall(r"GetScriptedGui\('([^']+)'\)", host):
                self.assertIn(command, definitions)
        for path in (self.run / "probe/common").rglob("*.txt"):
            self.assertTrue(parse(path.read_text(encoding="utf-8-sig")))

    def test_off_uses_same_lock_cycles_and_declared_count(self):
        other = Path(self.temp.name) / "off"
        with redirect_stdout(StringIO()):
            probe.prepare(other, "off")
        plan = json.loads((other / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["preset"], "off")
        self.assertEqual(plan["expected_labels"], self.plan["expected_labels"])

    def test_legacy_preflight_master_and_exact_net_repair_are_observed(self):
        definitions = {key: body for key, _, body in parse(self.controls)}
        for currency in probe.CURRENCIES:
            for label in probe.LEGACY_LABELS:
                self.assertIn(f"legacy_{currency}_{label}", self.plan["expected_labels"])
            master = repr(definitions[f"tnuq_legacy_{currency}_apply"])
            self.assertIn("tnt_deal_partner", master)
            self.assertIn("tnt_apply_deal_effect", master)
            self.assertIn(f"tnuq_{currency}_actor_stock", master)
            self.assertIn(f"tnuq_{currency}_partner_stock", master)
            self.assertIn(f"var:tnt_{currency}_p = 0 var:tnt_{currency}_r = 10 tnt_currencies_exclusive_trigger = yes", self.controls)
        self.assertEqual(self.controls.count("tnt_ab_net_effect = yes"), 3)
        self.assertEqual(self.controls.count("NOT = { tnt_deal_preflight_trigger"), 3)

    def test_autobalance_uses_real_gui_after_reseed_and_requires_honest_live_verdict(self):
        driver = (self.run / "probe/gui/tnuq_driver.gui").read_text(encoding="utf-8-sig")
        self.assertEqual(driver.count("GetScriptedGui('tnt_autobalance').Execute"), 3)
        self.assertEqual(driver.count("Not(GetScriptedGui('tnt_send_offer').IsValid"), 3)
        for currency in probe.CURRENCIES:
            seeded = driver.index(f"GetScriptedGui('tnuq_legacy_{currency}_reseed').Execute")
            balanced = driver.index("GetScriptedGui('tnt_autobalance').Execute", seeded)
            observed = driver.index(f"GetScriptedGui('tnuq_legacy_{currency}_balanced').Execute")
            self.assertLess(seeded, balanced)
            self.assertLess(balanced, observed)
        self.assertIn("var:tnt_ab_state = 3 tnt_ai_accept_value <= 0", self.controls)
        self.assertIn("var:tnt_ab_state = 4 tnt_ai_accept_value > 1", self.controls)
        self.assertIn("tnt_partner_piety_shortfall_value <= 0", self.controls)
        self.assertNotRegex(self.controls, r"tnt_(?:partner_)?\w+_shortfall_value = 0")

    def test_restore_script_parts_immediate_but_gui_validity_on_a_later_tick(self):
        definitions = {key: body for key, _, body in parse(self.controls)}
        for index, (currency, side) in enumerate((currency, side) for currency in probe.CURRENCIES for side in ("p", "r")):
            at, case = 3 + index * 5, f"{currency}_{side}"
            host = self.hosts["tnuq_" + case + "_host"]
            for part, mutation_stage, observation_stage in (("zero", at + 1, at + 2), ("clear", at + 3, at + 4)):
                for field in ("amounts", "triggers", "preview"):
                    body = repr(definitions[f"tnuq_{case}_{part}_{field}"])
                    self.assertIn(f"('var:tnwqa_phase', '=', '{mutation_stage}')", body)
                    self.assertNotIn("scope:observed", body)
                final = repr(definitions[f"tnuq_{case}_{part}"])
                self.assertIn(f"('var:tnwqa_phase', '=', '{observation_stage}')", final)
                self.assertIn("scope:observed", final)
                self.assertIn("tnt_currency_p_unlocked_trigger", final)
                self.assertIn("tnt_currency_r_unlocked_trigger", final)
                immediate = host.index(f"GetScriptedGui('tnuq_{case}_{part}_preview').Execute")
                delayed = host.index(f"GetScriptedGui('tnuq_{case}_{part}').Execute")
                self.assertLess(immediate, delayed)
                self.assertIn("duration = 3", host[immediate:delayed])

    def test_every_boolean_consumer_has_one_dynamic_scope_call_and_exact_controls(self):
        definitions = {key: body for key, _, body in parse(self.controls)}
        consumers = {key for key, body in definitions.items() if "scope:observed" in repr(body)}
        gui = "\n".join(path.read_text(encoding="utf-8-sig") for path in (self.run / "probe/gui").glob("*.gui"))
        calls = re.findall(r"GetScriptedGui\('(tnuq_[^']+)'\)\.Execute\(GuiScope.SetRoot\(GetPlayer.MakeScope\)([^\n]*)", gui)
        for consumer in consumers:
            matched = [tail for name, tail in calls if name == consumer]
            self.assertEqual(len(matched), 1, consumer)
            self.assertEqual(matched[0].count(".AddScope("), 1)
            self.assertTrue(matched[0].startswith(".AddScope('observed',MakeScopeBool("))
        self.assertIn("scope:observed = no NOT = { scope:observed = yes }", self.controls)
        self.assertIn("scope:observed = yes NOT = { scope:observed = no }", self.controls)
        self.assertNotRegex(self.controls, r"(?:save_(?:temporary_)?scope_as|name)\s*=\s*observed\b")


class CurrencyUiOracleTests(unittest.TestCase):
    def test_oracle_has_no_production_percentage_factor_or_amount_reads(self):
        source = probe.oracle_values()
        self.assertNotRegex(source, r"tnt_interest_\w+_(?:percent|factor|amount|weighted_amount)_value")
        self.assertNotIn("preview_percent_value", source)
        self.assertNotIn("display_percent_value", source)

    def test_independent_oracle_all_bands_and_policy_strengths(self):
        for policy, strength in (("off", D(0)), ("mild", D(".5")), ("standard", D(1)), ("strict", D(2))):
            world = InterestWorld(policy)
            world.defs.update({key: body for key, _, body in parse(probe.oracle_values())})
            for currency in probe.CURRENCIES:
                world.root.stats[f"tnt_interest_{currency}_capacity_value"] = D(100)
                for stock in (D(-1), D(0), D(25), D(50), D(100), D(150), D(200), D(1000)):
                    world.partner.stats[currency] = stock
                    receive = D(100) if stock < 100 else D(100) / (1 + strength) if stock < 200 else D(0)
                    surrender = D(100) if stock > 100 else D(100) / (1 + strength) if stock > 25 else D(100) / (1 + 3 * strength)
                    if policy == "off":
                        receive = surrender = D(100)
                    for side, expected in (("p", receive), ("r", surrender)):
                        with self.subTest(policy=policy, currency=currency, stock=stock, side=side):
                            self.assertEqual(world.value(f"tnuq_{currency}_{side}_oracle"), expected)


if __name__ == "__main__":
    unittest.main()
