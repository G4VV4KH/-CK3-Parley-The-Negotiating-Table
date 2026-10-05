#!/usr/bin/env python3
"""Prepare one immutable Parley GAME candidate and a numbered manual-upload kit.

No upload, Git commit/push, installation, journal/registry promotion or playset
mutation. Existing build/package projection tools remain authoritative. Run only
after committing the reviewed source and generated copy. A new GAME projection
still needs its own focused native smoke; DEV observations are separate evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import re
import struct
import subprocess
import sys
from pathlib import Path, PurePosixPath

MOD = "parley"
TITLE = "Parley: The Negotiating Table"
TARGET = "1.20.0.3"
STEAM_ID = "3811090081"
PLATFORMS = {
    "steam": (STEAM_ID, f"https://steamcommunity.com/sharedfiles/filedetails/?id={STEAM_ID}"),
    "paradox": ("161475", "https://mods.paradoxplaza.com/mods/161475/Any"),
    "nexus": ("399", "https://www.nexusmods.com/crusaderkings3/mods/399"),
    "github": (None, "https://github.com/G4VV4KH/-CK3-Parley-The-Negotiating-Table"),
}
RUNTIME_ROOTS = {"common", "data_binding", "events", "gui", "localization", "descriptor.mod", "thumbnail.png"}
MANIFEST = "07-VERIFICATION/kit-manifest.json"
SOURCE_EXCLUDES = {"docs/SOURCE-PROVENANCE.json", "publishing/screenshots/03-agot-marriage-and-fealty.png"}
SOURCE_ROOTS = {"mod", "docs", "publishing", "tests", "tools"}
SOURCE_TOP = {".gitattributes", ".gitignore", "README.md", "dev.md", "CHANGELOG.md", "LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"}
TEXT_SUFFIXES = {".md", ".txt", ".gui", ".yml", ".mod", ".json", ".py", ".ps1", ".bbcode", ".html", ".patch"}
CONTRIBUTING_FOOTER = b'\n## Contributing\n\nSee [dev.md](dev.md) for the source layout, checks and pull-request workflow.\n'


class PreparationError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise PreparationError(message)


def record(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def inventory(files):
    return {name: record(data) for name, data in sorted(files.items())}


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def read_file(path):
    require(path.is_file() and not path.is_symlink() and not (path.stat().st_file_attributes & 0x400
            if hasattr(path.stat(), "st_file_attributes") else False), f"Not a regular input: {path}")
    return path.read_bytes()


def tree(root):
    require(root.is_dir() and not root.is_symlink(), f"Missing/linked tree: {root}")
    files = {}
    for path in sorted(root.rglob("*")):
        require(path.resolve().is_relative_to(root.resolve()) and not path.is_symlink()
                and not getattr(path.lstat(), "st_file_attributes", 0) & 0x400, f"Linked tree entry: {path}")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = read_file(path)
    return files


def safe_relative(name):
    path = PurePosixPath(name)
    require(path.as_posix() == name and not path.is_absolute() and "\\" not in name and ":" not in name
            and all(part not in {"", ".", ".."} for part in path.parts), f"Unsafe relative path: {name}")
    return path


def write_new(root, name, data):
    safe_relative(name)
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def run(args, cwd=None):
    result = subprocess.run([str(arg) for arg in args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    require(result.returncode == 0, f"Command failed: {args[0]}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def load_module(path):
    spec = importlib.util.spec_from_file_location("parley_kit_packager", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runtime_inputs(repo):
    files = {name: data for name, data in tree(repo / "mod/parley").items()
             if PurePosixPath(name).parts[0] in RUNTIME_ROOTS}
    require(len(files) == 76, "Reviewed Parley source inventory must contain exactly 76 runtime files")
    for name, data in files.items():
        if name != "common/scripted_effects/tnt_3b_log.txt" and Path(name).suffix in TEXT_SUFFIXES:
            require(not re.search(rb"(?<![A-Za-z])[A-Z]:[/\\]", data),
                    f"Normalize machine-path citations in authoritative source before locking runtime: {name}")
    return files


def descriptor_check(data, version):
    text = data.decode("utf-8-sig")
    for key, expected in (("name", TITLE), ("version", version), ("supported_version", "1.20.*")):
        require(re.findall(rf'^\s*{key}\s*=\s*"([^"\r\n]*)"', text, re.M) == [expected],
                f"Unexpected public descriptor {key}")
    require(not re.search(r"^\s*(path|remote_file_id)\s*=", text, re.M), "Source descriptor must remain portable and platform-neutral")


def platform_payloads(game_files):
    """Only Steam receives the already assigned item ID; game/Nexus/Paradox do not."""
    descriptor = game_files["descriptor.mod"].rstrip(b"\r\n") + b"\n"
    require(not re.search(rb"(?m)^\s*(path|remote_file_id)\s*=", descriptor), "Unexpected existing descriptor overlay")
    steam = dict(game_files)
    steam["descriptor.mod"] = descriptor + f'remote_file_id="{STEAM_ID}"\n'.encode()
    portable_wrapper = descriptor + b'path="mod/parley"\n'
    steam_wrapper = steam["descriptor.mod"] + b'path="mod/parley"\n'
    return steam, steam_wrapper, portable_wrapper


def sanitize_source(name, data):
    """Export-only, declared local-path substitutions; original repo is untouched."""
    if Path(name).suffix not in TEXT_SUFFIXES:
        return data, []
    text = data.decode("utf-8")
    # Build literals in pieces so exporting this helper does not change its own
    # replacement table. Historical machine paths become portable examples.
    slash = "/"
    library = "D:" + slash + "SteamLibrary/steamapps/"
    pairs = [
        (library + "common/Crusader Kings III/game", "./game"),
        (library + "workshop/content/1158310/2962333032", "./agot"),
        (library + "workshop/content/1158310", "./workshop/content/1158310"),
        ("D:" + slash + "install/games/Crusader.Kings.III.Royal.Edition-InsaneRamZes/game", "<game>"),
        ("C:" + slash + "mnt/gsg/ck3/titus/source", "<CK3-engine-source>"),
        ("C:" + slash + "Users/Pavel/.../Crusader Kings III/logs/error.log", "<CK3-user-data>/logs/error.log"),
        ("C:" + slash + "Users/<user>/Documents/Paradox Interactive/Crusader Kings III/logs/error.log", "<CK3-user-data>/logs/error.log"),
        ("C:" + slash + "path/to", "./path/to"),
        ("D:" + slash + "SteamLibrary/", "<Steam-library>/"),
    ]
    changes = []
    for before, after in pairs:
        for needle in {before, before.replace("/", "\\"), before.replace("/", "\\\\")}:
            count = text.count(needle)
            if count:
                text = text.replace(needle, after)
                changes.append({"replacement": after, "count": count})
    # Unknown paths are not guessed or silently removed. The source author must
    # classify them before exporting; URL scheme and parser regexes are not paths.
    require(not re.search(r"(?<![A-Za-z])[A-Z]:[/\\]", text), f"Unclassified machine path in source export: {name}")
    return text.encode("utf-8"), changes


def image_size(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        require(data[12:16] == b"IHDR", "Malformed PNG header")
        return struct.unpack(">II", data[16:24])
    require(data.startswith(b"\xff\xd8"), "Unsupported cover/gallery format")
    offset = 2
    while offset < len(data):
        require(data[offset] == 255, "Malformed JPEG marker")
        while data[offset] == 255:
            offset += 1
        marker = data[offset]
        offset += 1
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue
        length = int.from_bytes(data[offset:offset + 2], "big")
        require(length >= 2, "Malformed JPEG segment")
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
            return width, height
        offset += length
    raise PreparationError("JPEG dimensions not found")


def source_snapshot(repo):
    names = run(["git", "ls-files", "-z"], repo).split("\0")
    files, transformations, excluded = {}, {}, []
    for name in filter(None, names):
        path = safe_relative(name)
        require(path.parts[0] in SOURCE_ROOTS or name in SOURCE_TOP, f"Unclassified tracked source file: {name}")
        require(not (path.parts[0] == "mod" and path.parts[1] != MOD), "Unrelated runtime in source repository")
        require(not any(part in {".git", "__pycache__", ".local", "artifacts", "save games", "logs"} for part in path.parts),
                f"Private/generated source path: {name}")
        if name in SOURCE_EXCLUDES:
            excluded.append(name)
            continue
        original = read_file(repo / name)
        exported, changes = sanitize_source(name, original)
        files[name] = exported
        if changes:
            transformations[name] = {"original": record(original), "exported": record(exported), "changes": changes}
    require({"README.md", "dev.md", "publishing/description.en.md", "mod/parley/descriptor.mod"} <= files.keys(),
            "Source export missing required files")
    return files, {"transformations": transformations, "excluded": excluded,
                   "scope": "Sanitized tracked-source projection, not a Git commit tree; repository and history are unchanged."}


def guide(version, build_id, source_commit):
    return f"""Parley: The Negotiating Table — {version}
Target CK3: {TARGET}; supported_version: 1.20.*
Status: PREPARED_RUNTIME_SMOKE_PENDING / NOT_UPLOADED
Build: {build_id}
Source commit: {source_commit}

This folder prepares an UPDATE to the existing items, not new publications.
Do not upload before the focused smoke of this GAME projection is recorded.
DEV tests and the new production projection are distinct evidence scopes.

STEAM
Existing item: {PLATFORMS['steam'][1]}
Upload runtime folder: 01-STEAM/runtime/parley/
Portable launcher wrapper: 01-STEAM/runtime/parley.mod
The only Steam payload overlay is remote_file_id={STEAM_ID} in descriptor.mod.
Public name remains exact; no DEV or GAME-PROD prefix. No dependency is required.
Tags: 1.20 'Crozier'; Gameplay; Character Interactions; Events.
Description: 02-TEXT/steam.bbcode
Publish/update the reviewed GitHub guide first: the compact Steam description
links to its expanded Getting started/game-rules anchor, which must be live.

PARADOX
Existing item: {PLATFORMS['paradox'][1]}
Upload: 03-PARADOX/parley-{version}-PARADOX.zip
descriptor.mod is at ZIP root. Rich description: 02-TEXT/paradox.html
Use the rich fragment in the editor; 02-TEXT/paradox.txt is reference text only.
Verify that the support heading is enlarged and clickable on the public page.
Cover: 05-IMAGES/parley-cover-horizontal-1920x1080.png (do not use square cover).
No required mod dependency. Language: English description; nine in-game languages.

NEXUS
Existing item: {PLATFORMS['nexus'][1]}
Upload: 04-NEXUS/parley-{version}-NEXUS-MANUAL.zip
Contains parley/, portable parley.mod and INSTALL.txt. NOT the Paradox ZIP.
Main description: 02-TEXT/nexus.bbcode (large linked support heading preserved).
Downloadable file version: {version}
Downloadable file Description: For CK3 {TARGET}
These are separate from the main mod description. Verify both on the Files tab.
Preserve actual permissions/license. Review current form choices before submit.
Cover: 05-IMAGES/parley-cover-square-1024x1024.jpg

GITHUB
Repository: {PLATFORMS['github'][1]}
06-GITHUB/source/ is a sanitized tracked-source projection, not a new repository.
Preserve the repository history/remote; do not upload .git or local evidence.
Projection transformations are recorded in 07-VERIFICATION/source-export.json.
Publication revision is independent of the runtime build hash; no push was done.

COPY AND MEDIA
Canonical description snapshot: 02-TEXT/description.en.md
Generated README: 02-TEXT/README.md
Changelog: 02-TEXT/CHANGELOG.md
Short description and platform metadata: 02-TEXT/metadata.json
Runtime thumbnail: 05-IMAGES/thumbnail.png (512x512 PNG).
Gallery order/captions/provenance: 05-IMAGES/gallery.json
Use GALLERY/01, 02, 03 in that order. Existing captures illustrate the historical
1.19.0.6 interface; they do not show the new 1.2 currency-rule choices.
Gallery images are below 2 MB each and the complete batch below 8 MB.
Cover artwork and actual gameplay captures are distinct; apply required AI-media
disclosures based on the recorded provenance and actual publication form.

Compatibility: vanilla CK3 1.20.* target {TARGET}; optional MCA is standalone.
AGOT integration remains on hold; do not imply current AGOT compatibility.
The held AGOT:MCA companion has no assigned Steam item. Use its assigned GitHub
link and explicit held status; do not invent a Steam destination.
All four Parley destinations above retain their assigned publication identities.
Save backup recommended; new game-rule choices are selected for a new campaign.
Close pending negotiations and use the mod's cleanup procedure before removal.

NEXT: review copy/media, record focused GAME smoke, then upload only with human
authorization. Reopen each page and verify downloaded runtime bytes separately.
Prepared files do not establish upload, publication or delivered-byte verification.
Rendered format structure was checked; actual upload-form visual review remains
pending. Local-file browser preview was unavailable; no bypass was attempted.
No playset, installed mod, save, old release or other mod was changed by this tool.
"""


def validate_copy(generated, readme, canonical, version):
    require({"steam.bbcode", "paradox.txt", "paradox.html", "nexus.bbcode", "github.md", "preview.html", "render-status.json", "metadata.json"} <= generated.keys(),
            "Render all selected-mod publication outputs before preparing")
    require(readme == generated["github.md"] + CONTRIBUTING_FOOTER,
            "Generated GitHub copy/expected Contributing footer and README diverged")
    require(f"Version {version}".encode() in canonical, "Canonical description version differs")
    require(len(generated["steam.bbcode"]) <= 8000, "Steam description exceeds reviewed 8000 UTF-8-byte limit")
    require(b"{{" not in b"".join(generated.values()), "Unresolved publication placeholder")
    label = "Want to support my work? Donate on Ko-fi 💛"
    url = "https://ko-fi.com/g4vv4kh"
    heading = f"[size=5][b][url={url}]{label}[/url][/b][/size]".encode()
    require(generated["nexus.bbcode"].count(heading) == 1 and generated["nexus.bbcode"].count(label.encode()) == 1,
            "Nexus description must preserve exactly one approved large linked support heading")
    rich_heading = f'<h3><a href="{url}">{label}</a></h3>'.encode()
    require(generated["paradox.html"].count(rich_heading) == 1, "Paradox requires the native linked support heading")
    require(len(generated["paradox.html"].decode().encode("utf-16-le")) // 2 <= 10000, "Paradox rich description exceeds 10000 UTF-16 units")
    metadata = json.loads(generated["metadata.json"])
    require(metadata.get("nexus_file_version") == version, "Nexus file version must be the mod release version")
    require(metadata.get("target_game_version") == TARGET and metadata.get("nexus_file_description") == f"For CK3 {TARGET}",
            "Nexus file Description must match the approved CK3 target")


def media_inputs(workspace, repo, runtime):
    media = workspace / "publication-media/parley"
    selected_media = {
        "05-IMAGES/parley-cover-square-1024x1024.jpg": media / "2026-10-01-paradox-cover/originals/squareTNT.jpg",
        "05-IMAGES/parley-cover-horizontal-1920x1080.png": media / "paradox-upload-png/parley-cover-horizontal-1920x1080.png",
        "05-IMAGES/thumbnail.png": repo / "mod/parley/thumbnail.png",
    }
    gallery_source = json.loads(read_file(media / "steam-upload-jpg-manifest.json"))
    gallery = []
    for item in gallery_source["images"]:
        path = Path(item["file"])
        data = read_file(path)
        require(record(data)["sha256"] == item["sha256"] and len(data) < 2_000_000, "Gallery source hash/Steam size limit mismatch")
        name = "05-IMAGES/GALLERY/" + path.name
        selected_media[name] = path
        gallery.append({"order": item["order"], "file": name.removeprefix("05-IMAGES/"), "caption": item["caption_en"],
                        "provenance": "Unaltered gameplay capture, historical CK3 1.19.0.6; JPEG compression of preserved PNG.", **record(data)})
    require(len(gallery) == 3 and [item["order"] for item in gallery] == [1, 2, 3]
            and sum(row["bytes"] for row in gallery) < 8_000_000, "Unexpected gallery inventory/order/batch size")
    files = {name: read_file(path) for name, path in selected_media.items()}
    cover_record = json.loads(read_file(media / "paradox-upload-png-manifest.json"))
    for name, dimensions, expected_hash in (
            ("05-IMAGES/parley-cover-square-1024x1024.jpg", (1024, 1024), cover_record["source_sha256"]),
            ("05-IMAGES/parley-cover-horizontal-1920x1080.png", (1920, 1080), cover_record["sha256"]),
            ("05-IMAGES/thumbnail.png", (512, 512), record(runtime["thumbnail.png"])["sha256"])):
        require(image_size(files[name]) == dimensions and record(files[name])["sha256"] == expected_hash,
                f"Approved media dimensions/hash differ: {name}")
    for item in gallery:
        require(image_size(files["05-IMAGES/" + item["file"]]) == (1920, 1080), "Gallery aspect ratio changed")
    media_inventory = inventory(files)
    files["05-IMAGES/gallery.json"] = json_bytes({"items": gallery, "new_rules_not_depicted": True})
    files["05-IMAGES/provenance.json"] = json_bytes({"gallery": "Historical authentic gameplay captures; no AI alteration.",
        "cover": "Existing approved composition reused unchanged. Horizontal cover is deterministic lossless padding of the supplied square; no newly generated artwork.",
        "source_records": ["publication-media/parley/paradox-upload-png-manifest.json", "publication-media/parley/steam-upload-jpg-manifest.json"],
        "media": media_inventory})
    return files


def prepare(args):
    workspace = args.workspace.resolve()
    repo = workspace / "dev/parley"
    tools = repo / "tools/release"
    bundle = (args.bundle or workspace / "deploy" / f"parley-{args.version}").resolve()
    build = workspace / "game" / args.build_id
    distribution = workspace / "distribution" / args.build_id
    evidence = workspace / "verification-evidence" / args.build_id
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.build_id), "Unsafe build ID")
    require(re.fullmatch(r"\d+\.\d+\.\d+", args.version), "Expected numeric three-part version")
    require(bundle.parent == (workspace / "deploy").resolve(), "Bundle must be a direct child of workspace/deploy")
    for target in (bundle, build, distribution, evidence):
        require(target.resolve().is_relative_to(workspace) and not target.resolve().is_relative_to(repo.resolve()),
                f"Output escapes release workspace or overlaps authoring source: {target}")
    packager = load_module(tools / "package_game.py")
    if args.verify:
        return verify(workspace, bundle, args.build_id, args.version, tools, packager)
    require(args.changelog and args.changelog.is_file(), "--changelog must identify reviewed release notes")
    for target in (bundle, build, distribution, evidence):
        require(not target.exists(), f"Refusing existing output: {target}; use --verify or a new build/kit identity")
    require(not run(["git", "status", "--porcelain"], repo).strip(), "Commit reviewed source/copy/tool changes before preparing")
    commit = run(["git", "rev-parse", "HEAD"], repo).strip()
    runtime = runtime_inputs(repo)
    descriptor_check(runtime["descriptor.mod"], args.version)
    snapshot, export_report = source_snapshot(repo)
    generated = tree(repo / "publishing/generated")
    readme = read_file(repo / "README.md")
    canonical = read_file(repo / "publishing/description.en.md")
    validate_copy(generated, readme, canonical, args.version)
    changelog = read_file(args.changelog)
    require(args.version.encode() in changelog, "Changelog must identify the prepared version")
    media_files = media_inputs(workspace, repo, runtime)
    contract_root = workspace.parent / "ck3-mods/docs/publishing"
    contract_files = {"07-VERIFICATION/publication-contract/" + name: read_file(contract_root / name)
                      for name in ("CONTRACT.md", "contract.json", "description.template.en.md")}
    links = json.loads(read_file(repo / "publishing/family-links.json"))["links"]
    for platform, (_, url) in PLATFORMS.items():
        require(links[f"PARLEY_{platform.upper()}_URL"] == url, f"Assigned {platform} identity changed")

    lock = {"schema": 1, "baseline": f"Parley {args.version}, scoped currency-rule update for CK3 {TARGET}; source {commit}. No engine verification of the GAME projection is implied.",
            "mods": {MOD: {"files": inventory(runtime)}}}
    evidence.mkdir(parents=True)
    write_new(evidence, "release-inputs.json", json_bytes(lock))
    source_evidence = {"schema": 1, "source_commit": commit, "source_runtime": inventory(runtime),
                       "tools": {p.name: record(read_file(p)) for p in (tools / "build_game.py", tools / "package_game.py", Path(__file__))},
                       "version": args.version, "game_target": TARGET, "source_clean_at_capture": True}
    write_new(evidence, "source-evidence.json", json_bytes(source_evidence))
    common = [sys.executable, "-B", tools / "build_game.py", "--dev-root", workspace / "dev", "--output-root", workspace / "game",
              "--lock", evidence / "release-inputs.json", "--build-id", args.build_id, "--mods", MOD]
    commands = [json.loads(run(common + ["--check"])), json.loads(run(common)), json.loads(run(common + ["--verify"]))]
    package = [sys.executable, "-B", tools / "package_game.py", "--build-dir", build, "--output-dir", distribution]
    commands.extend([json.loads(run(package)), json.loads(run(package + ["--verify"]))])
    game_files = tree(build / MOD)
    steam, steam_wrapper, portable_wrapper = platform_payloads(game_files)
    files = {f"01-STEAM/runtime/parley/{name}": data for name, data in steam.items()}
    files["01-STEAM/runtime/parley.mod"] = steam_wrapper
    files["02-TEXT/description.en.md"] = canonical
    files["02-TEXT/README.md"] = readme
    files["02-TEXT/CHANGELOG.md"] = changelog
    files.update({f"02-TEXT/{name}": data for name, data in generated.items()})
    files["02-TEXT/metadata.json"] = json_bytes({"title": TITLE, "version": args.version, "game_version": TARGET,
        "target_game_version": TARGET, "nexus_file_version": args.version, "nexus_file_description": f"For CK3 {TARGET}",
        "supported_version": "1.20.*", "tags": ["1.20 'Crozier'", "Gameplay", "Character Interactions", "Events"],
        "required_mods": [], "optional_companions": ["Marriage Calculation Assistant"], "agot_status": "HELD",
        "short_description": "Negotiate custom treaties: exchange wealth, prestige, piety, titles and political concessions, with configurable rules for players and AI.",
        "manual_choices": ["Preserve existing platform item IDs", "Review actual license/permissions; no new license granted", "Apply required AI-media provenance tags", "Record GAME smoke before upload"]})
    files[f"03-PARADOX/parley-{args.version}-PARADOX.zip"] = read_file(distribution / f"parley-{args.version}-payload.zip")
    nexus_files = {f"parley/{name}": data for name, data in game_files.items()}
    nexus_files["parley.mod"] = portable_wrapper
    nexus_files["INSTALL.txt"] = (f"Parley: The Negotiating Table {args.version}\nTarget CK3 {TARGET} (1.20.*).\n\n"
        "Extract parley/ and parley.mod together into your CK3 user-data mod folder.\n"
        "On Windows this is Documents/Paradox Interactive/Crusader Kings III/mod/.\n"
        "Enable Parley in the launcher. Do not enable a second Steam/Paradox/DEV copy.\n"
        "No other mod is required. AGOT support is on hold for this release.\n"
        "Back up saves before updating. Select new game-rule choices when starting\n"
        "a new campaign. Close pending negotiations and use Parley's cleanup\n"
        "procedure before removing the mod. Preserve your backup if unsure.\n").encode()
    import io
    stream = io.BytesIO()
    packager.write_zip(stream, nexus_files)
    files[f"04-NEXUS/parley-{args.version}-NEXUS-MANUAL.zip"] = stream.getvalue()
    files.update(media_files)
    files.update({"06-GITHUB/source/" + name: data for name, data in snapshot.items()})
    files["06-GITHUB/PROJECTION-NOTES.txt"] = ("This is a sanitized tracked-source projection, NOT a Git commit tree.\n"
        "Known machine paths become portable example roots; configure game/AGOT paths explicitly.\n"
        "Original repository history is preserved. Do not initialize/replace it from this snapshot.\n"
        f"Original reviewed source commit: {commit}\n").encode()
    files["07-VERIFICATION/source-export.json"] = json_bytes(export_report)
    for path in (evidence / "release-inputs.json", evidence / "source-evidence.json", build / "manifest.json", build / "transform-report.json", distribution / "archive-manifest.json"):
        files["07-VERIFICATION/" + path.name] = read_file(path)
    files["07-VERIFICATION/build-results.json"] = json_bytes(commands)
    files.update(contract_files)
    files["07-VERIFICATION/steam-overlay.json"] = json_bytes({"only_change": "Append existing Steam remote_file_id to public descriptor; no name/script changes.",
        "remote_file_id": STEAM_ID, "before": record(game_files["descriptor.mod"]), "after": record(steam["descriptor.mod"])})
    files["PUBLICATION-STATUS.json"] = json_bytes({"schema": 1, "mod": MOD, "version": args.version, "build_id": args.build_id,
        "status": "PREPARED_RUNTIME_SMOKE_PENDING", "game_target": TARGET, "source_commit": commit,
        "platforms": {name: {"status": "NOT_UPLOADED", "remote_id": item_id, "url": url} for name, (item_id, url) in PLATFORMS.items()},
        "runtime_smoke": "NOT_YET_RUN_ON_THIS_GAME_PROJECTION", "external_publication_performed": False})
    start = guide(args.version, args.build_id, commit)
    files["00-START-HERE.txt"] = start.encode()
    files["00-START-HERE.html"] = ("<!doctype html><meta charset='utf-8'><title>Parley publication kit</title>"
        "<style>body{max-width:1000px;margin:3rem auto;background:#182020;color:#eee;font:16px system-ui}"
        "pre{white-space:pre-wrap;line-height:1.5}button{padding:.5rem}</style><h1>Parley publication kit</h1>"
        "<button onclick=\"navigator.clipboard.writeText(document.querySelector('pre').textContent)\">Copy instructions</button>"
        "<pre>" + html.escape(start) + "</pre>").encode()
    files[MANIFEST] = json_bytes({"schema": 1, "mod": MOD, "version": args.version, "build_id": args.build_id,
        "source_commit": commit, "files": inventory(files), "manifest_excludes_itself": True,
        "game_payload": inventory(game_files), "steam_payload": inventory(steam), "nexus_members": inventory(nexus_files),
        "generator": record(read_file(Path(__file__)))})
    bundle.mkdir(parents=True)
    for name, data in sorted(files.items()):
        write_new(bundle, name, data)
    return verify(workspace, bundle, args.build_id, args.version, tools, packager)


def verify(workspace, bundle, build_id, version, tools, packager):
    manifest = json.loads(read_file(bundle / MANIFEST))
    require(manifest["build_id"] == build_id and manifest["version"] == version, "Kit identity mismatch")
    actual = tree(bundle)
    del actual[MANIFEST]
    require(inventory(actual) == manifest["files"], "Kit inventory/hash drift")
    require(record(read_file(Path(__file__))) == manifest["generator"], "Kit generator changed")
    build = workspace / "game" / build_id
    game_files = tree(build / MOD)
    require(inventory(game_files) == manifest["game_payload"], "Frozen GAME payload drift")
    steam, steam_wrapper, portable_wrapper = platform_payloads(game_files)
    require(tree(bundle / "01-STEAM/runtime/parley") == steam, "Steam overlay drift")
    require(read_file(bundle / "01-STEAM/runtime/parley.mod") == steam_wrapper, "Steam wrapper drift")
    paradox = packager.verify_zip(bundle / f"03-PARADOX/parley-{version}-PARADOX.zip", game_files)
    nexus = {f"parley/{name}": data for name, data in game_files.items()}
    nexus["parley.mod"] = portable_wrapper
    import zipfile
    nexus_path = bundle / f"04-NEXUS/parley-{version}-NEXUS-MANUAL.zip"
    with zipfile.ZipFile(nexus_path) as archive:
        nexus["INSTALL.txt"] = archive.read("INSTALL.txt")
    require(inventory(nexus) == manifest["nexus_members"], "Nexus reconstructed members drift")
    nexus_checked = packager.verify_zip(nexus_path, nexus)
    run([sys.executable, "-B", tools / "build_game.py", "--dev-root", workspace / "dev", "--output-root", workspace / "game",
         "--lock", workspace / "verification-evidence" / build_id / "release-inputs.json", "--build-id", build_id, "--mods", MOD, "--verify"])
    run([sys.executable, "-B", tools / "package_game.py", "--build-dir", build, "--output-dir", workspace / "distribution" / build_id, "--verify"])
    return {"status": "PREPARED_RUNTIME_SMOKE_PENDING", "publication": "NOT_UPLOADED", "build_id": build_id,
            "bundle": str(bundle), "files": len(actual) + 1, "game_files": len(game_files),
            "paradox_sha256": paradox["sha256"], "nexus_sha256": nexus_checked["sha256"], "verification": "PASS"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--changelog", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args), ensure_ascii=False, indent=2))
    except (PreparationError, OSError, ValueError, KeyError) as error:
        print(f"PREPARATION FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
