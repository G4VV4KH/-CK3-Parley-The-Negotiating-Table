"""Fail-closed local kit checks; fake evidence never reaches a release directory."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "tools/release"
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location("kit130_test", TOOLS / "prepare_parley_1_3_upload_kit.py")
kit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kit)


def png(width, height, fill=0):
    stream = io.BytesIO()
    Image.new("RGB", (width, height), (10, 20, 30)).save(stream, format="PNG")
    return stream.getvalue() + b"x" * fill


class KitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def ref(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"path": str(path), "sha256": kit.candidate.sha(data), "bytes": len(data)}

    def native_fixture(self):
        files = {"descriptor.mod": {"bytes": 1, "sha256": "a" * 64}}
        fresh = {"status": kit.NATIVE_PASS, "required_gaps": [], "visual_status": "NOT_VERIFIED",
                 "target_game_version": "1.20.0.4",
                 "candidate_manifest_sha256": "b" * 64, "runtime_full_file_inventory": files,
                 "per_language": {language: {"status": kit.NATIVE_PASS, "covered_public_keys": 720,
                                               "required_gaps": []} for language in kit.LANGUAGES}}
        return fresh, {"game_runtime": files}

    def run_native(self, saved=None, fresh=None):
        baseline, manifest = self.native_fixture()
        saved = baseline if saved is None else saved
        fresh = saved if fresh is None else fresh
        verifier = self.ref("verifier.py", b"# test-only fake; imported via mock only\n")
        support = self.ref("support.py", b"# test-only evidence support\n")
        dependencies = [{key: ref[key] for key in ("path", "sha256")} for ref in (verifier, support)]
        saved.setdefault("verifier_dependencies", dependencies)
        fresh.setdefault("verifier_dependencies", dependencies)
        ref = self.ref("gate.json", kit.candidate.json_bytes(saved))
        with mock.patch.object(kit.legacy, "load_module", return_value=SimpleNamespace(verify_gate=lambda *args: fresh)):
            return kit.native_gate(ref, verifier, [support], {"path": str(self.root / "candidate-manifest.json"),
                                  "sha256": "b" * 64}, manifest)

    def test_native_requires_recomputed_exact_nine_language_result(self):
        result = self.run_native()
        self.assertEqual(result["status"], kit.NATIVE_PASS)
        self.assertEqual(result["visual_status"], "NOT_VERIFIED")

    def test_native_saved_pass_cannot_mask_new_failure(self):
        good, _ = self.native_fixture()
        bad = copy.deepcopy(good)
        bad["per_language"]["french"]["status"] = "FAIL"
        with self.assertRaisesRegex(kit.KitError, "fresh evidence recomputation"):
            self.run_native(saved=good, fresh=bad)

    def test_native_timestamp_alone_may_change(self):
        saved, _ = self.native_fixture()
        fresh = copy.deepcopy(saved)
        saved["recorded_utc"], fresh["recorded_utc"] = "before", "after"
        self.assertEqual(self.run_native(saved, fresh)["status"], kit.NATIVE_PASS)

    def test_native_no_missing_language_or_failed_blank_context_accounting(self):
        for mutation in ("missing", "few_keys", "pending", "gap", "top_gap", "wrong_candidate", "wrong_runtime", "wrong_engine"):
            bad, _ = self.native_fixture()
            if mutation == "missing":
                del bad["per_language"]["korean"]
            elif mutation == "few_keys":
                bad["per_language"]["french"]["covered_public_keys"] = 719
            elif mutation == "pending":
                bad["per_language"]["russian"]["status"] = "REVIEW_REQUIRED"
            elif mutation == "gap":
                bad["per_language"]["english"]["required_gaps"] = ["context_unverified"]
            elif mutation == "top_gap":
                bad["required_gaps"] = ["unknown diagnostic"]
            elif mutation == "wrong_candidate":
                bad["candidate_manifest_sha256"] = "0" * 64
            elif mutation == "wrong_engine":
                bad["target_game_version"] = "1.19.0.6"
            else:
                bad["runtime_full_file_inventory"] = {}
            with self.subTest(mutation=mutation), self.assertRaises(kit.KitError):
                self.run_native(bad)

    def test_native_plain_pass_boolean_and_visual_omission_rejected(self):
        for value in ("PASS", True, "PASS_WITHOUT_NATIVE_RUN"):
            bad, _ = self.native_fixture()
            bad["status"] = value
            with self.assertRaises(kit.KitError):
                self.run_native(bad)
        bad, _ = self.native_fixture()
        del bad["visual_status"]
        with self.assertRaises(kit.KitError):
            self.run_native(bad)

    def test_unpinned_native_dependency_is_rejected(self):
        bad, _ = self.native_fixture()
        bad["verifier_dependencies"] = []
        with self.assertRaisesRegex(kit.KitError, "dependency inventory"):
            self.run_native(bad)

    def test_hash_pinned_evidence_and_absolute_path_required(self):
        ref = self.ref("input.txt", b"reviewed")
        self.assertEqual(kit.read_ref(ref), b"reviewed")
        Path(ref["path"]).write_bytes(b"drift")
        with self.assertRaises(kit.KitError):
            kit.read_ref(ref)
        with self.assertRaises(kit.KitError):
            kit.read_ref({"path": "relative", "sha256": "0" * 64})

    def test_linguistic_unreviewed_receipt_cannot_pass(self):
        with self.assertRaisesRegex(kit.KitError, "Unreviewed linguistic"):
            kit.linguistic_gate({"path": str(self.root / "anything"), "sha256": "0" * 64}, {})

    def test_all_gate_checks_precede_copy_and_output_preparation(self):
        with mock.patch.object(kit, "checked_candidate", return_value=({}, {}, {})), \
             mock.patch.object(kit, "linguistic_gate", side_effect=kit.KitError("pending")), \
             mock.patch.object(kit, "checked_copy") as copy_method:
            with self.assertRaisesRegex(kit.KitError, "pending"):
                kit.prepare({"schema": "parley-130-upload-plan-v1", "candidate": {}, "linguistic_review": {}})
            copy_method.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_platform_archive_shapes_and_steam_only_identity_overlay(self):
        game = {"descriptor.mod": b'version="1.3.0"\nname="Parley: The Negotiating Table"\n',
                "common/x.txt": b"fixture = 1\n"}
        files, proof = kit.platform_files(game)
        with zipfile.ZipFile(io.BytesIO(files["03-PARADOX/parley-1.3.0-PARADOX.zip"])) as archive:
            self.assertEqual(set(archive.namelist()), set(game))
            self.assertEqual(archive.read("descriptor.mod"), game["descriptor.mod"])
        with zipfile.ZipFile(io.BytesIO(files["04-NEXUS/parley-1.3.0-NEXUS-MANUAL.zip"])) as archive:
            self.assertEqual(set(archive.namelist()), {"parley/descriptor.mod", "parley/common/x.txt", "parley.mod", "INSTALL.txt"})
            self.assertNotIn(b"remote_file_id", archive.read("parley.mod"))
            self.assertIn(b'path="mod/parley"', archive.read("parley.mod"))
            self.assertIn(b"For CK3 1.20.0.4", archive.read("INSTALL.txt"))
        self.assertEqual(files["01-STEAM/runtime/parley/common/x.txt"], game["common/x.txt"])
        self.assertEqual(files["01-STEAM/runtime/parley/descriptor.mod"],
                         game["descriptor.mod"] + b'remote_file_id="3811090081"\n')
        self.assertEqual(proof["game_payload"], kit.legacy.inventory(game))

    def test_archive_output_is_deterministic(self):
        files = {"z.txt": b"a", "a.txt": b"b"}
        self.assertEqual(kit.zipped(files), kit.zipped(dict(reversed(list(files.items())))))

    def copy_path_fixture(self):
        repo = self.root / "copy-repo"
        rendered = {key: str(repo / "publishing/generated" / name) for key, name in {
            "steam": "steam.bbcode", "paradox_rich": "paradox.html", "nexus": "nexus.bbcode",
            "github": "github.md", "metadata": "metadata.json"}.items()}
        for path in rendered.values():
            kit.candidate.write_new(Path(path), b"Synthetic rendered publication copy\n")
        kit.candidate.write_new(repo / "README.md", b"Synthetic rendered publication copy\n" + kit.legacy.CONTRIBUTING_FOOTER)
        return repo, {"rendered_outputs": rendered}

    def test_github_revision_accepts_only_renderer_or_exact_public_readme(self):
        repo, revision = self.copy_path_fixture()
        kit.checked_rendered_paths(revision, repo)
        revision["rendered_outputs"]["github"] = str(repo / "README.md")
        kit.checked_rendered_paths(revision, repo)

    def test_github_readme_body_or_footer_drift_rejected_for_both_routes(self):
        repo, revision = self.copy_path_fixture()
        original = (repo / "README.md").read_bytes()
        for route in (repo / "README.md", repo / "publishing/generated/github.md"):
            revision["rendered_outputs"]["github"] = str(route)
            for changed in (original + b"Unreviewed footer", original.replace(b"Synthetic", b"Changed"),
                            b"Synthetic rendered publication copy\n"):
                (repo / "README.md").write_bytes(changed)
                with self.subTest(route=route, data=changed), self.assertRaisesRegex(kit.KitError, "exact contributor footer"):
                    kit.checked_rendered_paths(revision, repo)

    def test_copy_revision_cannot_validate_an_alternate_identical_file(self):
        repo, revision = self.copy_path_fixture()
        duplicate = repo / "alternate.md"
        duplicate.write_bytes((repo / "README.md").read_bytes())
        for key in revision["rendered_outputs"]:
            changed = copy.deepcopy(revision)
            changed["rendered_outputs"][key] = str(duplicate)
            with self.subTest(key=key), self.assertRaisesRegex(kit.KitError, "Validated copy differs"):
                kit.checked_rendered_paths(changed, repo)

    def test_native_sha_only_inventory_cannot_replace_exact_size_hash_mapping(self):
        bad, _ = self.native_fixture()
        bad["runtime_full_file_inventory"] = {name: row["sha256"] for name, row in bad["runtime_full_file_inventory"].items()}
        with self.assertRaisesRegex(kit.KitError, "exact candidate GAME bytes"):
            self.run_native(bad)

    def media_fixture(self):
        square = self.ref("square.png", png(1024, 1024))
        horizontal = self.ref("horizontal.png", png(1920, 1080))
        gallery = self.ref("gallery.png", png(1920, 1080, 1))
        square["provenance"] = horizontal["provenance"] = "Synthetic test image, never published"
        gallery.update({"caption_en": "Fixture", "provenance": "Synthetic test image", "source": dict(gallery)})
        return {"schema": "parley-130-media-plan-v1", "square": square, "horizontal": horizontal,
                "gallery": [gallery]}, {"thumbnail.png": png(512, 512)}

    def test_media_square_horizontal_thumbnail_and_png_gallery(self):
        plan, game = self.media_fixture()
        files = kit.media_inputs(plan, game)
        self.assertIn("05-IMAGES/parley-cover-square-1024x1024.png", files)
        self.assertIn("05-IMAGES/parley-cover-horizontal-1920x1080.png", files)
        self.assertIn("05-IMAGES/GALLERY/01.png", files)
        self.assertEqual(files["05-IMAGES/thumbnail.png"], game["thumbnail.png"])

    def test_cover_is_not_subject_to_steam_gallery_byte_limit(self):
        plan, game = self.media_fixture()
        cover = self.ref("large-horizontal.png", png(1920, 1080, 2_315_244))
        cover["provenance"] = "Synthetic equivalent of an approved separately uploaded Paradox cover"
        plan["horizontal"] = cover
        files = kit.media_inputs(plan, game)
        self.assertEqual(files["05-IMAGES/parley-cover-horizontal-1920x1080.png"], Path(cover["path"]).read_bytes())

    def test_media_missing_provenance_and_wrong_geometry_rejected(self):
        for failure in ("caption", "provenance", "geometry", "thumbnail", "format"):
            plan, game = self.media_fixture()
            if failure in ("caption", "provenance"):
                del plan["gallery"][0]["caption_en" if failure == "caption" else "provenance"]
            elif failure == "geometry":
                plan["horizontal"] = self.ref("bad.png", png(1024, 1024))
            elif failure == "thumbnail":
                game["thumbnail.png"] = png(1024, 1024)
            else:
                plan["gallery"][0].update(self.ref("fake.jpg", png(1920, 1080)))
            with self.subTest(failure=failure), self.assertRaises(kit.KitError):
                kit.media_inputs(plan, game)

    def test_media_two_mb_and_eight_mb_limits_are_strict(self):
        plan, game = self.media_fixture()
        huge = self.ref("huge.png", png(1920, 1080, 2_000_000))
        plan["gallery"][0].update(huge)
        with self.assertRaises(kit.KitError):
            kit.media_inputs(plan, game)
        plan, game = self.media_fixture()
        large = self.ref("large.png", png(1920, 1080, 1_700_000))
        plan["gallery"][0].update(large)
        plan["gallery"] *= 5
        with self.assertRaisesRegex(kit.KitError, "batch"):
            kit.media_inputs(plan, game)

    def test_corrupt_header_only_and_truncated_png_jpeg_rejected(self):
        header = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 1920, 1080) + b"x"
        stream = io.BytesIO()
        Image.new("RGB", (1920, 1080), (10, 20, 30)).save(stream, format="JPEG")
        for data, suffix in ((header, ".png"), (png(1920, 1080)[:40], ".png"),
                             (stream.getvalue()[:-200], ".jpg")):
            with self.subTest(suffix=suffix, bytes=len(data)), self.assertRaises(kit.KitError):
                kit.validate_image(data, (1920, 1080), suffix, "negative fixture")

    def source_fixture(self, extras=None, repo_name="repo"):
        repo = self.root / repo_name
        files = {"mod/parley/descriptor.mod": b'version="1.3.0"\n', "README.md": b"README",
                 "dev.md": b"Dev", "publishing/description.en.md": b"Description", **(extras or {})}
        for name, data in files.items():
            kit.candidate.write_new(repo / name, data)
        runtime = {"descriptor.mod": files["mod/parley/descriptor.mod"]}
        def git_command(args, cwd):
            if "status" in args:
                return ""
            if "rev-parse" in args:
                return "a" * 40
            return "\0".join(files) + "\0"
        return repo, runtime, git_command

    def test_clean_source_export_preserves_runtime_and_separate_history(self):
        repo, runtime, run = self.source_fixture()
        with mock.patch.object(kit.legacy, "run", side_effect=run):
            files, proof = kit.source_export(repo, "a" * 40, runtime, [])
        self.assertEqual(files["mod/parley/descriptor.mod"], runtime["descriptor.mod"])
        self.assertTrue(proof["source_clean"])
        self.assertIn("not a Git tree", proof["scope"])

    def test_dirty_source_and_missing_new_tracked_runtime_rejected(self):
        repo, runtime, run = self.source_fixture()
        with mock.patch.object(kit.legacy, "run", return_value="?? untracked-interest.txt"):
            with self.assertRaisesRegex(kit.KitError, "reviewed clean commit"):
                kit.source_export(repo, "a" * 40, runtime, [])
        runtime["common/new-interest.txt"] = b"new = yes"
        kit.candidate.write_new(repo / "mod/parley/common/new-interest.txt", b"new = yes")
        with mock.patch.object(kit.legacy, "run", side_effect=run):
            with self.assertRaisesRegex(kit.KitError, "omits candidate runtime"):
                kit.source_export(repo, "a" * 40, runtime, [])

    def test_cjs_machine_path_cannot_bypass_text_sanitizer(self):
        path_text = ("C:" + "/Users/Private/node_modules").encode()
        repo, runtime, run = self.source_fixture({"tools/design/prototype.cjs": path_text})
        with mock.patch.object(kit.legacy, "run", side_effect=run):
            with self.assertRaisesRegex(kit.legacy.PreparationError, "Unclassified machine path"):
                kit.source_export(repo, "a" * 40, runtime, [])

    def test_lowercase_drive_path_cannot_bypass_text_sanitizer(self):
        text = ("c:" + "/Users/Private/node_modules").encode()
        repo, runtime, run = self.source_fixture({"tools/design/prototype.cjs": text})
        with mock.patch.object(kit.legacy, "run", side_effect=run):
            with self.assertRaisesRegex(kit.KitError, "Unclassified machine path"):
                kit.source_export(repo, "a" * 40, runtime, [])

    def test_real_drive_paths_rejected_in_every_new_helper_text_type(self):
        variants = []
        for drive in ("C", "c"):
            for separator in ("/", "\\"):
                path = drive + ":" + separator + "Users" + separator + "Private"
                variants.extend((path.encode(), json.dumps({"path": path}).encode()))
        for suffix in (".cjs", ".js", ".mjs", ".ts", ".sh", ".toml", ".yaml", ".py", ".json"):
            for index, data in enumerate(variants):
                name = "tools/design/prototype" + suffix
                repo, runtime, run = self.source_fixture({name: data}, "case" + suffix + str(index))
                with self.subTest(suffix=suffix, data=data), mock.patch.object(kit.legacy, "run", side_effect=run):
                    with self.assertRaisesRegex((kit.KitError, kit.legacy.PreparationError), "Unclassified machine path"):
                        kit.source_export(repo, "a" * 40, runtime, [])

    def test_native_timestamp_regexes_are_preserved_without_file_exemptions(self):
        text = b"\n".join((
            rb're.sub(r"^\[\d\d:\d\d:\d\d\]", "", record, count=1)',
            rb're.split(r"(?m)(?=^\[\d\d:\d\d:\d\d\])", diagnostic)',
            rb're.findall(r"(?m)^\[(\d\d:\d\d:\d\d)\].*", text)',
        ))
        for suffix in (".py", ".cjs", ".js", ".mjs", ".ts", ".sh", ".toml", ".yaml"):
            name = "tools/design/timestamp" + suffix
            repo, runtime, run = self.source_fixture({name: text}, "timestamp" + suffix)
            with self.subTest(suffix=suffix), mock.patch.object(kit.legacy, "run", side_effect=run):
                files, proof = kit.source_export(repo, "a" * 40, runtime, [])
            self.assertEqual(files[name], text)
            self.assertEqual((repo / name).read_bytes(), text)
            self.assertNotIn(name, proof["transformations"])

    def test_timestamp_regex_cannot_hide_a_real_path_in_the_same_file(self):
        text = rb'pattern = r"\d\d:\d\d:\d\d"' + b"\n" + ("c:" + "/Users/Private").encode()
        repo, runtime, run = self.source_fixture({"tools/design/mixed.cjs": text})
        with mock.patch.object(kit.legacy, "run", side_effect=run):
            with self.assertRaisesRegex(kit.KitError, "Unclassified machine path"):
                kit.source_export(repo, "a" * 40, runtime, [])

    def test_only_omitted_logger_may_get_known_citation_sanitization(self):
        logger = (REPO / "mod/parley" / kit.legacy.LOGGER_FILE).read_bytes()
        repo, runtime, run = self.source_fixture({"mod/parley/" + kit.legacy.LOGGER_FILE: logger})
        runtime[kit.legacy.LOGGER_FILE] = logger
        with mock.patch.object(kit.legacy, "run", side_effect=run):
            files, report = kit.source_export(repo, "a" * 40, runtime, [])
        name = "mod/parley/" + kit.legacy.LOGGER_FILE
        self.assertNotEqual(files[name], logger)
        self.assertEqual(files[name], kit.legacy.sanitize_source(name, logger)[0])
        self.assertIn(name, report["transformations"])
        self.assertEqual((repo / name).read_bytes(), logger)

    def test_narrow_export_only_substitution_requires_exact_input_and_count(self):
        text = ("C:" + "/Users/Private/evidence").encode()
        repo, runtime, run = self.source_fixture({"docs/test.md": text})
        item = {"file": "docs/test.md", "source_sha256": kit.candidate.sha(text), "before": text.decode(),
                "after": "<external-test-evidence>", "count": 1, "reason": "Portable provenance; external input required"}
        with mock.patch.object(kit.legacy, "run", side_effect=run):
            files, proof = kit.source_export(repo, "a" * 40, runtime, [item])
            self.assertEqual(files["docs/test.md"], b"<external-test-evidence>")
            self.assertEqual((repo / "docs/test.md").read_bytes(), text)
            self.assertIn("docs/test.md", proof["transformations"])
            for altered in ({**item, "count": 2}, {**item, "source_sha256": "0" * 64},
                            {**item, "file": "mod/parley/descriptor.mod"}, {**item, "before": "not a path"}):
                with self.assertRaises(kit.KitError):
                    kit.source_export(repo, "a" * 40, runtime, [altered])

    def test_guide_does_not_claim_external_or_visual_acceptance(self):
        text = kit.guide("test", "a" * 40, {"visual_status": "NOT_VERIFIED"}, {
            "05-IMAGES/cover-square.jpg": b"", "05-IMAGES/cover-horizontal.png": b""})
        for phrase in ("NOT_ATTEMPTED", "NOT_VERIFIED", "not pixel/layout/hover", "Preserve existing Git history",
                       "For CK3 1.20.0.4", "Steam 3811090081", "Nexus 399", "Do not reuse old Nexus file 2607"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
