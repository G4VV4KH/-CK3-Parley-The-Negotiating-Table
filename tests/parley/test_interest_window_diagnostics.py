"""Fail-closed unit contract for the separate window-startup classifier."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent / "native_interest"))
import review_window_diagnostics as review


def diagnostic_fixture():
    items = []
    for body, count in review.expected_english().items():
        instant = "12:00:01" if body in review.DISCOVERY else "12:00:02"
        items.extend([f"[{instant}]" + body.replace(review.ENGLISH_DISPLAY, review.RUSSIAN_DISPLAY)] * count)
    return "\n\n".join(items)


def native_fixture():
    labels = sorted(review.OPEN_LABELS)
    manifest = {"expected_labels": labels, "expected_count": len(labels)}
    debug = "[12:00:03] TNGUI_TEST|BEGIN|production_window\n"
    debug += "[12:00:04] TNGUI_PHASE|BEFORE|production_open_effect\n[12:00:04] TNGUI_PHASE|AFTER|production_open_effect\n"
    debug += "\n".join("[12:00:05] TNGUI_TEST|PASS|" + name for name in labels)
    debug += "\n[12:00:06] TNGUI_TEST|END|production_window\n"
    return manifest, debug


def frozen_fixture():
    runtime = {"gui/window.gui": "base", "script.txt": "unchanged"}
    probe = {"gui/window.gui": "observed", "fixture.txt": "test"}
    merged = runtime | probe
    plan = {"runtime_source_at_plan_sha256": runtime, "probe_sha256": probe,
            "expected_labels": sorted(review.OPEN_LABELS), "expected_count": 6,
            "kind": "PRODUCTION_WINDOW_OPEN_CRASH_DIAGNOSTIC", "marker_prefix": "TNGUI_TEST", "preset": "standard"}
    manifest = deepcopy(plan)
    manifest.update(runtime_sha256=runtime, merged_sha256=merged,
                    overrides={"gui/window.gui": {"base_sha256": "base", "test_sha256": "observed"}})
    return deepcopy(manifest), deepcopy(plan), deepcopy({"runtime": runtime, "probe": probe, "merged": merged})


class WindowDiagnosticReviewTests(unittest.TestCase):
    def setUp(self):
        self.error = diagnostic_fixture()
        self.manifest, self.debug = native_fixture()

    def assertRejected(self, error=None, debug=None):
        _, problems = review.validate_startup(self.error if error is None else error,
                                             self.debug if debug is None else debug)
        self.assertTrue(problems)

    def test_exact_sixty_russian_startup_records_pass(self):
        phase, problems = review.validate_startup(self.error, self.debug)
        self.assertEqual(problems, [])
        self.assertEqual(phase["record_count"], 60)
        self.assertEqual(review.validate_native(self.manifest, self.debug), [])

    def test_only_exact_display_punctuation_changes_in_off_chain(self):
        actual = Counter(review.russian_to_english(review.court.normalize(item))
                         for item in review.court.records(self.error))
        self.assertEqual(actual, review.expected_english())
        self.assertRejected(self.error.replace(review.RUSSIAN_DISPLAY, review.ENGLISH_DISPLAY))
        self.assertRejected(self.error.replace("\u00a0\u2014", " \u2014"))

    def test_added_gui_diagnostic_is_never_accepted(self):
        self.assertRejected(self.error + "\n[12:00:02][E][pdx_gui_container.cpp:142]: gui/tnt_types.gui:159 - layout error")

    def test_replacement_gui_diagnostic_is_never_accepted(self):
        items = review.court.records(self.error)
        items[-1] = "[12:00:02][E][pdx_gui_container.cpp:142]: gui/tnt_types.gui:159 - layout error"
        self.assertRejected("\n".join(items))

    def test_changed_path_identity_or_wording_fails(self):
        for old, new in (("4294967295", "4294967294"), ("line: 9 ", "line: 10 "),
                         ("00_default_cultures", "01_default_cultures"), ("is not valid", "is invalid")):
            with self.subTest(old=old):
                self.assertRejected(self.error.replace(old, new, 1))

    def test_missing_duplicate_or_extra_burst_fails(self):
        items = review.court.records(self.error)
        self.assertRejected("\n".join(items[:-1]))
        self.assertRejected("\n".join(items + [items[-1]]))
        self.assertRejected(self.error + "\n" + self.error)

    def test_split_court_burst_fails_even_if_bodies_match(self):
        self.assertRejected(self.error.replace("[12:00:02]", "[12:00:01]", 1))

    def test_post_begin_or_equal_begin_burst_fails(self):
        self.assertRejected(self.error.replace("[12:00:02]", "[12:00:03]"))
        self.assertRejected(self.error.replace("[12:00:02]", "[12:00:04]"))

    def test_discovery_after_court_or_duplicate_begin_fails(self):
        self.assertRejected(self.error.replace("[12:00:01]", "[12:00:03]"))
        self.assertRejected(debug=self.debug + "[12:00:07] TNGUI_TEST|BEGIN|production_window\n")

    def test_unstamped_record_and_nonrecord_text_fail(self):
        self.assertRejected(self.error.replace("[12:00:01]", "", 1))
        self.assertRejected("unexpected preface\n" + self.error)

    def test_failed_duplicate_missing_native_assertions_fail(self):
        for debug in (self.debug.replace("|PASS|", "|FAIL|", 1),
                      self.debug + "[12:00:05] TNGUI_TEST|PASS|native_open_participants\n",
                      self.debug.replace("TNGUI_TEST|PASS|native_open_participants", "ignored")):
            self.assertTrue(review.validate_native(self.manifest, debug))

    def test_missing_actual_opener_or_boundary_order_fails(self):
        self.assertTrue(review.validate_native(self.manifest, self.debug.replace("TNGUI_PHASE|AFTER", "ignored")))
        self.assertTrue(review.validate_native(self.manifest, self.debug.replace("|BEGIN|", "|END|", 1)))

    def test_reduced_or_duplicate_declared_assertion_set_fails(self):
        manifest = {"expected_labels": [], "expected_count": 0}
        self.assertTrue(review.validate_native(manifest, self.debug))
        manifest = {"expected_labels": self.manifest["expected_labels"] * 2,
                    "expected_count": self.manifest["expected_count"] * 2}
        self.assertTrue(review.validate_native(manifest, self.debug))

    def test_intact_frozen_source_closure_passes(self):
        self.assertEqual(review.validate_frozen(*frozen_fixture()), [])

    def test_changed_runtime_probe_or_merged_file_fails(self):
        for tree in ("runtime", "probe", "merged"):
            with self.subTest(tree=tree):
                manifest, plan, trees = frozen_fixture()
                trees[tree]["gui/window.gui"] = "drift"
                self.assertTrue(review.validate_frozen(manifest, plan, trees))

    def test_missing_or_extra_frozen_file_fails(self):
        for extra in (False, True):
            manifest, plan, trees = frozen_fixture()
            if extra:
                trees["merged"]["unexpected.txt"] = "new"
            else:
                del trees["runtime"]["script.txt"]
            self.assertTrue(review.validate_frozen(manifest, plan, trees))

    def test_court_override_fails_even_if_inventory_is_rebound(self):
        manifest, plan, trees = frozen_fixture()
        path = "gfx/court_scene/scene_cultures/00_default_cultures.txt"
        for tree in trees:
            trees[tree][path] = "override"
            manifest[tree + "_sha256"][path] = "override"
        self.assertTrue(review.validate_frozen(manifest, plan, trees))

    def test_plan_or_override_base_drift_fails(self):
        manifest, plan, trees = frozen_fixture()
        plan["expected_count"] = 7
        self.assertTrue(review.validate_frozen(manifest, plan, trees))
        manifest, plan, trees = frozen_fixture()
        manifest["overrides"]["gui/window.gui"]["base_sha256"] = "wrong"
        self.assertTrue(review.validate_frozen(manifest, plan, trees))

    def test_self_consistent_merged_hash_cannot_hide_unrecorded_override(self):
        manifest, plan, trees = frozen_fixture()
        manifest["merged_sha256"]["script.txt"] = "edited"
        trees["merged"]["script.txt"] = "edited"
        self.assertTrue(review.validate_frozen(manifest, plan, trees))


if __name__ == "__main__":
    unittest.main()
