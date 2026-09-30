#!/usr/bin/env python3
"""Track verified dev/game associations and explicit publication evidence.

Standard library only. Frozen game/<build> payloads are read-only; publication
journals live under game/_history/<build>/<mod>/<platform>. No network writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

MODS = ("parley", "marriage_calc_assistant", "agot_marriage_calc_assistant")
PLATFORMS = ("steam", "paradox", "nexus", "github")
RUNTIME_ROOTS = {"common", "data_binding", "events", "gui", "localization",
                 "descriptor.mod", "thumbnail.png"}
PREFIXES = dict(zip(MODS, ("PARLEY", "MCA", "AGOT_MCA")))


class JournalError(Exception):
    pass


def require(ok, message):
    if not ok:
        raise JournalError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(inventory):
    return digest(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode())


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def scoped(root, *parts):
    path = root.joinpath(*parts)
    require(path.resolve().is_relative_to(root.resolve()), f"Path escapes workspace: {path}")
    return path


def inventory(root, source=False):
    require(root.is_dir(), f"Missing payload directory: {root}")
    rows = {}
    for path in sorted(root.rglob("*")):
        require(path.resolve().is_relative_to(root.resolve()), f"External payload link: {path}")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if source and PurePosixPath(relative).parts[0] not in RUNTIME_ROOTS:
                continue
            data = path.read_bytes()
            rows[relative] = {"sha256": digest(data), "bytes": len(data)}
    return rows


def git_executable(explicit=None):
    bundled = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/MinGit/cmd/git.exe"
    candidate = explicit or (str(bundled) if bundled.is_file() else shutil.which("git"))
    require(candidate, "Git was not found; pass --git with the executable path")
    return candidate


def git(repo, executable, *args):
    result = subprocess.run([executable, "-C", str(repo), *args], capture_output=True, text=True)
    require(result.returncode == 0, f"Git failed in {repo}: {result.stderr.strip()}")
    return result.stdout.strip()


def git_state(repo, mod, executable, source_inventory):
    runtime = f"mod/{mod}"
    paths = [f"{runtime}/{name}" for name in sorted(source_inventory)]
    clean = not git(repo, executable, "status", "--porcelain", "--", *paths)
    return {"commit": git(repo, executable, "rev-parse", "HEAD"),
            "runtime_tree": git(repo, executable, "rev-parse", f"HEAD:{runtime}"),
            "runtime_committed": clean}


def inspect(workspace, build_id, executable):
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", build_id), "Invalid build ID")
    root = workspace.resolve()
    build = scoped(root, "game", build_id)
    manifest_file = scoped(root, "game", build_id, "manifest.json")
    manifest = read_json(manifest_file)
    require(manifest.get("build_id") == build_id and set(manifest.get("mods", {})) == set(MODS),
            "Build manifest identity/mod inventory mismatch")
    manifest_sha = digest(manifest_file.read_bytes())
    archives_file = scoped(root, "distribution", build_id, "archive-manifest.json")
    archives = read_json(archives_file) if archives_file.exists() else {}
    if archives:
        require(archives.get("build_id") == build_id and
                archives.get("source_build_manifest_sha256") == manifest_sha,
                "Archive manifest does not identify this build")
    result = {}
    for mod in MODS:
        expected = manifest["mods"][mod]
        game = scoped(root, "game", build_id, mod)
        actual_game = inventory(game)
        require(actual_game == expected["game"], f"Game payload inventory/hash mismatch: {mod}")
        repo = scoped(root, "dev", mod)
        actual_source = inventory(scoped(root, "dev", mod, "mod", mod), source=True)
        version = re.search(r'^\s*version\s*=\s*"([^"\r\n]+)"',
                            (game / "descriptor.mod").read_text(encoding="utf-8-sig"), re.M)
        require(version, f"Version missing from descriptor: {mod}")
        item = {"build_id": build_id, "mod": mod, "version": version[1],
                "manifest_sha256": manifest_sha, "payload_fingerprint": fingerprint(actual_game),
                "source_fingerprint": fingerprint(expected["source"]),
                "current_source_fingerprint": fingerprint(actual_source),
                "source_matches": actual_source == expected["source"],
                "payload_files": len(actual_game), "source_files": len(expected["source"]),
                "source_git": git_state(repo, mod, executable, expected["source"])}
        archive = archives.get("archives", {}).get(mod)
        if archive:
            file = scoped(root, "distribution", build_id, archive["filename"])
            data = file.read_bytes()
            require(digest(data) == archive["sha256"] and len(data) == archive["bytes"] and
                    archive["members"] == actual_game, f"Archive mismatch: {mod}")
            item["archive"] = {"file": file.relative_to(root).as_posix(),
                               "sha256": digest(data), "bytes": len(data)}
        result[mod] = item
    return result


def load_history(path, kind, mod, build_id=None, platform=None):
    identity = {"schema": 1, "kind": kind, "mod": mod}
    if build_id:
        identity.update(build_id=build_id, platform=platform)
    if path.exists():
        history = read_json(path)
        require(all(history.get(key) == value for key, value in identity.items()) and
                isinstance(history.get("events"), list), f"Invalid journal identity: {path}")
        return history
    return {**identity, "events": []}


def save_history(path, history):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(history, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)
    lines = [f"# {history['mod']} — {history['kind']}", "",
             "Generated from history.json. Events are appended; a prepared build is not a publication.", ""]
    for event in history["events"]:
        lines.extend([f"## {event['recorded_at']} — {event['status']}", ""])
        for key, value in event.items():
            if key not in {"recorded_at", "status"} and value is not None:
                rendered = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
                lines.append(f"- **{key}**: {rendered.replace(chr(10), ' ')}")
        lines.append("")
    path.with_name("HISTORY.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def platform_path(root, build_id, mod, platform):
    return scoped(root, "game", "_history", build_id, mod, platform, "history.json")


def compatible(history, item):
    for event in history["events"]:
        if event.get("build_id") == item["build_id"]:
            require(event.get("manifest_sha256") == item["manifest_sha256"],
                    "Build ID was reused with another manifest; create a new build ID")


def initialize(root, build_id, executable):
    inspected = inspect(root, build_id, executable)
    pending = []
    links_file = scoped(root, "dev", "parley", "publishing", "family-links.json")
    links = read_json(links_file).get("links", {}) if links_file.exists() else {}
    for mod, item in inspected.items():
        require(item["source_matches"] and item["source_git"]["runtime_committed"],
                f"Dev runtime must match the manifest and be committed: {mod}")
        path = scoped(root, "dev", mod, "docs", "releases", "history.json")
        history = load_history(path, "dev-to-game", mod)
        compatible(history, item)
        if not any(event.get("build_id") == build_id for event in history["events"]):
            history["events"].append({"recorded_at": utc_now(), "status": "VERIFIED_ASSOCIATION",
                **item, "evidence": "Current committed dev runtime and frozen game payload match the build manifest.",
                "note": "Association verified now; this does not assert the original build commit or build time."})
        pending.append((path, history))
        for platform in PLATFORMS:
            path = platform_path(root, build_id, mod, platform)
            history = load_history(path, "publication", mod, build_id, platform)
            compatible(history, item)
            if not history["events"]:
                history["events"].append({"recorded_at": utc_now(), "status": "NOT_PUBLISHED", **item,
                    "destination_url": links.get(f"{PREFIXES[mod]}_{platform.upper()}_URL"),
                    "note": "No upload or remote verification is recorded."})
            pending.append((path, history))
    for path, history in pending:
        save_history(path, history)
    return {"build_id": build_id, "journals": len(pending), "result": "INITIALIZED"}


def web_url(value):
    parsed = urlparse(value or "")
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def record(root, build_id, executable, mod, platform, status, url=None, remote_id=None,
           artifact_sha256=None, revision=None, evidence=None, note=None):
    require(mod in MODS and platform in PLATFORMS, "Invalid mod/platform")
    require(status in {"PREPARED", "UPLOADED", "VERIFIED", "FAILED"}, "Invalid publication status")
    require(not artifact_sha256 or re.fullmatch(r"[a-fA-F0-9]{64}", artifact_sha256), "Invalid artifact SHA-256")
    require(not revision or re.fullmatch(r"[a-fA-F0-9]{40,64}", revision), "Use a full Git revision")
    item = inspect(root, build_id, executable)[mod]
    path = platform_path(root, build_id, mod, platform)
    require(path.exists(), "Initialize journals before recording publication")
    history = load_history(path, "publication", mod, build_id, platform)
    compatible(history, item)
    if status in {"UPLOADED", "VERIFIED"}:
        require(web_url(url), "UPLOADED/VERIFIED require a concrete publication URL")
        require(evidence and (web_url(evidence) or (root / evidence).is_file()),
                "UPLOADED/VERIFIED require an existing evidence file or evidence URL")
        require(bool(revision if platform == "github" else artifact_sha256),
                "Provide --revision for GitHub or --artifact-sha256 for the published payload/archive")
    if revision:
        require(platform == "github", "--revision is reserved for GitHub dev publication")
        repo = scoped(root, "dev", mod)
        require(git(repo, executable, "rev-parse", f"{revision}^{{commit}}") == revision,
                "Revision does not resolve to a local commit")
        require(git(repo, executable, "rev-parse", f"{revision}:mod/{mod}") == item["source_git"]["runtime_tree"],
                "GitHub revision runtime differs from the associated source tree")
        require(item["source_matches"] and item["source_git"]["runtime_committed"],
                "GitHub source runtime differs from this build")
    if artifact_sha256:
        known = {item["payload_fingerprint"], item.get("archive", {}).get("sha256")}
        require(artifact_sha256.lower() in known, "Artifact hash must match this payload fingerprint or verified archive")
    history["events"].append({"recorded_at": utc_now(), "status": status, **item,
        "url": url, "remote_id": remote_id, "artifact_sha256": artifact_sha256,
        "published_revision": revision, "evidence": evidence, "note": note})
    save_history(path, history)
    return {"mod": mod, "platform": platform, "status": status, "events": len(history["events"])}


def chain_status(root, build_id, executable):
    inspected = inspect(root, build_id, executable)
    result = {}
    for mod, item in inspected.items():
        platforms = {}
        github_events = []
        for platform in PLATFORMS:
            path = platform_path(root, build_id, mod, platform)
            history = load_history(path, "publication", mod, build_id, platform)
            compatible(history, item)
            platforms[platform] = history["events"][-1]["status"] if history["events"] else "UNINITIALIZED"
            if platform == "github":
                github_events = [event for event in history["events"]
                                 if event.get("published_revision") and event["status"] in {"UPLOADED", "VERIFIED"}]
        published = github_events[-1]["published_revision"] if github_events else None
        dev_history = load_history(scoped(root, "dev", mod, "docs", "releases", "history.json"),
                                   "dev-to-game", mod)
        compatible(dev_history, item)
        association = next((event for event in reversed(dev_history["events"])
                            if event.get("build_id") == build_id), None)
        result[mod] = {"runtime": "MATCH" if item["source_matches"] else "DRIFT",
                       "game": "VERIFIED_LOCAL", "current_dev_commit": item["source_git"]["commit"],
                       "runtime_committed": item["source_git"]["runtime_committed"], "platforms": platforms,
                       "dev_association": association["status"] if association else "UNINITIALIZED",
                       "github": {"last_published_revision": published,
                                  "dev_revision": ("NOT_PUBLISHED" if not published else "CURRENT"
                                                   if published == item["source_git"]["commit"] else "AHEAD_OR_DIFFERENT")}}
    return {"build_id": build_id, "mods": result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "record", "status"):
        command = sub.add_parser(name)
        command.add_argument("--workspace", type=Path, required=True)
        command.add_argument("--build-id", required=True)
        command.add_argument("--git")
        if name == "record":
            command.add_argument("--mod", choices=MODS, required=True)
            command.add_argument("--platform", choices=PLATFORMS, required=True)
            command.add_argument("--status", choices=("PREPARED", "UPLOADED", "VERIFIED", "FAILED"), required=True)
            for option in ("url", "remote-id", "artifact-sha256", "revision", "evidence", "note"):
                command.add_argument("--" + option)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    root = args.pop("workspace").resolve()
    executable = git_executable(args.pop("git"))
    try:
        action = {"init": initialize, "record": record, "status": chain_status}[command]
        result = action(root, executable=executable, **args)
        print(json.dumps(result, indent=2))
        return 0
    except (JournalError, OSError, ValueError, KeyError) as error:
        print(f"release-journal: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
