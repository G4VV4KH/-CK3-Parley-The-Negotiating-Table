"""English-only, exact startup review for the 17+2 localized badge probe.

Historical reviewers, logs and reports remain immutable. Re-run their complete
control/source checks, replacing only the enumerated Russian-language objections
with English checks. This never permits GUI diagnostics, a native failure, source
drift, a crash, or a visual/physical-hover PASS. No launch or production writes.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import inspect_interest_probe as ledger
import prepare_badge_layout_probe as badge
import review_window_diagnostics as window


CLASSIFICATION = "EXACT_ENGLISH_STABLE_UI_STARTUP_2_OR_60_RECORDS"
DIAGNOSTIC_BLOCKER = "Unreviewed engine diagnostics remain; no court/layout namespace waiver is applied."


def validate_startup(error, debug):
    items = window.court.records(error)
    actual = Counter(map(window.court.normalize, items))
    problems = []
    if actual not in (window.DISCOVERY, window.expected_english()):
        problems.append("Requires the exact English discovery pair alone or exact English 58+2 multiset; all other records are forbidden.")
    begins = window.court.marker_times(debug, "TNGUI_TEST|BEGIN|production_window")
    discovery = [item for item in items if window.court.normalize(item) in window.DISCOVERY]
    courts = [item for item in items if window.court.normalize(item) not in window.DISCOVERY]
    dt, ct = window.court.timestamps(discovery), window.court.timestamps(courts)
    if (len(begins) != 1 or len(dt) != 1
            or not dt[0] < begins[0]
            or any(not re.match(r"^\[\d\d:\d\d:\d\d\]", item) for item in items)):
        problems.append("The exact discovery pair must share one timestamp strictly before the unique fixture BEGIN.")
    if courts and (len(ct) != 1 or len(dt) != 1 or len(begins) != 1
                   or not dt[0] <= ct[0] < begins[0]):
        problems.append("The optional exact court burst must occur once, after discovery and strictly before BEGIN.")
    return {"court_times": ct, "discovery_times": dt, "begin_times": begins,
            "record_count": len(items), "phase": "STARTUP_BEFORE_PRODUCTION_WINDOW_FIXTURE"}, problems


def anticipated_old_objections(target, count):
    result = [str(target) + ": this exact classifier only covers the Russian production-window probe.",
              str(target) + ": native settings no longer identify the bound Russian locale.",
              str(target) + ": Requires exactly the reviewed Russian 60-record startup multiset; new/missing/GUI diagnostics are forbidden.",
              "Target is not the timestamp-stripped exact Russian window-control diagnostic multiset."]
    if count == 2:
        result.append(str(target) + ": Requires one court burst and one earlier discovery pair, strictly before the unique fixture BEGIN.")
    return result


def retain_old_problems(problems, expected):
    retained = [issue for issue in problems if issue not in expected]
    if Counter(issue for issue in problems if issue in expected) != Counter(expected):
        retained.append("Older reviewer did not return exactly the anticipated English/count objections.")
    return retained


def validate_badge_gate(result):
    problems = []
    if result.get("blockers") != [DIAGNOSTIC_BLOCKER]:
        problems.append("The fresh badge inspector must have only its single unreviewed-diagnostics blocker.")
        problems.extend(issue for issue in result.get("blockers", []) if issue != DIAGNOSTIC_BLOCKER)
    if (result.get("language") != "l_english" or result.get("classification") != "PRODUCTION_BADGE_LAYOUT_LANGUAGE_CYCLE"
            or result.get("native_window_assertions") != "PASS" or result.get("localized_witnesses") != "PASS"
            or result.get("pass_count") != 17 or result.get("expected_count") != 17
            or result.get("localized_witness_count") != 2 or result.get("source_exact_current") is not True
            or result.get("visual_status") != "NOT_VERIFIED" or result.get("physical_hover_status") != "NOT_VERIFIED"):
        problems.append("Requires current English 17 native assertions plus two actual localized witnesses; visuals remain unverified.")
    return problems


def review(off_control, window_control, target):
    target = Path(target).resolve()
    old = window.review(off_control, window_control, target)
    error = (target / "userdata/logs/error.log").read_text(encoding="utf-8-sig")
    debug = (target / "userdata/logs/debug.log").read_text(encoding="utf-8-sig")
    manifest = json.loads((target / "frozen-manifest.json").read_text(encoding="utf-8-sig"))
    phase, issues = validate_startup(error, debug)
    expected_objections = anticipated_old_objections(target, phase["record_count"])
    problems = retain_old_problems(old["problems"], expected_objections) + issues
    # Recompute, never trust a saved native report. This checks current source,
    # frozen helpers, 17 exact native assertions, and both real locale witnesses.
    native = badge.inspect(target)
    problems += validate_badge_gate(native)
    if manifest.get("kind") != "PRODUCTION_WINDOW_OPEN_CRASH_DIAGNOSTIC":
        problems.append("Only the ordinary production-window probe kind is covered.")
    # Discovery inheritance additionally requires the two complete production
    # interaction files to retain their reviewed historical hashes.
    discovery_review = Path(__file__).with_name("diagnostic-review.json")
    all_records = window.court.records(error)
    reviewed, remaining, discovery_issues, _ = ledger.review_diagnostics(all_records, target, manifest, discovery_review)
    problems += discovery_issues
    if (len(reviewed) != 2 or Counter(window.court.normalize(item["record"]) for item in reviewed) != window.DISCOVERY
            or Counter(map(window.court.normalize, remaining)) !=
            (window.expected_english() - window.DISCOVERY if phase["record_count"] == 60 else Counter())):
        problems.append("Exact discovery source inheritance or remaining court multiset is not verified.")
    bound = {item["path"]: item["sha256"] for item in old["bound_files"]}
    helpers = [Path(__file__), Path(window.__file__), Path(window.court.__file__), Path(ledger.__file__),
               Path(ledger.configuration.__file__),
               Path(badge.__file__), Path(badge.window_inspector.__file__), discovery_review]
    helpers += [Path(path) for path in badge.helper_bindings()]
    helpers += [Path(item["baseline_file"]) for item in reviewed]
    for path in helpers:
        bound[str(path.resolve())] = window.court.sha(path)
    return {"schema_version": 1, "classification": CLASSIFICATION,
            "status": "SCOPED_REVIEW_PASS" if not problems else "SCOPED_REVIEW_FAIL",
            "recorded_utc": datetime.now(timezone.utc).isoformat(),
            "off_control_run": old["off_control_run"], "window_control_run": old["window_control_run"],
            "target_run": str(target), "language": "l_english",
            "generator_sha256": window.court.sha(Path(__file__)),
            "bound_files": [{"path": path, "sha256": digest} for path, digest in sorted(bound.items())],
            "target_source_sha256": old["target_source_sha256"],
            "current_source_sha256": ledger.inventory(Path(manifest["runtime_source"])),
            "control_phase": old["control_phase"], "target_phase": phase,
            "base_review_expected_objections": expected_objections,
            "localized_witnesses": {"status": native["localized_witnesses"], "count": native["localized_witness_count"],
                                    "expected": native["expected_localized_copy"]},
            "accepted_diagnostics": all_records if not problems else [], "problems": problems,
            "current_source_acceptance": "EXACT_CURRENT_BADGE_PROBE_ONLY" if not problems else "NOT_ACCEPTED",
            "visual_status": "NOT_VERIFIED", "physical_hover_status": "NOT_VERIFIED",
            "limits": ["Exact English discovery pair alone, or the same pair plus one exact 57+1 pre-BEGIN court burst; no GUI/new-record/reload exception.",
                       "Historical Russian control chains to the Off control through only the original exact display-punctuation mapping; neither old reviewer is changed.",
                       "Underlying court cause is not proven fixed; Off contains Parley and is not a no-mod vanilla-only control. The full error log is not clean.",
                       "Current-source claim is limited to the 17-assertion window/two-tooltip cycle and two actual English locale witnesses, not full gameplay or user-save reproduction.",
                       "Visual layout, pixel position, clipping, glyph colors and physical hover remain NOT_VERIFIED.",
                       "Consumers must rerun this full reviewer and compare all fields except recorded_utc before producing a new supplemental report."]}


def apply_review(native, saved, verified, target, review_path, review_sha256):
    """Pure fail-closed consumer; only the exact diagnostics blocker can leave."""
    result = deepcopy(native)
    stable = lambda data: {key: value for key, value in data.items() if key != "recorded_utc"}
    records = native.get("unreviewed_diagnostics", [])
    valid = (saved.get("schema_version") == 1 and saved.get("classification") == CLASSIFICATION
             and saved.get("status") == verified.get("status") == "SCOPED_REVIEW_PASS"
             and Path(saved.get("target_run", "")).resolve() == Path(target).resolve()
             and stable(saved) == stable(verified)
             and saved.get("generator_sha256") == window.court.sha(Path(__file__))
             and len(records) in (2, 60) and Counter(records) == Counter(saved.get("accepted_diagnostics", []))
             and saved.get("target_phase", {}).get("record_count") == len(records)
             and not validate_badge_gate(native))
    if not valid:
        result["blockers"].append("Stable UI diagnostic review binding/recomputation failed.")
        result["status"] = "FAIL"
        return result
    result["blockers"] = []
    result["status"] = "PASS_WITH_SCOPED_DIAGNOSTICS_REVIEW"
    result["reviewed_diagnostics"] = [{"record": record, "classification": CLASSIFICATION,
                                      "review": str(review_path), "limits": saved["limits"]} for record in records]
    result["unreviewed_diagnostics"] = []
    result["diagnostic_review"] = {"path": str(review_path), "sha256": review_sha256,
                                   "recomputed": True, "generator_sha256": saved["generator_sha256"]}
    result["supplemental_inspector_sha256"] = window.court.sha(Path(__file__))
    return result


def inspect(target, review_path):
    target, review_path = Path(target).resolve(), Path(review_path).resolve()
    saved = json.loads(review_path.read_text(encoding="utf-8"))
    verified = review(Path(saved["off_control_run"]), Path(saved["window_control_run"]), target)
    return apply_review(badge.inspect(target), saved, verified, target, review_path, window.court.sha(review_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("review", "inspect"), required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--off-control", type=Path)
    parser.add_argument("--window-control", type=Path)
    parser.add_argument("--review", type=Path)
    ledger.configuration.add_arguments(parser)
    args = parser.parse_args()
    ledger.configuration.configure(args)
    if args.stage == "review":
        if args.off_control is None or args.window_control is None or args.review is not None:
            parser.error("Review requires both controls and no --review")
        result = review(args.off_control, args.window_control, args.target)
    else:
        if args.review is None or args.off_control is not None or args.window_control is not None:
            parser.error("Inspect requires only --review")
        result = inspect(args.target, args.review)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in ("status", "problems", "blockers", "pass_count", "expected_count") if key in result}))
