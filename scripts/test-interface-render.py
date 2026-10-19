#!/usr/bin/env python3
"""Exercise actual interface colors, not merely PNG existence or dimensions."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cli'))
from build123d import Box, Pos
from cad3d_visualization import render_views
from matplotlib.image import imread


class InterfaceRenderTests(unittest.TestCase):
    def test_engineering_set_highlights_current_interface_participants(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = {'engineering': {'mechanical_architecture': {'interfaces': [
                {'id': 'joint', 'components': ['left', 'right']} ]},
                'visualization': {'critical_interfaces': ['joint'], 'hidden_components': ['right']}}}
            manifest, _ = render_views(root, {'left': Pos(-8, 0, 0)*Box(10, 10, 10),
                                              'right': Pos(8, 0, 0)*Box(10, 10, 10)},
                                       contract=contract, view='engineering', section_axis='y')
            target = next(v for v in manifest['views'] if v['view'] == 'interfaces')
            pixels = imread(root / target['path'])[:, :, :3]
            red = (pixels[:, :, 0] > pixels[:, :, 1]*1.4) & (pixels[:, :, 0] > pixels[:, :, 2]*1.4)
            blue = (pixels[:, :, 2] > pixels[:, :, 0]*1.4) & (pixels[:, :, 2] > pixels[:, :, 1]*1.15)
            self.assertGreater(int(red.sum()), 1000, 'interface participant rendered gray')
            self.assertGreater(int(blue.sum()), 1000, 'second participant not highlighted')


if __name__ == '__main__':
    unittest.main()
