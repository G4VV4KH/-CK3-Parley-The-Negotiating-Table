"""Focused invariants for release journals; temporary repositories only."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "tools/release/release_journal.py"
SPEC = importlib.util.spec_from_file_location("release_journal", SCRIPT)
journal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(journal)


class ReleaseJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.build = "2026-09-30-test"
        self.git = journal.git_executable()
        self.manifest = {"schema": 1, "build_id": self.build, "mods": {}}
        for mod in journal.MODS:
            repo = self.root / "dev" / mod
            runtime = repo / "mod" / mod
            runtime.mkdir(parents=True)
            (runtime / "descriptor.mod").write_text('version="1.0.0"\n', encoding="utf-8")
            (runtime / "README.md").write_text("Source-only readme\n", encoding="utf-8")
            (runtime / "common").mkdir()
            (runtime / "common/runtime.txt").write_text("effect = yes\n", encoding="utf-8")
            game = self.root / "game" / self.build / mod
            (game / "common").mkdir(parents=True)
            (game / "descriptor.mod").write_bytes((runtime / "descriptor.mod").read_bytes())
            (game / "common/runtime.txt").write_bytes((runtime / "common/runtime.txt").read_bytes())
            journal.git(repo, self.git, "init", "-q")
            journal.git(repo, self.git, "config", "user.email", "test@example.invalid")
            journal.git(repo, self.git, "config", "user.name", "Journal Test")
            journal.git(repo, self.git, "config", "core.autocrlf", "false")
            journal.git(repo, self.git, "add", ".")
            journal.git(repo, self.git, "commit", "-qm", "fixture")
            self.manifest["mods"][mod] = {"source": journal.inventory(runtime, source=True),
                                           "game": journal.inventory(game)}
        (self.root / "game" / self.build / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def initialize(self):
        return journal.initialize(self.root, self.build, self.git)

    def history_file(self, platform="steam"):
        return journal.platform_path(self.root, self.build, "parley", platform)

    def test_initialization_is_idempotent_and_keeps_payload_pristine(self):
        before = journal.inventory(self.root / "game" / self.build)
        self.initialize()
        histories = {p: p.read_bytes() for p in self.root.rglob("history.json")}
        self.initialize()
        self.assertEqual(histories, {p: p.read_bytes() for p in self.root.rglob("history.json")})
        self.assertEqual(before, journal.inventory(self.root / "game" / self.build))
        self.assertEqual(len(histories), 15)
        for path, content in histories.items():
            self.assertNotIn(b"\r\n", content, str(path))
            self.assertNotIn(b"\r\n", path.with_name("HISTORY.md").read_bytes(), str(path))
        self.assertEqual(journal.read_json(self.history_file())["events"][0]["status"], "NOT_PUBLISHED")

    def test_game_tamper_and_extra_file_block_before_any_writes(self):
        target = self.root / "game" / self.build / "parley/common/runtime.txt"
        original = target.read_bytes()
        target.write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(journal.JournalError, "payload inventory/hash mismatch"):
            self.initialize()
        self.assertFalse((self.root / "game/_history").exists())
        target.write_bytes(original)
        target.with_name("extra.txt").write_text("extra", encoding="utf-8")
        with self.assertRaises(journal.JournalError):
            self.initialize()

    def test_source_drift_is_reported_and_blocks_new_association(self):
        self.initialize()
        runtime = self.root / "dev/parley/mod/parley/common/runtime.txt"
        runtime.write_text("changed", encoding="utf-8")
        report = journal.chain_status(self.root, self.build, self.git)
        self.assertEqual(report["mods"]["parley"]["runtime"], "DRIFT")
        with self.assertRaisesRegex(journal.JournalError, "Dev runtime must match"):
            self.initialize()

    def test_docs_only_commit_does_not_report_runtime_drift(self):
        self.initialize()
        repo = self.root / "dev/parley"
        old = journal.git(repo, self.git, "rev-parse", "HEAD")
        (repo / "README.md").write_text("Release documentation updated", encoding="utf-8")
        journal.git(repo, self.git, "add", "README.md")
        journal.git(repo, self.git, "commit", "-qm", "docs only")
        report = journal.chain_status(self.root, self.build, self.git)["mods"]["parley"]
        self.assertNotEqual(old, report["current_dev_commit"])
        self.assertEqual(report["runtime"], "MATCH")
        self.initialize()
        self.assertEqual(len(journal.read_json(repo / "docs/releases/history.json")["events"]), 1)

    def test_no_publication_without_evidence_and_upload_is_not_verified(self):
        self.initialize()
        args = (self.root, self.build, self.git, "parley", "steam")
        for status in ("UPLOADED", "VERIFIED"):
            with self.assertRaises(journal.JournalError):
                journal.record(*args, status=status, url="https://example.invalid/item/123")
        evidence = self.root / "upload-response.json"
        evidence.write_text('{"id":123}', encoding="utf-8")
        sha = journal.fingerprint(self.manifest["mods"]["parley"]["game"])
        journal.record(*args, status="UPLOADED", url="https://example.invalid/item/123",
                       remote_id="123", artifact_sha256=sha, evidence=str(evidence))
        self.initialize()
        events = journal.read_json(self.history_file())["events"]
        self.assertEqual([e["status"] for e in events], ["NOT_PUBLISHED", "UPLOADED"])
        journal.record(*args, status="VERIFIED", url="https://example.invalid/item/123",
                       artifact_sha256=sha, evidence=str(evidence), note="Separate download verification")
        self.assertEqual(journal.chain_status(self.root, self.build, self.git)["mods"]["parley"]["platforms"]["steam"], "VERIFIED")

    def test_github_records_commit_separately_from_game_hash(self):
        self.initialize()
        repo = self.root / "dev/parley"
        revision = journal.git(repo, self.git, "rev-parse", "HEAD")
        journal.record(self.root, self.build, self.git, "parley", "github", "UPLOADED",
                       url="https://github.com/example/repo", revision=revision,
                       evidence="https://github.com/example/repo/commit/" + revision)
        event = journal.read_json(self.history_file("github"))["events"][-1]
        self.assertEqual(event["published_revision"], revision)
        self.assertIsNone(event["artifact_sha256"])
        (repo / "README.md").write_text("New unpublished documentation", encoding="utf-8")
        journal.git(repo, self.git, "add", "README.md")
        journal.git(repo, self.git, "commit", "-qm", "unpublished docs")
        state = journal.chain_status(self.root, self.build, self.git)["mods"]["parley"]
        self.assertEqual(state["runtime"], "MATCH")
        self.assertEqual(state["platforms"]["github"], "UPLOADED")
        self.assertEqual(state["github"]["last_published_revision"], revision)
        self.assertEqual(state["github"]["dev_revision"], "AHEAD_OR_DIFFERENT")

    def test_invalid_path_and_unknown_artifact_rejected(self):
        with self.assertRaises(journal.JournalError):
            journal.initialize(self.root, "../escape", self.git)
        self.initialize()
        with self.assertRaisesRegex(journal.JournalError, "Artifact hash"):
            journal.record(self.root, self.build, self.git, "parley", "steam", "PREPARED",
                           artifact_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
