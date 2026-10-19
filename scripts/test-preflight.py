#!/usr/bin/env python3
"""Profile preflight regressions, no CAD, slicer or filesystem output needed."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("orca_engine", Path(__file__).with_name("orca-engine.py"))
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class PreflightTests(unittest.TestCase):
    def test_missing_material_is_explicit_and_does_not_slice_or_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(engine, "OUT", root / "build/slicer"), patch.object(engine, "version") as version:
                result = engine.preflight("elegoo-cc2", "petg-cf", "standard-0.20")
            self.assertEqual(result["status"], "NOT_EVALUATED")
            self.assertIn("unsupported material profile: petg-cf", result["reason"])
            self.assertEqual(result["requested"]["material"], "petg-cf")
            self.assertEqual(result["slicing"], "NOT_PERFORMED")
            self.assertFalse((root / "build").exists())
            version.assert_not_called()

    def test_valid_chain_reports_hashes_and_no_physical_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preset = root / "fixture.json"
            preset.write_text('{"name":"fixture"}')
            chain = [(preset, {"name": "fixture"})]
            with patch.object(engine, "PROFILES", root), patch.object(engine, "chains", return_value=(chain, chain, chain)), patch.object(engine, "version", return_value="fixture-version"):
                result = engine.preflight("elegoo-cc2", "petg", "standard-0.20")
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["scope"], "PRESET_CHAIN_AND_ENGINE_ONLY")
            self.assertEqual(result["physical_validation"], "NOT_EVALUATED")
            self.assertEqual(len(result["profiles"]["filament"][0]["sha256"]), 64)

    def test_cli_missing_preset_returns_four_without_replacing_slice_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "slice-report.json"
            report.write_text("existing evidence")
            with patch.object(engine, "OUT", root), patch("sys.argv", ["cad3d-orca", "preflight", "--printer", "elegoo-cc2", "--material", "petg-cf"]), contextlib.redirect_stdout(io.StringIO()) as output:
                code = engine.main()
            self.assertEqual(code, 4)
            self.assertEqual(json.loads(output.getvalue())["status"], "NOT_EVALUATED")
            self.assertEqual(report.read_text(), "existing evidence")


if __name__ == "__main__":
    unittest.main()
