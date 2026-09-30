#!/usr/bin/env python3
"""Create deterministic generic ZIP payloads from a verified CK3 game manifest.

This does not create Steam uploads, Nexus installers, or launcher .mod wrappers.
Only the three manifest-listed mod payloads enter the archives. ZIP_STORED avoids
compressor-version differences; member order, timestamps and permissions are fixed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

MODS = ("parley", "marriage_calc_assistant", "agot_marriage_calc_assistant")
GAME_DIRECTORIES = {"common", "data_binding", "events", "gui", "localization"}
GAME_SUFFIXES = {".txt", ".gui", ".yml"}
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
MANIFEST_NAME = "archive-manifest.json"


class PackageError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PackageError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def read_json(data: bytes):
    return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)


def reject_link(path: Path) -> None:
    require(not path.is_symlink(), f"Symlink is not allowed: {path}")
    # FILE_ATTRIBUTE_REPARSE_POINT also rejects Windows junctions on Python
    # versions before Path.is_junction became available.
    require(not (getattr(path.lstat(), "st_file_attributes", 0) & 0x400),
            f"Reparse point is not allowed: {path}")


def safe_payload_path(name: str) -> PurePosixPath:
    require(isinstance(name, str) and name and "\\" not in name, "Invalid manifest member path")
    path = PurePosixPath(name)
    require(not path.is_absolute() and path.as_posix() == name
            and all(part not in {"", ".", ".."} for part in path.parts)
            and ":" not in name, f"Unsafe manifest member: {name}")
    if name not in {"descriptor.mod", "thumbnail.png"}:
        require(len(path.parts) >= 2 and path.parts[0] in GAME_DIRECTORIES
                and path.suffix in GAME_SUFFIXES, f"Non-game file in payload manifest: {name}")
    return path


def descriptor_version(data: bytes) -> str:
    text = data.decode("utf-8-sig")
    tokens = [match.group() for match in re.finditer(
        r'"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}=]|[^\s{}=#"]+', text)
              if not match.group().startswith("#")]
    depth, versions = 0, []
    for i, token in enumerate(tokens):
        if depth == 0 and token == "version":
            require(i + 2 < len(tokens) and tokens[i + 1] == "=", "Malformed descriptor version")
            raw = tokens[i + 2]
            require(raw.startswith('"') and raw.endswith('"'), "Descriptor version must be quoted")
            versions.append(json.loads(raw))
        if token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
            require(depth >= 0, "Unbalanced descriptor block")
    require(depth == 0 and len(versions) == 1, "Expected exactly one root descriptor version")
    version = versions[0]
    require(isinstance(version, str) and len(version) <= 80
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version), "Unsafe descriptor version")
    return version


def read_payloads(build_dir: Path) -> tuple[dict, dict, bytes]:
    require(build_dir.is_dir(), f"Missing game build directory: {build_dir}")
    reject_link(build_dir)
    manifest_path = build_dir / "manifest.json"
    reject_link(manifest_path)
    manifest_bytes = manifest_path.read_bytes()
    manifest = read_json(manifest_bytes)
    require(manifest.get("schema") == 1 and set(manifest.get("mods", {})) == set(MODS),
            "Expected game-manifest schema 1 with exactly the three family mods")
    require(isinstance(manifest.get("build_id"), str) and manifest["build_id"], "Missing source build ID")
    payloads, versions = {}, {}
    for mod in MODS:
        root = build_dir / mod
        require(root.is_dir(), f"Missing game payload: {root}")
        reject_link(root)
        expected = manifest["mods"][mod].get("game")
        require(isinstance(expected, dict) and expected, f"Missing game inventory for {mod}")
        require("descriptor.mod" in expected, f"Missing root descriptor in {mod} manifest")
        for name, item in expected.items():
            safe_payload_path(name)
            require(isinstance(item, dict) and type(item.get("bytes")) is int and item["bytes"] >= 0
                    and isinstance(item.get("sha256"), str)
                    and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]),
                    f"Malformed inventory entry: {mod}/{name}")
        found = {}
        for path in sorted(root.rglob("*")):
            reject_link(path)
            if path.is_file():
                found[path.relative_to(root).as_posix()] = path
        require(set(found) == set(expected), f"Payload file inventory mismatch: {mod}")
        files = {}
        for name in sorted(expected):
            data = found[name].read_bytes()
            item = expected[name]
            require(len(data) == item["bytes"] and sha256(data) == item["sha256"],
                    f"Payload differs from verified game manifest: {mod}/{name}")
            files[name] = data
        payloads[mod] = files
        versions[mod] = descriptor_version(files["descriptor.mod"])
    return payloads, {"build_id": manifest["build_id"], "versions": versions}, manifest_bytes


def write_zip(stream, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=ZIP_TIME)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            info.comment = b""
            info.extra = b""
            archive.writestr(info, data)


def verify_zip(path: Path, files: dict[str, bytes]) -> dict:
    require(path.is_file(), f"Missing archive: {path}")
    reject_link(path)
    with zipfile.ZipFile(path, "r") as archive:
        entries = archive.infolist()
        names = [info.filename for info in entries]
        require(names == sorted(files) and len(names) == len(set(names)),
                f"Archive member inventory or order mismatch: {path.name}")
        require(archive.comment == b"", f"Unexpected archive comment: {path.name}")
        for info in entries:
            require(not info.is_dir() and info.date_time == ZIP_TIME
                    and info.compress_type == zipfile.ZIP_STORED
                    and info.create_system == 3 and info.external_attr == 0o100644 << 16
                    and info.comment == b"" and info.extra == b"" and not (info.flag_bits & 1),
                    f"Unexpected archive metadata: {path.name}/{info.filename}")
            data = archive.read(info)
            require(data == files[info.filename], f"Archive member hash/bytes mismatch: {path.name}/{info.filename}")
    data = path.read_bytes()
    return {"filename": path.name, "sha256": sha256(data), "bytes": len(data),
            "member_count": len(files), "members": {
                name: {"sha256": sha256(value), "bytes": len(value)} for name, value in sorted(files.items())}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--verify", action="store_true", help="Read-only archive and manifest verification")
    args = parser.parse_args()
    build_dir, output_dir = args.build_dir.resolve(), args.output_dir.resolve()
    require(output_dir != build_dir and build_dir not in output_dir.parents,
            "Distribution output must be outside the game build directory")
    payloads, metadata, game_manifest_bytes = read_payloads(build_dir)
    filenames = {mod: f"{mod}-{metadata['versions'][mod]}-payload.zip" for mod in MODS}
    expected_names = set(filenames.values()) | {MANIFEST_NAME}
    if args.verify:
        require(output_dir.is_dir(), f"Missing distribution directory: {output_dir}")
        reject_link(output_dir)
        require({path.name for path in output_dir.iterdir()} == expected_names,
                "Unexpected distribution file inventory")
    else:
        if output_dir.exists():
            reject_link(output_dir)
            require(output_dir.is_dir(), "Distribution output is not a directory")
            require(not any(output_dir.iterdir()), "Refusing a nonempty distribution directory")
        else:
            output_dir.mkdir(parents=True)
        for mod in MODS:
            # Exclusive creation preserves an existing artifact even if a file
            # appears between preflight and creation.
            with (output_dir / filenames[mod]).open("xb") as stream:
                write_zip(stream, payloads[mod])
    archives = {}
    for mod in MODS:
        archives[mod] = {"version": metadata["versions"][mod],
                         **verify_zip(output_dir / filenames[mod], payloads[mod])}
    manifest = {
        "schema": 1, "kind": "generic-ck3-game-payload-archives", "build_id": metadata["build_id"],
        "source_build_manifest_sha256": sha256(game_manifest_bytes),
        "packager_sha256": sha256(Path(__file__).read_bytes()),
        "zip_format": {"compression": "ZIP_STORED", "timestamp": list(ZIP_TIME),
                       "member_order": "lexicographic", "unix_mode": "100644"},
        "archives": archives,
        "platform_scope": "Generic payload ZIPs only. Steam uses the game folder. "
                          "Platform upload steps and a Nexus manual-install launcher wrapper are separate.",
    }
    output_manifest = output_dir / MANIFEST_NAME
    if args.verify:
        reject_link(output_manifest)
        require(read_json(output_manifest.read_bytes()) == manifest,
                "Archive manifest differs from the source build, archives or packager")
    else:
        with output_manifest.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps({"status": "VERIFIED" if args.verify else "PACKAGED AND VERIFIED",
                      "build_id": metadata["build_id"], "output_dir": str(output_dir),
                      "archives": {mod: {key: archives[mod][key] for key in
                                         ("filename", "sha256", "bytes", "member_count")}
                                   for mod in MODS}}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PackageError, OSError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile,
            zipfile.LargeZipFile, KeyError, TypeError) as error:
        print(f"PAYLOAD PACKAGING FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
