#!/usr/bin/env python3
"""Run in CAD image: product architecture blocks every model-loading command."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'cli/cad3d.py'


class GeometryGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / '.cad3d').mkdir()
        (self.root / '.cad3d/project.yaml').write_text('project:\n  name: gate-test\n  model: model.py\n')
        (self.root / '.cad3d/params.yaml').write_text('{}')
        (self.root / 'model.py').write_text('from pathlib import Path\nPath("model-executed").write_text("yes")\nfrom build123d import Box\ndef build(params): return {"part": Box(1, 1, 1)}\n')
        self.contract()

    def contract(self, level='product', flag='true'):
        (self.root / '.cad3d/engineering.yaml').write_text(f'engineering:\n  workflow_level: {level}\n  model_gate: {flag}\n')

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(CLI), *args], cwd=self.root, capture_output=True, text=True)

    def assert_blocked(self, *args):
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertFalse((self.root / 'model-executed').exists(), 'blocked operation executed project Python')
        self.assertFalse(list(self.root.rglob('*.stl')))
        self.assertFalse(list(self.root.rglob('*.step')))

    def test_export_is_blocked_before_model_import(self):
        self.assert_blocked('export')

    def test_every_geometry_command_obeys_gate_even_with_false_flag(self):
        commands = [('build',), ('export',), ('render',), ('validate',), ('report',), ('review',),
                    ('architecture', 'validate', '--geometry')]
        for flag in ('true', 'false'):
            self.contract(flag=flag)
            for args in commands:
                with self.subTest(flag=flag, args=args):
                    self.assert_blocked(*args)

    def test_blocked_review_retains_contract_findings(self):
        self.assert_blocked('review')
        report = json.loads((self.root / 'build/outputs/design-review.json').read_text())
        self.assertEqual(report['approval'], 'BLOCKED')
        self.assertTrue(report['findings'])
        self.assertEqual(report['geometry_gate']['reason'], 'product_architecture_gate_incomplete')

    def test_contract_diagnostics_do_not_load_model(self):
        result = self.run_cli('architecture', 'validate')
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertFalse((self.root / 'model-executed').exists())
        self.assertTrue((self.root / 'build/outputs/architecture-review.json').is_file())

    def test_lightweight_and_no_contract_can_export_prototypes(self):
        for no_contract in (False, True):
            if no_contract:
                (self.root / '.cad3d/engineering.yaml').unlink()
            else:
                self.contract(level='lightweight')
            result = self.run_cli('export')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((self.root / 'model-executed').is_file())
            self.assertTrue((self.root / 'build/outputs/part.stl').is_file())
            self.assertTrue((self.root / 'build/outputs/part.step').is_file())


if __name__ == '__main__':
    unittest.main()
