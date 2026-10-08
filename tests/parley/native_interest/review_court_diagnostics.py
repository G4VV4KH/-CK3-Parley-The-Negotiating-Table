"""Read-only, exact-burst native court diagnostic review; never launch CK3.

The control must be a stopped Off run with every required native assertion
passing and the one known invalid-character court burst before fixture BEGIN.
Each target burst equals the control except wall-clock timestamp. At most one
initial-load and one explicitly evidenced disk-load burst are accepted. This
does not waive any new location, identity, message, within-burst count or phase.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


SCENE_RELATIVE = "gfx/court_scene/scene_cultures/00_default_cultures.txt"
SCENE_SHA256 = "a712c20ca0708a5e5e997d65a38f9ad1a620e235710d5956254b161bf250456f"
SCENES = {"9 (byzantine:trigger)": 3, "277 (chinese:trigger)": 3,
          "352 (chinese_alt:trigger)": 3, "224 (indian:trigger)": 9,
          "311 (japanese:trigger)": 3, "39 (mediterranean:trigger)": 9,
          "139 (mena:trigger)": 9, "2 (papal:trigger)": 3,
          "338 (southeast_asia:trigger)": 3, "87 (steppe:trigger)": 3,
          "251 (western:trigger)": 9}
MANAGER = "[E][court_scene_manager.cpp:2764]: Failed to find applicable culture set for character with id 4294967295"
TRIGGER = ("[E][jomini_script_system.cpp:304]: Script system error!\n"
           "  Error: untyped trigger [ Scoped object of type 'character' is not valid ((no character) "
           "\x15weak (Character - 4294967295)\x15!) ]\n"
           "  Script location: file: " + SCENE_RELATIVE + " line: ")
FIXTURE_VARIABLES = {"tniqa_ai_actor_gold": "actor", "tniqa_ai_recipient_gold": "recipient"}


def fixture_warning(name):
    return ("[E][jomini_effect.cpp:1146]: Variable '" + name + "' is set but is never used. "
            "Note that use in localization doesn't count due to technical limitations. "
            "Use in unused scripted triggers and effects also does not count")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(text):
    return [item.strip() for item in re.split(r"(?m)(?=^\[\d\d:\d\d:\d\d\])", text) if item.strip()]


def normalize(record):
    return re.sub(r"^\[\d\d:\d\d:\d\d\]", "", record, count=1)


def court_records(text):
    return [record for record in records(text)
            if SCENE_RELATIVE in record or "[court_scene_manager.cpp:2764]" in record]


def exact_burst(items):
    expected = Counter({TRIGGER + location: count for location, count in SCENES.items()})
    expected[MANAGER] = 1
    return Counter(normalize(item) for item in items) == expected


def timestamps(items):
    return sorted({item[1:9] for item in items if re.match(r"^\[\d\d:\d\d:\d\d\]", item)})


def marker_times(text, marker):
    return re.findall(r"(?m)^\[(\d\d:\d\d:\d\d)\].*" + re.escape(marker), text)


def phase_of_burst(items, debug):
    times = timestamps(items)
    begins = marker_times(debug, "TNI_TEST|BEGIN|interest")
    if len(times) != 1 or len(begins) != 1:
        return "UNVERIFIED"
    instant = times[0]
    if instant < begins[0]:
        return "INITIAL_WORLD_LOAD_BEFORE_FIXTURE"
    loads = marker_times(debug, "TNI_RELOAD|native_exact_local_load|")
    restored = marker_times(debug, "TNI_RELOAD|loaded_state_observed_before_recovery|yes")
    if len(loads) == len(restored) == 1 and loads[0] <= instant <= restored[0]:
        return "NATIVE_DISK_LOAD_BEFORE_RESTORED_CALLBACK"
    return "UNVERIFIED"


def validate_target_bursts(items, debug, baseline):
    """A finite allowance per evidenced load phase, never per namespace."""
    groups = {instant: [item for item in items if item[1:9] == instant]
              for instant in timestamps(items)}
    problems, bursts, phases = [], [], set()
    if sum(len(group) for group in groups.values()) != len(items):
        problems.append("Target court record has no valid timestamp and cannot be phase-bound.")
    if not 1 <= len(groups) <= 2:
        problems.append("Target requires one or two finite court bursts, not zero or a third burst.")
    for instant, group in groups.items():
        phase = phase_of_burst(group, debug)
        if not exact_burst(group) or Counter(map(normalize, group)) != Counter(map(normalize, baseline)):
            problems.append("Target burst " + instant + " differs from the exact control 57-trigger + 1-manager multiset.")
        if phase == "UNVERIFIED" or phase in phases:
            problems.append("Target burst " + instant + " is outside a unique evidenced native load phase.")
        phases.add(phase)
        bursts.append({"time": instant, "phase": phase, "record_count": len(group)})
    return bursts, problems


def exact_off_fixture_warnings(run, manifest, diagnostics, debug):
    """Historical Off-only no-op captures; not a production-warning wildcard."""
    warnings = [item for item in diagnostics if normalize(item) in
                {fixture_warning(name) for name in FIXTURE_VARIABLES}]
    if not warnings:
        return []
    expected = Counter({fixture_warning(name): 2 for name in FIXTURE_VARIABLES})
    begins = marker_times(debug, "TNI_TEST|BEGIN|interest")
    path = run / "probe/events/tniqa_events.txt"
    if (manifest["preset"] != "off" or Counter(map(normalize, warnings)) != expected
            or len(begins) != 1 or any(item[1:9] >= begins[0] for item in warnings)
            or not path.is_file() or sha(path) != manifest["probe_sha256"].get("events/tniqa_events.txt")):
        return []
    event = path.read_text(encoding="utf-8-sig")
    for name, actor in FIXTURE_VARIABLES.items():
        if event.count(name) != 1 or f"set_variable = {{ name = {name} value = scope:{actor}.gold }}" not in event:
            return []
        if any(name in source.read_text(encoding="utf-8-sig", errors="replace")
               for source in (run / "runtime").rglob("*.txt")):
            return []
    return warnings


def review(control, target):
    control, target = control.resolve(), target.resolve()
    problems, references = [], []

    def bind(path):
        references.append({"path": str(path), "sha256": sha(path)})

    def read_run(run):
        manifest_path, process_path = run / "frozen-manifest.json", run / "process-result.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        process = json.loads(process_path.read_text(encoding="utf-8-sig"))
        error_path, debug_path = run / "userdata/logs/error.log", run / "userdata/logs/debug.log"
        for path in (manifest_path, process_path, error_path, debug_path):
            bind(path)
        error, debug = (path.read_text(encoding="utf-8-sig", errors="replace") for path in (error_path, debug_path))
        if process.get("status") != "EXIT_CONFIRMED":
            problems.append(str(run) + ": recorded process is not stopped.")
        for tree in ("runtime", "merged", "probe"):
            actual = {path.relative_to(run / tree).as_posix(): sha(path)
                      for path in (run / tree).rglob("*") if path.is_file()}
            if actual != manifest[tree + "_sha256"]:
                problems.append(str(run) + ": snapshot integrity changed for " + tree)
            if any(path.startswith("gfx/court_scene/") for path in actual):
                problems.append(str(run) + ": a test/mod court-scene override is present.")
            if any(re.search(r"(?m)^\s*replace_path\s*=", path.read_text(encoding="utf-8-sig", errors="replace"))
                   for path in (run / tree).rglob("*.mod")):
                problems.append(str(run) + ": a replace_path directive is present.")
        load_path = run / "userdata/dlc_load.json"
        wrapper = run / "userdata/mod/tniqa_merged.mod"
        bind(load_path)
        bind(wrapper)
        if json.loads(load_path.read_text(encoding="utf-8"))["enabled_mods"] != ["mod/tniqa_merged.mod"]:
            problems.append(str(run) + ": unexpected additional enabled mod.")
        if re.search(r"(?m)^\s*replace_path\s*=", wrapper.read_text(encoding="utf-8-sig")):
            problems.append(str(run) + ": a wrapper replace_path directive is present.")
        return manifest, process, error, debug

    cm, cp, ce, cd = read_run(control)
    tm, tp, te, td = read_run(target)
    if cm["preset"] != "off":
        problems.append("Control is not the independent Off preset.")
    control_passes = Counter(re.findall(r"TNI_TEST\|PASS\|([a-z0-9_]+)", cd))
    if control_passes != Counter(cm["expected_labels"]) or "TNI_TEST|FAIL|" in cd:
        problems.append("Control does not pass every declared native assertion exactly once.")
    if marker_times(cd, "TNI_TEST|BEGIN|interest").__len__() != 1 or len(marker_times(cd, "TNI_TEST|END|interest")) != 1:
        problems.append("Control lacks exact native BEGIN/END boundaries.")
    for field in ("game_version", "executable_sha256"):
        if cm[field] != tm[field]:
            problems.append("Target/control " + field + " differ.")
    exe = Path(tm["executable"])
    if sha(exe) != tm["executable_sha256"]:
        problems.append("Current compiled engine differs from the recorded executable.")
    bind(exe)
    scene = exe.parent.parent / "game" / SCENE_RELATIVE
    bind(scene)
    if sha(scene) != SCENE_SHA256:
        problems.append("Installed native court scene source differs from reviewed exact bytes.")
    last_write = datetime.fromtimestamp(scene.stat().st_mtime, timezone.utc)
    if last_write > datetime.fromisoformat(cp["started_utc"].replace("Z", "+00:00")):
        problems.append("Native court source was modified after the control started.")
    cc, tc = court_records(ce), court_records(te)
    if not exact_burst(cc):
        problems.append("Control is not the exact reviewed 57-trigger + 1-manager multiset.")
    control_phase = phase_of_burst(cc, cd)
    target_bursts, burst_problems = validate_target_bursts(tc, td, cc)
    problems.extend(burst_problems)
    if control_phase != "INITIAL_WORLD_LOAD_BEFORE_FIXTURE":
        problems.append("Control burst did not precede all fixture effects.")
    # The control may contain only the two separately-reviewed player-only
    # discovery messages besides its court burst. Unknown control failures
    # cannot establish an inherited-warning exception.
    discovery = {"[E][character_interaction.cpp:1262]: " + name +
                 ": 'ai_frequency' or 'ai_frequency_by_tier' scripted, but no 'ai_targets', won't be used"
                 for name in ("tnt_open_negotiations", "tnt_stage_marriage_interaction")}
    control_fixture = exact_off_fixture_warnings(control, cm, records(ce), cd)
    target_fixture = exact_off_fixture_warnings(target, tm, records(te), td)
    other_control = [item for item in records(ce) if item not in cc and item not in control_fixture]
    if any(normalize(item) not in discovery for item in other_control):
        problems.append("Off control contains an additional unreviewed diagnostic.")
    if any(count != 1 for count in Counter(map(normalize, other_control)).values()):
        problems.append("Off control discovery warning count differs from the exact reviewed bound.")
    return {
        "schema_version": 2,
        "classification": "EXACT_INHERITED_NATIVE_COURT_INITIALIZATION_BURSTS",
        "status": "SCOPED_REVIEW_PASS" if not problems else "SCOPED_REVIEW_FAIL",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "control_run": str(control), "target_run": str(target),
        "game_version": tm["game_version"], "control_phase": control_phase, "target_bursts": target_bursts,
        "control_times": timestamps(cc), "target_times": timestamps(tc),
        "source_hash_observation": "Native scene bytes hashed at review; filesystem last-write predates recorded control start.",
        "native_scene_last_write_utc": last_write.isoformat(),
        "bound_files": references, "generator_sha256": sha(Path(__file__)),
        "accepted_diagnostics": tc if not problems else [], "problems": problems,
        "accepted_fixture_diagnostics": target_fixture if not problems else [],
        "control_fixture_diagnostics": control_fixture,
        "fixture_review_reason": "Two unused test-only stock snapshots, each reported twice before BEGIN under Off; exact single assignments and absence from runtime verified. No gameplay effect is invoked by these captures.",
        "limits": ["Underlying native engine cause is not proven or fixed.",
                   "Observed in native court initialization under feature-Off control; the control contains Parley, not a proven no-mod vanilla-only cause.",
                   "Exact finite invalid-character 4294967295 court-init sequence only; no namespace/path wildcard exception.",
                   "Full engine log is not clean; this is inherited native UI/court initialization evidence, not visual acceptance.",
                   "At most one exact startup burst and one exact explicitly evidenced native-disk-load burst; duplicate phases, a third burst or new records remain blocking.",
                   "This review never waives a failed gameplay assertion or source drift."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = review(args.control, args.target)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "count": len(result["accepted_diagnostics"]), "problems": result["problems"]}))
