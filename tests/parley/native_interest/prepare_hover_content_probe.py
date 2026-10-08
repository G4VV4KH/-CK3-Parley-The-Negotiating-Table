"""Native gold-tooltip content cycle, using actual production breakdown rows.

Plan/freeze/inspect only: never launch, stop, or control a user's CK3 session.
The old 17 window assertions and two locale witnesses remain unchanged. Six
settled gold receive/surrender checkpoints capture the native GetSubValues row
objects used by widget_value_breakdown_list, not a second model built by a test.
An external fixed-point oracle checks descriptions, explicit base100, row sums,
native-input capacity and selected/preview percentages. Pixels remain unverified.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, ROUND_DOWN, InvalidOperation
import importlib.util
import json
from pathlib import Path
import re
import shutil

import prepare_badge_layout_probe as badge

base = badge.final.ordinary.base
NATIVE_LIST = base.GAME / "game/gui/shared/value_breakdown.gui"
NATIVE_RELATIVE = "gui/shared/value_breakdown.gui"
STAGES = {"p_clear1": (2, "p", False), "p_selected": (3, "p", True),
          "p_clear2": (7, "p", False), "r_clear1": (4, "r", False),
          "r_selected": (5, "r", True), "r_clear2": (8, "r", False)}
MAX_ROWS = 16
KEYS = ("tnt_interest_bd_base", "tnt_interest_bd_receiving_demand",
        "tnt_interest_bd_surrender_reserve", "tnt_interest_bd_rule_strength",
        "tnt_interest_bd_preview_receiving_demand", "tnt_interest_bd_preview_surrender_reserve")
FIELDS = ("total", "count", "scalar", "amount", "stock", "capacity", "income",
          "war_chest", "reserved", "expenses", "treasury", "strategy", "war", "builder")
D = Decimal


def helper_bindings():
    result = badge.helper_bindings()
    for path in (Path(__file__), Path(badge.__file__), Path(badge.window_inspector.__file__)):
        result[str(path)] = base.sha(path)
    return result


def localized_components(source, language):
    path = source / f"localization/{badge.LANGUAGES[language]}/tnt_l_{badge.LANGUAGES[language]}.yml"
    body = path.read_text(encoding="utf-8-sig")
    values = {}
    for key in KEYS:
        matches = re.findall(r'^ ' + re.escape(key) + r':\d+ "([^"\r\n]*)"\s*$', body, re.M)
        if len(matches) != 1 or not matches[0] or re.search(r"[\\\[\]|]", matches[0]):
            raise ValueError("One plain localized component is required: " + key)
        values[key] = matches[0]
    if len(set(values.values())) != len(values):
        raise ValueError("Component names must uniquely identify their semantics")
    return values


def phase(number):
    return f"EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('tnwqa_phase').GetValue,'(CFixedPoint){number}')"


def both(*conditions):
    result = conditions[0]
    for condition in conditions[1:]:
        result = f"And({result},{condition})"
    return result


def call(name, scopes=()):
    scope = "GuiScope.SetRoot(GetPlayer.MakeScope)"
    for key, expression, kind in scopes:
        scope += f".AddScope('{key}',MakeScope{kind}({expression}))"
    return f"GetScriptedGui('{name}').Execute({scope}.End)"


def states(name, condition, actions, seconds=1):
    """Reviewed timer pattern, directly on an existing widget: no layout child."""
    lines = [f"state = {{ name = {name} trigger_when = \"[{condition}]\" duration = {seconds} alpha = 1",
             f"on_finish = \"[PdxGuiWidget.TriggerAnimation(Select_CString({condition},'{name}_do','{name}_noop'))]\" }}",
             f"state = {{ name = {name}_do duration = 0 alpha = 1"]
    lines += [f'on_finish = "[{action}]"' for action in actions]
    return "\n".join(lines + ["}", f"state = {{ name = {name}_noop alpha = 1 }}"])


def parent(level):
    return "PdxGuiWidget" + ".AccessParent" * level


def name_is(widget, name):
    return f"EqualTo_string({widget}.GetName,'{name}')"


def once_replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Reviewed injection anchor changed: " + old[:120])
    return text.replace(old, new)


def assertion(label, condition):
    return (f'if = {{ limit = {{ {condition} }} debug_log = "TNGUI_TEST|PASS|{label}" }} '
            f'else = {{ debug_log = "TNGUI_TEST|FAIL|{label}" set_variable = {{ name = tnwqa_failed value = 1 }} }}\n')


def var_text(name, precision=3):
    return f"[GetPlayer.MakeScope.GetVariable('{name}').GetValue|{precision}]"


def root_control(stage, number, side, selected):
    prefix = "tnhqa_" + stage
    value_name = f"tnt_interest_gold_{side}_{'percent' if selected else 'preview_percent'}_value"
    condition = f"var:tnt_gold_{side} > 0" if selected else "NOT = { has_variable = tnt_gold_p } NOT = { has_variable = tnt_gold_r }"
    text = (f"{prefix}_root = {{ scope = character effect = {{ if = {{ limit = {{ var:tnwqa_phase = {number} "
            f"NOT = {{ has_variable = {prefix}_root_done }} }}\n"
            f"set_variable = {{ name = {prefix}_root_done value = 1 }}\n")
    text += assertion("hover_" + stage + "_native_context", "is_ai = no var:tnt_open = 1 exists = var:tnt_partner "
                      "scope:list_identity = yes scope:host_identity = yes scope:count > 0 "
                      f"scope:count <= {MAX_ROWS} " + condition)
    for key, value in (("total", "scope:total"), ("count", "scope:count"), ("scalar", value_name),
                       ("amount", "0"), ("stock", "var:tnt_partner.gold"),
                       ("capacity", "tnt_interest_gold_capacity_value")):
        text += f"set_variable = {{ name = {prefix}_{key} value = {value} }}\n"
    text += (f"if = {{ limit = {{ exists = var:tnt_gold_{side} }} "
             f"set_variable = {{ name = {prefix}_amount value = var:tnt_gold_{side} }} }}\n")
    for key, native in (("income", "yearly_character_income"), ("war_chest", "war_chest_gold_maximum"),
                        ("reserved", "reserved_gold_maximum"), ("expenses", "monthly_character_expenses")):
        text += f"set_variable = {{ name = {prefix}_{key} value = var:tnt_partner.{native} }}\n"
    for key, predicate in (("treasury", "has_treasury = yes"),
                           ("strategy", "OR = { ai_has_warlike_personality = yes ai_has_cautious_personality = yes ai_has_conqueror_personality = yes }"),
                           ("war", "is_at_war = yes"),
                           ("builder", "OR = { ai_has_economical_boom_personality = yes ai_has_pious_builder_personality = yes ai_should_focus_on_building_in_their_capital = yes }")):
        text += (f"set_variable = {{ name = {prefix}_{key} value = 0 }}\n"
                 f"if = {{ limit = {{ var:tnt_partner = {{ {predicate} }} }} set_variable = {{ name = {prefix}_{key} value = 1 }} }}\n")
    for field in FIELDS:
        text += f'debug_log = "TNH_INPUT|{stage}|{field}|{var_text(prefix + "_" + field)}|END"\n'
    return text + "} } }\n"


def row_control(stage, number, side, selected):
    prefix = "tnhqa_" + stage
    motive = ("receiving_demand" if side == "p" else "surrender_reserve")
    motive = "tnt_interest_bd_" + ("" if selected else "preview_") + motive
    text = f"{prefix}_row = {{ scope = character effect = {{ if = {{ limit = {{ var:tnwqa_phase = {number} }}\n"
    for index in range(MAX_ROWS):
        row = prefix + "_row_" + str(index)
        text += (f"if = {{ limit = {{ scope:index = {index} NOT = {{ has_variable = {row}_done }} }}\n"
                 f"set_variable = {{ name = {row}_done value = 1 }}\n"
                 f"set_variable = {{ name = {row}_value value = scope:row_value }}\n"
                 f"set_variable = {{ name = {row}_show value = 0 }}\n"
                 f"if = {{ limit = {{ scope:show = yes }} set_variable = {{ name = {row}_show value = 1 }} }}\n"
                 f"set_variable = {{ name = {row}_kind value = 0 }}\n")
        for flag, kind in (("is_base", 1), ("is_motive", 2), ("is_rule", 3)):
            text += f"if = {{ limit = {{ scope:{flag} = yes }} set_variable = {{ name = {row}_kind value = {kind} }} }}\n"
        text += (f'debug_log = "TNH_ROW|{stage}|{index}|{var_text(row + "_value")}|{var_text(row + "_show", 0)}|{var_text(row + "_kind", 0)}|END"\n'
                 f'debug_log = "TNH_NAME|{stage}|{index}|[GetVariableSystem.Get(\'{row}_name\')]|END"\n'
                 f'debug_log = "TNH_FORMAT|{stage}|{index}|[GetVariableSystem.Get(\'{row}_formatted\')]|END"\n'
                 "}\n")
    return text + "} } }\n", motive


def instrument_native_list(source):
    root_states, row_states, controls = [], [], []
    for stage, (number, side, selected) in STAGES.items():
        name = "tnt_interest_reason_rows" if selected else "tnt_interest_preview_reason_rows"
        host = "tnwqa_receive_tooltip_host" if side == "p" else "tnwqa_surrender_tooltip_host"
        root_identity, host_identity = name_is("PdxGuiWidget", name), name_is(parent(3), host)
        root_condition = both("GetPlayer.IsValid", phase(number), root_identity, host_identity)
        root_states.append(states("tnhqa_" + stage + "_root_observe", root_condition,
            [call("tnhqa_" + stage + "_root", (("total", "ValueBreakdown.GetFixedPointValue", "Value"),
              ("count", "IntToFixedPoint(GetDataModelSize(ValueBreakdown.GetSubValues))", "Value"),
              ("list_identity", root_identity, "Bool"), ("host_identity", host_identity, "Bool")))], 1))
        control, motive = row_control(stage, number, side, selected)
        controls.extend((root_control(stage, number, side, selected), control))
        # Actual vanilla hierarchy: item hbox -> model vbox -> margin vbox ->
        # named list widget -> tooltip body -> tooltip -> named host window.
        row_condition = both("GetPlayer.IsValid", phase(number), name_is(parent(3), name), name_is(parent(6), host))
        key = f"Concatenate('tnhqa_{stage}_row_',IntToString(PdxGuiWidget.GetIndexInDataModel))"
        row_states.append(states("tnhqa_" + stage + "_row_observe", row_condition,
            [f"GetVariableSystem.Set(Concatenate({key},'_name'),ValueBreakdown.GetName)",
             f"GetVariableSystem.Set(Concatenate({key},'_formatted'),ValueBreakdown.GetValue)",
             call("tnhqa_" + stage + "_row", (("index", "IntToFixedPoint(PdxGuiWidget.GetIndexInDataModel)", "Value"),
                  ("row_value", "ValueBreakdown.GetFixedPointValue", "Value"),
                  ("show", "ValueBreakdown.ShouldShowValue", "Bool"),
                  ("is_base", "EqualTo_string(ValueBreakdown.GetName,Localize('tnt_interest_bd_base'))", "Bool"),
                  ("is_motive", f"EqualTo_string(ValueBreakdown.GetName,Localize('{motive}'))", "Bool"),
                  ("is_rule", "EqualTo_string(ValueBreakdown.GetName,Localize('tnt_interest_bd_rule_strength'))", "Bool")))], 1))
    root_anchor = 'type widget_value_breakdown_list = widget {\n\t\tname = "values_grid"'
    row_anchor = 'name = "value_breakdown"\n\t\t\t\t\t\tlayoutpolicy_horizontal = expanding'
    source = once_replace(source, root_anchor, root_anchor + "\n" + "\n".join(root_states))
    # Limit the second anchor to the first type: other vanilla types use this name.
    first, remaining = source.split("\n\t# Used in a 'top level'", 1)
    first = once_replace(first, row_anchor, row_anchor + "\n" + "\n".join(row_states))
    return first + "\n\t# Used in a 'top level'" + remaining, "\n".join(controls)


def prepare(run, language="l_russian"):
    # Validate installed native inputs before the nested preparer creates files.
    run, native_inputs = base.configuration.validate_run(run, "reload_helper", "game_root")
    NATIVE_LIST.read_bytes()
    names = localized_components(base.SOURCE, language)
    badge.prepare(run, language)
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("reviewed_hover_timer", base.RELOAD_HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    controls_path = run / "probe" / badge.CONTROLS
    controls = controls_path.read_text(encoding="utf-8-sig")
    controls = once_replace(controls, "var:tnwqa_phase = 3 NOT = { has_variable = tnwqa_surrender_empty_ready_done }",
                            "var:tnwqa_phase = 7 NOT = { has_variable = tnwqa_surrender_empty_ready_done }")
    controls = once_replace(controls, "tnwqa_cycle_finish = { scope = character effect = { if = { limit = { var:tnwqa_phase = 5 }",
                            "tnwqa_cycle_finish = { scope = character effect = { if = { limit = { var:tnwqa_phase = 8 }")
    for side, host_name, selected_phase, restored_phase, next_command in (
            ("p", "receive", 3, 7, "tnwqa_surrender_empty_ready"),
            ("r", "surrender", 5, 8, "tnwqa_cycle_finish")):
        command = f"tnhqa_{side}_cleared"
        controls += (f"{command} = {{ scope = character effect = {{ if = {{ limit = {{ var:tnwqa_phase = {selected_phase} }} "
                     f"set_variable = {{ name = tnwqa_phase value = {restored_phase} }} }} }} }}\n")
        path = run / "probe" / f"gui/tnwqa_{host_name}_tooltip_host.gui"
        gui = path.read_text(encoding="utf-8-sig")
        gui = once_replace(gui, f"Or({phase(2 if side == 'p' else 4)},{phase(selected_phase)})",
                           f"Or(Or({phase(2 if side == 'p' else 4)},{phase(selected_phase)}),{phase(restored_phase)})")
        gui = once_replace(gui, '[' + call(next_command) + ']', '[' + call(command) + ']')
        timer = helper.state(f"tnhqa_{side}_restored_timer", both("GetPlayer.IsValid", phase(restored_phase)), [call(next_command)], 3)
        # Insert within the exact host window without modifying production children.
        closing = gui.rfind("}")
        gui = gui[:closing] + timer + "\n" + gui[closing:]
        base.write(path, gui)
    native = NATIVE_LIST.read_text(encoding="utf-8-sig")
    native_reference = run / "native-reference" / NATIVE_RELATIVE
    native_reference.parent.mkdir(parents=True)
    shutil.copy2(NATIVE_LIST, native_reference)
    instrumented, native_controls = instrument_native_list(native)
    base.write(run / "probe" / NATIVE_RELATIVE, instrumented)
    base.write(controls_path, controls + native_controls)
    plan["expected_labels"] += ["hover_" + stage + "_native_context" for stage in STAGES]
    plan.update(expected_count=len(plan["expected_labels"]), hover_content_cycle=True,
                hover_external_inputs=native_inputs,
                hover_components=names, hover_stages={key: list(value) for key, value in STAGES.items()},
                hover_helpers_sha256=helper_bindings(), hover_native_source=str(NATIVE_LIST),
                hover_native_source_sha256=base.sha(NATIVE_LIST), hover_max_rows=MAX_ROWS,
                hover_native_reference_sha256=base.sha(native_reference),
                probe_sha256=base.inventory(run / "probe"),
                hover_contract="Gold p/r; actual native rows; six settled checkpoints; independent raw-input fixed-point oracle.")
    plan["coverage_limits"] += ["Gold receive/surrender only; other currencies and advanced object tooltip contents are not claimed.",
        "Native row data proves content and arithmetic, not pixels, hover hitboxes, color, or badge coordinates.",
        "Only states are added to the native list/root item; no layout child, data model, rendered text or production formula is replaced.",
        "Absent base100 is a failure, never reconstructed as an implicit inspector contribution."]
    base.dump(run / "plan.json", plan)
    print(json.dumps({"run": str(run), "expected_assertions": plan["expected_count"], "content_checkpoints": len(STAGES), "status": plan["status"]}))


def freeze(run):
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    if plan.get("hover_content_cycle") is not True or plan.get("hover_helpers_sha256") != helper_bindings():
        raise ValueError("Hover content helper changed or wrong plan; prepare a fresh run")
    if plan["hover_native_source_sha256"] != base.sha(NATIVE_LIST):
        raise ValueError("Installed native breakdown source changed")
    if plan["hover_native_reference_sha256"] != base.sha(run / "native-reference" / NATIVE_RELATIVE):
        raise ValueError("Native reference snapshot changed")
    if localized_components(base.SOURCE, plan["language"]) != plan["hover_components"]:
        raise ValueError("Localized components changed")
    badge.freeze(run)


def number(text):
    # Native logs may use a locale decimal comma or grouping whitespace. Reject
    # all other strings rather than silently extracting a convenient substring.
    text = text.strip().replace("\u2212", "-").replace("\u00a0", "").replace("\u202f", "").replace(" ", "").replace(",", ".")
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        raise ValueError("Not an unambiguous native decimal: " + text)
    return D(text)


def fixed(value):
    return value.quantize(D(".001"), rounding=ROUND_DOWN)


def clamp(value, low, high):
    return max(D(low), min(D(high), value))


def expected_values(inputs, side, selected):
    """Independent scalar arithmetic on captured native quantities, Standard1.

    Each multiplication/division is quantized separately to native milli-units;
    no production script-value evaluator or AST interpreter supplies the oracle.
    """
    income = clamp(inputs["income"], 0, 25000)
    capacity = D(100) + income * 2
    if inputs["treasury"] == 0:
        capacity += clamp(inputs["war_chest"], 0, 25000) + clamp(inputs["reserved"], 0, 25000)
        if inputs["strategy"] == 1:
            capacity += clamp(inputs["war_chest"], 0, 25000)
        if inputs["war"] == 1:
            capacity += clamp(inputs["expenses"], 0, 2000) * 12
    if inputs["builder"] == 1:
        capacity += income
    capacity = clamp(capacity, 100, 100000)
    stock, amount = inputs["stock"], inputs["amount"]
    if not selected:
        if side == "p":
            total = D(0) if stock >= capacity * 2 else D(50) if stock >= capacity else D(100)
        else:
            total = D(25) if stock <= fixed(capacity / 4) else D(50) if stock <= capacity else D(100)
    elif side == "p":
        full = clamp(capacity - stock, 0, amount)
        tail = max(D(0), clamp(capacity * 2 - stock, 0, amount) - full)
        total = clamp(fixed(fixed((full + fixed(tail / 2)) * 100) / max(amount, D(".001"))), 0, 100)
    else:
        reserve = clamp(amount - max(stock - capacity, D(0)), 0, amount)
        critical = clamp(amount - max(stock - fixed(capacity * D(".25")), D(0)), 0, amount)
        weighted = amount + reserve + critical * 2
        total = clamp(fixed(fixed(amount * 100) / max(weighted, D(".001"))), 1, 100)
    return capacity, {1: D(100), 2: total - 100, 3: D(0)}, total


def validate_content(debug, components):
    issues, captured = [], {}
    begin, end = debug.find("TNGUI_TEST|BEGIN|production_window"), debug.find("TNGUI_TEST|END|production_window")
    records = [(match.start(), match[1], match[2]) for match in re.finditer(r"TNH_(INPUT|ROW|NAME|FORMAT)\|([^\r\n]*?)\|END", debug)]
    if debug.count("TNH_") != len(records):
        issues.append("Malformed or unknown hover-content records.")
    if not records or not all(begin >= 0 and begin < pos < end for pos, _, _ in records):
        issues.append("Missing content records or records outside the native cycle.")
    for _, kind, payload in records:
        if payload.split("|", 1)[0] not in STAGES:
            issues.append("Unknown content checkpoint: " + payload)
    for stage, (_, side, selected) in STAGES.items():
        local = [(kind, payload.split("|")) for _, kind, payload in records if payload.split("|", 1)[0] == stage]
        inputs, rows, names, formats = {}, {}, {}, {}
        try:
            for kind, fields in local:
                if kind == "INPUT":
                    if len(fields) != 3 or fields[1] not in FIELDS or fields[1] in inputs:
                        raise ValueError("missing/duplicate/unknown input shape")
                    inputs[fields[1]] = number(fields[2])
                elif kind == "ROW":
                    if len(fields) != 5 or fields[1] in rows:
                        raise ValueError("duplicate/malformed native row")
                    rows[fields[1]] = tuple(number(item) for item in fields[2:])
                else:
                    target = names if kind == "NAME" else formats
                    if len(fields) != 3 or fields[1] in target:
                        raise ValueError("duplicate/malformed row string")
                    target[fields[1]] = fields[2]
            if set(inputs) != set(FIELDS):
                raise ValueError("native input set is incomplete")
            count = inputs["count"]
            if count != int(count) or not 0 < count <= MAX_ROWS:
                raise ValueError("native model row count is outside the bounded contract")
            indexes = {str(index) for index in range(int(count))}
            if set(rows) != indexes or set(names) != indexes or set(formats) != indexes:
                raise ValueError("actual row/name/formatted records do not cover every model index exactly once")
            if any(inputs[key] not in (0, 1) for key in ("treasury", "strategy", "war", "builder")):
                raise ValueError("native capacity predicates are not booleans")
            if (inputs["amount"] > 0) != selected:
                raise ValueError("wrong actual production selection state")
            capacity, expected, total = expected_values(inputs, side, selected)
            if inputs["capacity"] != capacity:
                raise ValueError("native-input capacity oracle differs from production capacity")
            if inputs["total"] != total or inputs["scalar"] != total:
                raise ValueError("native root/production scalar differs from independent percentage oracle")
            motive = "tnt_interest_bd_" + ("" if selected else "preview_") + ("receiving_demand" if side == "p" else "surrender_reserve")
            expected_names = {1: components["tnt_interest_bd_base"], 2: components[motive], 3: components["tnt_interest_bd_rule_strength"]}
            observed_kinds = Counter()
            for index, (value, shown, row_kind) in rows.items():
                if row_kind not in expected or shown not in (0, 1):
                    raise ValueError("unknown description identity or invalid visibility flag")
                row_kind = int(row_kind)
                observed_kinds[row_kind] += 1
                if names[index] != expected_names[row_kind] or value != expected[row_kind]:
                    raise ValueError("localized row description or numeric contribution differs")
                if value != 0 and shown != 1:
                    raise ValueError("nonzero component is not shown by the native renderer")
                if shown:
                    plain = re.sub(r"#[A-Za-z_]+\s*|#!", "", formats[index]).strip()
                    plain = plain.removesuffix("%").strip()
                    formatted = number(plain)
                    # Native ValueBreakdown formats its own precision. Keep the
                    # exact original string; numeric drift >= one display unit fails.
                    normalized = plain.replace(",", ".")
                    decimals = len(normalized.rsplit(".", 1)[1]) if "." in normalized else 0
                    if abs(formatted - value) > D(1).scaleb(-decimals) / 2:
                        raise ValueError("formatted native row number does not represent its numeric contribution")
            required = {kind for kind, value in expected.items() if value != 0} | {1}
            if any(observed_kinds[kind] != 1 for kind in required) or any(count > 1 for count in observed_kinds.values()):
                raise ValueError("explicit base100 or nonzero component is missing/repeated")
            if sum((value for value, _, _ in rows.values()), D(0)) != total:
                raise ValueError("actual top-level component sum differs from the native total")
            captured[stage] = {"inputs": {key: str(value) for key, value in inputs.items()},
                               "rows": [{"index": index, "value": str(rows[index][0]), "shown": str(rows[index][1]),
                                         "kind": str(rows[index][2]), "name": names[index], "formatted": formats[index]} for index in sorted(indexes, key=int)]}
        except (ValueError, KeyError, InvalidOperation) as exc:
            issues.append(stage + ": " + str(exc))
    for side in ("p", "r"):
        first, last = captured.get(side + "_clear1"), captured.get(side + "_clear2")
        if first and last and first != last:
            issues.append(side + ": clear restored content/native inputs differ from the original clear state")
    return issues, captured


def inspect(run, diagnostic_review=None, window_diagnostic_review=None, currency_ui_diagnostic_review=None):
    result = badge.window_inspector.inspect(run, diagnostic_review, window_diagnostic_review, currency_ui_diagnostic_review)
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "frozen-manifest.json").read_text(encoding="utf-8"))
    issues = []
    for key in ("hover_content_cycle", "hover_components", "hover_stages", "hover_helpers_sha256",
                "hover_native_source_sha256", "hover_native_reference_sha256", "hover_max_rows", "localized_witnesses", "language", "expected_labels", "probe_sha256"):
        if manifest.get(key) != plan.get(key):
            issues.append("Frozen/plan hover contract mismatch: " + key)
    if not manifest.get("hover_content_cycle") or manifest.get("expected_count") != 23:
        issues.append("Expected exact23-assertion hover-content contract")
    if manifest.get("hover_helpers_sha256") != helper_bindings() or manifest.get("hover_native_source_sha256") != base.sha(NATIVE_LIST):
        issues.append("Bound helper or installed native list changed")
    if manifest.get("hover_native_reference_sha256") != base.sha(run / "native-reference" / NATIVE_RELATIVE):
        issues.append("Native reference snapshot changed")
    components = localized_components(run / "runtime", manifest["language"])
    if components != manifest.get("hover_components"):
        issues.append("Frozen component localization does not match the plan")
    settings = (run / "userdata/pdx_settings.txt").read_text(encoding="utf-8")
    if not re.search(r'"language"\s*=\s*\{[^}]*value\s*=\s*"' + re.escape(manifest["language"]) + '"', settings, re.S):
        issues.append("Stopped native profile no longer matches the declared language")
    debug = (run / "userdata/logs/debug.log").read_text(encoding="utf-8-sig")
    issues += badge.validate_localized_witnesses(debug, badge.localized_expectations(run / "runtime", manifest["language"]))
    content_issues, captured = validate_content(debug, components)
    issues += content_issues
    result["blockers"] += issues
    if result["blockers"]:
        result["status"] = "FAIL"
    result.update(classification="NATIVE_PRODUCTION_GOLD_HOVER_CONTENT_CYCLE", hover_content="PASS" if not content_issues else "FAIL",
                  captured_hover_content=captured, hover_content_inspector_sha256=base.sha(Path(__file__)),
                  native_breakdown_source_sha256=manifest["hover_native_source_sha256"])
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
            parser.error("--output is required for an immutable report")
        result = inspect(run, args.diagnostic_review, args.window_diagnostic_review, args.currency_ui_diagnostic_review)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(json.dumps({key: result[key] for key in ("status", "pass_count", "expected_count", "hover_content", "blockers")}))
