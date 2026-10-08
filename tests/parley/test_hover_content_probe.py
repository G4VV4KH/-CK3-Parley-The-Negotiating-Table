"""Helper/independent-oracle unit checks, never a substitute for native rows."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / "native_interest"))
import prepare_hover_content_probe as probe


def synthetic_log(components, *, include_zero=True):
    """Hand fixture C=300 from native income50/budget100, stock390, amount300."""
    lines = ["TNGUI_TEST|BEGIN|production_window"]
    totals = {"p_clear1": "50", "p_selected": "35", "p_clear2": "50",
              "r_clear1": "100", "r_selected": "58.823", "r_clear2": "100"}
    for stage, (_, side, selected) in probe.STAGES.items():
        total = probe.D(totals[stage])
        kinds = [1] + ([2] if total != 100 or include_zero else []) + ([3] if include_zero else [])
        inputs = dict(total=total, count=len(kinds), scalar=total, amount=300 if selected else 0,
                      stock=390, capacity=300, income=50, war_chest=100, reserved=0, expenses=10,
                      treasury=0, strategy=0, war=0, builder=0)
        for key in probe.FIELDS:
            lines.append(f"TNH_INPUT|{stage}|{key}|{inputs[key]}|END")
        motive = "tnt_interest_bd_" + ("" if selected else "preview_") + ("receiving_demand" if side == "p" else "surrender_reserve")
        names = {1: components["tnt_interest_bd_base"], 2: components[motive], 3: components["tnt_interest_bd_rule_strength"]}
        values = {1: probe.D(100), 2: total - 100, 3: probe.D(0)}
        for index, kind in enumerate(kinds):
            value = values[kind]
            lines += [f"TNH_ROW|{stage}|{index}|{value}|{int(value != 0)}|{kind}|END",
                      f"TNH_NAME|{stage}|{index}|{names[kind]}|END",
                      f"TNH_FORMAT|{stage}|{index}|{value}|END"]
    lines.append("TNGUI_TEST|END|production_window")
    return "\n".join(lines) + "\n"


class HoverContentPreparationTests(unittest.TestCase):
    def test_preparation_preserves_helpers_runtime_and_exact_native_rendering(self):
        before = probe.helper_bindings()
        runtime_before = probe.base.inventory(probe.base.SOURCE)
        native = probe.NATIVE_LIST.read_text(encoding="utf-8-sig")
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / "ru"
            with redirect_stdout(StringIO()):
                probe.prepare(run)
            plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["language"], "l_russian")
            self.assertEqual(plan["expected_count"], 23)
            self.assertEqual(len(set(plan["expected_labels"])), 23)
            self.assertEqual(plan["localized_witness_count"], 2)
            self.assertFalse((run / "runtime").exists())
            self.assertFalse((run / "userdata").exists())
            rendered = (run / "probe" / probe.NATIVE_RELATIVE).read_text(encoding="utf-8-sig")
            for fragment in ('datamodel = "[ValueBreakdown.GetSubValues]"',
                             'text = "[ValueBreakdown.GetName]"', 'text = "[ValueBreakdown.GetValue]"',
                             'text = "[ValueBreakdown.GetValue|L]"'):
                self.assertEqual(rendered.count(fragment), native.count(fragment))
            self.assertEqual(rendered.count("widget = {"), native.count("widget = {"))
            self.assertEqual(rendered.count("hbox = {"), native.count("hbox = {"))
            self.assertEqual(rendered.count("vbox = {"), native.count("vbox = {"))
            self.assertIn("MakeScopeValue(ValueBreakdown.GetFixedPointValue)", rendered)
            self.assertIn("MakeScopeBool(EqualTo_string(ValueBreakdown.GetName,Localize('tnt_interest_bd_base')))", rendered)
            self.assertEqual((run / "native-reference" / probe.NATIVE_RELATIVE).read_bytes(), probe.NATIVE_LIST.read_bytes())
            self.assertNotIn("gui/tnt_types.gui", plan["probe_sha256"])
            controls = (run / "probe" / probe.badge.CONTROLS).read_text(encoding="utf-8-sig")
            self.assertEqual(controls.count("TNGUI_LOCALIZED|"), 2)
            self.assertEqual(controls.count("TNH_INPUT|"), len(probe.STAGES) * len(probe.FIELDS))
            self.assertIn("value = var:tnt_partner.monthly_character_expenses", controls)
            for side, host, restored in (("p", "receive", 7), ("r", "surrender", 8)):
                gui = (run / "probe" / f"gui/tnwqa_{host}_tooltip_host.gui").read_text(encoding="utf-8-sig")
                self.assertIn(f"GetScriptedGui('tnt_gold_{side}_add')", gui)
                self.assertIn("GetScriptedGui('tnt_clear_all')", gui)
                self.assertIn(probe.phase(restored), gui)
                self.assertIn(f"GetScriptedGui('tnhqa_{side}_cleared')", gui)
                instance = probe.badge.final.tooltip_instance((probe.base.SOURCE / probe.badge.final.ordinary.WINDOW).read_text(encoding="utf-8-sig"), side)
                self.assertIn(instance, gui)
        self.assertEqual(before, probe.helper_bindings())
        self.assertEqual(runtime_before, probe.base.inventory(probe.base.SOURCE))

    def test_native_or_helper_drift_prevents_freeze(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / "plan"
            with redirect_stdout(StringIO()):
                probe.prepare(run, "l_english")
            with patch.object(probe, "helper_bindings", return_value={}), patch.object(probe.badge, "freeze") as freeze:
                with self.assertRaisesRegex(ValueError, "helper changed"):
                    probe.freeze(run)
                freeze.assert_not_called()
            reference = run / "native-reference" / probe.NATIVE_RELATIVE
            reference.write_text("modified test-only fixture", encoding="utf-8")
            with patch.object(probe.badge, "freeze") as freeze:
                with self.assertRaisesRegex(ValueError, "reference snapshot changed"):
                    probe.freeze(run)
                freeze.assert_not_called()

    def test_injection_rejects_unknown_native_structure(self):
        with self.assertRaisesRegex(ValueError, "anchor changed"):
            probe.instrument_native_list("types Unknown {}")


class HoverContentOracleTests(unittest.TestCase):
    def setUp(self):
        self.components = probe.localized_components(probe.base.SOURCE, "l_english")
        self.log = synthetic_log(self.components)

    def test_hand_calculated_six_checkpoints_and_optional_zero_rows(self):
        for zeros in (True, False):
            issues, captures = probe.validate_content(synthetic_log(self.components, include_zero=zeros), self.components)
            self.assertEqual(issues, [])
            self.assertEqual(len(captures), 6)
            self.assertEqual(captures["p_selected"]["inputs"]["total"], "35")
            self.assertEqual(captures["r_selected"]["inputs"]["total"], "58.823")

    def test_explicit_base_cannot_be_supplied_by_parent_metadata(self):
        # Keep parent100 and actual row count consistent, but omit the actual
        # base row. The inspector must not invent an implicit contribution100.
        lines = self.log.splitlines()
        lines = [line for line in lines if not line.startswith(("TNH_ROW|r_clear1|0|", "TNH_NAME|r_clear1|0|", "TNH_FORMAT|r_clear1|0|"))]
        changed = "\n".join(lines).replace("TNH_INPUT|r_clear1|count|3|END", "TNH_INPUT|r_clear1|count|2|END")
        changed = changed.replace("|r_clear1|1|", "|r_clear1|0|").replace("|r_clear1|2|", "|r_clear1|1|")
        self.assertTrue(probe.validate_content(changed, self.components)[0])

    def test_wrong_native_value_locale_format_or_capacity_fails(self):
        variants = (
            self.log.replace("TNH_ROW|p_selected|1|-65|1|2|END", "TNH_ROW|p_selected|1|-64|1|2|END"),
            self.log.replace(self.components["tnt_interest_bd_base"], "wrong language"),
            self.log.replace("TNH_FORMAT|p_selected|0|100|END", "TNH_FORMAT|p_selected|0|99|END"),
            self.log.replace("TNH_INPUT|p_selected|income|50|END", "TNH_INPUT|p_selected|income|51|END"),
            self.log.replace("TNH_ROW|p_selected|0|100|1|1|END", "TNH_ROW|p_selected|0|100|0|1|END"),
        )
        for variant in variants:
            with self.subTest(variant=variant[:120]):
                self.assertTrue(probe.validate_content(variant, self.components)[0])

    def test_missing_duplicate_unknown_or_out_of_boundary_records_fail(self):
        for changed in (self.log.replace("TNH_FORMAT|p_clear1|0|100|END\n", ""),
                        self.log + "TNH_FORMAT|p_clear1|0|100|END\n",
                        self.log.replace("|p_clear1|", "|unknown|"),
                        self.log.replace("TNGUI_TEST|BEGIN|production_window", "missing"),
                        self.log + "TNH_BOGUS|x|END\n",
                        self.log.replace("TNH_INPUT|p_selected|stock|390|END", "TNH_INPUT|p_selected|stock|NaN|END")):
            self.assertTrue(probe.validate_content(changed, self.components)[0])

    def test_ru_copy_and_fixedpoint_precision(self):
        russian = probe.localized_components(probe.base.SOURCE, "l_russian")
        self.assertEqual(probe.validate_content(synthetic_log(russian), russian)[0], [])
        self.assertEqual(probe.number("1\u00a0234,567"), probe.D("1234.567"))
        self.assertEqual(probe.fixed(probe.D("1.2349")), probe.D("1.234"))
        self.assertEqual(probe.fixed(probe.D("-1.2349")), probe.D("-1.234"))


if __name__ == "__main__":
    unittest.main()
