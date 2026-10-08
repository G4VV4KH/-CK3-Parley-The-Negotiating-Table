"""Create an immutable, exact-source functional interest matrix; never launch."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from inspect_interest_probe import inspect, inventory, sha, configuration


def aggregate(report_paths):
    problems, rows, snapshots, all_limits = [], [], [], set()
    presets = set()
    for path in report_paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        run = Path(report["run"])
        manifest_path = run / "frozen-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        diagnostic = report.get("diagnostic_review")
        court = report.get("court_diagnostic_review")
        fresh = inspect(run, Path(diagnostic["path"]) if diagnostic else None,
                        Path(court["path"]) if court else None)
        if (report["status"] != "PASS" or fresh["status"] != "PASS"
                or report["log_sha256"] != fresh["log_sha256"]
                or report["frozen_manifest_sha256"] != sha(manifest_path)):
            problems.append(run.name + ": report is not an unchanged, currently verified PASS.")
        if report["preset"] in presets:
            problems.append("Duplicate preset " + report["preset"])
        presets.add(report["preset"])
        snapshots.append(manifest["runtime_sha256"])
        all_limits.update(report["coverage_limits"])
        rows.append({"preset": report["preset"], "run": str(run), "status": fresh["status"],
                     "native_assertions": fresh["native_assertions"],
                     "assertion_count": report["expected_count"],
                     "report": {"path": str(path.resolve()), "sha256": sha(path)},
                     "manifest_sha256": sha(manifest_path), "logs_sha256": fresh["log_sha256"],
                     "process_record_sha256": sha(run / "process-result.json"),
                     "reviewed_diagnostic_count": len(fresh["reviewed_diagnostics"]),
                     "unreviewed_diagnostic_count": len(fresh["unreviewed_diagnostics"]),
                     "timing": fresh["timing"]})
    if presets != {"off", "mild", "standard", "strict"}:
        problems.append("Matrix must contain exactly the four interest presets.")
    same = bool(snapshots) and all(item == snapshots[0] for item in snapshots)
    if not same:
        problems.append("Runs do not share the same complete runtime bytes.")
    source = Path(manifest["runtime_source"])
    current = inventory(source)
    if not same or current != snapshots[0] or len(current) != 88:
        problems.append("Current authoring source is not the exact tested 88-file runtime.")
    total = sum(row["assertion_count"] for row in rows)
    if total != 352:
        problems.append("Expected final matrix scope is 352 native assertions.")
    fingerprint = hashlib.sha256(json.dumps(current, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    # A pre-execution limitation inherited from the plan is now superseded by
    # actual stopped-run evidence, never by preparation or static success.
    all_limits.discard("Native NOT_RUN until isolated execution.")
    all_limits.update({
        "PASS is scoped functional native acceptance with explicitly reviewed diagnostics, not a clean-log claim.",
        "Court initialization diagnostics occurred under a feature-Off control; vanilla-only root cause is not proven.",
        "Standard rich reload changed native monthly expenses; independent pre/post capacity, gold utility and whole-score oracles pass. Exact quote equality is conditional on unchanged valuation inputs.",
        "Standard001/002 failed unconditional quote identity and remain preserved; Standard003 diagnoses the input change, not a production code fix.",
        "Visual layout/hover/manual interaction and multiplayer remain NOT_VERIFIED.",
    })
    return {"schema_version": 1, "status": "PASS_WITH_SCOPED_DIAGNOSTICS_REVIEW" if not problems else "FAIL",
            "scope": "EXACT_SOURCE_NATIVE_FUNCTIONAL_INTEREST_MATRIX_WITH_SCOPED_DIAGNOSTIC_REVIEW",
            "recorded_utc": datetime.now(timezone.utc).isoformat(),
            "game_version": manifest["game_version"], "executable_sha256": manifest["executable_sha256"],
            "runtime_source": str(source), "runtime_files": len(current),
            "runtime_fingerprint_sha256": fingerprint,
            "fingerprint_format": "SHA256 UTF-8 JSON sorted relative-path:SHA256 map, separators comma/colon",
            "all_runs_same_runtime": same, "source_exact_current": same and current == snapshots[0],
            "native_assertion_count": total, "runs": rows,
            "coverage_limits": sorted(all_limits), "blockers": problems,
            "aggregator_sha256": sha(Path(__file__))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs=4, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    configuration.add_arguments(parser)
    args = parser.parse_args()
    configuration.configure(args)
    result = aggregate(args.reports)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in ("status", "runtime_files", "native_assertion_count", "blockers")}))
