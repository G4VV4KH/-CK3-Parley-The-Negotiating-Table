#!/usr/bin/env python3
"""Build and verify selected CK3 game payloads from pinned dev runtime bytes.

Python standard library only. Never writes to dev inputs. Diagnostics are removed
by token spans, so comments, quoted strings, BOMs and untouched newlines survive.
The sibling release-inputs.json is the complete, self-contained input allowlist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

MODS = ("parley", "marriage_calc_assistant", "agot_marriage_calc_assistant")
LANGUAGES = ("english", "french", "german", "japanese", "korean", "polish",
             "russian", "simp_chinese", "spanish")
RUNTIME_ROOTS = {"common", "data_binding", "events", "gui", "localization",
                 "descriptor.mod", "thumbnail.png"}
SCRIPT_SUFFIXES = {".txt", ".gui", ".mod"}
LOG_FILE = "common/scripted_effects/tnt_3b_log.txt"
APPLY_FILE = "common/scripted_effects/tnt_32_apply.txt"
RULE_FILE = "common/game_rules/tnt_81_ai_rules.txt"
INTRO_FILE = "events/tnt_intro_events.txt"
OFFER_FILE = "common/scripted_effects/tnt_37_ai_offer.txt"
EVENT_FILE = "events/tnt_ai_events.txt"
UNINSTALL_FILE = "common/decisions/tnt_86_uninstall.txt"
TEST_SETTING = "tnt_ai_offer_rate_test"
LOG_VARIABLES = {"tnt_log_b", "tnt_log_c1", *(f"tnt_log_n{i}" for i in range(1, 10))}
LOG_NAME = re.compile(r"tnt_log_\w+_effect\Z")
LOC_KEY = re.compile(r"^\s*([^\s:#]+):[0-9]*\s+\"")
REMOVED_LOC = {
    "rule_tnt_ai_telemetry",
    "setting_tnt_ai_telemetry_off", "setting_tnt_ai_telemetry_off_desc",
    "setting_tnt_ai_telemetry_on", "setting_tnt_ai_telemetry_on_desc",
    "setting_tnt_ai_telemetry_verbose", "setting_tnt_ai_telemetry_verbose_desc",
    "setting_tnt_ai_offer_rate_test", "setting_tnt_ai_offer_rate_test_desc",
    "tnt_intro_desc_rate_test",
}
EXPECTED_CALLS = {
    EVENT_FILE: 12, "common/on_action/tnt_70_on_actions.txt": 1,
    APPLY_FILE: 1, "common/scripted_effects/tnt_34_marriage.txt": 1,
    OFFER_FILE: 14, "common/scripted_effects/tnt_38_ai_world.txt": 43,
}
EXPECTED_TEST_CHECKS = {EVENT_FILE: 3, OFFER_FILE: 5}
PARLEY_LOCALIZATION_COUNTS = {
    "1.1.0": (632, 622),
    "1.2.0": (642, 632),
    "1.2.1": (662, 652),
    "1.2.2": (662, 652),
    "1.3.0": (730, 720),
}


class ReleaseError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def selected_mods(names, label="mod selection") -> tuple[str, ...]:
    require(isinstance(names, (dict, list, tuple)) and bool(names), f"Empty or invalid {label}")
    require(len(names) == len(set(names)) and set(names) <= set(MODS), f"Unknown or duplicate {label}")
    return tuple(mod for mod in MODS if mod in names)


@dataclass(frozen=True)
class Token:
    value: str
    start: int
    end: int
    kind: str = "word"


def lex(text: str) -> list[Token]:
    """Lex Clausewitz/Jomini text; never interpret comments or quoted strings."""
    result = []
    i = 0
    while i < len(text):
        c = text[i]
        if c.isspace() or c == "\ufeff":
            i += 1
        elif c == "#":
            newline = text.find("\n", i)
            i = len(text) if newline < 0 else newline
        elif c == '"':
            start = i
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                elif text[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise ReleaseError(f"Unterminated quoted string at character {start}")
            require(i <= len(text), "Quoted string ends with an incomplete escape")
            result.append(Token(text[start:i], start, i, "string"))
        elif c in "{}=<>!?":
            start = i
            i += 1
            if c in "<>!?" and i < len(text) and text[i] == "=":
                i += 1
            result.append(Token(text[start:i], start, i, "symbol"))
        else:
            start = i
            while i < len(text) and not text[i].isspace() and text[i] not in '{}=<>!?#"':
                i += 1
            result.append(Token(text[start:i], start, i))
    return result


def brace_pairs(tokens: list[Token]) -> tuple[dict[int, int], dict[int, int]]:
    stack = []
    pairs, depths = {}, {}
    for i, token in enumerate(tokens):
        depths[i] = len(stack)
        if token.value == "{" and token.kind == "symbol":
            stack.append(i)
        elif token.value == "}" and token.kind == "symbol":
            require(bool(stack), f"Unmatched closing brace at {token.start}")
            pairs[stack.pop()] = i
    require(not stack, "Unclosed script block")
    return pairs, depths


def assignments(tokens: list[Token]):
    for i in range(len(tokens) - 2):
        if tokens[i].kind == "word" and tokens[i + 1].value == "=":
            yield i, tokens[i].value, tokens[i + 2].value


def edit_text(text: str, edits: list[tuple[int, int, str]]) -> str:
    cursor, chunks = 0, []
    for start, end, replacement in sorted(edits):
        require(cursor <= start < end <= len(text), "Overlapping or invalid transform spans")
        chunks.extend((text[cursor:start], replacement))
        cursor = end
    chunks.append(text[cursor:])
    return "".join(chunks)


def transform_script(path: str, data: bytes) -> tuple[bytes | None, dict]:
    text = data.decode("utf-8")  # keep a BOM as U+FEFF, round-trip it unchanged
    tokens = lex(text)
    pairs, depths = brace_pairs(tokens)
    rows = list(assignments(tokens))
    report = {"log_definitions_removed": 0, "log_calls_removed": 0,
              "telemetry_rules_removed": 0, "test_options_removed": 0,
              "test_checks_false": 0, "test_intro_blocks_removed": 0,
              "diagnostic_variable_exists_removed": 0, "diagnostic_variable_cleanup_removed": 0}
    edits = []
    removed_exists, removed_cleanup = [], []

    def remove_block(i: int) -> None:
        require(tokens[i + 2].value == "{", f"Expected block: {path}:{tokens[i].start}")
        edits.append((tokens[i].start, tokens[pairs[i + 2]].end, ""))

    if path == LOG_FILE:
        definitions = [(i, name) for i, name, value in rows if LOG_NAME.fullmatch(name)
                       and value == "{" and depths[i] == 0]
        require(len(definitions) == 75, "Logger file must have exactly 75 top-level helpers")
        covered = set()
        for i, _ in definitions:
            covered.update(range(i, pairs[i + 2] + 1))
        require(covered == set(range(len(tokens))), "Logger file contains non-helper active code")
        report["log_definitions_removed"] = len(definitions)
        report["internal_log_calls_removed_with_file"] = sum(
            bool(LOG_NAME.fullmatch(name) and value == "yes") for _, name, value in rows)
        report["log_emitters_removed"] = sum(name == "error_log" for _, name, _ in rows)
        require(report["internal_log_calls_removed_with_file"] == 6, "Logger internal calls changed")
        require(report["log_emitters_removed"] == 188, "Logger emitters changed")
        return None, report

    for i, name, value in rows:
        if LOG_NAME.fullmatch(name) and value == "{":
            require(path == APPLY_FILE and name == "tnt_log_preflight_fail_effect" and depths[i] == 0,
                    f"Unexpected logging definition in {path}: {name}")
            body_rows = list(assignments(tokens[i + 3:pairs[i + 2]]))
            report["log_emitters_removed"] = sum(key == "error_log" for _, key, _ in body_rows)
            require(report["log_emitters_removed"] == 3, "Preflight logging emitters changed")
            remove_block(i)
            report["log_definitions_removed"] += 1
        elif name == "tnt_ai_telemetry":
            require(path == RULE_FILE and depths[i] == 0, "Unexpected telemetry rule location")
            remove_block(i)
            report["telemetry_rules_removed"] += 1
        elif name == TEST_SETTING:
            require(path == RULE_FILE and value == "{" and depths[i] == 1,
                    "Unexpected test option location")
            require(pairs[i + 2] == i + 3, "Test option is no longer an empty rule option")
            remove_block(i)
            report["test_options_removed"] += 1
        elif path == INTRO_FILE and name == "triggered_desc" and value == "{":
            end = pairs[i + 2]
            body = [x.value for x in tokens[i + 3:end]]
            if TEST_SETTING in body:
                require(body == ["trigger", "=", "{", "has_game_rule", "=", TEST_SETTING,
                                 "}", "desc", "=", "tnt_intro_desc_rate_test"],
                        "Diagnostic intro structure changed; refusing broad deletion")
                remove_block(i)
                report["test_intro_blocks_removed"] += 1

    block_spans = [(a, b) for a, b, _ in edits]
    for i, name, value in rows:
        if any(a <= tokens[i].start < b for a, b in block_spans):
            continue
        if LOG_NAME.fullmatch(name):
            require(value == "yes", f"Unsupported logging call in {path}: {name}")
            edits.append((tokens[i].start, tokens[i + 2].end, ""))
            report["log_calls_removed"] += 1
        elif name == "has_game_rule" and value == TEST_SETTING:
            # Only replace this trigger. NOT, trigger_if, if/else and cooldown
            # bodies retain their positions and behave as a public rate did.
            edits.append((tokens[i].start, tokens[i + 2].end, "always = no"))
            report["test_checks_false"] += 1
        elif name == "exists" and value in {"var:" + variable for variable in LOG_VARIABLES}:
            require(path == UNINSTALL_FILE, f"Unexpected surviving diagnostic-variable reader in {path}")
            edits.append((tokens[i].start, tokens[i + 2].end, ""))
            removed_exists.append(value.removeprefix("var:"))
            report["diagnostic_variable_exists_removed"] += 1
        elif name == "remove_variable" and value in LOG_VARIABLES:
            require(path == UNINSTALL_FILE, f"Unexpected surviving diagnostic-variable cleanup in {path}")
            edits.append((tokens[i].start, tokens[i + 2].end, ""))
            removed_cleanup.append(value)
            report["diagnostic_variable_cleanup_removed"] += 1

    require(report["log_calls_removed"] == EXPECTED_CALLS.get(path, 0),
            f"Unexpected external log-call count in {path}: {report['log_calls_removed']}")
    require(report["test_checks_false"] == EXPECTED_TEST_CHECKS.get(path, 0),
            f"Unexpected test-check count in {path}: {report['test_checks_false']}")
    require(report["log_definitions_removed"] == (1 if path == APPLY_FILE else 0),
            f"Unexpected extra-helper count in {path}")
    require(report["telemetry_rules_removed"] == (1 if path == RULE_FILE else 0),
            f"Unexpected telemetry-rule count in {path}")
    require(report["test_options_removed"] == (1 if path == RULE_FILE else 0),
            f"Unexpected test-option count in {path}")
    require(report["test_intro_blocks_removed"] == (1 if path == INTRO_FILE else 0),
            f"Unexpected test-intro count in {path}")
    expected_variables = LOG_VARIABLES if path == UNINSTALL_FILE else set()
    require(len(removed_exists) == len(expected_variables) and set(removed_exists) == expected_variables,
            f"Unexpected diagnostic-variable exists atoms in {path}")
    require(len(removed_cleanup) == len(expected_variables) and set(removed_cleanup) == expected_variables,
            f"Unexpected diagnostic-variable cleanup statements in {path}")
    projected = edit_text(text, edits).encode("utf-8")
    brace_pairs(lex(projected.decode("utf-8")))
    return projected, report


def localization_keys(data: bytes, label: str) -> set[str]:
    text = data.decode("utf-8-sig")
    matches = [LOC_KEY.match(line) for line in text.splitlines()]
    keys = [match.group(1) for match in matches if match]
    require(len(keys) == len(set(keys)), f"Duplicate localization key in {label}")
    return set(keys)


def parley_localization_counts(files: dict) -> tuple[int, int]:
    versions = re.findall(r'^\s*version\s*=\s*"([^"\r\n]+)"',
                          files["descriptor.mod"].decode("utf-8-sig"), re.M)
    require(len(versions) == 1 and versions[0] in PARLEY_LOCALIZATION_COUNTS,
            "Unreviewed Parley version for localization projection")
    return PARLEY_LOCALIZATION_COUNTS[versions[0]]


def transform_localization(path: str, data: bytes, counts=(632, 622)) -> tuple[bytes, dict]:
    text = data.decode("utf-8")
    kept, removed = [], []
    for line in text.splitlines(keepends=True):
        match = LOC_KEY.match(line.lstrip("\ufeff"))
        key = match.group(1) if match else None
        if key in REMOVED_LOC:
            removed.append(key)
        else:
            kept.append(line)
    require(len(removed) == 10 and set(removed) == REMOVED_LOC,
            f"Expected exactly 10 diagnostic localization keys in {path}")
    result = "".join(kept).encode("utf-8")
    # The AGOT-only failure message is parked as a comment in every language.
    require(len(localization_keys(data, path)) == counts[0], f"Unexpected dev localization count: {path}")
    require(len(localization_keys(result, path)) == counts[1], f"Unexpected game localization count: {path}")
    return result, {"localization_keys_removed": sorted(removed)}


def validate_lock_inputs(inputs: dict, lock: dict, mods=None) -> None:
    selection = selected_mods(inputs if mods is None else mods)
    locked = selected_mods(lock.get("mods", {}), "source-lock mod inventory")
    require(set(selection) <= set(locked), "Source lock does not include every selected mod")
    require(set(inputs) == set(selection), "Source mod inventory differs from selection")
    for mod in selection:
        expected = lock["mods"][mod]["files"]
        require(set(inputs[mod]) == set(expected), f"Source runtime inventory differs: {mod}")
        for path, data in inputs[mod].items():
            item = expected[path]
            require(len(data) == item["bytes"] and digest(data) == item["sha256"],
                    f"Source runtime bytes differ from pinned checked build: {mod}/{path}")


def load_inputs(dev_root: Path, lock: dict, mods=MODS) -> dict:
    inputs = {}
    for mod in selected_mods(mods):
        root = dev_root / mod / "mod" / mod
        require(root.is_dir(), f"Missing dev runtime folder: {root}")
        files = {}
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root)
            if rel.parts[0] not in RUNTIME_ROOTS:
                continue
            require(not path.is_symlink(), f"Symlink/reparse input is not allowed: {path}")
            if hasattr(path, "is_junction"):
                require(not path.is_junction(), f"Junction input is not allowed: {path}")
            if path.is_file():
                files[rel.as_posix()] = path.read_bytes()
        inputs[mod] = files
    validate_lock_inputs(inputs, lock, mods)
    return inputs


def project(inputs: dict) -> tuple[dict, dict]:
    outputs, transforms = {}, {}
    for mod in selected_mods(inputs):
        files, changes = {}, {}
        counts = parley_localization_counts(inputs[mod]) if mod == "parley" else None
        for path, data in sorted(inputs[mod].items()):
            result, report = data, {}
            if mod == "parley" and Path(path).suffix in SCRIPT_SUFFIXES:
                result, report = transform_script(path, data)
            elif mod == "parley" and path.startswith("localization/"):
                result, report = transform_localization(path, data, counts)
            if result is not None:
                files[path] = result
            if result != data:
                changes[path] = {"action": "omit" if result is None else "transform", **report}
        outputs[mod], transforms[mod] = files, changes
    return outputs, transforms


def validate_localizations(outputs: dict) -> dict:
    evidence = {}
    for mod in selected_mods(outputs):
        by_language = {language: {} for language in LANGUAGES}
        for path, data in outputs[mod].items():
            if not path.startswith("localization/"):
                continue
            parts = path.split("/")
            require(len(parts) == 3 and parts[1] in by_language, f"Unexpected localization path: {path}")
            language = parts[1]
            require(path.endswith(f"_l_{language}.yml"), f"Unexpected localization filename: {path}")
            require(data.startswith(b"\xef\xbb\xbf"), f"Localization is missing UTF-8 BOM: {path}")
            require(data.decode("utf-8-sig").splitlines()[0] == f"l_{language}:",
                    f"Wrong localization language header: {path}")
            normalized = parts[2].replace(f"_l_{language}.yml", "_l_LANGUAGE.yml")
            by_language[language][normalized] = localization_keys(data, f"{mod}/{path}")
        reference = by_language["english"]
        require(len(reference) == 1, f"Expected one English localization file for {mod}")
        for language, files in by_language.items():
            require(files == reference, f"Localization file/key coverage mismatch: {mod}/{language}")
        count = sum(len(keys) for keys in reference.values())
        expected_count = (parley_localization_counts(outputs[mod])[1] if mod == "parley"
                          else {"marriage_calc_assistant": 22, "agot_marriage_calc_assistant": 5}[mod])
        require(count == expected_count, f"Wrong key count: {mod}")
        evidence[mod] = {"languages": list(LANGUAGES), "files_per_language": 1,
                         "keys_per_language": count}
    return evidence


def validate_no_diagnostics(outputs: dict) -> dict:
    for mod, files in outputs.items():
        for path, data in files.items():
            if Path(path).suffix not in SCRIPT_SUFFIXES:
                continue
            tokens = lex(data.decode("utf-8"))
            brace_pairs(tokens)
            for token in tokens:
                value = token.value
                require(not LOG_NAME.fullmatch(value), f"Logging helper leak: {mod}/{path}: {value}")
                require("tnt_ai_telemetry" not in value and TEST_SETTING not in value,
                        f"Diagnostic rule leak: {mod}/{path}: {value}")
                require("TNTLOG|" not in value, f"Telemetry string leak: {mod}/{path}")
                require("tnt_log_" not in value, f"Diagnostic variable/state leak: {mod}/{path}: {value}")
            for _, name, _ in assignments(tokens):
                require(name not in {"error_log", "debug_log", "info_log", "debug_log_scopes",
                                     "error_log_scopes", "info_log_scopes", "debug_log_stack_trace",
                                     "error_log_stack_trace", "info_log_stack_trace"},
                        f"Logging emitter leak: {mod}/{path}: {name}")
    return {"emitters": 0, "logging_helper_definitions_or_calls": 0,
            "diagnostic_rules": 0, "diagnostic_variable_references": 0}


def public_setting_proof(inputs: dict, outputs: dict) -> dict:
    """Check retained public rule choices/default and each replaced predicate."""
    if "parley" not in inputs:
        return {"status": "NOT_APPLICABLE", "reason": "Parley is not selected in this build."}
    source = inputs["parley"]
    game = outputs["parley"]
    def rate_choices(data: bytes):
        tokens = lex(data.decode("utf-8"))
        pairs, depths = brace_pairs(tokens)
        starts = [i for i, name, value in assignments(tokens)
                  if name == "tnt_ai_offer_rate" and value == "{" and depths[i] == 0]
        require(len(starts) == 1, "Expected exactly one letter-rate rule")
        start = starts[0]
        inside = tokens[start + 3:pairs[start + 2]]
        rows = list(assignments(inside))
        return [name for _, name, value in rows if name.startswith("tnt_ai_offer_rate_")], [
            value for _, name, value in rows if name == "default"]
    original_options, original_default = rate_choices(source[RULE_FILE])
    game_options, game_default = rate_choices(game[RULE_FILE])
    public = ["tnt_ai_offer_rate_off", "tnt_ai_offer_rate_rare", "tnt_ai_offer_rate_normal",
              "tnt_ai_offer_rate_frequent"]
    require(original_options == public + [TEST_SETTING] and game_options == public,
            "Public letter-rate rule options changed")
    require(original_default == game_default == ["tnt_ai_offer_rate_frequent"],
            "Public letter-rate default changed")
    truth_table = [{"public_setting": setting, "source_test_predicate": False,
                    "game_always_no": False, "negated_source_predicate": True,
                    "negated_game_always_no": True} for setting in public]
    return {"public_settings_unchanged": public, "default_unchanged": game_default[0],
            "active_gameplay_predicates_replaced": 8, "predicate_truth_table": truth_table,
            "method": "Only exact has_game_rule=test predicates become always=no. All surrounding "
                      "NOT, trigger_if, if/else, cooldown and gameplay tokens survive the projection. "
                      "The diagnostic intro's exact triggered_desc and localization are omitted.",
            "dev_test_saves": "The removed test preset is not a supported public configuration; "
                              "no claim of preserving its debug cooldown behavior."}


def exact_projection(actual: dict, expected: dict) -> None:
    require(set(actual) == set(expected), "Output mod inventory mismatch")
    for mod in selected_mods(expected):
        require(set(actual[mod]) == set(expected[mod]), f"Output file inventory mismatch: {mod}")
        for path in expected[mod]:
            require(actual[mod][path] == expected[mod][path], f"Output differs from exact projection: {mod}/{path}")


def expect_rejected(label: str, function) -> dict:
    try:
        function()
    except ReleaseError as error:
        return {"case": label, "result": "PASS", "rejected_because": str(error)}
    raise ReleaseError(f"Negative control was incorrectly accepted: {label}")


def negative_controls(inputs: dict, outputs: dict, lock: dict) -> list[dict]:
    if "parley" not in inputs:
        return subset_negative_controls(inputs, outputs, lock)
    controls = []
    changed = {mod: dict(files) for mod, files in outputs.items()}
    require(b"always = no" in changed["parley"][OFFER_FILE], "Missing generated predicate for negative control")
    changed["parley"][OFFER_FILE] = changed["parley"][OFFER_FILE].replace(b"always = no", b"always = yes", 1)
    controls.append(expect_rejected("altered non-diagnostic gameplay predicate",
                                    lambda: exact_projection(changed, outputs)))
    leaked = {mod: dict(files) for mod, files in outputs.items()}
    leaked["parley"][OFFER_FILE] += b'\nrelease_negative_control = { error_log = "TNTLOG|leak" }\n'
    controls.append(expect_rejected("active diagnostic emitter leak",
                                    lambda: validate_no_diagnostics(leaked)))
    variable_leaked = {mod: dict(files) for mod, files in outputs.items()}
    variable_leaked["parley"][UNINSTALL_FILE] += (
        b"\nrelease_negative_control = { exists = var:tnt_log_n1 remove_variable = tnt_log_n1 }\n")
    controls.append(expect_rejected("diagnostic variable without a setter leaked into uninstall",
                                    lambda: validate_no_diagnostics(variable_leaked)))
    source_changed = {mod: dict(files) for mod, files in inputs.items()}
    source_changed["parley"][OFFER_FILE] += b"\n# negative control: unexpected source change\n"
    controls.append(expect_rejected("source bytes differ from frozen allowlist",
                                    lambda: validate_lock_inputs(source_changed, lock)))
    loc_changed = {mod: dict(files) for mod, files in outputs.items()}
    loc_path = "localization/french/tnt_l_french.yml"
    loc_changed["parley"][loc_path] += b' release_negative_control_key:0 "extra"\n'
    controls.append(expect_rejected("one language contains an extra localization key",
                                    lambda: validate_localizations(loc_changed)))
    extra_file = {mod: dict(files) for mod, files in outputs.items()}
    extra_file["parley"]["README.md"] = b"This must not be in a game payload."
    controls.append(expect_rejected("documentation file leaked into game payload",
                                    lambda: exact_projection(extra_file, outputs)))
    # Lexer control: apparent calls in comments/strings cannot become edits.
    sample = '\ufeff# tnt_log_fake_effect = yes\r\nsample = "# tnt_log_fake_effect = yes { }"\r\n'
    projected, _ = transform_script("common/lexer_negative_control.txt", sample.encode("utf-8"))
    require(projected == sample.encode("utf-8"), "Lexer changed a quoted string/comment/BOM/CRLF")
    controls.append({"case": "comments, quoted hashes/braces, BOM and CRLF preservation", "result": "PASS"})
    return controls


def subset_negative_controls(inputs: dict, outputs: dict, lock: dict) -> list[dict]:
    """Keep integrity controls meaningful when Parley's transforms do not apply."""
    mod = selected_mods(outputs)[0]
    script = next(path for path in outputs[mod] if Path(path).suffix in SCRIPT_SUFFIXES)
    changed = {name: dict(files) for name, files in outputs.items()}
    changed[mod][script] += b"\n# unexpected payload change\n"
    controls = [expect_rejected("game payload bytes changed", lambda: exact_projection(changed, outputs))]
    leaked = {name: dict(files) for name, files in outputs.items()}
    leaked[mod][script] += b'\nrelease_negative_control = { error_log = "TNTLOG|leak" }\n'
    controls.append(expect_rejected("active diagnostic emitter leak", lambda: validate_no_diagnostics(leaked)))
    source_changed = {name: dict(files) for name, files in inputs.items()}
    source_changed[mod][script] += b"\n# unexpected source change\n"
    controls.append(expect_rejected("source bytes differ from frozen allowlist",
                                    lambda: validate_lock_inputs(source_changed, lock)))
    loc_changed = {name: dict(files) for name, files in outputs.items()}
    loc_path = next(path for path in outputs[mod] if path.startswith("localization/french/"))
    loc_changed[mod][loc_path] += b' release_negative_control_key:0 "extra"\n'
    controls.append(expect_rejected("one language contains an extra localization key",
                                    lambda: validate_localizations(loc_changed)))
    extra_file = {name: dict(files) for name, files in outputs.items()}
    extra_file[mod]["README.md"] = b"Not a game payload file."
    controls.append(expect_rejected("documentation file leaked into game payload",
                                    lambda: exact_projection(extra_file, outputs)))
    return controls


def inventory(files: dict) -> dict:
    return {path: {"sha256": digest(data), "bytes": len(data)} for path, data in sorted(files.items())}


def transform_totals(transformations: dict) -> dict:
    numeric_keys = ("log_definitions_removed", "log_calls_removed", "log_emitters_removed",
                    "internal_log_calls_removed_with_file", "telemetry_rules_removed",
                    "test_options_removed", "test_checks_false", "test_intro_blocks_removed",
                    "diagnostic_variable_exists_removed", "diagnostic_variable_cleanup_removed")
    totals = {key: sum(row.get(key, 0) for changes in transformations.values() for row in changes.values())
              for key in numeric_keys}
    totals["localization_keys_removed_all_languages"] = sum(
        len(row.get("localization_keys_removed", []))
        for changes in transformations.values() for row in changes.values())
    expected = {"log_definitions_removed": 76, "log_calls_removed": 72,
                       "log_emitters_removed": 191, "internal_log_calls_removed_with_file": 6,
                       "telemetry_rules_removed": 1, "test_options_removed": 1,
                       "test_checks_false": 8, "test_intro_blocks_removed": 1,
                       "diagnostic_variable_exists_removed": 11, "diagnostic_variable_cleanup_removed": 11,
                       "localization_keys_removed_all_languages": 90}
    if "parley" not in transformations:
        expected = dict.fromkeys(expected, 0)
    require(totals == expected,
            f"Unexpected aggregate transformation counts: {totals}")
    return totals


def dump_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def read_outputs(build_root: Path, expected: dict) -> dict:
    require(build_root.is_dir(), f"Missing build folder: {build_root}")
    require({path.name for path in build_root.iterdir()} == set(expected) | {"manifest.json", "transform-report.json"},
            "Unexpected files at versioned build root")
    outputs = {}
    for mod in selected_mods(expected):
        root = build_root / mod
        files = {}
        for path in sorted(root.rglob("*")):
            require(not path.is_symlink(), f"Output symlink is not allowed: {path}")
            if hasattr(path, "is_junction"):
                require(not path.is_junction(), f"Output junction is not allowed: {path}")
            if path.is_file():
                files[path.relative_to(root).as_posix()] = path.read_bytes()
        outputs[mod] = files
    exact_projection(outputs, expected)
    return outputs


def main() -> int:
    tool_dir = Path(__file__).resolve().parent
    # Canonical family owner: dev/parley/tools/release/. The sibling workspace
    # tools/ location is retained as a staging convenience during preparation.
    canonical = (tool_dir.name == "release" and tool_dir.parent.name == "tools"
                 and tool_dir.parents[1].name == "parley")
    default_dev = tool_dir.parents[2] if canonical else tool_dir.parent / "dev"
    default_game = tool_dir.parents[3] / "game" if canonical else tool_dir.parent / "game"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev-root", type=Path, default=default_dev)
    parser.add_argument("--output-root", type=Path, default=default_game)
    parser.add_argument("--lock", type=Path, default=tool_dir / "release-inputs.json")
    parser.add_argument("--mods", nargs="+", choices=MODS, default=list(MODS),
                        help="Explicit mod subset; default is the full three-mod family")
    parser.add_argument("--build-id", required=True, help="New, immutable local output directory name")
    parser.add_argument("--verify", action="store_true", help="Read-only verification of existing output")
    parser.add_argument("--check", action="store_true", help="Validate projection in memory; write nothing")
    args = parser.parse_args()
    require(not (args.verify and args.check), "Choose --verify or --check, not both")
    require(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.build_id)) and args.build_id not in {".", ".."},
            "Unsafe build-id")
    lock_bytes = args.lock.read_bytes()
    lock = json.loads(lock_bytes)
    require(lock.get("schema") == 1, "Unsupported source lock")
    selection = selected_mods(args.mods)
    locked = selected_mods(lock.get("mods", {}), "source-lock mod inventory")
    require(set(selection) <= set(locked), "Source lock does not include every selected mod; use explicit --mods")
    inputs = load_inputs(args.dev_root.resolve(), lock, selection)
    expected, transformations = project(inputs)
    evidence = {
        "schema": 1, "build_id": args.build_id,
        "no_diagnostics": validate_no_diagnostics(expected),
        "localization_coverage": validate_localizations(expected),
        "public_rate_projection": public_setting_proof(inputs, expected),
        "negative_controls": negative_controls(inputs, expected, lock),
        "transform_totals": transform_totals(transformations),
        "transformations": transformations,
        "scope": "Static deterministic package projection. Original dev gameplay gates remain separate; "
                 "a short engine load/UI smoke for this generated game build is still pending.",
        "retained_comments": "Source comments are retained; inert historical notes are not runtime telemetry.",
    }
    manifest = {
        "schema": 1, "build_id": args.build_id, "input_lock_sha256": digest(lock_bytes),
        "builder_sha256": digest(Path(__file__).read_bytes()),
        "mods": {mod: {"source": inventory(inputs[mod]), "game": inventory(expected[mod])} for mod in selection},
    }
    output_root = args.output_root.resolve()
    build_root = output_root / args.build_id
    dev_root = args.dev_root.resolve()
    require(build_root != dev_root and dev_root not in build_root.parents and build_root not in dev_root.parents,
            "Output must not overlap the dev source directory")
    if args.verify:
        actual = read_outputs(build_root, expected)
        require(json.loads((build_root / "manifest.json").read_text(encoding="utf-8")) == manifest,
                "Stored manifest differs from source, generated files, lock or builder")
        require(json.loads((build_root / "transform-report.json").read_text(encoding="utf-8")) == evidence,
                "Stored transform report differs from current validation")
        validate_no_diagnostics(actual)
        validate_localizations(actual)
        mode = "VERIFIED"
    elif args.check:
        mode = "CHECKED IN MEMORY"
    else:
        require(not build_root.exists(), f"Refusing to overwrite existing build: {build_root}; use --verify")
        build_root.mkdir(parents=True)
        for mod, files in expected.items():
            for path, data in files.items():
                destination = build_root / mod / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
        dump_json(build_root / "manifest.json", manifest)
        dump_json(build_root / "transform-report.json", evidence)
        read_outputs(build_root, expected)
        mode = "BUILT AND VERIFIED"
    print(json.dumps({"status": mode, "build_id": args.build_id,
                      "output": str(build_root) if not args.check else None,
                      "source_files": {mod: len(files) for mod, files in inputs.items()},
                      "game_files": {mod: len(files) for mod, files in expected.items()},
                      "localization_keys_per_language": {mod: row["keys_per_language"]
                                                         for mod, row in evidence["localization_coverage"].items()},
                      "negative_controls": len(evidence["negative_controls"]),
                      "pending": "Short engine load/UI smoke of this new game projection"}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReleaseError, OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"RELEASE VALIDATION FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
