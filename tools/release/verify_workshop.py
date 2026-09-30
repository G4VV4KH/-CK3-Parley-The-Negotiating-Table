"""Read-only comparison of downloaded Workshop mods with a game build manifest."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys


MODS = {"parley", "marriage_calc_assistant", "agot_marriage_calc_assistant"}
METADATA = re.compile(
    rb'^[ \t]*(remote_file_id|path)[ \t]*=[ \t]*"([^"\r\n]*)"[ \t]*(?:#[^\r\n]*)?(?:\r?\n)?$'
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate manifest key: {key}")
        result[key] = value
    return result


def is_link(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def inventory(root):
    require(root.is_dir(), f"Missing mod directory: {root}")
    require(not is_link(root), f"Mod directory is a link/reparse point: {root}")
    files = {}
    for current, dirs, names in os.walk(root, followlinks=False):
        base = Path(current)
        for name in dirs + names:
            path = base / name
            require(not is_link(path), f"Link/reparse point in payload: {path}")
        for name in names:
            path = base / name
            require(stat.S_ISREG(path.stat().st_mode), f"Nonregular payload file: {path}")
            files[path.relative_to(root).as_posix()] = path
    return files


def validate_entries(entries, slug):
    require(isinstance(entries, dict) and entries, f"Missing game inventory for {slug}")
    folded = set()
    for name, record in entries.items():
        require(isinstance(name, str) and name, f"Invalid game path in {slug}")
        parts = name.split("/")
        require(not PurePosixPath(name).is_absolute() and "\\" not in name and ":" not in name
                and all(part not in ("", ".", "..") for part in parts),
                f"Unsafe game path: {slug}/{name}")
        require(name.casefold() not in folded, f"Case-colliding game path: {slug}/{name}")
        folded.add(name.casefold())
        require(isinstance(record, dict)
                and isinstance(record.get("sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
                and type(record.get("bytes")) is int and record["bytes"] >= 0,
                f"Invalid hash/size record: {slug}/{name}")
    require("descriptor.mod" in entries, f"Missing descriptor.mod inventory: {slug}")


def descriptor_without_metadata(data):
    """Remove only complete top-level metadata lines; preserve all other bytes."""
    data.decode("utf-8")  # Reject undecodable metadata rather than replacing bytes.
    bom = b"\xef\xbb\xbf" if data.startswith(b"\xef\xbb\xbf") else b""
    rest = data[len(bom):]
    kept, values, depth = [], {}, 0
    for line in rest.splitlines(keepends=True):
        match = METADATA.fullmatch(line) if depth == 0 else None
        if match:
            key = match[1].decode("ascii")
            require(key not in values, f"Duplicate descriptor metadata key: {key}")
            values[key] = match[2].decode("utf-8")
            continue
        kept.append(line)
        quoted, escaped = False, False
        for byte in line:
            if quoted:
                if escaped:
                    escaped = False
                elif byte == 92:
                    escaped = True
                elif byte == 34:
                    quoted = False
            elif byte == 35:
                break
            elif byte == 34:
                quoted = True
            elif byte == 123:
                depth += 1
            elif byte == 125:
                depth -= 1
                require(depth >= 0, "Unbalanced descriptor braces")
        require(not quoted, "Multiline/unterminated descriptor string is unsupported")
    require(depth == 0, "Unbalanced descriptor braces")
    return bom + b"".join(kept), values


def descriptor_exception(expected, actual, workshop_id):
    expected_body, expected_metadata = descriptor_without_metadata(expected)
    actual_body, actual_metadata = descriptor_without_metadata(actual)
    require(expected_body == actual_body, "Descriptor differs outside permitted metadata lines")
    if "remote_file_id" in actual_metadata:
        require(actual_metadata["remote_file_id"] == workshop_id,
                "Descriptor remote_file_id does not match the mapped Workshop ID")
    changes = {
        key: {"build": expected_metadata.get(key), "workshop": actual_metadata.get(key)}
        for key in sorted(set(expected_metadata) | set(actual_metadata))
        if expected_metadata.get(key) != actual_metadata.get(key)
    }
    return {
        "path": "descriptor.mod",
        "reason": "Explicitly allowed top-level remote_file_id/path lines only",
        "metadata_changes": changes,
        "metadata_lines_only": True,
        "build_sha256": sha256(expected),
        "workshop_sha256": sha256(actual),
        "build_bytes": len(expected),
        "workshop_bytes": len(actual),
    }


def verify_mod(build_dir, workshop_root, slug, workshop_id, entries, allow_metadata):
    validate_entries(entries, slug)
    build_files = inventory(build_dir / slug)
    expected_names = set(entries)
    build_missing = sorted(expected_names - set(build_files))
    build_extra = sorted(set(build_files) - expected_names)
    baseline_errors = []
    expected_bytes = {}
    for name in sorted(expected_names & set(build_files)):
        data = build_files[name].read_bytes()
        expected_bytes[name] = data
        if sha256(data) != entries[name]["sha256"] or len(data) != entries[name]["bytes"]:
            baseline_errors.append(name)
    report = {
        "mod": slug, "workshop_id": workshop_id,
        "workshop_directory": str(workshop_root / workshop_id),
        "expected_file_count": len(entries), "status": "FAIL",
        "build_missing": build_missing, "build_extra": build_extra,
        "build_hash_mismatches": baseline_errors,
        "missing": [], "extra": [], "mismatches": [], "descriptor_metadata_exceptions": [],
        "exact_matches": 0,
    }
    if build_missing or build_extra or baseline_errors:
        report["reason"] = "Local build payload does not match its manifest; Workshop comparison skipped"
        return report
    downloaded = inventory(workshop_root / workshop_id)
    report["missing"] = sorted(expected_names - set(downloaded))
    report["extra"] = sorted(set(downloaded) - expected_names)
    for name in sorted(expected_names & set(downloaded)):
        data = downloaded[name].read_bytes()
        expected = expected_bytes[name]
        if data == expected:
            report["exact_matches"] += 1
            continue
        mismatch = {
            "path": name, "build_sha256": entries[name]["sha256"],
            "workshop_sha256": sha256(data), "build_bytes": len(expected),
            "workshop_bytes": len(data),
        }
        if name == "descriptor.mod" and allow_metadata:
            try:
                report["descriptor_metadata_exceptions"].append(
                    descriptor_exception(expected, data, workshop_id)
                )
                continue
            except (ValueError, UnicodeError) as error:
                mismatch["reason"] = str(error)
        report["mismatches"].append(mismatch)
    if not (report["missing"] or report["extra"] or report["mismatches"]):
        report["status"] = "PASS_WITH_DESCRIPTOR_METADATA" if report["descriptor_metadata_exceptions"] else "PASS_EXACT"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True,
                        help="Existing game build directory containing manifest.json and mod folders")
    parser.add_argument("--workshop-root", type=Path, required=True,
                        help="Steam Workshop app directory, e.g. .../workshop/content/1158310")
    parser.add_argument("--mod", action="append", required=True, metavar="SLUG=WORKSHOP_ID",
                        help="Repeat for each mod to verify; only mapped mods are checked")
    parser.add_argument("--allow-descriptor-metadata", action="store_true",
                        help="Explicitly allow only top-level remote_file_id/path descriptor lines; report every exception")
    args = parser.parse_args()
    try:
        mappings = {}
        for value in args.mod:
            parts = value.split("=")
            require(len(parts) == 2 and parts[0] in MODS and re.fullmatch(r"[1-9][0-9]*", parts[1]),
                    f"Invalid --mod mapping: {value}")
            require(parts[0] not in mappings, f"Duplicate mod mapping: {parts[0]}")
            require(parts[1] not in mappings.values(), f"Workshop ID mapped twice: {parts[1]}")
            mappings[parts[0]] = parts[1]
        build_dir = args.build_dir.resolve(strict=True)
        workshop_root = args.workshop_root.resolve(strict=True)
        require(build_dir.is_dir() and workshop_root.is_dir(), "Build and Workshop roots must be directories")
        manifest_bytes = (build_dir / "manifest.json").read_bytes()
        manifest = json.loads(manifest_bytes, object_pairs_hook=no_duplicate_keys)
        require(isinstance(manifest, dict) and manifest.get("schema") == 1
                and isinstance(manifest.get("mods"), dict), "Unsupported game manifest schema")
        results = []
        for slug, workshop_id in mappings.items():
            require(slug in manifest["mods"] and isinstance(manifest["mods"][slug], dict),
                    f"Mod absent from manifest: {slug}")
            try:
                results.append(verify_mod(build_dir, workshop_root, slug, workshop_id,
                                          manifest["mods"][slug].get("game"),
                                          args.allow_descriptor_metadata))
            except (OSError, ValueError) as error:
                results.append({"mod": slug, "workshop_id": workshop_id,
                                "status": "FAIL", "reason": str(error)})
        success = all(result["status"].startswith("PASS_") for result in results)
        report = {
            "schema": 1, "status": "PASS" if success else "FAIL",
            "build_id": manifest.get("build_id"), "build_directory": str(build_dir),
            "manifest_sha256": sha256(manifest_bytes), "workshop_root": str(workshop_root),
            "descriptor_metadata_allowed": args.allow_descriptor_metadata,
            "scope": "Delivery comparison for mapped mods only. No files changed; no engine/runtime test performed.",
            "unchecked_manifest_mods": sorted(set(manifest["mods"]) - set(mappings)),
            "mods": results,
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if success else 1
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"schema": 1, "status": "ERROR", "reason": str(error)}, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
