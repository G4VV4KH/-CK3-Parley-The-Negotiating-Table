"""Second native hover observer: pure GUI capture, then separate script consume.

v1 and its failed native evidence remain immutable. No GuiScope or Execute call
is allowed during the one-second capture phase: SetRoot may invalidate the
ValueBreakdown provider being observed. Consumption occurs at two seconds.
No launch or production edit. Gold p/r only; pixels remain NOT_VERIFIED.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import importlib.util
import json
from pathlib import Path
import re

import prepare_hover_content_probe as old

base, badge = old.base, old.badge
STAGES, MAX_ROWS = old.STAGES, old.MAX_ROWS
NATIVE_FIELDS = tuple(key for key in old.FIELDS if key not in ("total", "count"))
ROOT_FIELDS = ("captured", "container_milli", "count", "name", "list", "host")
ROW_FIELDS = ("captured", "milli", "show", "has_tooltip", "name", "formatted")


def helper_bindings():
    return {**old.helper_bindings(), str(Path(__file__)): base.sha(Path(__file__))}


def stored(key):
    return f"GetVariableSystem.Get('{key}')"


def put(key, expression):
    return f"GetVariableSystem.Set({key},{expression})"


def milli(expression):
    return f"IntToString(FixedPointToInt(Multiply_CFixedPoint({expression},'(CFixedPoint)1000')))"


def pure_instrumentation(native):
    roots, rows = [], []
    for stage, (number, side, selected) in STAGES.items():
        name = "tnt_interest_reason_rows" if selected else "tnt_interest_preview_reason_rows"
        host = "tnwqa_receive_tooltip_host" if side == "p" else "tnwqa_surrender_tooltip_host"
        key = "tnhqb_" + stage + "_root_"
        condition = old.both("GetPlayer.IsValid", old.phase(number), old.name_is("PdxGuiWidget", name),
                            old.name_is(old.parent(3), host), f"Not(GetVariableSystem.Exists('{key}captured'))")
        actions = [put(f"'{key}container_milli'", milli("ValueBreakdown.GetFixedPointValue")),
                   put(f"'{key}count'", "IntToString(GetDataModelSize(ValueBreakdown.GetSubValues))"),
                   put(f"'{key}name'", "ValueBreakdown.GetName"),
                   put(f"'{key}list'", "PdxGuiWidget.GetName"),
                   put(f"'{key}host'", old.parent(3) + ".GetName"),
                   put(f"'{key}captured'", "'1'")]
        roots.append(old.states("tnhqb_" + stage + "_pure_root", condition, actions, 1))
        key = f"Concatenate('tnhqb_{stage}_row_',IntToString(PdxGuiWidget.GetIndexInDataModel))"
        condition = old.both("GetPlayer.IsValid", old.phase(number), old.name_is(old.parent(3), name),
                            old.name_is(old.parent(6), host), f"Not(GetVariableSystem.Exists(Concatenate({key},'_captured')))")
        actions = [put(f"Concatenate({key},'_milli')", milli("ValueBreakdown.GetFixedPointValue")),
                   put(f"Concatenate({key},'_name')", "ValueBreakdown.GetName"),
                   put(f"Concatenate({key},'_formatted')", "ValueBreakdown.GetValue"),
                   put(f"Concatenate({key},'_show')", "Select_CString(ValueBreakdown.ShouldShowValue,'1','0')"),
                   put(f"Concatenate({key},'_has_tooltip')", "Select_CString(ValueBreakdown.HasTooltip,'1','0')"),
                   put(f"Concatenate({key},'_captured')", "'1'")]
        rows.append(old.states("tnhqb_" + stage + "_pure_row", condition, actions, 1))
    root_anchor = 'type widget_value_breakdown_list = widget {\n\t\tname = "values_grid"'
    row_anchor = 'name = "value_breakdown"\n\t\t\t\t\t\tlayoutpolicy_horizontal = expanding'
    native = old.once_replace(native, root_anchor, root_anchor + "\n" + "\n".join(roots))
    first, tail = native.split("\n\t# Used in a 'top level'", 1)
    first = old.once_replace(first, row_anchor, row_anchor + "\n" + "\n".join(rows))
    result = first + "\n\t# Used in a 'top level'" + tail
    if any(token in "\n".join(roots + rows) for token in ("GuiScope", ".Execute(", "GetScriptedGui")):
        raise ValueError("Capture phase must not reset GuiScope or execute scripts")
    return result


def consume_control(stage, number, side, selected):
    prefix = "tnhqb_" + stage
    value_name = f"tnt_interest_gold_{side}_{'percent' if selected else 'preview_percent'}_value"
    condition = f"var:tnt_gold_{side} > 0" if selected else "NOT = { has_variable = tnt_gold_p } NOT = { has_variable = tnt_gold_r }"
    text = (f"{prefix}_consume = {{ scope = character effect = {{ if = {{ limit = {{ var:tnwqa_phase = {number} "
            f"NOT = {{ has_variable = {prefix}_done }} }}\nset_variable = {{ name = {prefix}_done value = 1 }}\n")
    # These native values are read only AFTER every GUI row had its capture frame.
    values = {"scalar": value_name, "amount": "0", "stock": "var:tnt_partner.gold",
              "capacity": "tnt_interest_gold_capacity_value", "income": "var:tnt_partner.yearly_character_income",
              "war_chest": "var:tnt_partner.war_chest_gold_maximum", "reserved": "var:tnt_partner.reserved_gold_maximum",
              "expenses": "var:tnt_partner.monthly_character_expenses"}
    for key, value in values.items():
        text += f"set_variable = {{ name = {prefix}_{key} value = {value} }}\n"
    text += (f"if = {{ limit = {{ exists = var:tnt_gold_{side} }} "
             f"set_variable = {{ name = {prefix}_amount value = var:tnt_gold_{side} }} }}\n")
    flags = {"treasury": "has_treasury = yes", "war": "is_at_war = yes",
             "strategy": "OR = { ai_has_warlike_personality = yes ai_has_cautious_personality = yes ai_has_conqueror_personality = yes }",
             "builder": "OR = { ai_has_economical_boom_personality = yes ai_has_pious_builder_personality = yes ai_should_focus_on_building_in_their_capital = yes }"}
    for key, predicate in flags.items():
        text += (f"set_variable = {{ name = {prefix}_{key} value = 0 }}\n"
                 f"if = {{ limit = {{ var:tnt_partner = {{ {predicate} }} }} set_variable = {{ name = {prefix}_{key} value = 1 }} }}\n")
    # Actual trigger reads give observed variables a native use and fail if any
    # field was not written. No lint-only scope assignment can shadow GUI inputs.
    ready = " ".join("has_variable = " + prefix + "_" + field for field in NATIVE_FIELDS)
    text += old.assertion("hover_" + stage + "_native_context", "is_ai = no var:tnt_open = 1 exists = var:tnt_partner " + condition + " " + ready)
    for field in NATIVE_FIELDS:
        text += f'debug_log = "TNH2_INPUT|{stage}|{field}|{old.var_text(prefix + "_" + field)}|END"\n'
    for field in ROOT_FIELDS:
        text += f'debug_log = "TNH2_ROOT|{stage}|{field}|[{stored(prefix + "_root_" + field)}]|END"\n'
    for index in range(MAX_ROWS):
        for field in ROW_FIELDS:
            text += f'debug_log = "TNH2_SLOT|{stage}|{index}|{field}|[{stored(prefix + "_row_" + str(index) + "_" + field)}]|END"\n'
    return text + "} } }\n"


def prepare(run, language="l_russian"):
    old.prepare(run, language)
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    controls_path = run / "probe" / badge.CONTROLS
    controls = controls_path.read_text(encoding="utf-8-sig")
    anchor = "tnhqa_p_clear1_root = {"
    if controls.count(anchor) != 1:
        raise ValueError("Expected one v1 observation extension")
    controls = controls[:controls.index(anchor)]
    spec = importlib.util.spec_from_file_location("reviewed_hover_v2_timer", base.RELOAD_HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    for stage, (number, side, selected) in STAGES.items():
        controls += consume_control(stage, number, side, selected)
        host = "receive" if side == "p" else "surrender"
        path = run / "probe" / f"gui/tnwqa_{host}_tooltip_host.gui"
        gui = path.read_text(encoding="utf-8-sig")
        consumer = helper.state("tnhqb_" + stage + "_consume_timer", old.both("GetPlayer.IsValid", old.phase(number)),
                                [old.call("tnhqb_" + stage + "_consume")], 2)
        closing = gui.rfind("}")
        base.write(path, gui[:closing] + consumer + "\n" + gui[closing:])
    base.write(controls_path, controls)
    base.write(run / "probe" / old.NATIVE_RELATIVE, pure_instrumentation(old.NATIVE_LIST.read_text(encoding="utf-8-sig")))
    plan.update(hover_content_version=2, hover_helpers_sha256=helper_bindings(), probe_sha256=base.inventory(run / "probe"),
                hover_contract="Pure native GUI capture at1s, script consume at2s; no GuiScope mutation during capture.")
    plan["coverage_limits"] += ["ValueBreakdown root numeric payload is captured as container_milli, not assumed to be the aggregate; row sum is checked against the independently verified production scalar.",
        "Capacity raw inputs are logged to .001 while native underlying operations can retain more precision: at most .001 capacity discrepancy is accepted, never a wide percentage tolerance."]
    base.dump(run / "plan.json", plan)
    print(json.dumps({"run": str(run), "expected_assertions": 23, "hover_content_version": 2, "status": plan["status"]}))


def freeze(run):
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    if plan.get("hover_content_version") != 2 or plan.get("hover_helpers_sha256") != helper_bindings():
        raise ValueError("Wrong v2 plan or helper drift")
    if plan["hover_native_source_sha256"] != base.sha(old.NATIVE_LIST) or plan["hover_native_reference_sha256"] != base.sha(run / "native-reference" / old.NATIVE_RELATIVE):
        raise ValueError("Native source/reference drift")
    if old.localized_components(base.SOURCE, plan["language"]) != plan["hover_components"]:
        raise ValueError("Localized components changed")
    badge.freeze(run)


def expected_percent(capacity, stock, amount, side, selected):
    D, fixed, clamp = old.D, old.fixed, old.clamp
    if not selected:
        if side == "p":
            return D(0) if stock >= capacity * 2 else D(50) if stock >= capacity else D(100)
        return D(25) if stock <= fixed(capacity / 4) else D(50) if stock <= capacity else D(100)
    if side == "p":
        full = clamp(capacity - stock, 0, amount)
        tail = max(D(0), clamp(capacity * 2 - stock, 0, amount) - full)
        return clamp(fixed(fixed((full + fixed(tail / 2)) * 100) / max(amount, D(".001"))), 0, 100)
    reserve = clamp(amount - max(stock - capacity, D(0)), 0, amount)
    critical = clamp(amount - max(stock - fixed(capacity * D(".25")), D(0)), 0, amount)
    return clamp(fixed(fixed(amount * 100) / max(amount + reserve + critical * 2, D(".001"))), 1, 100)


def validate_content(debug, components):
    issues, captured = [], {}
    begin, end = debug.find("TNGUI_TEST|BEGIN|production_window"), debug.find("TNGUI_TEST|END|production_window")
    records = [(match.start(), match[1], match[2].split("|")) for match in re.finditer(r"TNH2_(INPUT|ROOT|SLOT)\|([^\r\n]*?)\|END", debug)]
    if debug.count("TNH2_") != len(records) or not records or not all(begin >= 0 and begin < pos < end for pos, _, _ in records):
        issues.append("Malformed/missing/out-of-boundary v2 records")
    if any(fields[0] not in STAGES for _, _, fields in records):
        issues.append("Unknown v2 checkpoint")
    for stage, (_, side, selected) in STAGES.items():
        inputs, root, slots = {}, {}, {str(index): {} for index in range(MAX_ROWS)}
        try:
            for _, kind, fields in records:
                if fields[0] != stage:
                    continue
                if kind == "SLOT":
                    if len(fields) != 4 or fields[1] not in slots or fields[2] not in ROW_FIELDS or fields[2] in slots[fields[1]]:
                        raise ValueError("Unknown/duplicate/malformed slot record")
                    slots[fields[1]][fields[2]] = fields[3]
                else:
                    target, expected = (inputs, NATIVE_FIELDS) if kind == "INPUT" else (root, ROOT_FIELDS)
                    if len(fields) != 3 or fields[1] not in expected or fields[1] in target:
                        raise ValueError("Unknown/duplicate/malformed root/input record")
                    target[fields[1]] = old.number(fields[2]) if kind == "INPUT" else fields[2]
            if set(inputs) != set(NATIVE_FIELDS) or set(root) != set(ROOT_FIELDS) or any(set(slot) != set(ROW_FIELDS) for slot in slots.values()):
                raise ValueError("Incomplete capture/consume contract")
            name = "tnt_interest_reason_rows" if selected else "tnt_interest_preview_reason_rows"
            host = "tnwqa_receive_tooltip_host" if side == "p" else "tnwqa_surrender_tooltip_host"
            if root["captured"] != "1" or root["list"] != name or root["host"] != host:
                raise ValueError("Actual native list/host identity was not captured")
            old.number(root["container_milli"])
            count = old.number(root["count"])
            if count != int(count) or not 0 < count <= MAX_ROWS:
                raise ValueError("Native model is empty/unbounded")
            active = {index: slot for index, slot in slots.items() if slot["captured"] == "1"}
            if set(active) != {str(index) for index in range(int(count))} or any(any(slot.values()) for slot in slots.values() if slot["captured"] != "1"):
                raise ValueError("Pure native row captures do not match model indexes")
            if any(inputs[key] not in (0, 1) for key in ("treasury", "war", "builder", "strategy")) or (inputs["amount"] > 0) != selected:
                raise ValueError("Native inputs/selection invalid")
            independent_capacity, _, _ = old.expected_values(inputs, side, selected)
            if abs(independent_capacity - inputs["capacity"]) > Decimal(".001"):
                raise ValueError("Capacity differs from independently captured native-input arithmetic by more than .001")
            total = expected_percent(inputs["capacity"], inputs["stock"], inputs["amount"], side, selected)
            if inputs["scalar"] != total:
                raise ValueError("Production scalar differs from independent marginal/integrated formula")
            motive = "tnt_interest_bd_" + ("" if selected else "preview_") + ("receiving_demand" if side == "p" else "surrender_reserve")
            expected = {components["tnt_interest_bd_base"]: Decimal(100), components[motive]: total - 100,
                        components["tnt_interest_bd_rule_strength"]: Decimal(0)}
            names, values, observed_rows = Counter(), [], []
            for index, slot in active.items():
                value = old.number(slot["milli"]) / 1000
                if slot["name"] not in expected or value != expected[slot["name"]] or slot["show"] not in ("0", "1") or slot["has_tooltip"] not in ("0", "1"):
                    raise ValueError("Captured native row name/numeric contribution does not match expected component")
                names[slot["name"]] += 1
                values.append(value)
                if value and slot["show"] != "1":
                    raise ValueError("Nonzero component hidden by native renderer")
                if slot["show"] == "1":
                    # CK3 emits native rich-text controls as U+0015, not #.
                    plain = re.sub(r"[\x15#][A-Za-z_]+\s*|[\x15#]!", "", slot["formatted"]).strip().removesuffix("%").strip()
                    formatted = old.number(plain)
                    normalized = plain.replace(",", ".")
                    decimals = len(normalized.rsplit(".", 1)[1]) if "." in normalized else 0
                    if abs(formatted - value) > Decimal(1).scaleb(-decimals) / 2:
                        raise ValueError("Native formatted number contradicts numeric contribution")
                observed_rows.append({"index": index, **slot, "numeric": str(value)})
            if any(names[name] != 1 for name, value in expected.items() if value != 0) or names[components["tnt_interest_bd_base"]] != 1 or any(count > 1 for count in names.values()):
                raise ValueError("Explicit base100/nonzero component missing or duplicated")
            if sum(values, Decimal(0)) != total:
                raise ValueError("Actual native component sum differs from independently verified scalar")
            captured[stage] = {"inputs": {key: str(value) for key, value in inputs.items()}, "native_container": root,
                               "row_sum": str(sum(values, Decimal(0))), "rows": observed_rows}
        except (ValueError, KeyError, InvalidOperation) as exc:
            issues.append(stage + ": " + str(exc))
    for side in ("p", "r"):
        first, last = captured.get(side + "_clear1"), captured.get(side + "_clear2")
        if first and last and first != last:
            issues.append(side + ": clear content/native inputs did not restore exactly")
    return issues, captured


def inspect(run, diagnostic_review=None, window_diagnostic_review=None, currency_ui_diagnostic_review=None):
    result = badge.window_inspector.inspect(run, diagnostic_review, window_diagnostic_review, currency_ui_diagnostic_review)
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "frozen-manifest.json").read_text(encoding="utf-8"))
    issues = []
    for key in ("hover_content_version", "hover_components", "hover_stages", "hover_helpers_sha256", "hover_native_source_sha256",
                "hover_native_reference_sha256", "localized_witnesses", "language", "expected_labels", "probe_sha256"):
        if manifest.get(key) != plan.get(key):
            issues.append("Frozen/plan mismatch: " + key)
    if manifest.get("hover_content_version") != 2 or manifest.get("expected_count") != 23:
        issues.append("Not the exact v2/23 assertion contract")
    if manifest.get("hover_helpers_sha256") != helper_bindings() or manifest.get("hover_native_source_sha256") != base.sha(old.NATIVE_LIST) or manifest.get("hover_native_reference_sha256") != base.sha(run / "native-reference" / old.NATIVE_RELATIVE):
        issues.append("Native source/reference or helper drift")
    components = old.localized_components(run / "runtime", manifest["language"])
    if components != manifest.get("hover_components"):
        issues.append("Frozen localized components differ")
    debug = (run / "userdata/logs/debug.log").read_text(encoding="utf-8-sig")
    issues += badge.validate_localized_witnesses(debug, badge.localized_expectations(run / "runtime", manifest["language"]))
    settings = (run / "userdata/pdx_settings.txt").read_text(encoding="utf-8")
    if not re.search(r'"language"\s*=\s*\{[^}]*value\s*=\s*"' + re.escape(manifest["language"]) + '"', settings, re.S):
        issues.append("Stopped profile language mismatch")
    content_issues, captured = validate_content(debug, components)
    issues += content_issues
    result["blockers"] += issues
    if result["blockers"]:
        result["status"] = "FAIL"
    result.update(classification="NATIVE_PRODUCTION_GOLD_HOVER_PURE_CAPTURE_V2", hover_content="PASS" if not content_issues else "FAIL",
                  captured_hover_content=captured, hover_content_inspector_sha256=base.sha(Path(__file__)))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--stage", choices=("plan", "freeze", "inspect"), default="plan")
    parser.add_argument("--language", choices=badge.LANGUAGES, default="l_russian")
    parser.add_argument("--output", type=Path)
    reviews = parser.add_mutually_exclusive_group()
    reviews.add_argument("--diagnostic-review", type=Path)
    reviews.add_argument("--window-diagnostic-review", type=Path)
    reviews.add_argument("--currency-ui-diagnostic-review", type=Path)
    base.add_path_arguments(parser)
    args = parser.parse_args()
    base.configure_paths(args)
    if not re.fullmatch("[a-z0-9_-]+", args.run_name):
        parser.error("Use a fresh lower-case isolated run name")
    run = base.EVIDENCE / args.run_name
    if args.stage == "plan":
        prepare(run, args.language)
    elif args.stage == "freeze":
        freeze(run)
    else:
        if args.output is None:
            parser.error("--output required")
        result = inspect(run, args.diagnostic_review, args.window_diagnostic_review, args.currency_ui_diagnostic_review)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(json.dumps({key: result[key] for key in ("status", "pass_count", "expected_count", "hover_content", "blockers")}))
