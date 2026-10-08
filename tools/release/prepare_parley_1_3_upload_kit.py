#!/usr/bin/env python3
"""Prepare an immutable 1.3.0 upload kit only after exact-candidate acceptance.

Never rebuild the candidate, upload, commit, push, launch CK3 or promote a
registry. A hash-pinned JSON plan supplies reviewed inputs. The native verifier
must recompute the nine-language gate; a saved PASS field is insufficient.
"""
from __future__ import annotations

import argparse
import html
import io
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
import prepare_parley_1_3_candidate as candidate
import prepare_publication as legacy
import package_game as packager

VERSION = "1.3.0"
TARGET = "1.20.0.4"
LANGUAGES = frozenset(("english", "french", "german", "japanese", "korean", "polish",
                       "russian", "simp_chinese", "spanish"))
LINGUISTIC_SHA = "ac76543efd43286bf71f83fa3203257a25b11b00bada2a294abc0fdf977089cf"
NATIVE_PASS = "PASS_SCOPED_NATIVE_LOCALIZATION_RESOLUTION"
MANIFEST = "07-VERIFICATION/kit-manifest.json"
STATUS = "PREPARED_LOCAL_GATES_PASS_PUBLICATION_PENDING"


class KitError(Exception):
    pass


def require(ok, message):
    if not ok:
        raise KitError(message)


def read_ref(reference):
    require(isinstance(reference, dict) and set(reference) >= {"path", "sha256"}, "Expected hash-pinned input")
    path = Path(reference["path"])
    require(path.is_absolute(), "Evidence paths must be explicit and absolute")
    data = legacy.read_file(path)
    require(candidate.sha(data) == reference["sha256"], f"Input hash drift: {path}")
    if "bytes" in reference:
        require(len(data) == reference["bytes"], f"Input size drift: {path}")
    return data


def read_json_ref(reference):
    return json.loads(read_ref(reference))


def checked_candidate(reference):
    manifest = read_json_ref(reference)
    directory = Path(reference["path"]).parent
    require(Path(reference["path"]).name == "candidate-manifest.json", "Unexpected candidate manifest name")
    candidate.verify(directory, reference["sha256"])
    require(manifest.get("version") == VERSION and manifest.get("target_game_version") == TARGET,
            "Wrong candidate version/target")
    game = candidate.tree(directory / "game" / manifest["build_id"] / "parley")
    source = candidate.tree(directory / "source/dev/parley/mod/parley")
    require(len(game) == 88 and len(source) == 89, "Wrong exact candidate runtime inventory")
    return manifest, game, source


def linguistic_gate(reference, manifest):
    require(reference["sha256"] == LINGUISTIC_SHA, "Unreviewed linguistic acceptance receipt")
    report = read_json_ref(reference)
    require(report.get("schema") == "parley-130-localization-source-review-v1"
            and report.get("status") == "SOURCE_REVIEW_COMPLETE_NATIVE_PUBLICATION_GATE_NOT_VERIFIED",
            "Wrong source-linguistic review schema/status")
    require(report.get("game_target") == TARGET and set(report["per_language"]) == LANGUAGES,
            "Linguistic review target/languages differ")
    language_inventory = report["language_inventory"]
    read_ref(language_inventory)
    require(set(language_inventory["languages"]) == LANGUAGES, "Installed required-language inventory differs")
    read_ref(report["baseline"])
    for language, row in report["per_language"].items():
        require(row["defined_dev_keys"] == 730 and row["public_keys_after_ten_diagnostic_removals"] == 720
                and row["unchanged_published_keys"] == 651 and row["new_public_keys"] == 68
                and row["changed_published_keys"] == ["tnt_item_title_desc"]
                and row["new_and_changed_public_source_semantics"] == "REVIEWED"
                and row["missing_keys"] == row["duplicates"] == row["malformed_lines"] == [],
                f"Incomplete linguistic accounting: {language}")
        runtime_name = f"localization/{language}/tnt_l_{language}.yml"
        require(row["source_sha256"] == manifest["source_runtime"][runtime_name]["sha256"],
                f"Linguistic source differs from exact candidate: {language}")
        read_ref({"path": row["historical_dev_locale_path"], "sha256": row["historical_dev_locale_sha256"]})
    return {"status": "PASS_LINGUISTIC_DELTA_AND_HASH_BOUND_INHERITANCE", "receipt": reference,
            "languages": sorted(LANGUAGES), "public_keys_per_language": 720,
            "scope": "651 unchanged accepted texts plus 68 new and one changed reviewed text per language; "
                     "not a native-resolution or native-speaker certification."}


def native_gate(gate_ref, verifier_ref, verifier_support, candidate_ref, manifest):
    require(sys.flags.optimize == 0, "Native verifier assertions require Python without -O/PYTHONOPTIMIZE")
    saved = read_json_ref(gate_ref)
    read_ref(verifier_ref)
    require(isinstance(verifier_support, list) and verifier_support,
            "Native verifier transitive helper inventory is required")
    for ref in verifier_support:
        read_ref(ref)
    # The reviewed aggregator imports two sibling helpers. Resolve from its
    # explicit directory, then bind its reported complete dependency inventory.
    sys.path.insert(0, str(Path(verifier_ref["path"]).parent))
    try:
        verifier = legacy.load_module(Path(verifier_ref["path"]))
    finally:
        sys.path.pop(0)
    require(callable(getattr(verifier, "verify_gate", None)),
            "Reviewed native verifier must expose read-only verify_gate(gate_path, candidate_manifest_path)")
    fresh = verifier.verify_gate(Path(gate_ref["path"]), Path(candidate_ref["path"]))
    require(isinstance(fresh, dict), "Native verifier returned no evidence")
    # A timestamp may differ; every gate/evidence field must otherwise agree.
    saved_stable = {key: value for key, value in saved.items() if key != "recorded_utc"}
    fresh_stable = {key: value for key, value in fresh.items() if key != "recorded_utc"}
    require(saved_stable == fresh_stable, "Saved native gate differs from fresh evidence recomputation")
    require(fresh.get("status") == NATIVE_PASS and fresh.get("required_gaps") == [],
            "Current candidate native localization gate is incomplete or failed")
    require(fresh.get("target_game_version") == TARGET, "Native gate engine target differs")
    supplied = [verifier_ref, *verifier_support]
    expected_dependencies = {str(Path(ref["path"]).resolve()): ref["sha256"] for ref in supplied}
    dependencies = fresh.get("verifier_dependencies", [])
    actual_dependencies = {str(Path(ref["path"]).resolve()): ref["sha256"] for ref in dependencies}
    require(len(expected_dependencies) == len(supplied) and len(actual_dependencies) == len(dependencies)
            and actual_dependencies == expected_dependencies,
            "Native verifier dependency inventory differs from reviewed plan")
    require(fresh.get("candidate_manifest_sha256") == candidate_ref["sha256"]
            and fresh.get("runtime_full_file_inventory") == manifest["game_runtime"],
            "Native gate does not cover exact candidate GAME bytes")
    rows = fresh.get("per_language", {})
    require(set(rows) == LANGUAGES, "Native gate must cover all nine languages exactly")
    for language, row in rows.items():
        require(row.get("status") == NATIVE_PASS and row.get("covered_public_keys") == 720
                and row.get("required_gaps") == [], f"Incomplete native localization coverage: {language}")
    require(fresh.get("visual_status") in {"PASS", "NOT_VERIFIED", "PARTIAL"},
            "Native gate must state a separate visual status")
    return fresh


def source_export(repo, expected_commit, expected_runtime, substitutions):
    require(not legacy.run(["git", "status", "--porcelain", "--untracked-files=all"], repo).strip(),
            "Source export requires a reviewed clean commit, including new runtime and tooling files")
    commit = legacy.run(["git", "rev-parse", "HEAD"], repo).strip()
    require(commit == expected_commit and re.fullmatch(r"[0-9a-f]{40}", commit), "Source commit differs from plan")
    require(candidate.tree(repo / "mod/parley") == expected_runtime, "Source runtime differs from frozen candidate")
    names = set(filter(None, legacy.run(["git", "ls-files", "-z"], repo).split("\0")))
    require({"mod/parley/" + name for name in expected_runtime} <= names, "Tracked source export omits candidate runtime")
    changes_by_file = {}
    for change in substitutions:
        require(set(change) == {"file", "source_sha256", "before", "after", "count", "reason"},
                "Source substitutions require exact per-file bytes, count and reason")
        legacy.safe_relative(change["file"])
        require(not change["file"].startswith("mod/") and change["reason"].strip(),
                "Never sanitize/alter frozen runtime source; substitution reason required")
        require(change["file"] in names and type(change["count"]) is int and change["count"] > 0
                and re.search(r"(?i)[a-z]:[/\\]", change["before"])
                and not re.search(r"(?i)[a-z]:[/\\]", change["after"]),
                "Invalid export-only substitution")
        changes_by_file.setdefault(change["file"], []).append(change)
    files, transformations, excluded, originals = {}, {}, [], {}
    for name in sorted(names):
        path = legacy.safe_relative(name)
        require(path.parts[0] in legacy.SOURCE_ROOTS or name in legacy.SOURCE_TOP,
                f"Unclassified tracked source file: {name}")
        require(not (path.parts[0] == "mod" and (len(path.parts) < 2 or path.parts[1] != "parley")),
                "Unrelated runtime in source export")
        require(not any(part in {".git", "__pycache__", ".local", "artifacts", "save games", "logs"}
                        for part in path.parts), f"Private/generated source path: {name}")
        originals[name] = legacy.read_file(repo / name)
        if name in legacy.SOURCE_EXCLUDES:
            excluded.append(name)
            continue
        original = originals[name]
        data = original
        explicit = changes_by_file.get(name, [])
        for change in explicit:
            require(candidate.sha(original) == change["source_sha256"], f"Source substitution input drift: {name}")
            before, after = change["before"].encode(), change["after"].encode()
            require(data.count(before) == change["count"], f"Source substitution count drift: {name}")
            data = data.replace(before, after)
        # New helper languages were absent from the legacy export allowlist.
        # Treat them as text too; unknown machine paths must never slip through
        # merely because a file is .cjs instead of .py.
        scan_name = name + ".txt" if path.suffix.lower() in {".cjs", ".js", ".mjs", ".ts", ".sh", ".toml", ".yaml"} else name
        exported, automatic = legacy.sanitize_source(scan_name, data)
        if Path(scan_name).suffix.lower() in legacy.TEXT_SUFFIXES:
            # A drive letter is not a regex escape. In timestamp expressions,
            # the final digit-class escape before a colon must not be read as
            # a lower-case drive. JSON-escaped paths still start at the same
            # unescaped drive letter; escaping their separators cannot hide it.
            require(not re.search(rb"(?i)(?<![a-z\\])[a-z]:[/\\]", exported),
                    f"Unclassified machine path in source export: {name}")
        files[name] = exported
        if exported != original:
            transformations[name] = {"original": legacy.record(original), "exported": legacy.record(exported),
                                     "explicit": explicit, "known_portable_substitutions": automatic}
    require({"README.md", "dev.md", "publishing/description.en.md"} <= files.keys(), "Incomplete source projection")
    exported_runtime = {name.removeprefix("mod/parley/"): data for name, data in files.items()
                        if name.startswith("mod/parley/")}
    expected_export = dict(expected_runtime)
    # The developer-only logger is wholly omitted by the frozen GAME projection.
    # Its known machine-path citation may be sanitized in the public SOURCE
    # projection, as in earlier releases. No other runtime byte may change.
    if legacy.LOGGER_FILE in expected_export:
        expected_export[legacy.LOGGER_FILE] = legacy.sanitize_source(
            legacy.LOGGER_FILE, expected_export[legacy.LOGGER_FILE])[0]
    require(exported_runtime == expected_export, "Export changed/omitted frozen runtime beyond logger citation")
    require(all(legacy.read_file(repo / name) == data for name, data in originals.items()),
            "Source bytes changed during export")
    require(legacy.run(["git", "rev-parse", "HEAD"], repo).strip() == commit
            and not legacy.run(["git", "status", "--porcelain", "--untracked-files=all"], repo).strip(),
            "Source Git state changed during export")
    return files, {"source_commit": commit, "source_clean": True, "transformations": transformations,
                   "excluded": excluded, "source_inventory": legacy.inventory(originals), "inventory": legacy.inventory(files),
                   "scope": "Sanitized source projection, not a Git tree or new repository. Preserve existing history. "
                            "Only the DEV-only omitted logger may have known path-citation sanitization; all shipped runtime bytes are exact."}


def validate_image(data, dimensions, suffix, label):
    # Header dimensions alone accept corrupt/truncated images. Verify container
    # integrity and decode the full raster without modifying the source bytes.
    from PIL import Image
    expected_format = "PNG" if suffix == ".png" else "JPEG"
    require(suffix in {".png", ".jpg", ".jpeg"}, f"Unsupported image suffix: {label}")
    try:
        with Image.open(io.BytesIO(data)) as picture:
            require(picture.format == expected_format and picture.size == dimensions
                    and getattr(picture, "n_frames", 1) == 1, f"Image format/geometry differs: {label}")
            picture.verify()
        with Image.open(io.BytesIO(data)) as picture:
            picture.load()
    except (OSError, ValueError, SyntaxError) as error:
        raise KitError(f"Corrupt or undecodable image: {label}: {error}") from error


def media_inputs(plan, game):
    require(plan.get("schema") == "parley-130-media-plan-v1", "Unreviewed media plan schema")
    files = {"05-IMAGES/thumbnail.png": game["thumbnail.png"]}
    validate_image(game["thumbnail.png"], (512, 512), ".png", "runtime thumbnail")
    for key, name, size in (("square", "parley-cover-square-1024x1024", (1024, 1024)),
                            ("horizontal", "parley-cover-horizontal-1920x1080", (1920, 1080))):
        ref = plan[key]
        data = read_ref(ref)
        suffix = Path(ref["path"]).suffix.lower()
        validate_image(data, size, suffix, key + " cover")
        # The contract's 2 MB limit is for Steam gallery images, not the
        # separately supplied Paradox cover. Preserve approved cover bytes.
        require(ref.get("provenance"), "Cover provenance missing")
        files[f"05-IMAGES/{name}{suffix}"] = data
    gallery = plan.get("gallery", [])
    require(1 <= len(gallery) <= 8, "Reviewed gallery required")
    items = []
    for index, item in enumerate(gallery, 1):
        data = read_ref(item)
        original = read_ref(item["source"])
        suffix = Path(item["path"]).suffix.lower()
        validate_image(data, (1920, 1080), suffix, f"gallery {index}")
        validate_image(original, (1920, 1080), Path(item["source"]["path"]).suffix.lower(), f"gallery original {index}")
        require(len(data) < 2_000_000 and item.get("caption_en") and item.get("provenance"),
                "Gallery size/caption/provenance missing")
        name = f"05-IMAGES/GALLERY/{index:02d}{suffix}"
        files[name] = data
        items.append({"file": name.removeprefix("05-IMAGES/"), **item})
    require(sum(len(data) for name, data in files.items() if name.startswith("05-IMAGES/GALLERY/")) < 8_000_000,
            "Selected Steam gallery batch must be below8MB")
    files["05-IMAGES/gallery.json"] = candidate.json_bytes({"items": items})
    files["05-IMAGES/provenance.json"] = candidate.json_bytes(plan)
    return files


def checked_rendered_paths(revision, repo):
    for key, name in {"steam": "steam.bbcode", "paradox_rich": "paradox.html", "nexus": "nexus.bbcode",
                      "metadata": "metadata.json"}.items():
        require(Path(revision["rendered_outputs"][key]).resolve() == (repo / "publishing/generated" / name).resolve(),
                f"Validated copy differs from packaging input: {key}")
    # The scoped renderer produces github.md, then README adds exactly its
    # reviewed contributor footer. The public-copy validator may validly bind
    # either output, but not an arbitrary byte-identical file elsewhere.
    github = Path(revision["rendered_outputs"]["github"]).resolve()
    generated = repo / "publishing/generated/github.md"
    readme = repo / "README.md"
    require(github in {generated.resolve(), readme.resolve()},
            "Validated copy differs from packaging input: github")
    require(legacy.read_file(readme) == legacy.read_file(generated) + legacy.CONTRIBUTING_FOOTER,
            "Validated GitHub README differs from renderer output plus exact contributor footer")


def checked_copy(plan, repo):
    for key in ("revision", "config", "validator"):
        read_ref(plan[key])
    revision = read_json_ref(plan["revision"])
    require(revision["mod"] == "parley" and revision["version"] == VERSION and revision["game_target"] == TARGET,
            "Wrong publication-copy identity")
    require(Path(revision["source_projection"]).resolve() == repo.resolve()
            and Path(revision["canonical_description"]).resolve() == (repo / "publishing/description.en.md").resolve(),
            "Copy revision does not bind source export")
    require(read_ref(plan["config"]) == (repo / "publishing/family-links.json").read_bytes(), "Source config differs")
    checked_rendered_paths(revision, repo)
    for ref in plan["contract_files"].values():
        read_ref(ref)
    require(set(plan["contract_files"]) == {"CONTRACT.md", "contract.json", "description.template.en.md"},
            "Full reviewed publication contract required")
    validator = legacy.load_module(Path(plan["validator"]["path"]))
    proof = validator.validate(Path(plan["revision"]["path"]), Path(plan["config"]["path"]),
                               Path(plan["contract_files"]["contract.json"]["path"]))
    require(proof["status"] == "PASS", "Current scoped publication-copy validation failed")
    generated = candidate.tree(repo / "publishing/generated")
    readme, canonical = (repo / "README.md").read_bytes(), (repo / "publishing/description.en.md").read_bytes()
    legacy.validate_copy(generated, readme, canonical, VERSION)
    links = json.loads(read_ref(plan["config"]))["links"]
    for platform, (_, url) in legacy.PLATFORMS.items():
        require(links[f"PARLEY_{platform.upper()}_URL"] == url, f"Assigned {platform} identity differs")
    files = {"02-TEXT/" + name: data for name, data in generated.items()}
    files.update({"02-TEXT/README.md": readme, "02-TEXT/description.en.md": canonical})
    return files, proof


def zipped(files):
    stream = io.BytesIO()
    packager.write_zip(stream, files)
    return stream.getvalue()


def platform_files(game):
    steam, steam_wrapper, portable_wrapper = legacy.platform_payloads(game)
    result = {"01-STEAM/runtime/parley/" + name: data for name, data in steam.items()}
    result["01-STEAM/runtime/parley.mod"] = steam_wrapper
    result[f"03-PARADOX/parley-{VERSION}-PARADOX.zip"] = zipped(game)
    nexus = {"parley/" + name: data for name, data in game.items()}
    nexus["parley.mod"] = portable_wrapper
    nexus["INSTALL.txt"] = (f"Parley: The Negotiating Table {VERSION}\nFor CK3 {TARGET}\n\n"
        "Extract parley/ and parley.mod together into Documents/Paradox Interactive/Crusader Kings III/mod/.\n"
        "Enable Parley in the launcher; do not enable another Steam/Paradox/DEV copy at the same time.\n"
        "No dependency is required. AGOT integration remains on hold. Back up saves before updating.\n"
        "Choose game-rule settings for a new campaign. Close pending negotiations and use Parley's\n"
        "cleanup procedure before removing it. Keep your save backup.\n").encode()
    result[f"04-NEXUS/parley-{VERSION}-NEXUS-MANUAL.zip"] = zipped(nexus)
    return result, {"game_payload": legacy.inventory(game), "steam_payload": legacy.inventory(steam),
                    "nexus_members": legacy.inventory(nexus)}


def guide(build_id, commit, native, images):
    square = next(name for name in images if "cover-square" in name)
    horizontal = next(name for name in images if "cover-horizontal" in name)
    return f"""Parley: The Negotiating Table — {VERSION}
Target CK3: {TARGET}; supported_version: 1.20.*
Status: {STATUS}; external publication NOT_ATTEMPTED
Candidate build: {build_id}; source commit: {commit}

Update existing pages only: Steam 3811090081; Paradox 161475; Nexus 399.
GitHub: https://github.com/G4VV4KH/-CK3-Parley-The-Negotiating-Table
Publish the reviewed GitHub guide first if Steam links to its expanded guide.
Preserve existing Git history; 06-GITHUB/source is a sanitized projection, not a replacement repository.

Steam: 01-STEAM/runtime/parley and existing item 3811090081; 02-TEXT/steam.bbcode.
Only descriptor remote_file_id is overlaid. No dependency is required.
Paradox: 03-PARADOX/parley-{VERSION}-PARADOX.zip (descriptor at root), 02-TEXT/paradox.html.
Paradox cover: {horizontal}. Plain paradox.txt is reference, not rich-render acceptance.
Nexus: 04-NEXUS/parley-{VERSION}-NEXUS-MANUAL.zip (parley/ + parley.mod + INSTALL.txt).
Nexus file version: {VERSION}; separate file Description: For CK3 {TARGET}.
Nexus main description: 02-TEXT/nexus.bbcode; square cover: {square}.
Do not reuse old Nexus file 2607 as evidence this new archive was uploaded.

Exact candidate native language resolution: PASS for 9×720 accounted keys.
Linguistic acceptance: reviewed delta plus hash-bound unchanged translations.
Native diagnostic scope and inherited evidence remain as recorded in 07-VERIFICATION.
Visual status: {native['visual_status']}. Native resolution is not pixel/layout/hover acceptance.
Media provenance and explicit historical/current scope: 05-IMAGES/provenance.json.
Gallery order: 05-IMAGES/gallery.json; each gallery image <2 MB, selected gallery batch <8 MB.
These Steam gallery limits do not impose a new byte limit on the separate Paradox cover.
Preserve cover AI-media disclosures, actual permissions and license; no new license is granted.
AGOT integration remains on hold. Optional MCA is not a required dependency.

After upload, verify public rendering/support links and delivered archive bytes separately.
Prepared kit is not an upload receipt, live-page confirmation or delivered-byte acceptance.
No installed mod, playset, save, previous release or external service was changed.
"""


def prepare(plan):
    require(plan.get("schema") == "parley-130-upload-plan-v1", "Wrong upload-kit plan schema")
    manifest, game, source = checked_candidate(plan["candidate"])
    linguistic = linguistic_gate(plan["linguistic_review"], manifest)
    native = native_gate(plan["native_gate"], plan["native_verifier"], plan["native_verifier_support"],
                         plan["candidate"], manifest)
    repo = Path(plan["source_repo"])
    copy_files, copy_proof = checked_copy(plan["copy"], repo)
    exported, export_proof = source_export(repo, plan["source_commit"], source, plan.get("source_substitutions", []))
    media_plan = read_json_ref(plan["media_plan"])
    media = media_inputs(media_plan, game)
    changelog = read_ref(plan["changelog"])
    require(VERSION.encode() in changelog, "Changelog must name1.3.0")
    files, payloads = platform_files(game)
    files.update(copy_files)
    files["02-TEXT/CHANGELOG.md"] = changelog
    files.update(media)
    files.update({"06-GITHUB/source/" + name: data for name, data in exported.items()})
    files["06-GITHUB/PROJECTION-NOTES.txt"] = (
        f"Sanitized source projection from existing repository commit {plan['source_commit']}.\n"
        "Preserve repository/history/remotes; do not initialize or replace from this folder.\n"
        "Export-only substitutions and exclusions are enumerated in 07-VERIFICATION/source-export.json.\n").encode()
    for name, value in (("source-export.json", export_proof), ("linguistic-gate.json", linguistic),
                        ("native-localization-gate.json", native), ("publication-copy-validation.json", copy_proof)):
        files["07-VERIFICATION/" + name] = candidate.json_bytes(value)
    for name, ref in (("candidate-manifest.json", plan["candidate"]), ("linguistic-review.json", plan["linguistic_review"]),
                      ("native-gate-input.json", plan["native_gate"]), ("media-plan.json", plan["media_plan"]),
                      ("metadata-revision.json", plan["copy"]["revision"]), ("family-links.json", plan["copy"]["config"])):
        files["07-VERIFICATION/" + name] = read_ref(ref)
    for name, ref in plan["copy"]["contract_files"].items():
        files["07-VERIFICATION/publication-contract/" + name] = read_ref(ref)
    files["07-VERIFICATION/upload-plan.json"] = candidate.json_bytes(plan)
    start = guide(manifest["build_id"], plan["source_commit"], native, media)
    files["00-START-HERE.txt"] = start.encode()
    files["00-START-HERE.html"] = ("<!doctype html><meta charset='utf-8'><title>Parley1.3.0 kit</title><pre>"
                                   + html.escape(start) + "</pre>").encode()
    files["PUBLICATION-STATUS.json"] = candidate.json_bytes({
        "schema": "parley-130-kit-status-v1", "version": VERSION, "build_id": manifest["build_id"],
        "status": STATUS, "external_publication_performed": False, "visual_status": native["visual_status"],
        "platforms": {name: {"status": "NOT_UPLOADED", "remote_id": identity, "url": url}
                      for name, (identity, url) in legacy.PLATFORMS.items()}})
    files[MANIFEST] = candidate.json_bytes({"schema": "parley-130-kit-v1", "version": VERSION, "status": STATUS,
        "build_id": manifest["build_id"], "candidate_manifest_sha256": plan["candidate"]["sha256"],
        "source_commit": plan["source_commit"], "files": legacy.inventory(files), **payloads,
        "generator_files": {name: legacy.record((Path(__file__).parent / name).read_bytes()) for name in
                            (Path(__file__).name, "prepare_parley_1_3_candidate.py", "prepare_publication.py", "package_game.py")}})
    return files


def verify_bundle(output, expected_sha256):
    raw = legacy.read_file(output / MANIFEST)
    require(candidate.sha(raw) == expected_sha256, "Kit manifest differs from explicit reviewed pin")
    manifest = json.loads(raw)
    require(manifest.get("schema") == "parley-130-kit-v1" and manifest.get("version") == VERSION
            and manifest.get("status") == STATUS, "Unexpected kit manifest")
    files = candidate.tree(output)
    del files[MANIFEST]
    require(legacy.inventory(files) == manifest["files"], "Kit bytes/inventory changed")
    plan = json.loads(files["07-VERIFICATION/upload-plan.json"])
    require(prepare(plan) == {**files, MANIFEST: raw}, "Kit differs from freshly recomputed accepted inputs")
    return {"status": STATUS, "integrity": "PASS", "manifest_sha256": expected_sha256,
            "publication": "NOT_UPLOADED", "files": len(files) + 1}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--plan-sha256")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest-sha256")
    args = parser.parse_args(argv)
    if args.verify:
        require(args.output and args.manifest_sha256, "Verify requires output and manifest pin")
        result = verify_bundle(args.output, args.manifest_sha256)
    else:
        require(args.plan and args.plan_sha256, "Check/build requires exact reviewed plan hash")
        plan = read_json_ref({"path": str(args.plan), "sha256": args.plan_sha256})
        files = prepare(plan)  # All acceptance checks precede any output creation.
        result = {"status": "CHECKED_LOCAL_GATES_PASS_PUBLICATION_PENDING", "files": len(files),
                  "manifest_sha256": candidate.sha(files[MANIFEST]), "external_publication_performed": False}
        if args.build:
            require(args.output is not None, "Build requires new output path")
            candidate.safe_output(Path(plan["source_repo"]), args.output)
            frozen = Path(plan["candidate"]["path"]).parent.resolve()
            dest = args.output.resolve()
            require(frozen != dest and frozen not in dest.parents and dest not in frozen.parents,
                    "Upload kit must not overlap frozen candidate")
            args.output.mkdir(parents=True)
            for name, data in sorted(files.items()):
                legacy.write_new(args.output, name, data)
            result = verify_bundle(args.output, result["manifest_sha256"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KitError, candidate.CandidateError, legacy.PreparationError, packager.PackageError,
            OSError, ValueError, KeyError, TypeError, ImportError) as error:
        print(f"UPLOAD KIT BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(1)
