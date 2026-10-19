#!/usr/bin/env python3
"""Independent hand values and negative controls for preliminary beam screening."""
import copy
import importlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cli'))


class StructuralScreening(unittest.TestCase):
    def record(self):
        return dict(id='beam', model='rectangular_cantilever_end_load', units='N-mm-MPa',
                    length_mm=100, width_mm=20, thickness_mm=10, load_n=10,
                    elastic_modulus_mpa=2000, allowable_stress_mpa=12,
                    max_deflection_mm=2, safety_factor=2,
                    provenance={'elastic_modulus_mpa': {'basis': 'measured', 'source': 'test coupon E'},
                                'allowable_stress_mpa': {'basis': 'supplier', 'source': 'test material allowable'}},
                    assumptions={key: True for key in ('fixed_support', 'transverse_tip_load', 'prismatic_solid_section', 'linear_elastic_homogeneous')})

    def screen(self, record=None):
        try:
            module = importlib.import_module('structural_screening')
        except ModuleNotFoundError:
            self.fail('preliminary structural screening module missing')
        return module.cantilever_screen(self.record() if record is None else record)

    def test_hand_calculated_results_and_safety_factor(self):
        r = self.screen()
        self.assertEqual(r['status'], 'PASS')
        self.assertAlmostEqual(r['second_moment_mm4'], 5000/3)
        self.assertAlmostEqual(r['max_bending_stress_mpa'], 3)
        self.assertAlmostEqual(r['tip_deflection_mm'], 1)
        self.assertAlmostEqual(r['stress_limit_mpa'], 6)
        self.assertAlmostEqual(r['achieved_stress_safety_factor'], 4)
        self.assertEqual(r['physical_load_validation'], 'NOT_EVALUATED')

    def test_stress_or_deflection_limit_failure(self):
        for key, value in (('allowable_stress_mpa', 5), ('max_deflection_mm', .5)):
            r = self.record()
            r[key] = value
            self.assertEqual(self.screen(r)['status'], 'FAIL')

    def test_thickness_axis_cubic_stiffness_and_zero_load(self):
        r = self.record()
        r['thickness_mm'] = 5
        self.assertAlmostEqual(self.screen(r)['tip_deflection_mm'], 8)
        self.assertAlmostEqual(self.screen(r)['max_bending_stress_mpa'], 12)
        r['load_n'] = 0
        report = self.screen(r)
        self.assertEqual(report['tip_deflection_mm'], 0)
        self.assertIsNone(report['achieved_stress_safety_factor'])

    def test_assumed_material_is_warning_missing_is_unknown(self):
        r = self.record()
        r['provenance']['elastic_modulus_mpa']['basis'] = 'assumed'
        self.assertEqual(self.screen(r)['status'], 'WARNING')
        for key in ('elastic_modulus_mpa', 'allowable_stress_mpa', 'provenance', 'assumptions'):
            r = self.record()
            r.pop(key)
            self.assertEqual(self.screen(r)['status'], 'NOT_EVALUATED', key)
        r = self.record()
        r['assumptions']['fixed_support'] = False
        self.assertNotEqual(self.screen(r)['status'], 'PASS')

    def test_unsupported_models_units_and_invalid_numbers_rejected(self):
        for key, value in (('model', 'hollow_beam'), ('units', 'SI'), ('length_mm', 0),
                           ('load_n', -1), ('elastic_modulus_mpa', float('inf')),
                           ('width_mm', True), ('safety_factor', .5)):
            r = self.record()
            r[key] = value
            with self.assertRaises(ValueError, msg=key):
                self.screen(r)

    def test_small_deflection_scope_warning(self):
        r = self.record()
        r.update(load_n=100, allowable_stress_mpa=1000, max_deflection_mm=20)
        self.assertEqual(self.screen(r)['status'], 'WARNING')


if __name__ == '__main__':
    unittest.main(verbosity=2)
