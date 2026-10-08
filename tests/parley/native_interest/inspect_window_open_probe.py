"""Inspect a stopped production-window diagnostic; never stop/launch a process.

The six window observations are separate from diagnostic and source-integrity
gates. A generated candidate is not an authoring-runtime acceptance claim.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from inspect_interest_probe import inventory, review_diagnostics, sha, configuration
import review_window_diagnostics as window_reviewer
import review_currency_ui_diagnostics as currency_ui_reviewer


def apply_window_review(records, run, review_path=None):
    """Recompute the exact reviewer; ignore only its new generation timestamp."""
    if review_path is None:
        return [], records, [], None
    try:
        saved = json.loads(review_path.read_text(encoding="utf-8"))
        verified = window_reviewer.review(Path(saved["off_control_run"]),
                                          Path(saved["window_control_run"]), run)
        stable = lambda data: {key: value for key, value in data.items() if key != "recorded_utc"}
        valid = (saved.get("schema_version") == 1
                 and saved.get("classification") == "EXACT_RUSSIAN_WINDOW_STARTUP_60_RECORDS"
                 and saved.get("status") == verified.get("status") == "SCOPED_REVIEW_PASS"
                 and Path(saved["target_run"]).resolve() == run.resolve()
                 and saved.get("generator_sha256") == sha(Path(window_reviewer.__file__))
                 and stable(saved) == stable(verified)
                 and len(saved.get("accepted_diagnostics", [])) == 60
                 and Counter(records) == Counter(saved["accepted_diagnostics"]))
        if not valid:
            return [], records, ["Exact window diagnostic review binding/verification failed."], None
        reviewed = [{"record": record, "classification": saved["classification"],
                     "review": str(review_path), "limits": saved["limits"]} for record in records]
        return reviewed, [], [], {"path": str(review_path), "sha256": sha(review_path),
                                  "recomputed": True, "generator_sha256": saved["generator_sha256"]}
    except (KeyError, OSError, ValueError, TypeError, AttributeError) as exc:
        return [], records, ["Window diagnostic revalidation failed: " + str(exc)], None


def apply_currency_ui_review(records, run, review_path=None):
    """Recompute the separate exact4 classifier; never use a saved PASS alone."""
    if review_path is None:
        return [], records, [], None
    try:
        saved = json.loads(review_path.read_text(encoding="utf-8"))
        verified = currency_ui_reviewer.review(Path(saved["off_control_run"]),
                                               Path(saved["window_control_run"]), run)
        stable = lambda data: {key: value for key, value in data.items() if key != "recorded_utc"}
        valid = (saved.get("schema_version") == 1
                 and saved.get("classification") == currency_ui_reviewer.CLASSIFICATION
                 and saved.get("status") == verified.get("status") == "SCOPED_REVIEW_PASS"
                 and Path(saved["target_run"]).resolve() == run.resolve()
                 and saved.get("generator_sha256") == sha(Path(currency_ui_reviewer.__file__))
                 and stable(saved) == stable(verified)
                 and len(saved.get("accepted_diagnostics", [])) == 4
                 and saved.get("target_phase", {}).get("record_count") == len(saved["accepted_diagnostics"])
                 and Counter(records) == Counter(saved["accepted_diagnostics"]))
        if not valid:
            return [], records, ["Exact currency UI diagnostic review binding/verification failed."], None
        reviewed = [{"record": record, "classification": saved["classification"],
                     "review": str(review_path), "limits": saved["limits"]} for record in records]
        return reviewed, [], [], {"path": str(review_path), "sha256": sha(review_path),
                                  "recomputed": True, "generator_sha256": saved["generator_sha256"]}
    except (KeyError, OSError, ValueError, TypeError, AttributeError) as exc:
        return [], records, ["Currency UI diagnostic revalidation failed: " + str(exc)], None


def inspect(run, diagnostic_review=None, window_diagnostic_review=None, currency_ui_diagnostic_review=None):
    manifest_path = run / "frozen-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    process_path = run / "process-result.json"
    process = json.loads(process_path.read_text(encoding="utf-8-sig")) if process_path.exists() else {}
    blockers = []
    if process.get("status") != "EXIT_CONFIRMED":
        blockers.append("Root has not confirmed the exact recorded process exit.")
    for tree in ("runtime", "probe", "merged"):
        if inventory(run / tree) != manifest[tree + "_sha256"]:
            blockers.append("Frozen " + tree + " integrity changed.")
    current = inventory(Path(manifest["runtime_source"]))
    exact = current == manifest["runtime_sha256"]
    if not exact:
        blockers.append("Current authoring runtime differs from frozen baseline.")
    profile = run / "userdata"
    if sha(profile / "pdx_settings.txt") != manifest["prepared_settings_sha256"]:
        # CK3 can rewrite window/autosave settings; report rather than silently
        # conflate that with unchanged prepared settings.
        settings_changed = True
    else:
        settings_changed = False
    paths = {name: profile / "logs" / name for name in ("debug.log", "error.log")}
    logs = {name: path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""
            for name, path in paths.items()}
    markers = re.findall(r"TNGUI_TEST\|(BEGIN|END|PASS|FAIL)\|([a-z0-9_]+)", logs["debug.log"])
    passes = Counter(label for kind, label in markers if kind == "PASS")
    failures = Counter(label for kind, label in markers if kind == "FAIL")
    boundaries = Counter(kind for kind, label in markers if label == "production_window" and kind in ("BEGIN", "END"))
    expected = Counter(manifest["expected_labels"])
    native_ok = passes == expected and not failures and boundaries == {"BEGIN": 1, "END": 1}
    if not native_ok:
        blockers.append("Required actual-show/survival assertions or native completion did not pass exactly once.")
    phase = re.findall(r"TNGUI_PHASE\|(BEFORE|AFTER)\|production_open_effect", logs["debug.log"])
    if phase != ["BEFORE", "AFTER"]:
        blockers.append("Production opener BEFORE/AFTER markers missing, duplicated or out of order.")
    records = [item.strip() for item in re.split(r"(?m)(?=^\[\d\d:\d\d:\d\d\])", logs["error.log"]) if item.strip()]
    if currency_ui_diagnostic_review is not None:
        reviewed, remaining, issues, review_identity = apply_currency_ui_review(records, run, currency_ui_diagnostic_review)
        if diagnostic_review is not None or window_diagnostic_review is not None:
            issues.append("Use the currency UI review alone, not combined with older diagnostic reviews.")
    elif window_diagnostic_review is not None:
        reviewed, remaining, issues, review_identity = apply_window_review(records, run, window_diagnostic_review)
        if diagnostic_review is not None:
            issues.append("Use either the complete window review or the older discovery review, not both.")
    else:
        reviewed, remaining, issues, review_identity = review_diagnostics(records, run, manifest, diagnostic_review)
    blockers.extend(issues)
    if remaining:
        blockers.append("Unreviewed engine diagnostics remain; no court/layout namespace waiver is applied.")
    crashes = inventory(profile / "crashes") if (profile / "crashes").exists() else {}
    if crashes:
        blockers.append("Isolated profile has crash artifacts; retain them for diagnosis.")
    candidate = bool(manifest.get("isolated_tooltip_flow_fix"))
    final_cycle = bool(manifest.get("final_actual_source_cycle"))
    currency_ui_cycle = bool(manifest.get("currency_ui_preview_lock_cycle"))
    classification = ("ISOLATED_GENERATED_CANDIDATE_DIAGNOSTIC" if candidate else
                      "PRODUCTION_CURRENCY_PREVIEW_EXCLUSIVITY_GUI_CYCLE" if currency_ui_cycle else
                      "PRODUCTION_FINAL_SOURCE_WINDOW_TOOLTIP_CYCLE_DIAGNOSTIC" if final_cycle else
                      "PRODUCTION_BASELINE_WINDOW_DIAGNOSTIC")
    status = "FAIL" if blockers else "PASS_WITH_SCOPED_DIAGNOSTICS_REVIEW" if reviewed else "PASS"
    return {"schema_version": 1, "status": status,
            "native_window_assertions": "PASS" if native_ok else "FAIL",
            "classification": classification, "final_actual_source_cycle": final_cycle,
            "currency_ui_preview_lock_cycle": currency_ui_cycle,
            "visual_status": "NOT_VERIFIED", "physical_hover_status": "NOT_VERIFIED",
            "forced_tooltip_materialization": manifest.get("forced_tooltip_materialization", False),
            "tooltip_materialization_contract": manifest.get("tooltip_materialization_contract"),
            "authoring_acceptance": False, "run": str(run), "recorded_utc": datetime.now(timezone.utc).isoformat(),
            "game_version": manifest["game_version"], "preset": manifest["preset"], "language": manifest["language"],
            "process": process, "process_record_sha256": sha(process_path) if process_path.exists() else None,
            "frozen_manifest_sha256": sha(manifest_path), "source_exact_current": exact,
            "runtime_files": len(manifest["runtime_sha256"]), "overrides": manifest["overrides"],
            "expected_count": sum(expected.values()), "pass_count": sum(passes.values()),
            "passes": dict(passes), "failures": dict(failures), "boundaries": dict(boundaries),
            "opener_phases": phase, "diagnostic_count": len(records),
            "reviewed_diagnostics": reviewed, "unreviewed_diagnostics": remaining,
            "diagnostic_review": review_identity, "isolated_crash_files_sha256": crashes,
            "log_sha256": {name: sha(path) for name, path in paths.items() if path.exists()},
            "settings_rewritten_by_native_session": settings_changed,
            "inspector_sha256": sha(Path(__file__)), "blockers": blockers,
            "coverage_limits": manifest["coverage_limits"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    reviews = parser.add_mutually_exclusive_group()
    reviews.add_argument("--diagnostic-review", type=Path)
    reviews.add_argument("--window-diagnostic-review", type=Path)
    reviews.add_argument("--currency-ui-diagnostic-review", type=Path)
    configuration.add_arguments(parser)
    args = parser.parse_args()
    configuration.configure(args)
    result = inspect(args.run, args.diagnostic_review, args.window_diagnostic_review, args.currency_ui_diagnostic_review)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in ("status", "native_window_assertions", "pass_count", "expected_count", "blockers")}))
