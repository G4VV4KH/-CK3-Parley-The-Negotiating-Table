#!/usr/bin/env python3
"""Freeze a Parley 1.3.0 runtime candidate, never a publication-ready kit.

The current working tree (including untracked runtime files) is the input, not
HEAD. A check is read-only. Freezing requires its exact reviewed fingerprint and
a new directory. Only the established build_game diagnostic projection is used.
No archives, uploads, native launch, registry changes or acceptance are produced.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

VERSION = "1.3.0"
TARGET = "1.20.0.4"
TITLE = "Parley: The Negotiating Table"
STATUS = "CANDIDATE_PREPARED_LOCALIZATION_AND_NATIVE_ACCEPTANCE_PENDING"
RUNTIME_PATHS = frozenset("""
common/character_interactions/tnt_10_interaction.txt
common/character_interactions/tnt_12_marriage_picker.txt
common/decision_group_types/tnt_92_decision_groups.txt
common/decisions/tnt_85_decisions.txt
common/decisions/tnt_86_uninstall.txt
common/game_rules/tnt_80_game_rules.txt
common/game_rules/tnt_81_ai_rules.txt
common/hook_types/tnt_90_hook_types.txt
common/important_actions/tnt_91_alerts.txt
common/on_action/tnt_70_on_actions.txt
common/on_action/tnt_71_ai.txt
common/on_action/tnt_72_ai_world.txt
common/on_action/tnt_73_intro.txt
common/opinion_modifiers/tnt_61_opinions.txt
common/customizable_localization/tnt_90_cooldown_loc.txt
common/script_values/tnt_50_values.txt
common/script_values/tnt_51_relation_values.txt
common/script_values/tnt_52_marriage_values.txt
common/script_values/tnt_53_currency_values.txt
common/script_values/tnt_54_multiselect_values.txt
common/script_values/tnt_55_hc_values.txt
common/script_values/tnt_56_ai_values.txt
common/script_values/tnt_57_threat_values.txt
common/script_values/tnt_58_person_values.txt
common/script_values/tnt_59_usehook_values.txt
common/script_values/tnt_5a_stress_values.txt
common/script_values/tnt_5b_scaled_land_values.txt
common/script_values/tnt_5c_scaled_person_values.txt
common/script_values/tnt_5d_scaled_strategic_values.txt
common/script_values/tnt_5e_display_values.txt
common/script_values/tnt_5e_valuation_policy.txt
common/script_values/tnt_5f_scaled_balance_values.txt
common/script_values/tnt_60_interest_policy.txt
common/script_values/tnt_61_interest_currency_values.txt
common/script_values/tnt_62_interest_advanced_values.txt
common/script_values/tnt_63_interest_ledger_values.txt
common/script_values/tnt_64_interest_ai_values.txt
common/script_values/tnt_65_interest_preview_values.txt
common/scripted_effects/tnt_1f_addon_hooks.txt
common/scripted_effects/tnt_30_effects.txt
common/scripted_effects/tnt_31_lists.txt
common/scripted_effects/tnt_32_apply.txt
common/scripted_effects/tnt_33_currency_apply.txt
common/scripted_effects/tnt_34_marriage.txt
common/scripted_effects/tnt_35_multiselect.txt
common/scripted_effects/tnt_35a_sort.txt
common/scripted_effects/tnt_36_hooks_contracts.txt
common/scripted_effects/tnt_37_ai_offer.txt
common/scripted_effects/tnt_38_ai_world.txt
common/scripted_effects/tnt_39_autobalance.txt
common/scripted_effects/tnt_3a_people.txt
common/scripted_effects/tnt_3b_log.txt
common/scripted_effects/tnt_3c_stress.txt
common/scripted_guis/tnt_20_scripted_guis.txt
common/scripted_guis/tnt_21_pickers.txt
common/scripted_guis/tnt_22_v2.txt
common/scripted_guis/tnt_22a_marriage.txt
common/scripted_guis/tnt_22b_multiselect.txt
common/scripted_guis/tnt_22c_hooks_contracts.txt
common/scripted_guis/tnt_23_usehook.txt
common/scripted_guis/tnt_24_people.txt
common/scripted_triggers/tnt_40_triggers.txt
common/scripted_triggers/tnt_41_gates.txt
common/scripted_triggers/tnt_42_people_gates.txt
common/scripted_triggers/tnt_43_preflight.txt
data_binding/tnt_macros.txt
descriptor.mod
events/tnt_ai_events.txt
events/tnt_events.txt
events/tnt_intro_events.txt
gui/event_window_widgets/tnt_offer_summary.gui
gui/scripted_widgets/tnt_diplomacy.txt
gui/tnt_diplomacy_window.gui
gui/tnt_panel_contract.gui
gui/tnt_panel_marriage.gui
gui/tnt_panel_multiselect.gui
gui/tnt_panel_people.gui
gui/tnt_panels.gui
gui/tnt_types.gui
localization/english/tnt_l_english.yml
localization/french/tnt_l_french.yml
localization/german/tnt_l_german.yml
localization/japanese/tnt_l_japanese.yml
localization/korean/tnt_l_korean.yml
localization/polish/tnt_l_polish.yml
localization/russian/tnt_l_russian.yml
localization/simp_chinese/tnt_l_simp_chinese.yml
localization/spanish/tnt_l_spanish.yml
thumbnail.png
""".split())
PENDING = {
    "publication_ready": False,
    "localization_acceptance": "NOT_VERIFIED",
    "native_game_candidate_acceptance": "NOT_VERIFIED",
    "visual_acceptance": "NOT_VERIFIED",
    "external_publication": "NOT_ATTEMPTED",
    "reason": "Static key parity is not translation review or native localization resolution. "
              "All nine languages and the exact generated GAME runtime require separate acceptance. "
              "This is not a GitHub source export or upload kit; dirty source is recorded, not approved.",
}


class CandidateError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise CandidateError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def inventory(files):
    return {name: {"bytes": len(data), "sha256": sha(data)} for name, data in sorted(files.items())}


def regular(path):
    require(not path.is_symlink() and not getattr(path.lstat(), "st_file_attributes", 0) & 0x400,
            f"Linked/reparse input is forbidden: {path}")


def tree(root):
    require(root.is_dir(), f"Missing tree: {root}")
    regular(root)
    result = {}
    for path in sorted(root.rglob("*")):
        regular(path)
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def validate_runtime(files):
    require(set(files) == RUNTIME_PATHS,
            f"Runtime inventory differs: missing={sorted(RUNTIME_PATHS - files.keys())}; "
            f"extra={sorted(files.keys() - RUNTIME_PATHS)}")
    text = files["descriptor.mod"].decode("utf-8-sig")
    for key, expected in (("version", VERSION), ("name", TITLE), ("supported_version", "1.20.*")):
        require(re.findall(rf'^\s*{key}\s*=\s*"([^"\r\n]+)"', text, re.M) == [expected],
                f"Descriptor {key} must be exactly {expected}")
    require(not re.search(r'^\s*(?:path|archive|remote_file_id)\s*=', text, re.M),
            "Candidate descriptor must be portable and have no remote identity overlay")


def load_builder(path):
    regular(path)
    spec = importlib.util.spec_from_file_location("parley_130_candidate_builder", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(module.PARLEY_LOCALIZATION_COUNTS.get(VERSION) == (730, 720),
            "Builder lacks the reviewed 730→720 Parley 1.3.0 localization profile")
    return module


def validate_projection(builder, files):
    inputs = {"parley": files}
    lock = {"schema": 1, "mods": {"parley": {"files": inventory(files)}}}
    builder.validate_lock_inputs(inputs, lock, ("parley",))
    outputs, transforms = builder.project(inputs)
    require(set(outputs["parley"]) == RUNTIME_PATHS - {builder.LOG_FILE}, "Unexpected GAME inventory")
    builder.validate_no_diagnostics(outputs)
    coverage = builder.validate_localizations(outputs)
    builder.public_setting_proof(inputs, outputs)
    builder.negative_controls(inputs, outputs, lock)
    builder.transform_totals(transforms)
    return outputs["parley"], coverage


def git_state(repo):
    def run(*args):
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
        return result.stdout.decode("utf-8")
    return {"head": run("rev-parse", "HEAD").strip(),
            "branch": run("branch", "--show-current").strip(),
            "porcelain": run("status", "--porcelain=v1", "--untracked-files=all")}


def inspect_source(repo):
    files = tree(repo / "mod/parley")
    validate_runtime(files)
    builder_path = Path(__file__).parent / "build_game.py"
    builder = load_builder(builder_path)
    game, coverage = validate_projection(builder, files)
    tools = {"build_game.py": builder_path.read_bytes(), Path(__file__).name: Path(__file__).read_bytes()}
    evidence = {"version": VERSION, "target_game_version": TARGET,
                "source_repo": str(repo.absolute()), "source_runtime": inventory(files),
                "source_runtime_sha256": sha(json_bytes(inventory(files))),
                "game_runtime": inventory(game), "game_runtime_sha256": sha(json_bytes(inventory(game))),
                "tool_inventory": inventory(tools), "static_localization_coverage": coverage,
                "git_observation": git_state(repo), "acceptance": PENDING}
    # The review pin covers bytes and tools, not mutable Git metadata or timestamps.
    evidence["source_fingerprint_sha256"] = sha(json_bytes({
        "runtime": evidence["source_runtime"], "tools": evidence["tool_inventory"]}))
    return files, tools, evidence


def safe_output(repo, output):
    require(not output.exists(), f"Refusing existing candidate path: {output}")
    a, b = repo.resolve(), output.resolve()
    require(a != b and a not in b.parents and b not in a.parents, "Candidate output overlaps source repository")


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def run_builder(output, build_id, *flags):
    command = [sys.executable, "-B", str(output / "tools/build_game.py"),
               "--dev-root", str(output / "source/dev"), "--output-root", str(output / "game"),
               "--lock", str(output / "source-lock.json"), "--mods", "parley", "--build-id", build_id, *flags]
    result = subprocess.run(command, capture_output=True, text=True)
    require(result.returncode == 0, f"Frozen builder failed: {result.stdout}\n{result.stderr}")
    return {"command": command, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


def freeze(repo, output, build_id, expected_source_sha256):
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", build_id) is not None, "Unsafe build id")
    safe_output(repo, output)
    files, tools, evidence = inspect_source(repo)
    require(evidence["source_fingerprint_sha256"] == expected_source_sha256,
            "Source/tool fingerprint drifted from the explicit reviewed check")
    # No candidate directory exists until all in-memory projection checks pass.
    output.mkdir(parents=True)
    for name, data in files.items():
        write_new(output / "source/dev/parley/mod/parley" / name, data)
    for name, data in tools.items():
        write_new(output / "tools" / name, data)
    lock = {"schema": 1, "baseline": f"Parley {VERSION} candidate; acceptance pending",
            "mods": {"parley": {"files": evidence["source_runtime"]}}}
    write_new(output / "source-lock.json", json_bytes(lock))
    checks = [run_builder(output, build_id, "--check"), run_builder(output, build_id),
              run_builder(output, build_id, "--verify")]
    # Detect writes during preparation. Failed partial output is kept as evidence, never reused.
    require(tree(repo / "mod/parley") == files, "Authoring runtime changed during freeze")
    require(all((Path(__file__).parent / name).read_bytes() == data for name, data in tools.items()),
            "Candidate tooling changed during freeze")
    generated = tree(output / "game" / build_id / "parley")
    require(inventory(generated) == evidence["game_runtime"], "Frozen GAME bytes differ from check")
    write_new(output / "builder-checks.json", json_bytes(checks))
    artifacts = inventory(tree(output))
    manifest = {"schema": "parley-1.3-candidate-v1", "status": STATUS,
                "created_utc": datetime.now(timezone.utc).isoformat(), "build_id": build_id,
                **evidence, "artifacts": artifacts}
    manifest_bytes = json_bytes(manifest)
    write_new(output / "candidate-manifest.json", manifest_bytes)
    return {"status": STATUS, "manifest": str(output / "candidate-manifest.json"),
            "manifest_sha256": sha(manifest_bytes), "source_fingerprint_sha256": expected_source_sha256,
            "game_runtime_sha256": evidence["game_runtime_sha256"], "acceptance": PENDING}


def verify(output, expected_manifest_sha256):
    regular(output / "candidate-manifest.json")
    raw = (output / "candidate-manifest.json").read_bytes()
    require(sha(raw) == expected_manifest_sha256, "Candidate manifest hash differs from explicit reviewed pin")
    manifest = json.loads(raw)
    require(manifest.get("schema") == "parley-1.3-candidate-v1" and manifest.get("status") == STATUS,
            "Unknown candidate schema/status")
    require(manifest.get("acceptance") == PENDING, "Candidate cannot assert publication acceptance")
    files = tree(output)
    del files["candidate-manifest.json"]
    require(inventory(files) == manifest["artifacts"], "Frozen candidate artifact inventory/bytes drift")
    source = tree(output / "source/dev/parley/mod/parley")
    validate_runtime(source)
    require(inventory(source) == manifest["source_runtime"], "Source runtime differs from manifest")
    require(sha(json_bytes(inventory(source))) == manifest["source_runtime_sha256"], "Source fingerprint mismatch")
    require(sha((output / "tools/build_game.py").read_bytes()) == manifest["tool_inventory"]["build_game.py"]["sha256"],
            "Frozen builder hash mismatch")
    game = tree(output / "game" / manifest["build_id"] / "parley")
    require(inventory(game) == manifest["game_runtime"], "GAME runtime differs from manifest")
    require(sha(json_bytes(inventory(game))) == manifest["game_runtime_sha256"], "GAME fingerprint mismatch")
    result = run_builder(output, manifest["build_id"], "--verify")
    return {"status": "CANDIDATE_INTEGRITY_VERIFIED_ACCEPTANCE_STILL_PENDING",
            "manifest_sha256": expected_manifest_sha256, "builder_verification": result, "acceptance": PENDING}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Read-only source and deterministic projection checks")
    mode.add_argument("--freeze", action="store_true", help="Write a new candidate, never a distribution kit")
    mode.add_argument("--verify", action="store_true", help="Read-only integrity check of an already pinned candidate")
    parser.add_argument("--source-repo", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--build-id")
    parser.add_argument("--expected-source-sha256")
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args(argv)
    if args.verify:
        require(args.output and args.expected_manifest_sha256, "--verify requires --output and --expected-manifest-sha256")
        result = verify(args.output, args.expected_manifest_sha256)
    else:
        require(args.source_repo is not None, "--source-repo is required")
        if args.check:
            _, _, result = inspect_source(args.source_repo)
            result = {"status": "CHECKED_IN_MEMORY_ACCEPTANCE_PENDING", **result}
        else:
            require(args.output and args.build_id and args.expected_source_sha256,
                    "--freeze requires --output, --build-id and --expected-source-sha256")
            result = freeze(args.source_repo, args.output, args.build_id, args.expected_source_sha256)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CandidateError, OSError, UnicodeError, ValueError, subprocess.SubprocessError) as error:
        print(f"CANDIDATE PREPARATION FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
