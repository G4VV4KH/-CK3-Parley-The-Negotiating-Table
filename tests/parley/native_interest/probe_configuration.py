"""Explicit external inputs for native probes; importing performs no I/O.

These tools do not bundle CK3, user settings, the reviewed reload helper, or the
historical diagnostic baseline. Neither configuration nor validation launches
the engine. New evidence records retain the resolved paths and input hashes.
"""
import hashlib
import os
from pathlib import Path, PurePosixPath, PureWindowsPath


OPTIONS = {
    "evidence_root": ("--evidence-root", "PARLEY_QA_EVIDENCE_ROOT"),
    "game_root": ("--game-root", "CK3_GAME_ROOT"),
    "settings_source": ("--settings-source", "CK3_USER_SETTINGS"),
    "reload_helper": ("--reload-helper", "PARLEY_QA_RELOAD_HELPER"),
    "baseline_root": ("--baseline-root", "PARLEY_QA_BASELINE_ROOT"),
}
_cli = {}


def add_arguments(parser, names=None):
    for name in names or OPTIONS:
        flag, environment = OPTIONS[name]
        parser.add_argument(flag, type=Path,
                            help=f"Explicit external input; alternatively set {environment}.")


def configure(args):
    """CLI and environment may agree, but conflicting identities are rejected."""
    global _cli
    _cli = {name: getattr(args, name, None) for name in OPTIONS}
    for name, value in _cli.items():
        if value is not None:
            resolve(name)


def resolve(name):
    flag, environment = OPTIONS[name]
    supplied, inherited = _cli.get(name), os.environ.get(environment)
    if supplied is None and not inherited:
        raise ValueError(f"Missing external input: supply {flag} or {environment}")
    candidates = [Path(value).expanduser() for value in (supplied, inherited) if value is not None and str(value)]
    if any(not path.is_absolute() for path in candidates):
        raise ValueError(f"{flag} must be an explicit absolute path")
    candidates = [path.resolve() for path in candidates]
    if len(set(candidates)) != 1:
        raise ValueError(f"Conflicting {flag} and {environment}")
    path = candidates[0]
    if name in ("evidence_root", "game_root", "baseline_root"):
        if not path.is_dir():
            raise ValueError(f"{flag} must name an existing directory: {path}")
    elif not path.is_file():
        raise ValueError(f"{flag} must name a readable regular file: {path}")
    if name == "game_root":
        for member in ("binaries/ck3.exe", "launcher/launcher-settings.json"):
            if not (path / member).is_file():
                raise ValueError(f"Missing installed CK3 input: {path / member}")
    return path


class ExternalPath:
    """Lazy PathLike keeps pure fixture imports independent of local installs."""
    def __init__(self, name, *members):
        self.name, self.members = name, members

    def path(self):
        return resolve(self.name).joinpath(*self.members)

    def __fspath__(self):
        return os.fspath(self.path())

    def __str__(self):
        return str(self.path())

    def __truediv__(self, member):
        return ExternalPath(self.name, *self.members, member)

    def __getattr__(self, name):
        return getattr(self.path(), name)


def inputs(*names):
    """Validate/read every requested dependency before any output is created."""
    result = {}
    for name in names:
        path = resolve(name)
        item = {"path": str(path)}
        files = ({"executable": path / "binaries/ck3.exe",
                  "launcher_settings": path / "launcher/launcher-settings.json"}
                 if name == "game_root" else {"file": path} if path.is_file() else {})
        item["files"] = {key: {"path": str(member),
                               "sha256": hashlib.sha256(member.read_bytes()).hexdigest()}
                         for key, member in files.items()}
        result[name] = item
    return result


def validate_run(run, *required):
    identities = inputs(*required)
    run = Path(run)
    if not run.is_absolute():
        raise ValueError("Evidence run must be an explicit absolute path")
    run = run.resolve()
    # A supplied settings file identifies an input profile, never an output.
    if _cli.get("settings_source") is not None or os.environ.get("CK3_USER_SETTINGS"):
        profile = resolve("settings_source").parent
        if run == profile or profile in run.parents:
            raise ValueError("Evidence output must not be inside the input user profile")
    if len(run.parts) < 3:
        raise ValueError("Evidence requires a dedicated per-run directory")
    return run, identities


def baseline_member(entry, schema_version, baseline_root=None):
    """Resolve v2 relative members, or read explicitly pinned historical v1."""
    if schema_version == 1:
        path = Path(entry["baseline_file"])
        if not path.is_absolute():
            raise ValueError("Historical v1 baseline must have an absolute identity")
        path = path.resolve()
    elif schema_version == 2:
        member = entry["baseline_member"]
        relative = PurePosixPath(member)
        windows = PureWindowsPath(member)
        if (not member or "\\" in member or relative.is_absolute()
                or windows.drive or ".." in relative.parts or "." in member.split("/")
                or relative.as_posix() != member):
            raise ValueError("Unsafe diagnostic baseline member")
        root = Path(baseline_root) if baseline_root is not None else resolve("baseline_root")
        if not root.is_absolute():
            raise ValueError("Diagnostic baseline root must be absolute")
        root = root.resolve()
        if not root.is_dir():
            raise ValueError("Diagnostic baseline root is missing")
        path = (root / Path(*relative.parts)).resolve()
        if root not in path.parents:
            raise ValueError("Diagnostic baseline member escapes its root")
    else:
        raise ValueError("Unsupported diagnostic-review schema")
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        raise ValueError("Diagnostic baseline file is missing or its hash differs")
    return path
