"""Short native badge-layout smoke in English or Russian; never launch CK3.

Reuses the 17-assertion real-window/two-tooltip cycle unchanged, adding two
engine-localized string witnesses. Those witnesses prove loaded localized copy,
not glyph color, row position, clipping or a physical tooltip hover. Historical
helpers remain byte-for-byte unchanged. The root owns freeze/launch/stop.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

import prepare_final_window_probe as final
import inspect_window_open_probe as window_inspector


LANGUAGES = {"l_english": "english", "l_russian": "russian"}
WITNESS_KEYS = ("tnt_interest_bd_base", "tnt_interest_preview_currency")
CONTROLS = "common/scripted_guis/tnwqa_controls.txt"


def helper_bindings():
    base = final.ordinary.base
    paths = (Path(__file__), Path(final.__file__), Path(final.ordinary.__file__), Path(base.__file__),
             Path(base.configuration.__file__), base.RELOAD_HELPER)
    return {str(path): base.sha(path) for path in paths}


def localized_expectations(source, language):
    if language not in LANGUAGES:
        raise ValueError("Only the reviewed English/Russian language pair is supported")
    name = LANGUAGES[language]
    path = source / f"localization/{name}/tnt_l_{name}.yml"
    body = path.read_text(encoding="utf-8-sig")
    result = {}
    for key in WITNESS_KEYS:
        values = re.findall(r"^ " + re.escape(key) + r':\d+ "([^"\r\n]*)"\s*$', body, re.M)
        if len(values) != 1 or not values[0] or re.search(r"[\\\[\]|]", values[0]):
            raise ValueError("Localized witness must be one plain, nonempty source string: " + key)
        result[key] = values[0]
    return result


def language_settings(settings, language):
    if language not in LANGUAGES:
        raise ValueError("Unsupported native language")
    settings, count = re.subn(r'("language"=\{.*?value=)"[^"]+"',
                              lambda match: match[1] + '"' + language + '"', settings, flags=re.S)
    if count != 1:
        raise ValueError("Expected exactly one isolated profile language field")
    return settings


def prepare(run, language="l_russian"):
    base = final.ordinary.base
    expected = localized_expectations(base.SOURCE, language)
    final.prepare(run)
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    if plan["expected_count"] != 17:
        raise ValueError("Reviewed short cycle no longer has exactly 17 assertions")
    path = run / "probe" / CONTROLS
    controls = path.read_text(encoding="utf-8-sig")
    anchor = 'debug_log = "TNGUI_PHASE|BEFORE|production_tooltip_cycle"'
    if controls.count(anchor) != 1:
        raise ValueError("Expected one guarded post-window/pre-tooltip witness point")
    logs = "\n".join(f'debug_log = "TNGUI_LOCALIZED|{key}|[Localize(\'{key}\')]|END"' for key in WITNESS_KEYS)
    base.write(path, controls.replace(anchor, logs + "\n" + anchor))
    plan.update(language=language, badge_layout_language_cycle=True,
                localized_witnesses=expected, localized_witness_count=2,
                layout_probe_helpers_sha256=helper_bindings(),
                preparer=str(Path(__file__)), preparer_sha256=base.sha(Path(__file__)),
                probe_sha256=base.inventory(run / "probe"))
    plan["coverage_limits"] += ["Two native Localize witnesses are checked against the selected locale's frozen source; settings alone are not language evidence.",
                                "Bare badge text/fontcolor and 64px layout require separate visual confirmation; hidden native survival never certifies pixels."]
    base.dump(run / "plan.json", plan)
    print(json.dumps({"run": str(run), "status": plan["status"], "expected_assertions": 17,
                      "localized_witnesses": 2, "language": language}))


def freeze(run):
    base = final.ordinary.base
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    if plan.get("badge_layout_language_cycle") is not True:
        raise ValueError("Not a badge-layout language probe")
    if base.inventory(base.SOURCE) != plan["runtime_source_at_plan_sha256"]:
        raise ValueError("Production changed after plan; prepare a fresh run")
    if helper_bindings() != plan["layout_probe_helpers_sha256"]:
        raise ValueError("A bound helper changed after plan; prepare a fresh run")
    if localized_expectations(base.SOURCE, plan["language"]) != plan["localized_witnesses"]:
        raise ValueError("Localized witness contract changed")
    # Shared freezer snapshots full runtime and probe, emits exact-process guards,
    # and creates only this disposable userdir. Do not call the Russian-only
    # ordinary.freeze or alter historical helper bytes to select English.
    base.freeze(run)
    settings_path = run / "userdata/pdx_settings.txt"
    settings_path.write_text(language_settings(settings_path.read_text(encoding="utf-8"), plan["language"]), encoding="utf-8")
    manifest_path = run / "frozen-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(language=plan["language"], prepared_settings_sha256=base.sha(settings_path),
                    freezer=str(Path(__file__)), freezer_sha256=base.sha(Path(__file__)))
    base.dump(manifest_path, manifest)


def validate_localized_witnesses(debug, expected):
    found = re.findall(r"TNGUI_LOCALIZED\|([^|\r\n]+)\|([^|\r\n]*)\|END", debug)
    if (Counter(found) != Counter(expected.items()) or debug.count("TNGUI_LOCALIZED|") != len(expected)):
        return ["Native localized witnesses are missing, repeated, unresolved or different from the frozen locale strings."]
    begin = debug.find("TNGUI_TEST|BEGIN|production_window")
    end = debug.find("TNGUI_TEST|END|production_window")
    positions = [match.start() for match in re.finditer("TNGUI_LOCALIZED\\|", debug)]
    if not all(begin >= 0 and begin < position < end for position in positions):
        return ["Localized witnesses are outside the actual native window-cycle boundaries."]
    return []


def inspect(run, diagnostic_review=None, window_diagnostic_review=None):
    base = final.ordinary.base
    result = window_inspector.inspect(run, diagnostic_review, window_diagnostic_review)
    manifest = json.loads((run / "frozen-manifest.json").read_text(encoding="utf-8"))
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    issues = []
    if (manifest.get("badge_layout_language_cycle") is not True
            or manifest.get("expected_count") != 17 or manifest.get("localized_witness_count") != 2):
        issues.append("Missing exact 17-assertion/two-witness badge-layout contract.")
    for key in ("language", "localized_witnesses", "localized_witness_count", "layout_probe_helpers_sha256", "expected_labels", "probe_sha256"):
        if manifest.get(key) != plan.get(key):
            issues.append("Frozen/plan badge-layout contract mismatch: " + key)
    if manifest.get("layout_probe_helpers_sha256") != helper_bindings():
        issues.append("A reviewed badge-layout helper changed since this run was planned.")
    expected = localized_expectations(run / "runtime", manifest["language"])
    if manifest.get("localized_witnesses") != expected:
        issues.append("Localized expectations do not match the frozen runtime locale.")
    settings = (run / "userdata/pdx_settings.txt").read_text(encoding="utf-8")
    if not re.search(r'"language"\s*=\s*\{[^}]*value\s*=\s*"' + re.escape(manifest["language"]) + '"', settings, re.S):
        issues.append("Stopped native profile no longer matches the declared language.")
    debug = (run / "userdata/logs/debug.log").read_text(encoding="utf-8-sig")
    locale_issues = validate_localized_witnesses(debug, expected)
    issues += locale_issues
    result["blockers"] += issues
    if result["blockers"]:
        result["status"] = "FAIL"
    result.update(classification="PRODUCTION_BADGE_LAYOUT_LANGUAGE_CYCLE",
                  localized_witnesses="PASS" if not issues else "FAIL",
                  expected_localized_copy=expected, localized_witness_count=2,
                  layout_probe_inspector_sha256=base.sha(Path(__file__)))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--stage", choices=("plan", "freeze", "inspect"), default="plan")
    parser.add_argument("--language", choices=LANGUAGES, default="l_russian", help="Used only for a new plan; freeze/inspect read its bound language.")
    parser.add_argument("--output", type=Path)
    reviews = parser.add_mutually_exclusive_group()
    reviews.add_argument("--diagnostic-review", type=Path)
    reviews.add_argument("--window-diagnostic-review", type=Path)
    final.ordinary.base.add_path_arguments(parser)
    args = parser.parse_args()
    final.ordinary.base.configure_paths(args)
    if not re.fullmatch("[a-z0-9_-]+", args.run_name):
        parser.error("Use a fresh lower-case isolated run name")
    run = final.ordinary.base.EVIDENCE / args.run_name
    if args.stage == "plan":
        prepare(run, args.language)
    elif args.stage == "freeze":
        freeze(run)
    else:
        if args.output is None:
            parser.error("--output is required for an immutable inspection report")
        result = inspect(run, args.diagnostic_review, args.window_diagnostic_review)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(json.dumps({key: result[key] for key in ("status", "pass_count", "expected_count", "localized_witnesses", "blockers")}))
