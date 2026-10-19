#!/usr/bin/env python3
"""Regression checks for dependency freshness. Run in the CAD image (PyYAML)."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cli'))
from product_engineering import validate_architecture


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ('.cad3d', 'src', 'build/outputs'):
            (self.root / folder).mkdir(parents=True)
        self.put('.cad3d/project.yaml', 'project:\n  name: regression\n  model: src/model.py\n')
        self.put('.cad3d/params.yaml', '{}\n')
        self.put('.cad3d/engineering.yaml', 'engineering: {}\n')
        self.put('src/model.py', 'from source import build\n')
        self.put('source.py', 'def build(params): return {}\n')
        self.put('parameters.json', '{"wall": 2}\n')
        self.put('build/outputs/validation.json', json.dumps({'states': {'geometric_validity': 'PASS', 'assembly_validity': 'PASS'}}))

    def put(self, path, content):
        (self.root / path).write_text(content)

    def manifest(self, with_closure=True):
        paths = {'source_sha256': 'src/model.py', 'parameters_sha256': '.cad3d/params.yaml',
                 'engineering_sha256': '.cad3d/engineering.yaml'}
        manifest = {key: hashlib.sha256((self.root / path).read_bytes()).hexdigest() for key, path in paths.items()}
        manifest['assembly_sha256'] = None
        manifest['artifacts'] = [{'path': 'validation.json', 'sha256': hashlib.sha256((self.root / 'build/outputs/validation.json').read_bytes()).hexdigest()}]
        if with_closure:
            from source_fingerprint import project_fingerprint
            manifest['project_inputs'] = project_fingerprint(self.root)
        self.put('build/outputs/manifest.json', json.dumps(manifest))

    def freshness(self):
        report = validate_architecture(self.root)
        checks = [c for c in report['checks'] if c['id'] == 'system-verification-phase'][0]['detail']
        return [c for c in checks if c['id'] == 'cad-review-input'][0]['evidence']['source_freshness']

    def test_legacy_manifest_cannot_prove_dependency_freshness(self):
        self.manifest(with_closure=False)
        self.assertEqual(self.freshness()['status'], 'NOT_EVALUATED')

    def test_local_import_and_json_changes_invalidate_review(self):
        for path in ('source.py', 'parameters.json', '.cad3d/project.yaml'):
            with self.subTest(path=path):
                self.manifest()
                self.assertEqual(self.freshness()['status'], 'PASS')
                self.put(path, (self.root / path).read_text() + '\n')
                self.assertEqual(self.freshness()['status'], 'FAIL')

    def test_added_and_deleted_source_invalidate_review(self):
        self.manifest()
        self.put('src/new_helper.py', '# new input\n')
        self.assertEqual(self.freshness()['status'], 'FAIL')
        self.manifest()
        (self.root / 'source.py').unlink()
        self.assertEqual(self.freshness()['status'], 'FAIL')

    def test_generated_outputs_cache_and_secret_files_are_excluded(self):
        self.manifest()
        self.put('build/outputs/new.json', '{}')
        (self.root / 'reports').mkdir()
        self.put('reports/geometry_validation.json', '{}')
        (self.root / '__pycache__').mkdir()
        self.put('__pycache__/generated.py', '# cache')
        self.put('.env', 'TOKEN=do-not-read')
        (self.root / '.git').mkdir()
        self.put('.git/config', 'not source')
        self.assertEqual(self.freshness()['status'], 'PASS')

    def test_unsafe_symlinks_and_explicit_escape_are_rejected(self):
        from source_fingerprint import project_fingerprint
        (self.root / 'outside.py').symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):
            project_fingerprint(self.root)
        (self.root / 'outside.py').unlink()
        self.put('.cad3d/project.yaml', 'project:\n  model: src/model.py\n  source_inputs: [../secret.txt]\n')
        with self.assertRaises(ValueError):
            project_fingerprint(self.root)

    def test_declared_nonstandard_input_is_hashed(self):
        self.put('.cad3d/project.yaml', 'project:\n  model: src/model.py\n  source_inputs: [measurements.csv]\n')
        self.put('measurements.csv', 'diameter,12\n')
        self.manifest()
        self.put('measurements.csv', 'diameter,14\n')
        self.assertEqual(self.freshness()['status'], 'FAIL')

    def test_validation_artifact_change_invalidates_review(self):
        self.manifest()
        self.put('build/outputs/validation.json', '{"states": {}}')
        self.assertEqual(self.freshness()['status'], 'FAIL')

    def test_configured_output_is_excluded(self):
        self.put('.cad3d/project.yaml', 'project:\n  model: src/model.py\n  output: render-artifacts\n')
        (self.root / 'render-artifacts').mkdir()
        self.manifest()
        self.put('render-artifacts/view.json', '{}')
        self.assertEqual(self.freshness()['status'], 'PASS')

    def test_unsafe_model_and_parameter_paths_are_rejected(self):
        from source_fingerprint import project_fingerprint
        for config in ('model: /etc/passwd', 'model: src/model.py\n  parameters: ../../secret.yaml'):
            with self.subTest(config=config):
                self.put('.cad3d/project.yaml', 'project:\n  ' + config + '\n')
                with self.assertRaises(ValueError):
                    project_fingerprint(self.root)

    def test_fingerprint_is_bounded(self):
        from source_fingerprint import MAX_BYTES, project_fingerprint
        with (self.root / 'huge.json').open('wb') as output:
            output.truncate(MAX_BYTES + 1)
        with self.assertRaises(ValueError):
            project_fingerprint(self.root)

    def test_real_manifest_writer_records_local_dependency_inventory(self):
        import cad3d
        self.put('.cad3d/engineering.yaml', 'engineering: {workflow_level: lightweight}\n')
        self.put('src/model.py', 'from build123d import Box\ndef build(params): return {"part": Box(1, 1, 1)}\n')
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            cad3d.write_manifest()
        finally:
            os.chdir(previous)
        manifest = json.loads((self.root / 'build/outputs/manifest.json').read_text())
        recorded = {row['path'] for row in manifest['project_inputs']['files']}
        self.assertTrue({'source.py', 'parameters.json', '.cad3d/project.yaml', 'src/model.py'} <= recorded)
        self.assertEqual(self.freshness()['status'], 'PASS')
        self.put('parameters.json', '{"wall": 3}')
        self.assertEqual(self.freshness()['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
