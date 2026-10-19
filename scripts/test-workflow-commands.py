#!/usr/bin/env python3
"""Project migration and command evidence loading for mandatory workflow gates."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cli'))
from workflow_commands import evaluate_project, initialize_workflow, validate_physical_report


class WorkflowCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / '.cad3d').mkdir()
        (self.root / '.cad3d/project.yaml').write_text('project:\n  name: fixture\n')

    def test_init_activates_schema_and_creates_contract_without_overwriting(self):
        result = initialize_workflow(self.root)
        self.assertEqual(result['status'], 'PASS')
        self.assertTrue((self.root / '.cad3d/workflow.yaml').is_file())
        self.assertIn('workflow_schema_version: 1', (self.root / '.cad3d/project.yaml').read_text())
        with self.assertRaises(FileExistsError):
            initialize_workflow(self.root)

    def test_missing_or_uninitialized_workflow_cannot_pass_requested_gate(self):
        report = evaluate_project(self.root, requested_gate='requirements')
        self.assertEqual(report['requested_gate_status']['status'], 'FAIL')
        initialize_workflow(self.root)
        report = evaluate_project(self.root, requested_gate='requirements')
        self.assertEqual(report['requested_gate_status']['status'], 'NOT_EVALUATED')

    def test_unknown_or_outside_evidence_paths_are_rejected(self):
        from workflow_gates import sha256_file
        with self.assertRaises(ValueError):
            sha256_file(self.root, '../outside.png')
        with self.assertRaises(ValueError):
            sha256_file(self.root, '/etc/passwd')

    def test_physical_pass_requires_hashed_test_evidence(self):
        report = {'status': 'PASS', 'tests': [{'id': 'fit', 'method': 'measured_fit',
                   'result': 'PASS'}], 'evidence': []}
        self.assertEqual(validate_physical_report(self.root, report)['status'], 'NOT_EVALUATED')
        evidence = self.root / 'bench.txt'
        evidence.write_text('measured interface fit: pass\n')
        import hashlib
        report['evidence'] = [{'path': 'bench.txt',
                               'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}]
        self.assertEqual(validate_physical_report(self.root, report)['status'], 'PASS')
        evidence.write_text('changed after review\n')
        self.assertEqual(validate_physical_report(self.root, report)['status'], 'FAIL')

    def test_malformed_test_record_fails_closed_without_crashing(self):
        report = {'status': 'PASS', 'tests': [None], 'evidence': [{'path': 'x', 'sha256': '0'}]}
        result = validate_physical_report(self.root, report)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('<invalid-test-record>', result['invalid_tests'])

    def test_physical_warning_remains_warning_after_evidence_validation(self):
        evidence = self.root / 'bench.txt'
        evidence.write_text('test evidence\n')
        import hashlib
        report = {'status': 'WARNING', 'tests': [{'id': 'fit', 'method': 'measured_fit',
                   'result': 'PASS'}], 'evidence': [{'path': 'bench.txt',
                   'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}]}
        self.assertEqual(validate_physical_report(self.root, report)['status'], 'WARNING')


if __name__ == '__main__':
    unittest.main()
