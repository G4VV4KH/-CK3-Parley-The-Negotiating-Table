"""Pure-capture harness checks; synthetic strings are not native acceptance."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent / "native_interest"))
import prepare_hover_content_probe_v2 as probe
from test_hover_content_probe import synthetic_log


def v2_log(components):
    v1 = synthetic_log(components)
    output = ["TNGUI_TEST|BEGIN|production_window"]
    for stage, (_, side, selected) in probe.STAGES.items():
        fields = {match[1]: match[2] for match in re.finditer(r"TNH_INPUT\|" + stage + r"\|([^|]+)\|([^|]+)\|END", v1)}
        for key in probe.NATIVE_FIELDS:
            output.append(f"TNH2_INPUT|{stage}|{key}|{fields[key]}|END")
        root = dict(captured="1", container_milli="0", count=fields["count"], name="",
                    list="tnt_interest_reason_rows" if selected else "tnt_interest_preview_reason_rows",
                    host="tnwqa_receive_tooltip_host" if side == "p" else "tnwqa_surrender_tooltip_host")
        for key, value in root.items():
            output.append(f"TNH2_ROOT|{stage}|{key}|{value}|END")
        for index in range(probe.MAX_ROWS):
            slot = {field: "" for field in probe.ROW_FIELDS}
            match = re.search(r"TNH_ROW\|" + stage + rf"\|{index}\|([^|]+)\|([^|]+)\|([^|]+)\|END", v1)
            if match:
                value = probe.old.number(match[1])
                slot.update(captured="1", milli=str(int(value * 1000)), show=match[2], has_tooltip="0",
                            name=re.search(r"TNH_NAME\|" + stage + rf"\|{index}\|([^|]*)\|END", v1)[1],
                            formatted=f"\x15negative_value {value}\x15!")
            for key, value in slot.items():
                output.append(f"TNH2_SLOT|{stage}|{index}|{key}|{value}|END")
    return "\n".join(output + ["TNGUI_TEST|END|production_window"]) + "\n"


class PureCaptureProbeTests(unittest.TestCase):
    def test_preparation_has_zero_scope_mutation_during_capture_and_no_old_helper_edits(self):
        before = probe.old.helper_bindings()
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(StringIO()):
            run = Path(directory) / "v2"
            probe.prepare(run)
            plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["expected_count"], 23)
            self.assertEqual(plan["hover_content_version"], 2)
            gui = (run / "probe" / probe.old.NATIVE_RELATIVE).read_text(encoding="utf-8-sig")
            added = gui[:gui.index("\n\t# Used in a 'top level'")]
            self.assertNotIn("GuiScope", added)
            self.assertNotIn(".Execute(", added)
            self.assertIn("ValueBreakdown.GetFixedPointValue", added)
            self.assertIn("ValueBreakdown.HasTooltip", added)
            self.assertIn("duration = 1", added)
            controls = (run / "probe" / probe.badge.CONTROLS).read_text(encoding="utf-8-sig")
            for obsolete in ("scope:total", "scope:row_value", "scope:show", "scope:is_base", "scope:host_identity"):
                self.assertNotIn(obsolete, controls)
            for stage in probe.STAGES:
                for field in probe.NATIVE_FIELDS:
                    self.assertIn(f"has_variable = tnhqb_{stage}_{field}", controls)
            host = (run / "probe/gui/tnwqa_receive_tooltip_host.gui").read_text(encoding="utf-8-sig")
            self.assertIn("duration = 2", host)
            self.assertIn("tnhqb_p_clear2_consume", host)
        self.assertEqual(before, probe.old.helper_bindings())

    def test_native_container_zero_is_not_misrepresented_as_aggregate(self):
        for language in ("l_english", "l_russian"):
            components = probe.old.localized_components(probe.base.SOURCE, language)
            issues, captured = probe.validate_content(v2_log(components), components)
            self.assertEqual(issues, [])
            self.assertEqual(captured["p_selected"]["native_container"]["container_milli"], "0")
            self.assertEqual(captured["p_selected"]["row_sum"], "35")

    def test_scope_swap_missing_base_and_bad_format_remain_failures(self):
        components = probe.old.localized_components(probe.base.SOURCE, "l_english")
        log = v2_log(components)
        for changed in (log.replace(components["tnt_interest_bd_base"], "What the partner gives"),
                        log.replace("TNH2_SLOT|p_clear1|0|captured|1|END", "TNH2_SLOT|p_clear1|0|captured||END"),
                        log.replace("TNH2_SLOT|p_clear1|0|milli|100000|END", "TNH2_SLOT|p_clear1|0|milli|99000|END"),
                        log.replace("TNH2_ROOT|p_clear1|host|tnwqa_receive_tooltip_host|END", "TNH2_ROOT|p_clear1|host|other|END"),
                        log + "TNH2_ROOT|p_clear1|count|3|END\n"):
            self.assertTrue(probe.validate_content(changed, components)[0])

    def test_capacity_tolerance_is_exactly_one_milli_not_wide(self):
        components = probe.old.localized_components(probe.base.SOURCE, "l_english")
        log = v2_log(components)
        # Clear receiving remains in the same marginal band and should pass a
        # single milli of logged native-input rounding, but not two milli.
        for delta, should_fail in (("300.001", False), ("300.002", True)):
            changed = log.replace("|capacity|300|END", "|capacity|" + delta + "|END")
            # Selected band arithmetic can legitimately change with capacity;
            # assert the clear checkpoint specifically, not a broad price waiver.
            issues, captured = probe.validate_content(changed, components)
            self.assertEqual(any(issue.startswith("p_clear1:") for issue in issues), should_fail)


if __name__ == "__main__":
    unittest.main()
