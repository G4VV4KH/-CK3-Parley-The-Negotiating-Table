"""Public tooling inputs are explicit; no browser, font download or CK3 launch."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

try:
    from PIL import Image, ImageChops
except ImportError:
    Image = ImageChops = None


ROOT = Path(__file__).resolve().parents[2]
ANNOTATOR = ROOT / "tools/publishing/annotate_interest_preview.py"
PROTOTYPE = ROOT / "tools/design/check_interest_prototype.cjs"


class PrototypePortabilityTests(unittest.TestCase):
    def test_standard_package_resolution_remains_opt_in(self):
        text = PROTOTYPE.read_text(encoding="utf-8")
        self.assertIn("require('playwright')", text)
        self.assertLess(text.index("if (!process.argv.includes('--browser'))"),
                        text.index("require('playwright')"))
        self.assertNotRegex(text, re.compile(r"[a-z]:[/\\]|\\\\[a-z0-9_-]+\\", re.I))
        self.assertIn("NOT_VERIFIED", text)

    @unittest.skipUnless(shutil.which("node") and os.environ.get("PARLEY_QA_PROTOTYPE_HTML"),
                         "Requires caller-provided Node and external prototype HTML")
    def test_external_model_runs_without_browser_opt_in(self):
        result = subprocess.run([shutil.which("node"), str(PROTOTYPE),
                                 str(Path(os.environ["PARLEY_QA_PROTOTYPE_HTML"]).resolve())],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([row["status"] for row in records],
                         ["PASS", "PASS", "NOT_VERIFIED"])

    @unittest.skipUnless(shutil.which("node") and os.environ.get("PARLEY_QA_PROTOTYPE_HTML"),
                         "Requires caller-provided Node and external prototype HTML")
    def test_opt_in_unavailable_browser_reports_not_verified_without_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            preload = Path(directory) / "no-browser.cjs"
            preload.write_text(
                "const Module=require('node:module');const original=Module._load;"
                "Module._load=function(name,...args){if(name==='playwright')return"
                "{chromium:{launch:async()=>{throw new Error('fixture browser unavailable')}}};"
                "return original.call(this,name,...args)};", encoding="utf-8")
            result = subprocess.run(
                [shutil.which("node"), "--require", str(preload), str(PROTOTYPE),
                 str(Path(os.environ["PARLEY_QA_PROTOTYPE_HTML"]).resolve()), "--browser"],
                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        last = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(last["status"], "NOT_VERIFIED")
        self.assertIn("fixture browser unavailable", last["reason"])


@unittest.skipIf(Image is None, "Annotation tool requires caller-installed Pillow")
class AnnotationFontInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.png"
        Image.new("RGB", (1920, 1080), (30, 35, 40)).save(self.source)
        self.output = self.root / "new-output" / "annotated.png"
        self.receipt = self.root / "new-output" / "receipt.json"
        self.source_sha = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def invoke(self, extra):
        return subprocess.run([sys.executable, "-B", str(ANNOTATOR), "--source", str(self.source),
                               "--output", str(self.output), "--receipt", str(self.receipt), *extra],
                              capture_output=True, text=True, encoding="utf-8")

    def test_missing_directory_and_invalid_font_fail_before_output(self):
        invalid = self.root / "invalid.ttf"
        invalid.write_bytes(b"not a font")
        for extra in ([], ["--font", str(self.root / "missing.ttf")],
                      ["--font", str(self.root)], ["--font", str(invalid)]):
            with self.subTest(extra=extra):
                result = self.invoke(extra)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.parent.exists())
                self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.source_sha)

    @unittest.skipUnless(os.environ.get("PARLEY_QA_ANNOTATION_FONT"),
                         "Requires explicitly supplied licensed annotation font")
    def test_supplied_font_is_bound_and_other_pixels_unchanged(self):
        font = Path(os.environ["PARLEY_QA_ANNOTATION_FONT"]).resolve()
        result = self.invoke(["--font", str(font)])
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt["font"], str(font))
        self.assertEqual(receipt["font_sha256"], hashlib.sha256(font.read_bytes()).hexdigest())
        self.assertEqual(receipt["outside_overlay_pixels_changed"], 0)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.source_sha)
        output_sha = hashlib.sha256(self.output.read_bytes()).hexdigest()
        again = self.invoke(["--font", str(font)])
        self.assertNotEqual(again.returncode, 0)
        self.assertEqual(hashlib.sha256(self.output.read_bytes()).hexdigest(), output_sha)


if __name__ == "__main__":
    unittest.main()
