#!/usr/bin/env python3
"""Exports must represent the current model, never previously cached part files."""
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cli'))
import cad3d
from build123d import import_step


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        previous = Path.cwd()
        os.chdir(root)
        self.addCleanup(os.chdir, previous)
        self.root = root
        (root / '.cad3d').mkdir()
        (root / '.cad3d/project.yaml').write_text('project:\n  name: export-test\n  model: model.py\n')
        (root / '.cad3d/params.yaml').write_text('width: 2\n')
        (root / 'model.py').write_text('from build123d import Box, Compound, Pos\ndef build(p): return {"part": Compound([Box(p["width"],2,2),Pos(10,0,0)*Box(1,1,1)])}\n')

    def quiet(self, function):
        with redirect_stdout(StringIO()):
            function(None)

    def test_changed_parameters_replace_existing_artifacts(self):
        self.quiet(cad3d.build)
        (self.root / '.cad3d/params.yaml').write_text('width: 5\n')
        self.quiet(cad3d.export)
        shape = import_step(str(self.root / 'build/outputs/part.step'))
        self.assertAlmostEqual(sum(s.volume for s in shape.solids()), 21.0, places=6)
        report = json.loads((self.root / 'build/outputs/export-validation.json').read_text())
        self.assertEqual(report[0]['source_solid_count'], 2)
        self.assertTrue(report[0]['step_matches_source'])
        self.assertAlmostEqual(report[0]['source_solid_volume_mm3'], 21.0, places=6)

    def test_corrupted_cached_step_is_replaced_by_current_export(self):
        self.quiet(cad3d.build)
        (self.root / 'build/outputs/part.step').write_text('stale corrupted file')
        self.quiet(cad3d.export)
        shape = import_step(str(self.root / 'build/outputs/part.step'))
        self.assertEqual(len(shape.solids()), 2)


if __name__ == '__main__':
    unittest.main()
