"""Plan the final actual-source UI cycle; no candidate type override or launch.

Real production opener, then exact production gold receive/surrender tooltip
instances with empty and selected drafts. Selection/clearing use the same
scripted GUI commands as the shipped buttons. No price or stock is mocked.
Re-plan after a production patch; ordinary.freeze rejects source drift.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

import prepare_window_open_probe as ordinary


def tooltip_instance(source, side):
    target = "tnt_interest_gold_" + side + "_percent_value"
    for match in re.finditer(r"\btnt_interest_tooltip\s*=\s*\{", source):
        start = match.start()
        depth, quoted, escaped = 0, False, False
        for index in range(source.index("{", start), len(source)):
            char = source[index]
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    result = source[start:index + 1]
                    if target in result and "tnt_interest_gold_capacity_value" in result:
                        return result
                    break
        else:
            raise ValueError("Unbalanced production tooltip instance")
    raise ValueError("Production gold tooltip is missing")


def prepare(run, preset="standard"):
    ordinary.prepare(run, preset)
    base = ordinary.base
    probe = run / "probe"
    plan_path = run / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    labels = plan["expected_labels"]
    spec = importlib.util.spec_from_file_location("reviewed_final_window_timer", base.RELOAD_HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    call = lambda name: f"GetScriptedGui('{name}').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)"
    phase = lambda n: f"EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('tnwqa_phase').GetValue,'(CFixedPoint){n}')"
    flag = lambda name: f"GetPlayer.MakeScope.GetVariable('{name}').IsSet"
    window_valid = "var:tnt_open = 1 exists = var:tnt_partner var:tnt_partner = { is_alive = yes }"
    empty = "NOT = { has_variable = tnt_gold_p } NOT = { has_variable = tnt_gold_r }"

    def assertion(name, condition):
        labels.append(name)
        return (f'if = {{ limit = {{ {condition} }} debug_log = "TNGUI_TEST|PASS|{name}" }} '
                f'else = {{ debug_log = "TNGUI_TEST|FAIL|{name}" set_variable = {{ name = tnwqa_failed value = 1 }} }}\n')

    def action(name, expected_phase, label, condition, next_phase=None, marker=None):
        guard = f"var:tnwqa_phase = {expected_phase} NOT = {{ has_variable = tnwqa_{name}_done }}"
        body = f"tnwqa_{name} = {{ scope = character effect = {{ if = {{ limit = {{ {guard} }}\n"
        body += f"set_variable = {{ name = tnwqa_{name}_done value = 1 }}\n"
        body += assertion(label, window_valid + " " + condition)
        if marker:
            body += f"set_variable = {{ name = {marker} value = 1 }}\n"
        if next_phase is not None:
            body += f"set_variable = {{ name = tnwqa_phase value = {next_phase} }}\n"
        return body + "} } }\n"

    controls_path = probe / "common/scripted_guis/tnwqa_controls.txt"
    controls = controls_path.read_text(encoding="utf-8-sig")
    token = 'set_variable = { name = tnwqa_phase value = 2 }\ndebug_log = "TNGUI_TEST|END|production_window"'
    if controls.count(token) != 1:
        raise ValueError("Expected one ordinary-window completion point")
    controls = controls.replace(token, 'debug_log = "TNGUI_PHASE|BEFORE|production_tooltip_cycle"\nset_variable = { name = tnwqa_phase value = 2 }')
    controls += action("receive_host_show", 2, "empty_receive_host_show", empty, marker="tnwqa_receive_host_seen")
    controls += action("receive_empty_survived", 2, "empty_receive_tooltip_survives_3s", "has_variable = tnwqa_receive_host_seen " + empty)
    controls += action("receive_selected_ready", 2, "receive_selection_applied_by_production_gui", "var:tnt_gold_p > 0 NOT = { has_variable = tnt_gold_r }", 3)
    controls += action("receive_selected_survived", 3, "selected_receive_tooltip_survives_3s", "has_variable = tnwqa_receive_host_seen var:tnt_gold_p > 0 NOT = { has_variable = tnt_gold_r }")
    controls += action("surrender_empty_ready", 3, "draft_cleared_by_production_gui", empty, 4)
    controls += action("surrender_host_show", 4, "empty_surrender_host_show", empty, marker="tnwqa_surrender_host_seen")
    controls += action("surrender_empty_survived", 4, "empty_surrender_tooltip_survives_3s", "has_variable = tnwqa_surrender_host_seen " + empty)
    controls += action("surrender_selected_ready", 4, "surrender_selection_applied_by_production_gui", "var:tnt_gold_r > 0 NOT = { has_variable = tnt_gold_p }", 5)
    controls += action("surrender_selected_survived", 5, "selected_surrender_tooltip_survives_3s", "has_variable = tnwqa_surrender_host_seen var:tnt_gold_r > 0 NOT = { has_variable = tnt_gold_p }")
    controls += "tnwqa_cycle_finish = { scope = character effect = { if = { limit = { var:tnwqa_phase = 5 }\n"
    controls += assertion("final_draft_cleared_by_production_gui", window_valid + " " + empty)
    controls += assertion("final_window_tooltip_cycle_no_prior_failure", "NOT = { has_variable = tnwqa_failed }")
    controls += 'set_variable = { name = tnwqa_phase value = 6 }\ndebug_log = "TNGUI_TEST|END|production_window"\n} } }\n'
    base.write(controls_path, controls)
    production = (base.SOURCE / ordinary.WINDOW).read_text(encoding="utf-8-sig")
    instances = {}
    for side, name, empty_phase, selected_phase in (("p", "receive", 2, 3), ("r", "surrender", 4, 5)):
        instance = tooltip_instance(production, side)
        instances[side] = hashlib.sha256(instance.encode()).hexdigest()
        visible = helper.both("GetPlayer.IsValid", f"Or({phase(empty_phase)},{phase(selected_phase)})")
        gui = (f'window = {{ name = tnwqa_{name}_tooltip_host layer = top size = {{ 500 700 }} '
               f'parentanchor = center alwaystransparent = no visible = "[{visible}]"\n'
               f'state = {{ name = _show on_start = "[{call("tnwqa_" + name + "_host_show")}]" }}\n'
               + instance + "\n")
        condition = helper.both("GetPlayer.IsValid", phase(empty_phase), flag("tnwqa_" + name + "_host_seen"))
        gui += helper.state("tnwqa_" + name + "_empty_timer", condition,
            [call("tnwqa_" + name + "_empty_survived"), call("tnt_gold_" + side + "_add"),
             call("tnwqa_" + name + "_selected_ready")], 3) + "\n"
        condition = helper.both("GetPlayer.IsValid", phase(selected_phase), flag("tnwqa_" + name + "_host_seen"))
        gui += helper.state("tnwqa_" + name + "_selected_timer", condition,
            [call("tnwqa_" + name + "_selected_survived"), call("tnt_clear_all"),
             call("tnwqa_surrender_empty_ready" if side == "p" else "tnwqa_cycle_finish")], 3) + "\n}\n"
        base.write(probe / f"gui/tnwqa_{name}_tooltip_host.gui", gui)
        base.write(probe / f"gui/scripted_widgets/tnwqa_{name}_tooltip_host.txt", f"gui/tnwqa_{name}_tooltip_host.gui = tnwqa_{name}_tooltip_host\n")
    plan.update(final_actual_source_cycle=True, forced_tooltip_materialization=True,
                expected_labels=labels, expected_count=len(labels), probe_sha256=base.inventory(probe),
                tooltip_materialization_contract={"selection_cycle": "empty receive, selected receive, empty surrender, selected surrender",
                    "production_gui_actions": ["tnt_gold_p_add", "tnt_clear_all", "tnt_gold_r_add", "tnt_clear_all"],
                    "instance_sha256": instances, "stock_or_formula_writes": False,
                    "construction_caveat": "Native children may instantiate before visibility; use actual failure timestamps.",
                    "context_caveat": "Standalone real type, not physical hover. Unknown TooltipInfo context diagnostics remain blockers."})
    plan["coverage_limits"] += ["Re-plan after source repair before freezing; a pre-fix blueprint cannot certify post-fix bytes.",
                                "No tnt_types candidate override: final run must use the repaired actual authoring source."]
    base.dump(plan_path, plan)
    print(json.dumps({"run": str(run), "status": plan["status"], "expected_assertions": len(labels), "final_actual_source_cycle": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--stage", choices=("plan", "freeze"), default="plan")
    ordinary.base.add_path_arguments(parser)
    args = parser.parse_args()
    ordinary.base.configure_paths(args)
    if not re.fullmatch("[a-z0-9_-]+", args.run_name):
        parser.error("Use a lower-case isolated run name")
    run = ordinary.base.EVIDENCE / args.run_name
    prepare(run) if args.stage == "plan" else ordinary.freeze(run)
