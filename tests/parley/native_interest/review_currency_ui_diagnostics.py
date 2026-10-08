"""Narrow read-only review: exactly two historical interaction-discovery records
and two startup warnings for this probe's GUI-supplied boolean scope.

No original logs/reports are rewritten. The older reviewer is rerun in full;
only its exact count/multiset/absent-court objections are eligible for replacement
by the stricter four-record and fixture-source checks below. All other objections,
including any native FAIL, remain blocking. This never accepts visual/hover UI.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import prepare_currency_ui_probe as fixture
import review_window_diagnostics as window


CLASSIFICATION = "EXACT_CURRENCY_UI_STARTUP_4_DYNAMIC_BOOL_RECORDS"
WARNING = ("[E][jomini_effect.cpp:1162]: Event target 'observed' is used but is never set. "
           "Setting it in an unused scripted trigger or effect does not count")
EXPECTED_COUNT = 206
TEXT_SUFFIXES = {".txt", ".gui", ".yml", ".mod", ".asset", ".gfx"}


def expected_calls():
    def both(values):
        values = iter(values)
        result = next(values)
        for value in values:
            result = f"And({result},{value})"
        return result

    valid = lambda name: f"GetScriptedGui('{name}').IsValid(GuiScope.SetRoot(GetPlayer.MakeScope).End)"
    calls = {"tnuq_initial": "IsGamePaused", "tnuq_bool_true": "IsGamePaused", "tnuq_bool_false": "Not(IsGamePaused)"}
    for currency in fixture.CURRENCIES:
        unlocked = both(valid(f"tnt_{currency}_{side}_{writer}") for side in ("p", "r") for writer in fixture.WRITERS)
        for side, other in (("p", "r"), ("r", "p")):
            for suffix in ("unlocked", "zero", "clear"):
                calls[f"tnuq_{currency}_{side}_{suffix}"] = unlocked
            calls[f"tnuq_{currency}_{side}_disabled"] = both(f"Not({valid(f'tnt_{currency}_{other}_{writer}')})" for writer in fixture.WRITERS)
        calls[f"tnuq_legacy_{currency}_send"] = f"Not({valid('tnt_send_offer')})"
        calls[f"tnuq_legacy_{currency}_clear"] = both(valid(f"tnt_{currency}_{side}_add") for side in ("p", "r"))
    calls["tnuq_finish_clear"] = both(valid(f"tnt_gold_{side}_add") for side in ("p", "r"))
    return calls


def script_blocks(text):
    """Extract top-level blocks without interpreting nested script or comments."""
    tokens = re.compile(r'"(?:\\.|[^"\\])*"|#[^\n]*|[{}]')
    blocks, end = {}, 0
    for match in re.finditer(r"(?m)^(\w+)\s*=\s*\{", text):
        if match.start() < end:
            continue
        depth = 0
        for token in tokens.finditer(text, text.index("{", match.start())):
            if token.group() == "{":
                depth += 1
            elif token.group() == "}":
                depth -= 1
                if depth == 0:
                    end = token.end()
                    if match[1] in blocks:
                        raise ValueError("Duplicate scripted GUI definition: " + match[1])
                    blocks[match[1]] = text[match.start():end]
                    break
        else:
            raise ValueError("Unclosed scripted GUI block")
    return blocks


def validate_fixture(runtime_texts, probe_texts, manifest, plan):
    problems = []
    for relative, text in runtime_texts.items():
        # Existing production prose uses the English word "observed" in
        # comments. Comments cannot declare or supply an engine event target.
        text = re.sub(r'"(?:\\.|[^"\\])*"|#[^\n]*',
                      lambda match: "" if match[0].startswith("#") else match[0], text)
        if re.search(r"\bobserved\b", text):
            problems.append("Production contains the reviewed event-target token: " + relative)
    control_path = "common/scripted_guis/tnwqa_controls.txt"
    controls = probe_texts.get(control_path, "")
    blocks = script_blocks(controls)
    consumers = {name for name, body in blocks.items() if re.search(r"\bobserved\b", body)}
    calls = expected_calls()
    if consumers != set(calls):
        problems.append("Boolean consumer set is not the exact 34 reviewed scripted-GUI callbacks.")
    for name in consumers:
        body = blocks[name]
        if (len(re.findall(r"\bobserved\b", body)) != len(re.findall(r"scope:observed = (?:yes|no)\b", body))
                or "exists = scope:observed" in body):
            problems.append("Boolean consumer has a noncomparison use or dummy assignment: " + name)
        expected = ("scope:observed = no NOT = { scope:observed = yes }" if name == "tnuq_bool_false" else
                    "scope:observed = yes NOT = { scope:observed = no }" if name == "tnuq_bool_true" else "scope:observed = yes")
        if expected not in body:
            problems.append("Boolean polarity contract changed: " + name)
    actual = Counter()
    for relative, text in probe_texts.items():
        if not re.search(r"\bobserved\b", text):
            continue
        if relative == control_path:
            if len(re.findall(r"\bobserved\b", text)) != sum(len(re.findall(r"\bobserved\b", blocks[name])) for name in consumers):
                problems.append("Boolean token outside reviewed consumer definitions.")
            continue
        if not re.fullmatch(r"gui/tnuq_(?:driver|(?:gold|prestige|piety)_[pr]_host)\.gui", relative):
            problems.append("Unexpected probe file uses the observed token: " + relative)
            continue
        for line in text.splitlines():
            if re.search(r"\bobserved\b", line):
                matched = []
                for name, expression in calls.items():
                    expected = f'on_finish = "[GetScriptedGui(\'{name}\').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).AddScope(\'observed\',MakeScopeBool({expression})).End)]"'
                    if line.strip() == expected:
                        matched.append(name)
                if len(matched) != 1:
                    problems.append("Unexpected dynamic boolean expression or call: " + relative)
                else:
                    actual[matched[0]] += 1
    if actual != Counter({name: 1 for name in calls}):
        problems.append("Every reviewed boolean consumer must have exactly one matching dynamic AddScope producer.")
    # A second, plain Execute could otherwise invoke a reviewed callback without
    # its boolean. Inspect all GUI callers, not only lines containing observed.
    for name in calls:
        count = sum(len(re.findall(re.escape(f"GetScriptedGui('{name}').Execute("), text))
                    for relative, text in probe_texts.items() if relative.endswith(".gui"))
        if count != 1:
            problems.append("Missing or additional callback invocation: " + name)
    required = {"gui_bool_true_control", "gui_bool_false_control", "preview_fixture_native_preconditions",
                "global_clear_restores", "currency_ui_cycle_no_prior_failure"} | window.OPEN_LABELS
    for record, generator in ((manifest, fixture.ordinary), (plan, fixture)):
        # The shared ordinary.freeze deliberately records its own hash in
        # frozen-manifest; the plan retains the currency generator hash. Bind
        # both exactly instead of pretending those two fields have one meaning.
        if (record.get("currency_ui_preview_lock_cycle") is not True
                or record.get("expected_count") != EXPECTED_COUNT
                or not required <= set(record.get("expected_labels", []))
                or Path(record.get("preparer", "")).resolve() != Path(fixture.__file__).resolve()
                or record.get("preparer_sha256") != window.court.sha(Path(generator.__file__))):
            problems.append("Fixture plan/manifest is not the current reviewed 206-assertion generator contract.")
    return problems


def validate_startup(error, debug):
    items = window.court.records(error)
    warnings = [item for item in items if window.court.normalize(item) == WARNING]
    remaining = [item for item in items if window.court.normalize(item) != WARNING]
    begins = window.court.marker_times(debug, "TNGUI_TEST|BEGIN|production_window")
    discovery_times = window.court.timestamps(remaining)
    phase = {"court_times": [], "discovery_times": discovery_times, "begin_times": begins,
             "record_count": len(items), "phase": "STARTUP_BEFORE_PRODUCTION_WINDOW_FIXTURE"}
    problems = []
    if Counter(map(window.court.normalize, remaining)) != window.DISCOVERY or len(discovery_times) != 1:
        problems.append("Requires exactly the two reviewed discovery records at one startup time; court/GUI/other messages are forbidden.")
    times = window.court.timestamps(warnings)
    if len(items) != 4 or len(warnings) != 2 or len(times) != 2:
        problems.append("Requires exactly two distinct-time observed warnings plus the exact discovery pair, four records total.")
    if (len(phase["begin_times"]) != 1 or len(phase["discovery_times"]) != 1 or len(times) != 2
            or not phase["discovery_times"][0] <= times[0] < times[1] < phase["begin_times"][0]):
        problems.append("Both dynamic-scope static warnings must precede the unique native BEGIN, after discovery starts.")
    return phase | {"record_count": len(items), "dynamic_bool_warning_times": times,
                    "dynamic_bool_warning_count": len(warnings)}, problems


def review(off_control, window_control, target):
    target = Path(target).resolve()
    base = window.review(off_control, window_control, target)
    error = (target / "userdata/logs/error.log").read_text(encoding="utf-8-sig")
    debug = (target / "userdata/logs/debug.log").read_text(encoding="utf-8-sig")
    manifest = json.loads((target / "frozen-manifest.json").read_text(encoding="utf-8-sig"))
    plan = json.loads((target / "plan.json").read_text(encoding="utf-8-sig"))
    expected_rejections = [str(target) + ": Requires exactly the reviewed Russian 60-record startup multiset; new/missing/GUI diagnostics are forbidden.",
                           "Target is not the timestamp-stripped exact Russian window-control diagnostic multiset.",
                           str(target) + ": Requires one court burst and one earlier discovery pair, strictly before the unique fixture BEGIN."]
    # All original source, process, scene, executable, profile, control and
    # native-success checks run unchanged. No arbitrary diagnostic is removed.
    problems = [issue for issue in base["problems"] if issue not in expected_rejections]
    if Counter(issue for issue in base["problems"] if issue in expected_rejections) != Counter(expected_rejections):
        problems.append("Older reviewer did not return exactly the anticipated count/multiset/absent-court objections.")
    phase, issues = validate_startup(error, debug)
    problems += issues
    texts = {}
    for tree in ("runtime", "probe"):
        texts[tree] = {path.relative_to(target / tree).as_posix(): path.read_text(encoding="utf-8-sig")
                       for path in (target / tree).rglob("*") if path.is_file() and path.suffix in TEXT_SUFFIXES}
    problems += validate_fixture(texts["runtime"], texts["probe"], manifest, plan)
    bound = {item["path"]: item["sha256"] for item in base["bound_files"]}
    for path in (Path(window.__file__), Path(fixture.__file__), Path(fixture.ordinary.__file__), Path(fixture.ordinary.base.RELOAD_HELPER)):
        bound[str(path.resolve())] = window.court.sha(path)
    return {"schema_version": 1, "classification": CLASSIFICATION,
            "status": "SCOPED_REVIEW_PASS" if not problems else "SCOPED_REVIEW_FAIL",
            "recorded_utc": datetime.now(timezone.utc).isoformat(),
            "off_control_run": base["off_control_run"], "window_control_run": base["window_control_run"], "target_run": str(target),
            "generator_sha256": window.court.sha(Path(__file__)), "window_reviewer_sha256": window.court.sha(Path(window.__file__)),
            "bound_files": [{"path": path, "sha256": value} for path, value in sorted(bound.items())],
            "target_source_sha256": base["target_source_sha256"], "control_phase": base["control_phase"], "target_phase": phase,
            "base_review_expected_diagnostic_rejections": expected_rejections,
            "accepted_diagnostics": window.court.records(error) if not problems else [], "problems": problems,
            "current_source_acceptance": "NOT_ASSESSED_HISTORICAL_FROZEN_SOURCE_ONLY",
            "visual_status": "NOT_VERIFIED", "physical_hover_status": "NOT_VERIFIED",
            "limits": ["Historical controls retain the exact 60-record Russian startup classification; no historical evidence is edited."] + base["limits"][1:] + ["The target must contain exactly four records: the historical discovery pair plus the two exact dynamic-scope warnings. No court or other engine diagnostics are accepted by this classifier.",
                "Additionally accepts exactly two pre-fixture static warnings for the test-only dynamic observed scope, with exact 34 producer/consumer pairs and true/false native polarity controls.",
                "No script-side dummy assignment, production observed usage, other event target, GUI warning, native assertion failure or crash is covered.",
                "The 206-assertion fixture and all frozen inventories must match the bound generator; consumers must rerun this entire review."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("off-control", "window-control", "target", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    fixture.ordinary.base.add_path_arguments(parser)
    args = parser.parse_args()
    fixture.ordinary.base.configure_paths(args)
    result = review(args.off_control, args.window_control, args.target)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "count": len(result["accepted_diagnostics"]), "problems": result["problems"]}))
