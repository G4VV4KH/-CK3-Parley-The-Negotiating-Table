"""Static controls for the separate real production-window crash diagnostic."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock


HARNESS = Path(__file__).parent / "native_interest"
sys.path.insert(0, str(HARNESS))
spec = importlib.util.spec_from_file_location("interest_window_probe", HARNESS / "prepare_window_open_probe.py")
window_probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(window_probe)
spec = importlib.util.spec_from_file_location("interest_final_window_probe", HARNESS / "prepare_final_window_probe.py")
final_probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(final_probe)


class ProductionWindowProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / "probe-case"

    def unfixed_source_fixture(self):
        """Reconstruct only the two historical headers in a disposable copy."""
        fixture = Path(self.temp.name) / "unfixed-source-fixture"
        shutil.copytree(window_probe.base.SOURCE, fixture)
        types = fixture / "gui/tnt_types.gui"
        raw = types.read_bytes()
        newline = b"\r\n" if b"\r\n" in raw else b"\n"
        for name in (b"tnt_interest_points", b"tnt_interest_capacity"):
            fixed = b"flowcontainer = {" + newline + b"\t\t\t\tdirection = vertical" + newline + b'\t\t\t\tname = "' + name + b'"'
            original = b"vbox = {" + newline + b'\t\t\t\tname = "' + name + b'"'
            self.assertEqual(raw.count(fixed) + raw.count(original), 1)
            raw = raw.replace(fixed, original)
        types.write_bytes(raw)
        return fixture

    def test_real_opener_and_real_window_observers(self):
        window_probe.prepare(self.run, "standard")
        controls = (self.run / "probe/common/scripted_guis/tnwqa_controls.txt").read_text(encoding="utf-8-sig")
        self.assertIn("tnt_open_window_effect = yes", controls)
        self.assertNotIn("name = tnt_open", controls)
        self.assertNotIn("add_gold", controls)
        self.assertNotIn("tnt_ai_accept_value", controls)
        gui = (self.run / "probe/gui/tnt_diplomacy_window.gui").read_text(encoding="utf-8-sig")
        self.assertEqual(gui.count('on_start = "[TntExec(\'tnt_refresh_lists\')]"'), 1)
        self.assertEqual(gui.count("GetScriptedGui('tnwqa_observe_show')"), 1)
        self.assertIn("duration = 3", gui)
        self.assertIn("duration = 15", gui)
        self.assertNotIn("frontend_ingame_menu.gui", window_probe.base.inventory(self.run / "probe"))
        self.assertNotIn("gui/window_save_game.gui", window_probe.base.inventory(self.run / "probe"))

    def test_production_rows_unchanged_after_removing_instrumentation(self):
        window_probe.prepare(self.run, "standard")
        source = (window_probe.base.SOURCE / window_probe.WINDOW).read_text(encoding="utf-8-sig")
        gui = (self.run / "probe" / window_probe.WINDOW).read_text(encoding="utf-8-sig")
        gui = gui.replace('\n\t\ton_start = "[GetScriptedGui(\'tnwqa_observe_show\').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"', "")
        marker = "\n# TEST ONLY production-window lifetime observers; no row/layout replacement\n"
        start = gui.index(marker)
        gui = gui[:start] + gui[gui.rfind("}"):]
        self.assertEqual(gui, source)

    def test_candidate_changes_exactly_two_raw_byte_replacements(self):
        production_before = window_probe.base.inventory(window_probe.base.SOURCE)
        fixture = self.unfixed_source_fixture()
        with mock.patch.object(window_probe.base, "SOURCE", fixture):
            window_probe.prepare(self.run, "standard", tooltip_flow_fix=True)
        source = (fixture / "gui/tnt_types.gui").read_bytes()
        candidate = (self.run / "probe/gui/tnt_types.gui").read_bytes()
        newline = b"\r\n" if b"\r\n" in source else b"\n"
        for name in (b"tnt_interest_points", b"tnt_interest_capacity"):
            candidate = candidate.replace(b"flowcontainer = {" + newline + b"\t\t\t\tdirection = vertical" + newline + b'\t\t\t\tname = "' + name + b'"',
                                          b"vbox = {" + newline + b'\t\t\t\tname = "' + name + b'"')
        self.assertEqual(candidate, source)
        self.assertEqual(window_probe.base.inventory(window_probe.base.SOURCE), production_before)

    def test_plan_pins_complete_runtime_and_exact_six_labels(self):
        window_probe.prepare(self.run, "standard")
        plan = json.loads((self.run / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["runtime_source_at_plan_sha256"], window_probe.base.inventory(window_probe.base.SOURCE))
        self.assertEqual(plan["probe_sha256"], window_probe.base.inventory(self.run / "probe"))
        self.assertEqual(plan["expected_count"], 6)
        self.assertEqual(len(set(plan["expected_labels"])), 6)
        self.assertEqual(plan["language"], "l_russian")

    def test_empty_tooltip_is_exact_production_instance_and_never_seeds_gold(self):
        window_probe.prepare(self.run, "standard", materialize_tooltip=True)
        source = (window_probe.base.SOURCE / window_probe.WINDOW).read_text(encoding="utf-8-sig")
        instance = window_probe.production_gold_tooltip_instance(source)
        tooltip = (self.run / "probe/gui/tnwqa_tooltip_host.gui").read_text(encoding="utf-8-sig")
        self.assertIn(instance, tooltip)
        controls = (self.run / "probe/common/scripted_guis/tnwqa_controls.txt").read_text(encoding="utf-8-sig")
        self.assertNotIn("name = tnt_gold_p", controls)
        self.assertIn("NOT = { has_variable = tnt_gold_p }", controls)
        plan = json.loads((self.run / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["expected_count"], 9)
        self.assertTrue(plan["forced_tooltip_materialization"])
        self.assertIn("EMPTY", plan["tooltip_materialization_contract"]["selection"])

    def test_tooltip_ab_probe_diff_is_only_minimal_type_override(self):
        candidate = Path(self.temp.name) / "candidate"
        fixture = self.unfixed_source_fixture()
        with mock.patch.object(window_probe.base, "SOURCE", fixture):
            window_probe.prepare(self.run, "standard", materialize_tooltip=True)
            window_probe.prepare(candidate, "standard", tooltip_flow_fix=True, materialize_tooltip=True)
        baseline_files = window_probe.base.inventory(self.run / "probe")
        candidate_files = window_probe.base.inventory(candidate / "probe")
        self.assertEqual({key: value for key, value in candidate_files.items() if key != "gui/tnt_types.gui"}, baseline_files)
        self.assertEqual(len(candidate_files), len(baseline_files) + 1)


class FinalProductionWindowCycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / "final-case"
        self.production_before = window_probe.base.inventory(window_probe.base.SOURCE)
        final_probe.prepare(self.run)
        self.plan = json.loads((self.run / "plan.json").read_text(encoding="utf-8"))
        self.controls = (self.run / "probe/common/scripted_guis/tnwqa_controls.txt").read_text(encoding="utf-8-sig")

    def test_exact_seventeen_labels_and_single_completion(self):
        labels = self.plan["expected_labels"]
        self.assertEqual(len(labels), 17)
        self.assertEqual(len(set(labels)), 17)
        self.assertEqual(self.plan["expected_count"], 17)
        self.assertEqual(self.controls.count('TNGUI_TEST|END|production_window'), 1)
        self.assertEqual(re.findall(r'TNGUI_TEST\|PASS\|([^"\s]+)', self.controls), labels)
        self.assertEqual(re.findall(r'TNGUI_TEST\|FAIL\|([^"\s]+)', self.controls), labels)
        for side in ("receive", "surrender"):
            self.assertIn(f"empty_{side}_tooltip_survives_3s", labels)
            self.assertIn(f"selected_{side}_tooltip_survives_3s", labels)

    def test_both_hosts_reuse_verbatim_production_instances(self):
        source = (window_probe.base.SOURCE / window_probe.WINDOW).read_text(encoding="utf-8-sig")
        for side, direction in (("p", "receive"), ("r", "surrender")):
            instance = final_probe.tooltip_instance(source, side)
            host = (self.run / f"probe/gui/tnwqa_{direction}_tooltip_host.gui").read_text(encoding="utf-8-sig")
            self.assertEqual(host.count(instance), 1)
            self.assertIn(f"TntBreakdown('tnt_interest_gold_{side}_percent_value')", instance)
            self.assertIn("TntBreakdown('tnt_interest_gold_capacity_value')", instance)
            self.assertEqual(host.count("duration = 3"), 2)
            self.assertIn(f"GetScriptedGui('tnwqa_{direction}_host_show')", host)

    def test_each_tooltip_survival_requires_native_host_callback_witness(self):
        for direction in ("receive", "surrender"):
            for selection in ("empty", "selected"):
                label = f"{selection}_{direction}_tooltip_survives_3s"
                condition = re.search(r'if = \{ limit = \{ ([^\n]+?) \} debug_log = "TNGUI_TEST\|PASS\|' + label + '"', self.controls)
                self.assertIsNotNone(condition)
                self.assertIn(f"has_variable = tnwqa_{direction}_host_seen", condition.group(1))

    def test_selection_and_clear_use_production_gui_without_stock_or_formula_writes(self):
        combined = "\n".join(path.read_text(encoding="utf-8-sig") for path in (self.run / "probe/gui").glob("tnwqa_*_tooltip_host.gui"))
        for command in ("tnt_gold_p_add", "tnt_gold_r_add"):
            self.assertEqual(combined.count(f"GetScriptedGui('{command}')"), 1)
        self.assertEqual(combined.count("GetScriptedGui('tnt_clear_all')"), 2)
        self.assertNotRegex(self.controls, r"name\s*=\s*tnt_(gold|prestige|piety)_[pr]\b")
        self.assertNotRegex(self.controls, r"\b(add|remove|set)_gold\s*=")
        self.assertNotIn("tnt_ai_accept_value", self.controls)
        self.assertIn("tnt_open_window_effect = yes", self.controls)
        self.assertFalse(self.plan["tooltip_materialization_contract"]["stock_or_formula_writes"])

    def test_final_source_binding_no_candidate_override_and_explicit_limits(self):
        self.assertTrue(self.plan["final_actual_source_cycle"])
        self.assertFalse(self.plan["isolated_tooltip_flow_fix"])
        self.assertEqual(self.plan["runtime_source_at_plan_sha256"], self.production_before)
        self.assertEqual(window_probe.base.inventory(window_probe.base.SOURCE), self.production_before)
        self.assertEqual(self.plan["probe_sha256"], window_probe.base.inventory(self.run / "probe"))
        self.assertNotIn("gui/tnt_types.gui", self.plan["probe_sha256"])
        self.assertEqual(self.plan["language"], "l_russian")
        self.assertIn("not physical hover", self.plan["tooltip_materialization_contract"]["context_caveat"])
        self.assertIn("before visibility", self.plan["tooltip_materialization_contract"]["construction_caveat"])


if __name__ == "__main__":
    unittest.main()
