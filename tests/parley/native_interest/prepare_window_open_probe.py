"""Isolated real production-window open diagnostic. Never launch the engine.

The only production GUI instrumentation is one extra _show callback and two
transparent, window-local timer observers. All real rows, layouts, bindings and
normal tnt_open_window_effect initialization remain present and untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

import prepare_interest_probe as base

WINDOW = "gui/tnt_diplomacy_window.gui"


def production_gold_tooltip_instance(source):
    """Extract the first actual gold receiving tooltip instance verbatim."""
    match = re.search(r"\btnt_interest_tooltip\s*=\s*\{", source)
    if not match:
        raise ValueError("Production tooltip instance missing")
    depth, quoted, escaped, comment = 0, False, False, False
    for index in range(source.index("{", match.start()), len(source)):
        char = source[index]
        if comment:
            comment = char != "\n"
        elif quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == "#":
            comment = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                instance = source[match.start():index + 1]
                if "tnt_interest_gold_p_percent_value" not in instance or "tnt_interest_gold_capacity_value" not in instance:
                    raise ValueError("First production tooltip is no longer the expected gold receiving instance")
                return instance
    raise ValueError("Production tooltip instance has unbalanced braces")


def prepare(run, preset, tooltip_flow_fix=False, materialize_tooltip=False):
    run, external_inputs = base.configuration.validate_run(run, "reload_helper")
    run.mkdir(parents=True, exist_ok=False)
    probe = run / "probe"
    source_hashes = base.inventory(base.SOURCE)
    spec = importlib.util.spec_from_file_location("reviewed_gui_timer_helper", base.RELOAD_HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    call = lambda name: f"GetScriptedGui('{name}').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)"
    flag = lambda name: f"GetPlayer.MakeScope.GetVariable('{name}').IsSet"
    phase = lambda n: f"EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('tnwqa_phase').GetValue,'(CFixedPoint){n}')"
    labels = []

    def assertion(label, condition):
        labels.append(label)
        return (f'if = {{ limit = {{ {condition} }} debug_log = "TNGUI_TEST|PASS|{label}" }} '
                f'else = {{ debug_log = "TNGUI_TEST|FAIL|{label}" set_variable = {{ name = tnwqa_failed value = 1 }} }}\n')

    start = """on_game_start_after_lobby = { on_actions = { tnwqa_start } }
tnwqa_start = { effect = { every_player = {
 if = { limit = { NOT = { has_variable = tnwqa_initialized } }
  set_variable = { name = tnwqa_initialized value = 1 }
  set_variable = { name = tnwqa_phase value = 0 }
  debug_log = "TNGUI_TEST|BEGIN|production_window"
 }
} } }
"""
    controls = "tnwqa_open = { scope = character effect = {\nif = { limit = { var:tnwqa_phase = 0 }\n"
    controls += "set_variable = { name = tnwqa_phase value = 1 }\nsave_scope_as = actor\ntitle:e_byzantium.holder = { save_scope_as = recipient }\n"
    controls += assertion("native_open_participants", "is_ai = no exists = scope:recipient scope:recipient = { is_ai = yes is_alive = yes }")
    controls += 'debug_log = "TNGUI_PHASE|BEFORE|production_open_effect"\ntnt_open_window_effect = yes\ndebug_log = "TNGUI_PHASE|AFTER|production_open_effect"\n'
    controls += assertion("production_numeric_open_state", "var:tnt_open = 1 exists = var:tnt_partner var:tnt_partner = scope:recipient")
    controls += "} } }\n"
    controls += "tnwqa_observe_show = { scope = character effect = {\nif = { limit = { NOT = { has_variable = tnwqa_show_seen } var:tnwqa_phase = 1 }\n"
    controls += "set_variable = { name = tnwqa_show_seen value = 1 }\n"
    controls += assertion("production_window_show_callback", "var:tnt_open = 1 exists = var:tnt_partner var:tnt_partner = { is_alive = yes }")
    controls += "} } }\n"
    for seconds in (3, 15):
        controls += f"tnwqa_observe_{seconds}s = {{ scope = character effect = {{\nif = {{ limit = {{ has_variable = tnwqa_show_seen NOT = {{ has_variable = tnwqa_seen_{seconds}s }} }}\n"
        controls += f"set_variable = {{ name = tnwqa_seen_{seconds}s value = 1 }}\n"
        controls += assertion(f"production_window_survives_{seconds}s", "var:tnt_open = 1 exists = var:tnt_partner var:tnt_partner = { is_alive = yes }")
        if seconds == 15:
            controls += assertion("production_window_no_prior_failure", "has_variable = tnwqa_seen_3s NOT = { has_variable = tnwqa_failed }")
            if materialize_tooltip:
                controls += 'debug_log = "TNGUI_PHASE|BEFORE|production_tooltip_materialization"\nset_variable = { name = tnwqa_phase value = 2 }\n'
            else:
                controls += 'set_variable = { name = tnwqa_phase value = 2 }\ndebug_log = "TNGUI_TEST|END|production_window"\n'
        controls += "} } }\n"
    if materialize_tooltip:
        controls += "tnwqa_tooltip_show = { scope = character effect = { if = { limit = { var:tnwqa_phase = 2 NOT = { has_variable = tnwqa_tooltip_seen } }\nset_variable = { name = tnwqa_tooltip_seen value = 1 }\n"
        controls += assertion("production_tooltip_host_show", "var:tnt_open = 1 NOT = { has_variable = tnt_gold_p } exists = var:tnt_partner")
        controls += "} } }\n"
        controls += "tnwqa_tooltip_survived = { scope = character effect = { if = { limit = { var:tnwqa_phase = 2 has_variable = tnwqa_tooltip_seen }\n"
        controls += assertion("production_tooltip_survives_5s", "var:tnt_open = 1 NOT = { has_variable = tnt_gold_p } exists = var:tnt_partner")
        controls += assertion("production_tooltip_no_prior_failure", "NOT = { has_variable = tnwqa_failed }")
        controls += 'set_variable = { name = tnwqa_phase value = 3 }\ndebug_log = "TNGUI_TEST|END|production_window"\n} } }\n'
    opener = helper.state("tnwqa_delayed_open", helper.both("GetPlayer.IsValid", flag("tnwqa_initialized"), phase(0)), [call("tnwqa_open")], 3)
    controller = 'window = { name = tnwqa_driver size = { 1 1 } alwaystransparent = yes\n' + opener + '\n}\n'
    window = (base.SOURCE / WINDOW).read_text(encoding="utf-8-sig")
    original_callback = 'on_start = "[TntExec(\'tnt_refresh_lists\')]"'
    if window.count(original_callback) != 1:
        raise ValueError("Expected exactly one unchanged production _show refresh callback")
    window = window.replace(original_callback, original_callback + '\n\t\ton_start = "[' + call("tnwqa_observe_show") + ']"')
    observers = ""
    for seconds in (3, 15):
        condition = helper.both("GetPlayer.IsValid", flag("tnwqa_show_seen"), phase(1),
                                "GreaterThan_CFixedPoint(GetPlayer.MakeScope.Var('tnt_open').GetValue,'(CFixedPoint)0')",
                                f"Not({flag('tnwqa_seen_' + str(seconds) + 's')})")
        observers += helper.state("tnwqa_window_alive_" + str(seconds), condition,
                                  [call("tnwqa_observe_" + str(seconds) + "s")], seconds) + "\n"
    window = helper.inject_window(window, "tnt_diplomacy_window", observers).replace(
        "# TEST ONLY native reload worker", "# TEST ONLY production-window lifetime observers; no row/layout replacement")
    files = {"common/on_action/tnwqa_start.txt": start,
             "common/scripted_guis/tnwqa_controls.txt": controls,
             "gui/tnwqa_driver.gui": controller,
             "gui/scripted_widgets/tnwqa_driver.txt": "gui/tnwqa_driver.gui = tnwqa_driver\n",
             WINDOW: window}
    if materialize_tooltip:
        # Separate scenario: this is the real tooltip type and the same gold
        # bindings, instantiated visibly only after ordinary-window survival.
        # It is not mouse-hover proof, and never alters the ordinary baseline.
        visible = helper.both("GetPlayer.IsValid", phase(2))
        production_tooltip = production_gold_tooltip_instance((base.SOURCE / WINDOW).read_text(encoding="utf-8-sig"))
        tooltip = ('window = { name = tnwqa_tooltip_host layer = top size = { 500 700 } '
                   'parentanchor = center alwaystransparent = no visible = "[' + visible + ']"\n'
                   'state = { name = _show on_start = "[' + call("tnwqa_tooltip_show") + ']" }\n'
                   + production_tooltip + '\n')
        tooltip += helper.state("tnwqa_tooltip_alive", helper.both(visible, flag("tnwqa_tooltip_seen")),
                                [call("tnwqa_tooltip_survived")], 5) + '\n}\n'
        files["gui/tnwqa_tooltip_host.gui"] = tooltip
        files["gui/scripted_widgets/tnwqa_tooltip_host.txt"] = "gui/tnwqa_tooltip_host.gui = tnwqa_tooltip_host\n"
    if tooltip_flow_fix:
        # Isolated candidate only: do not edit authoring bytes. Both named
        # children are immediately inside the production tooltip flowcontainer.
        types_path = "gui/tnt_types.gui"
        types = (base.SOURCE / types_path).read_text(encoding="utf-8-sig")
        for name in ("tnt_interest_points", "tnt_interest_capacity"):
            token = f'vbox = {{\n\t\t\t\tname = "{name}"'
            replacement = f'flowcontainer = {{\n\t\t\t\tdirection = vertical\n\t\t\t\tname = "{name}"'
            if types.count(token) != 1:
                raise ValueError("Expected exactly one original tooltip vbox " + name)
            types = types.replace(token, replacement)
        files[types_path] = types
    for relative, content in files.items():
        if tooltip_flow_fix and relative == "gui/tnt_types.gui":
            # Preserve all original bytes, including BOM/newline policy, outside
            # the two candidate replacements so the A/B remains minimal.
            raw = (base.SOURCE / relative).read_bytes()
            newline = b"\r\n" if b"\r\n" in raw else b"\n"
            for name in ("tnt_interest_points", "tnt_interest_capacity"):
                token = b"vbox = {" + newline + b'\t\t\t\tname = "' + name.encode() + b'"'
                replacement = b"flowcontainer = {" + newline + b"\t\t\t\tdirection = vertical" + newline + b'\t\t\t\tname = "' + name.encode() + b'"'
                if raw.count(token) != 1:
                    raise ValueError("Exact native encoding candidate anchor missing: " + name)
                raw = raw.replace(token, replacement)
            target = probe / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        else:
            base.write(probe / relative, content)
    plan = {"status": "PLAN_ONLY_RUNTIME_NOT_FROZEN", "preset": preset,
            "runtime_source": str(base.SOURCE), "runtime_source_at_plan_sha256": source_hashes,
            "kind": "PRODUCTION_WINDOW_OPEN_CRASH_DIAGNOSTIC", "marker_prefix": "TNGUI_TEST",
            "language": "l_russian", "isolated_tooltip_flow_fix": tooltip_flow_fix,
            "forced_tooltip_materialization": materialize_tooltip,
            "tooltip_materialization_contract": {
                "selection": "EMPTY: production opener leaves tnt_gold_p absent; fixture never writes it",
                "instance": "First actual production gold receiving tooltip instance, extracted verbatim",
                "instance_sha256": hashlib.sha256(production_tooltip.encode("utf-8")).hexdigest(),
                "binding": "Exact production GetPlayer/TntBreakdown percent and capacity scopes",
                "host": "Additive visible native window after ordinary production window survives15s",
                "not_proven": "Actual mouse hover/popup positioning or user campaign identity"
            } if materialize_tooltip else None,
            "ai_enabled": True, "expected_labels": labels, "expected_count": len(labels),
            "probe_sha256": base.inventory(probe),
            "helper": str(base.RELOAD_HELPER), "helper_sha256": base.sha(base.RELOAD_HELPER),
            "external_inputs": external_inputs, "configuration_sha256": base.sha(Path(base.configuration.__file__)),
            "instrumentation": {"production_window": WINDOW,
                "source_sha256": source_hashes[WINDOW], "instrumented_sha256": base.sha(probe / WINDOW),
                "changes": ["One additional production _show on_start callback after the unchanged tnt_refresh_lists.",
                            "Two transparent child timer observers within the real production window, at3s and15s."]},
            "coverage_limits": ["Native NOT_RUN until root launches this isolated profile.",
                "Reproduces the production opening effect and real window instantiation, not mouse interaction menu selection.",
                "No value mocks, synthetic object-rich draft, direct quote loops, save/load overlay or production-row suppression.",
                "Native survival is not visual layout/hover acceptance or exact user-campaign reproduction.",
                "Do not reuse currency-ledger inspector: this probe deliberately has no save/reload requirement."]}
    base.dump(run / "plan.json", plan)
    print(json.dumps({"status": plan["status"], "run": str(run), "expected_assertions": len(labels)}))


def freeze(run):
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    if base.inventory(base.SOURCE) != plan["runtime_source_at_plan_sha256"]:
        raise ValueError("Production changed after plan; re-plan in a fresh run rather than overwrite newer GUI bytes")
    base.freeze(run)
    # The common full-runtime freezer sets English for its ledger probes. This
    # separate crash reproduction deliberately uses the user's Russian locale.
    settings_path = run / "userdata/pdx_settings.txt"
    settings = settings_path.read_text(encoding="utf-8")
    settings, count = re.subn(r'("language"=\{.*?value=)"[^"]+"', r'\1"l_russian"', settings, flags=re.S)
    if count != 1:
        raise ValueError("Expected exactly one isolated profile locale")
    settings_path.write_text(settings, encoding="utf-8")
    manifest_path = run / "frozen-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(language="l_russian", prepared_settings_sha256=base.sha(settings_path),
                    preparer_sha256=base.sha(Path(__file__)))
    base.dump(manifest_path, manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--preset", choices=base.PRESETS, default="standard")
    parser.add_argument("--stage", choices=("plan", "freeze"), default="plan")
    parser.add_argument("--tooltip-flow-fix", action="store_true", help="Candidate-only override: two tooltip vboxes become vertical flowcontainers.")
    parser.add_argument("--materialize-tooltip", action="store_true", help="Separate second stage: instantiate the real gold-interest tooltip after ordinary-window15s survival.")
    base.add_path_arguments(parser)
    args = parser.parse_args()
    base.configure_paths(args)
    if not re.fullmatch("[a-z0-9_-]+", args.run_name):
        parser.error("Use a lower-case isolated run name")
    run = base.EVIDENCE / args.run_name
    prepare(run, args.preset, args.tooltip_flow_fix, args.materialize_tooltip) if args.stage == "plan" else freeze(run)
