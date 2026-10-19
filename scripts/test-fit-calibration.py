#!/usr/bin/env python3
"""Measured calibration: provenance, scope and interval controls."""
import copy
import hashlib
import importlib
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cli'))


class FitCalibration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'measure.csv').write_text('feature,nominal,actual\nhole,10,10.2\nhole,10,10.4\n')
        now = datetime.now(timezone.utc)
        self.identity = dict(printer='test-printer', nozzle_mm=0.4, material='test-material/lot-1',
                             process_sha256='a' * 64, orientation='hole-axis-Z')
        self.payload = dict(identity=copy.deepcopy(self.identity), confirmed_measured=True,
                            measured_at=(now-timedelta(days=1)).isoformat(),
                            valid_until=(now+timedelta(days=1)).isoformat(),
                            evidence={'path': 'measure.csv', 'sha256': hashlib.sha256((self.root/'measure.csv').read_bytes()).hexdigest()},
                            measurements=[{'feature': 'hole', 'nominal_mm': 10, 'actual_mm': v, 'uncertainty_mm': .05} for v in (10.2, 10.4)])

    def derive(self, payload=None, identity=None):
        try:
            module = importlib.import_module('fit_calibration')
        except ModuleNotFoundError:
            self.fail('measured fit calibration module missing')
        return module.derive_fit_calibration(self.payload if payload is None else payload,
                                             self.identity if identity is None else identity, self.root)

    def test_measured_envelope_and_no_preset_mutation(self):
        before = copy.deepcopy(self.payload)
        r = self.derive()
        self.assertEqual(r['status'], 'PASS')
        f = r['features']['hole']
        self.assertAlmostEqual(f['mean_bias_mm'], .3)
        self.assertAlmostEqual(f['bias_interval_mm'][0], .15)
        self.assertAlmostEqual(f['bias_interval_mm'][1], .45)
        self.assertAlmostEqual(f['recommended_nominal_offset_mm'], -.3)
        self.assertAlmostEqual(r['tolerance_dimensions']['hole']['min_mm'], 10.15)
        self.assertAlmostEqual(r['tolerance_dimensions']['hole']['max_mm'], 10.45)
        self.assertEqual(r['physical_fit_validation'], 'NOT_EVALUATED')
        self.assertEqual(self.payload, before)

    def test_each_identity_component_must_match(self):
        for key in self.identity:
            p = copy.deepcopy(self.payload)
            p['identity'][key] = .6 if key == 'nozzle_mm' else 'b' * 64 if key == 'process_sha256' else 'different'
            r = self.derive(p)
            self.assertEqual(r['status'], 'FAIL', key)
            self.assertEqual(r['features'], {})
        p = copy.deepcopy(self.payload)
        p['identity'].pop('printer')
        self.assertEqual(self.derive(p)['status'], 'NOT_EVALUATED')
        self.assertEqual(self.derive(identity={})['status'], 'NOT_EVALUATED')

    def test_missing_confirmation_evidence_and_hash_mismatch(self):
        for key in ('confirmed_measured', 'evidence', 'measured_at', 'valid_until'):
            p = copy.deepcopy(self.payload)
            p.pop(key)
            self.assertEqual(self.derive(p)['status'], 'NOT_EVALUATED', key)
        (self.root/'measure.csv').write_text('changed')
        self.assertEqual(self.derive()['status'], 'FAIL')

    def test_outside_evidence_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            file = Path(outside)/'outside.csv'
            file.write_text('outside')
            (self.root/'link').symlink_to(file)
            for path in (str(file), 'link', '../outside.csv'):
                p = copy.deepcopy(self.payload)
                p['evidence']['path'] = path
                self.assertNotEqual(self.derive(p)['status'], 'PASS')

    def test_dates_and_nonmeasured_values_cannot_calibrate(self):
        for change in ({'valid_until': '2000-01-01T00:00:00+00:00'},
                       {'measured_at': '2999-01-01T00:00:00+00:00'},
                       {'measured_at': '2026-01-01'}, {'confirmed_measured': 'true'},
                       {'measurements': []}):
            p = copy.deepcopy(self.payload)
            p.update(change)
            self.assertNotEqual(self.derive(p)['status'], 'PASS')
        for key, value in (('actual_mm', float('nan')), ('uncertainty_mm', -.1), ('nominal_mm', True)):
            p = copy.deepcopy(self.payload)
            p['measurements'][0][key] = value
            with self.assertRaises(ValueError):
                self.derive(p)

    def test_mixed_nominals_not_extrapolated(self):
        self.payload['measurements'][1]['nominal_mm'] = 12
        with self.assertRaises(ValueError):
            self.derive()


if __name__ == '__main__':
    unittest.main(verbosity=2)
