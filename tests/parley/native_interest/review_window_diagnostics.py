"""Exact startup-only diagnostic review for the production-window probes.

This is deliberately separate from the historical ledger/court inspector. It
does not launch CK3, edit a prior report, accept a crash, claim current source
identity, or claim visual/physical-hover acceptance. Missing evidence raises;
any new diagnostic, count, location, identity or phase fails closed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import review_court_diagnostics as court


CONTROL_PINS = {
    "off": {
        "plan.json": "ca2ba5a61724e3e47acc772496eaaf3327e06eb6ca0cb468d728d912ff863da3",
        "frozen-manifest.json": "b60292774c989f06b76365493aee1e6e7c4b26d5d64235eb5e71a157afde7617",
        "process-result.json": "990b494e40c280bbe9a86b12afacc6d37b0977181667bb4d3980c4dd8d0c9302",
        "userdata/logs/debug.log": "9453140214678d8896184306752d0329e6b61fcf2859988e76b05ff3dde92f03",
        "userdata/logs/error.log": "37a1d93838cc28a3d6ed012ae7524ba17f12e755535273b0195dfe89d204f5a0",
    },
    "window": {
        "plan.json": "ae41820276d960ba0d2bbb35f0ba9f2ccf5666a0d5688b325c5100caaabde5e1",
        "frozen-manifest.json": "117fd07dd8cf018d07797b594ece14972f2f0777ed442df455f8a81a480dc5a8",
        "process-result.json": "f13df23d756110bc78b58fb5d0695a9b3a616e0879e5d4235aae455d9fa70afa",
        "userdata/logs/debug.log": "ae87ee2d8649ec24a3b5a6bff491218d5da7b9166b9c2b9d84152c1e36b31f30",
        "userdata/logs/error.log": "9f24e950d719b287567f5458b1f5dbbc759c67873fce156007e45d9931a4fae8",
    },
}
DISCOVERY = Counter({
    "[E][character_interaction.cpp:1262]: " + name
    + ": 'ai_frequency' or 'ai_frequency_by_tier' scripted, but no 'ai_targets', won't be used": 1
    for name in ("tnt_open_negotiations", "tnt_stage_marriage_interaction")
})
OPEN_LABELS = {"native_open_participants", "production_numeric_open_state",
               "production_window_show_callback", "production_window_survives_3s",
               "production_window_survives_15s", "production_window_no_prior_failure"}
ENGLISH_DISPLAY = "Character - 4294967295"
RUSSIAN_DISPLAY = "Character\u00a0\u2014 4294967295"


def expected_english():
    result = Counter({court.TRIGGER + place: count for place, count in court.SCENES.items()})
    result[court.MANAGER] = 1
    return result + DISCOVERY


def russian_to_english(record):
    # Only this exact display punctuation changes. No whitespace normalization,
    # identity/path matching, substring allowance or error-body stripping.
    return record.replace(RUSSIAN_DISPLAY, ENGLISH_DISPLAY)


def validate_startup(error, debug):
    items, problems = court.records(error), []
    expected = Counter({body.replace(ENGLISH_DISPLAY, RUSSIAN_DISPLAY): count
                        for body, count in expected_english().items()})
    if len(items) != 60 or Counter(map(court.normalize, items)) != expected:
        problems.append("Requires exactly the reviewed Russian 60-record startup multiset; new/missing/GUI diagnostics are forbidden.")
    begins = court.marker_times(debug, "TNGUI_TEST|BEGIN|production_window")
    courts = [item for item in items if court.SCENE_RELATIVE in item or court.MANAGER in item]
    discoveries = [item for item in items if court.normalize(item) in DISCOVERY]
    ct, dt = court.timestamps(courts), court.timestamps(discoveries)
    if (len(begins) != 1 or len(ct) != 1 or len(dt) != 1
            or not dt[0] <= ct[0] < begins[0]
            or any(not re.match(r"^\[\d\d:\d\d:\d\d\]", item) for item in items)):
        problems.append("Requires one court burst and one earlier discovery pair, strictly before the unique fixture BEGIN.")
    return {"court_times": ct, "discovery_times": dt, "begin_times": begins,
            "record_count": len(items), "phase": "STARTUP_BEFORE_PRODUCTION_WINDOW_FIXTURE"}, problems


def validate_native(manifest, debug):
    problems = []
    labels = manifest["expected_labels"]
    if (len(labels) != manifest["expected_count"] or len(labels) != len(set(labels))
            or not OPEN_LABELS <= set(labels)):
        problems.append("Declared window assertions do not include the exact mandatory open/show/survival contract.")
    markers = re.findall(r"TNGUI_TEST\|(BEGIN|END|PASS|FAIL)\|([a-z0-9_]+)", debug)
    expected = Counter(("PASS", label) for label in labels)
    expected.update({("BEGIN", "production_window"): 1, ("END", "production_window"): 1})
    if Counter(markers) != expected or "TNGUI_TEST|FAIL|" in debug:
        problems.append("Native assertions/boundaries must all pass exactly once, with no extra or failed marker.")
    if not markers or markers[0] != ("BEGIN", "production_window") or markers[-1] != ("END", "production_window"):
        problems.append("Native assertion order lacks outer BEGIN/END boundaries.")
    if re.findall(r"TNGUI_PHASE\|(BEFORE|AFTER)\|production_open_effect", debug) != ["BEFORE", "AFTER"]:
        problems.append("Actual production opener must have exactly one ordered BEFORE/AFTER witness.")
    return problems


def inventory(root):
    return {path.relative_to(root).as_posix(): court.sha(path)
            for path in root.rglob("*") if path.is_file()}


def validate_frozen(manifest, plan, trees):
    problems = []
    for tree in ("runtime", "probe", "merged"):
        if trees[tree] != manifest[tree + "_sha256"]:
            problems.append("Frozen " + tree + " inventory changed.")
        if any(name.startswith("gfx/court_scene/") for name in trees[tree]):
            problems.append("A court scene override is forbidden.")
    for key in ("expected_labels", "expected_count", "kind", "marker_prefix", "preset", "probe_sha256", "runtime_source_at_plan_sha256"):
        if plan.get(key) != manifest.get(key):
            problems.append("Plan/frozen contract differs for " + key)
    if manifest["runtime_sha256"] != manifest["runtime_source_at_plan_sha256"]:
        problems.append("Runtime does not match its own planned source inventory.")
    expected_merged = manifest["runtime_sha256"] | manifest["probe_sha256"]
    for relative, entry in manifest["overrides"].items():
        base_hash = entry.get("base_sha256", entry.get("runtime_sha256"))
        if base_hash != manifest["runtime_sha256"].get(relative):
            problems.append("Override base hash mismatch: " + relative)
        expected_merged[relative] = entry["test_sha256"]
    if expected_merged != manifest["merged_sha256"]:
        problems.append("Merged source does not equal its bound runtime/probe/override closure.")
    return problems


def review(off_control, window_control, target):
    off_control, window_control, target = (Path(path).resolve() for path in (off_control, window_control, target))
    problems, bound = [], {}

    def bind(path):
        bound[str(path)] = court.sha(path)

    for kind, run in (("off", off_control), ("window", window_control)):
        for relative, digest in CONTROL_PINS[kind].items():
            path = run / relative
            bind(path)
            if court.sha(path) != digest:
                problems.append(kind + " historical control anchor changed: " + relative)

    # Re-execute the existing read-only validation against its own immutable Off
    # evidence, rather than trusting an old saved PASS record.
    old = court.review(off_control, off_control)
    if old["status"] != "SCOPED_REVIEW_PASS":
        problems.append("Historical Off court/source review no longer passes: " + repr(old["problems"]))
    for item in old["bound_files"]:
        bound[item["path"]] = item["sha256"]
    bind(Path(court.__file__))
    off_error = (off_control / "userdata/logs/error.log").read_text(encoding="utf-8-sig")
    off_items = Counter(map(court.normalize, court.records(off_error)))
    fixture = Counter({court.fixture_warning(name): 2 for name in court.FIXTURE_VARIABLES})
    if off_items != expected_english() + fixture:
        problems.append("Historical Off must contain exactly 58 court + 2 discovery + 4 separately validated fixture diagnostics.")

    def read_window(run):
        manifest_path, plan_path = run / "frozen-manifest.json", run / "plan.json"
        process_path = run / "process-result.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        process = json.loads(process_path.read_text(encoding="utf-8-sig"))
        error_path, debug_path = (run / "userdata/logs" / name for name in ("error.log", "debug.log"))
        for path in (manifest_path, plan_path, process_path, error_path, debug_path):
            bind(path)
        if process.get("status") != "EXIT_CONFIRMED":
            problems.append(str(run) + ": process exit is not confirmed.")
        for field in ("profile", "executable"):
            if Path(process[field]).resolve() != Path(manifest[field]).resolve():
                problems.append(str(run) + ": process/manifest " + field + " differs.")
        if Path(manifest["profile"]).resolve() != (run / "userdata").resolve():
            problems.append(str(run) + ": profile is not this isolated evidence directory.")
        if inventory(run / "userdata/crashes"):
            problems.append(str(run) + ": crash artifacts exist; never covered by diagnostic review.")
        trees = {tree: inventory(run / tree) for tree in ("runtime", "probe", "merged")}
        problems.extend(str(run) + ": " + issue for issue in validate_frozen(manifest, plan, trees))
        for tree in trees:
            for path in (run / tree).rglob("*.mod"):
                if re.search(r"(?m)^\s*replace_path\s*=", path.read_text(encoding="utf-8-sig")):
                    problems.append(str(run) + ": replace_path is forbidden.")
        if manifest.get("kind") != "PRODUCTION_WINDOW_OPEN_CRASH_DIAGNOSTIC" or manifest.get("language") != "l_russian":
            problems.append(str(run) + ": this exact classifier only covers the Russian production-window probe.")
        wrapper, load = run / "userdata/mod/tniqa_merged.mod", run / "userdata/dlc_load.json"
        settings = run / "userdata/pdx_settings.txt"
        for path in (wrapper, load, settings):
            bind(path)
        body = wrapper.read_text(encoding="utf-8-sig")
        paths = re.findall(r'(?m)^path\s*=\s*"([^"]+)"', body)
        if (len(paths) != 1 or Path(paths[0]).resolve() != (run / "merged").resolve()
                or re.search(r"(?m)^\s*replace_path\s*=", body)):
            problems.append(str(run) + ": wrapper does not load only the bound merged tree.")
        if json.loads(load.read_text(encoding="utf-8-sig"))["enabled_mods"] != ["mod/tniqa_merged.mod"]:
            problems.append(str(run) + ": unexpected enabled mod.")
        if not re.search(r'"language"\s*=\s*\{[^}]*value\s*=\s*"l_russian"', settings.read_text(encoding="utf-8-sig"), re.S):
            problems.append(str(run) + ": native settings no longer identify the bound Russian locale.")
        error, debug = (path.read_text(encoding="utf-8-sig") for path in (error_path, debug_path))
        phase, issues = validate_startup(error, debug)
        problems.extend(str(run) + ": " + issue for issue in issues + validate_native(manifest, debug))
        return manifest, error, phase

    cm, ce, cp = read_window(window_control)
    tm, te, tp = read_window(target)
    if Counter(map(court.normalize, court.records(ce))) != Counter(map(court.normalize, court.records(te))):
        problems.append("Target is not the timestamp-stripped exact Russian window-control diagnostic multiset.")
    if Counter(russian_to_english(court.normalize(item)) for item in court.records(ce)) != expected_english():
        problems.append("Russian control does not chain to the exact Off 58+2 multiset using only the reviewed punctuation mapping.")
    off_manifest = json.loads((off_control / "frozen-manifest.json").read_text(encoding="utf-8"))
    for field in ("game_version", "executable_sha256"):
        if not cm[field] == tm[field] == off_manifest[field]:
            problems.append("Compiled game/control identity differs for " + field)
    exe = Path(tm["executable"])
    bind(exe)
    if court.sha(exe) != tm["executable_sha256"]:
        problems.append("Installed compiled engine no longer matches the tested executable.")
    return {
        "schema_version": 1, "classification": "EXACT_RUSSIAN_WINDOW_STARTUP_60_RECORDS",
        "status": "SCOPED_REVIEW_PASS" if not problems else "SCOPED_REVIEW_FAIL",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "off_control_run": str(off_control), "window_control_run": str(window_control), "target_run": str(target),
        "generator_sha256": court.sha(Path(__file__)), "historical_court_reviewer_sha256": court.sha(Path(court.__file__)),
        "bound_files": [{"path": path, "sha256": digest} for path, digest in sorted(bound.items())],
        "target_source_sha256": {name: tm[name + "_sha256"] for name in ("runtime", "probe", "merged")},
        "control_phase": cp, "target_phase": tp,
        "accepted_diagnostics": court.records(te) if not problems else [], "problems": problems,
        "current_source_acceptance": "NOT_ASSESSED_HISTORICAL_FROZEN_SOURCE_ONLY",
        "visual_status": "NOT_VERIFIED", "physical_hover_status": "NOT_VERIFIED",
        "limits": ["Exactly one pre-BEGIN 57+1 court burst and the exact earlier two discovery records; no reload/GUI/crash exception.",
                   "Only Character NBSP/em-dash display punctuation maps to the English Off control; all remaining body bytes/counts match.",
                   "Underlying native cause is not proven fixed. The Off control contains Parley, not a no-mod vanilla-only proof.",
                   "This diagnostic review never establishes current authoring identity, clean logs, visual layout, physical hover or user-save reproduction.",
                   "Consumers must rerun this reviewer and compare bound files, accepted diagnostics and phases before using saved evidence."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--off-control", required=True, type=Path)
    parser.add_argument("--window-control", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = review(args.off_control, args.window_control, args.target)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "count": len(result["accepted_diagnostics"]), "problems": result["problems"]}))
