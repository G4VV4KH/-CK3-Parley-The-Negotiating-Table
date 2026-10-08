"""Read a stopped isolated interest run and write a new immutable result.

Exact labels and complete runtime/probe integrity are mandatory. Unreviewed
engine diagnostics prevent native acceptance; this tool never broadly ignores
vanilla errors or silently treats static checks as engine evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_configuration as configuration


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p)
            for p in sorted(root.rglob("*")) if p.is_file()}


def review_diagnostics(records, run, manifest, review_path=None, baseline_root=None):
    """Match exact reviewed records only when both entire source files match.

    No message regex, namespace allowlist, or wildcard paths are accepted.
    Timestamp is the sole removed field. A duplicate beyond the reviewed bound
    stays unreviewed and therefore blocks acceptance.
    """
    if review_path is None:
        return [], records, [], None
    data = json.loads(review_path.read_text(encoding="utf-8"))
    if data.get("schema_version") not in (1, 2):
        return [], records, ["Unsupported diagnostic-review schema."], None
    permitted, issues = {}, []
    for entry in data.get("entries", []):
        relative = Path(entry["runtime_file"])
        message = entry["exact_message_without_timestamp"]
        try:
            baseline = configuration.baseline_member(entry, data["schema_version"], baseline_root)
        except (KeyError, OSError, ValueError) as error:
            issues.append("Diagnostic review baseline verification failed: " + str(error))
            continue
        expected_hash = entry["sha256"]
        valid = (
            not relative.is_absolute() and ".." not in relative.parts
            and relative.as_posix().startswith("common/character_interactions/")
            and entry.get("classification") == "UNCHANGED_PLAYER_ONLY_AI_DISCOVERY_DISABLED"
            and entry.get("max_occurrences") == 1
            and entry.get("function") in ("tnt_open_negotiations", "tnt_stage_marriage_interaction")
            and message == ("[E][character_interaction.cpp:1262]: " + entry["function"] +
                            ": 'ai_frequency' or 'ai_frequency_by_tier' scripted, but no 'ai_targets', won't be used")
            and bool(entry.get("reason"))
            and baseline.is_file() and sha(baseline) == expected_hash
            and manifest["runtime_sha256"].get(relative.as_posix()) == expected_hash
            and (run / "runtime" / relative).is_file()
            and sha(run / "runtime" / relative) == expected_hash
            and (run / "merged" / relative).is_file()
            and sha(run / "merged" / relative) == expected_hash
        )
        if not valid or message in permitted:
            issues.append("Diagnostic review source/message verification failed: " + entry["runtime_file"])
        else:
            permitted[message] = dict(entry, baseline_file=str(baseline))
    reviewed, remaining, counts = [], [], Counter()
    for record in records:
        exact = re.sub(r"^\[\d\d:\d\d:\d\d\]", "", record, count=1)
        entry = permitted.get(exact)
        if entry and counts[exact] < entry["max_occurrences"]:
            counts[exact] += 1
            reviewed.append({"record": record, "classification": entry["classification"],
                             "runtime_file": entry["runtime_file"], "baseline_file": entry["baseline_file"],
                             "source_sha256": entry["sha256"], "reason": entry["reason"]})
        else:
            remaining.append(record)
    return reviewed, remaining, issues, {"path": str(review_path), "sha256": sha(review_path),
                                        "resolver_sha256": sha(Path(configuration.__file__))}


def apply_court_review(records, run, review_path=None):
    if review_path is None:
        return [], records, [], None
    review = json.loads(review_path.read_text(encoding="utf-8"))
    # Re-run the finite exact classifier. A hand-edited review JSON cannot turn
    # arbitrary 58 errors into court records merely by claiming PASS.
    generator = Path(__file__).with_name("review_court_diagnostics.py")
    spec = importlib.util.spec_from_file_location("interest_court_review", generator)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        verified = module.review(Path(review["control_run"]), run)
    except (KeyError, OSError, ValueError, TypeError) as exc:
        return [], records, ["Court diagnostic revalidation failed: " + str(exc)], None
    valid = (review.get("schema_version") == 2
             and review.get("classification") == "EXACT_INHERITED_NATIVE_COURT_INITIALIZATION_BURSTS"
             and review.get("status") == "SCOPED_REVIEW_PASS"
             and Path(review["target_run"]).resolve() == run.resolve()
             and len(review.get("accepted_diagnostics", [])) in (58, 116)
             and bool(review.get("bound_files"))
             and verified["status"] == "SCOPED_REVIEW_PASS"
             and review.get("generator_sha256") == sha(generator)
             and all(review.get(key) == verified.get(key) for key in
                     ("accepted_diagnostics", "accepted_fixture_diagnostics", "bound_files",
                      "control_phase", "target_bursts", "classification")))
    for reference in review.get("bound_files", []):
        path = Path(reference["path"])
        valid = valid and path.is_file() and sha(path) == reference["sha256"]
    if not valid:
        return [], records, ["Exact court diagnostic review binding/verification failed."], None
    accepted = Counter(review["accepted_diagnostics"] + review.get("accepted_fixture_diagnostics", []))
    reviewed, remaining = [], []
    for record in records:
        if accepted[record] > 0:
            accepted[record] -= 1
            reviewed.append({"record": record, "classification":
                             "EXACT_OFF_FIXTURE_UNUSED_STOCK_CAPTURE" if record in review.get("accepted_fixture_diagnostics", []) else review["classification"],
                             "review": str(review_path), "limits": review["limits"]})
        else:
            remaining.append(record)
    if any(accepted.values()):
        return [], records, ["Court diagnostic review records are not present exactly as bound."], None
    return reviewed, remaining, [], {"path": str(review_path), "sha256": sha(review_path)}


def inspect(run, diagnostic_review=None, court_diagnostic_review=None):
    manifest = json.loads((run / "frozen-manifest.json").read_text(encoding="utf-8"))
    process_path = run / "process-result.json"
    process = json.loads(process_path.read_text(encoding="utf-8-sig")) if process_path.exists() else {}
    blockers = []
    if process.get("status") != "EXIT_CONFIRMED":
        blockers.append("The recorded isolated process has not been confirmed exited.")
    for tree, key in (("runtime", "runtime_sha256"), ("merged", "merged_sha256"), ("probe", "probe_sha256")):
        if inventory(run / tree) != manifest[key]:
            blockers.append(tree + " snapshot integrity differs from frozen manifest.")
    current = inventory(Path(manifest["runtime_source"]))
    exact_current = current == manifest["runtime_sha256"]
    profile = run / "userdata"
    log = profile / "logs/debug.log"
    error = profile / "logs/error.log"
    text = log.read_text(encoding="utf-8-sig", errors="replace") if log.exists() else ""
    markers = re.findall(r"TNI_TEST\|(BEGIN|END|PASS|FAIL)\|([a-z0-9_]+)", text)
    boundary = Counter(kind for kind, label in markers if label == "interest" and kind in ("BEGIN", "END"))
    if boundary != {"BEGIN": 1, "END": 1}:
        blockers.append("Missing or duplicate native BEGIN/END markers.")
    passes = Counter(label for kind, label in markers if kind == "PASS")
    fails = Counter(label for kind, label in markers if kind == "FAIL")
    expected = manifest["expected_labels"]
    if passes != Counter(expected):
        blockers.append("Required native assertion counts differ; each must PASS exactly once.")
    if fails:
        blockers.append("Native FAIL marker present.")
    diagnostic = error.read_text(encoding="utf-8-sig", errors="replace") if error.exists() else ""
    records = [line.strip() for line in re.split(r"(?m)(?=^\[\d\d:\d\d:\d\d\])", diagnostic) if line.strip()]
    reviewed, unreviewed, review_issues, review_identity = review_diagnostics(records, run, manifest, diagnostic_review)
    blockers.extend(review_issues)
    court_reviewed, unreviewed, court_issues, court_identity = apply_court_review(unreviewed, run, court_diagnostic_review)
    reviewed.extend(court_reviewed)
    blockers.extend(court_issues)
    if unreviewed:
        blockers.append("Engine error.log contains unreviewed diagnostics; exact scoped review is required.")
    if not exact_current:
        blockers.append("Authoring source has changed; this run is historical smoke, not current-source acceptance.")
    saves = {p.relative_to(profile).as_posix(): sha(p)
             for p in sorted((profile / "save games").glob("*.ck3")) if p.is_file()}
    if not saves:
        blockers.append("Native save/reload has no preserved local save artifact.")
    observations = re.findall(r"TNI_OBSERVE\|(contract_[a-z_]+)\|([A-Z_]+)", text)
    timing = []
    for name in ("quote_10", "autobalance"):
        samples = re.findall(r"(?m)^\[(\d\d):(\d\d):(\d\d)\].*TNI_TIMING\|(BEGIN|END)\|" + name + r"\s*$", text)
        if samples:
            valid = [sample[3] for sample in samples] == ["BEGIN", "END"]
            elapsed = None
            if valid:
                start, end = (int(h) * 3600 + int(m) * 60 + int(s) for h, m, s, _ in samples)
                elapsed = (end - start) % 86400
            timing.append({"name": name, "exact_boundaries": valid,
                           "elapsed_seconds_from_log": elapsed,
                           "resolution_seconds": 1,
                           "interpretation": "Coarse native log timestamps; not a subsecond profiler or visual responsiveness proof."})
    report = {
        "status": "PASS" if not blockers else "FAIL",
        "acceptance_classification": "PASS_WITH_SCOPED_DIAGNOSTICS_REVIEW" if not blockers and reviewed else ("PASS" if not blockers else "FAIL"),
        "native_assertions": "PASS" if passes == Counter(expected) and not fails and boundary == {"BEGIN": 1, "END": 1} else "FAIL",
        "run": str(run), "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_manifest_sha256": sha(run / "frozen-manifest.json"),
        "process": process, "game_version": manifest["game_version"], "preset": manifest["preset"],
        "source_exact_current": exact_current, "expected_count": len(expected),
        "pass_count": sum(passes.values()), "passes": dict(passes), "failures": dict(fails),
        "missing": [label for label in expected if passes[label] != 1],
        "unexpected": [label for label in passes if label not in expected],
        "log_sha256": {p.name: sha(p) for p in (log, error) if p.exists()},
        "native_save_sha256": saves, "diagnostic_count": len(records),
        "contract_observations": dict(observations), "timing": timing,
        "inspector_sha256": sha(Path(__file__)),
        "unreviewed_diagnostics": unreviewed, "reviewed_diagnostics": reviewed,
        "diagnostic_review": review_identity, "blockers": blockers,
        "court_diagnostic_review": court_identity,
        "coverage_limits": manifest["coverage_limits"],
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diagnostic-review", type=Path)
    parser.add_argument("--court-diagnostic-review", type=Path)
    configuration.add_arguments(parser)
    args = parser.parse_args()
    configuration.configure(args)
    result = inspect(args.run.resolve(), args.diagnostic_review, args.court_diagnostic_review)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "pass_count": result["pass_count"],
                      "expected_count": result["expected_count"], "blockers": result["blockers"]}))
