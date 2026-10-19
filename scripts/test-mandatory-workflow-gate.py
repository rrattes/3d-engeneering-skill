#!/usr/bin/env python3
"""End-to-end check that incomplete upstream gates stop before project Python executes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'cli/cad3d.py'


class MandatoryWorkflowGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / '.cad3d').mkdir()
        (self.root / '.cad3d/project.yaml').write_text(
            'project:\n  name: gate-fixture\n  model: model.py\n  parameters: params.yaml\n  workflow_schema_version: 1\n')
        (self.root / '.cad3d/params.yaml').write_text('{}\n')
        (self.root / '.cad3d/workflow.yaml').write_text('workflow:\n  schema_version: 1\n')
        (self.root / '.cad3d/engineering.yaml').write_text(
            'engineering:\n  workflow_level: product\n  requirements: []\n')
        (self.root / 'model.py').write_text(
            'from pathlib import Path\nPath("model-was-imported").write_text("yes")\n'
            'from build123d import Box\ndef build(params): return {"part": Box(1,1,1)}\n')

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(CLI), *args], cwd=self.root,
                              capture_output=True, text=True)

    def test_export_cannot_skip_missing_requirements_architecture_gates(self):
        result = self.run_cli('export')
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertFalse((self.root / 'model-was-imported').exists())
        payload = json.loads(result.stderr)
        self.assertEqual(payload['reason'], 'mandatory_workflow_gate_blocked')
        self.assertEqual(payload['requested_gate'], 'mechanical_architecture')

    def test_deleting_workflow_contract_does_not_allow_model_import(self):
        (self.root / '.cad3d/workflow.yaml').unlink()
        result = self.run_cli('export')
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertFalse((self.root / 'model-was-imported').exists())
        self.assertEqual(json.loads(result.stderr)['reason'], 'mandatory_workflow_contract_missing')

    def test_gate_check_reports_missing_requirement_evidence(self):
        result = self.run_cli('workflow', 'check', '--gate', 'requirements')
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['requested_gate_status']['status'], 'FAIL')
        self.assertEqual(report['requested_gate'], 'requirements')
        self.assertTrue((self.root / 'build/outputs/workflow-gates.json').is_file())


if __name__ == '__main__':
    unittest.main()
