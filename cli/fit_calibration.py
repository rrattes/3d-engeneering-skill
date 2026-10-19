"""Measured feature envelopes tied to a declared manufacturing identity.

Recommendations are returned only; this module never writes presets or input files.
Observed sample bounds are not population guarantees or physical fit qualification.
"""
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import re

IDENTITY_KEYS = ('printer', 'nozzle_mm', 'material', 'process_sha256', 'orientation')


def _number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('invalid ' + name)
    if value < 0 or (positive and value == 0):
        raise ValueError('out of range ' + name)
    return float(value)


def _identity_valid(identity):
    if not isinstance(identity, dict) or any(key not in identity for key in IDENTITY_KEYS):
        return False
    if any(not isinstance(identity[key], str) or not identity[key].strip()
           for key in IDENTITY_KEYS if key != 'nozzle_mm'):
        return False
    try:
        _number(identity['nozzle_mm'], 'nozzle_mm', positive=True)
    except ValueError:
        return False
    return re.fullmatch(r'[0-9a-f]{64}', identity['process_sha256']) is not None


def _date(value):
    if not isinstance(value, str):
        raise ValueError('date missing')
    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('timezone required')
    return value.astimezone(timezone.utc)


def derive_fit_calibration(payload, expected_identity, project_root='.'):
    """Derive sample envelopes, keyed by feature, without extrapolating to other sizes.

    Each measurement requires feature, nominal_mm, actual_mm and uncertainty_mm.
    Evidence is a project-local file with a declared SHA256. Confirmation is a user
    declaration; the file hash records provenance, it does not certify metrology.
    """
    if not isinstance(payload, dict):
        raise ValueError('calibration payload must be a mapping')
    report = {'status': 'NOT_EVALUATED', 'method': 'observed_measurement_envelope',
              'physical_fit_validation': 'NOT_EVALUATED', 'features': {},
              'tolerance_dimensions': {}, 'presets_modified': False,
              'recommendations_only': True, 'issues': [],
              'scope': 'declared measured samples at each exact nominal and identity; no population bounds, extrapolation, thermal compensation or fit qualification'}

    def stop(reason, status='NOT_EVALUATED'):
        report['issues'].append(reason)
        report['status'] = status
        return report

    if payload.get('confirmed_measured') is not True:
        return stop('real_measurements_not_confirmed')
    identity = payload.get('identity')
    if not _identity_valid(identity) or not _identity_valid(expected_identity):
        return stop('manufacturing_identity_missing_or_invalid')
    # All supplied identity keys participate, so a declared lot or machine revision
    # cannot silently be dropped by the comparison.
    if identity != expected_identity:
        return stop('manufacturing_identity_mismatch', 'FAIL')
    report['identity'] = dict(identity)
    try:
        measured_at, valid_until = _date(payload.get('measured_at')), _date(payload.get('valid_until'))
    except (ValueError, TypeError, OverflowError):
        return stop('validity_dates_missing_or_invalid')
    now = datetime.now(timezone.utc)
    if not measured_at <= now <= valid_until:
        return stop('measurement_future_or_expired', 'FAIL')
    report.update(measured_at=measured_at.isoformat(), valid_until=valid_until.isoformat(), evaluated_at=now.isoformat())
    evidence = payload.get('evidence')
    if not isinstance(evidence, dict) or not isinstance(evidence.get('path'), str) or not evidence['path'].strip():
        return stop('local_evidence_missing')
    digest = evidence.get('sha256')
    if not isinstance(digest, str) or re.fullmatch(r'[0-9a-f]{64}', digest) is None:
        return stop('evidence_sha256_missing_or_invalid')
    root = Path(project_root).resolve()
    path = Path(evidence['path'])
    if path.is_absolute():
        return stop('evidence_must_be_project_relative', 'FAIL')
    path = (root / path).resolve()
    if not path.is_relative_to(root):
        return stop('evidence_outside_project', 'FAIL')
    try:
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return stop('local_evidence_unavailable')
    if actual_hash != digest:
        return stop('evidence_hash_mismatch', 'FAIL')
    report['evidence'] = {'path': str(path.relative_to(root)), 'sha256': actual_hash}
    measurements = payload.get('measurements')
    if not isinstance(measurements, list) or not measurements:
        return stop('measurements_missing')
    grouped = {}
    for measurement in measurements:
        if not isinstance(measurement, dict):
            raise ValueError('measurement must be a mapping')
        feature = measurement.get('feature')
        if not isinstance(feature, str) or not feature.strip():
            raise ValueError('measurement requires feature')
        values = {key: _number(measurement.get(key), key, positive=key != 'uncertainty_mm')
                  for key in ('nominal_mm', 'actual_mm', 'uncertainty_mm')}
        grouped.setdefault(feature, []).append(values)
    features, dimensions = {}, {}
    for feature, samples in grouped.items():
        nominal = samples[0]['nominal_mm']
        if any(sample['nominal_mm'] != nominal for sample in samples):
            raise ValueError('feature nominal sizes differ; use separate feature identifiers')
        try:
            mean_actual = math.fsum(sample['actual_mm'] / len(samples) for sample in samples)
            bias = mean_actual - nominal
            lower = min(sample['actual_mm'] - sample['uncertainty_mm'] for sample in samples)
            upper = max(sample['actual_mm'] + sample['uncertainty_mm'] for sample in samples)
            bias_bounds = [lower - nominal, upper - nominal]
        except OverflowError as exc:
            raise ValueError('measurement result outside numeric range') from exc
        if not all(math.isfinite(v) for v in (mean_actual, bias, lower, upper, *bias_bounds)) or lower <= 0:
            raise ValueError('invalid physical dimension envelope')
        features[feature] = {'sample_count': len(samples), 'tested_nominal_mm': nominal,
                             'mean_actual_mm': mean_actual, 'mean_bias_mm': bias,
                             'bias_interval_mm': bias_bounds, 'observed_actual_interval_mm': [lower, upper],
                             'recommended_nominal_offset_mm': -bias,
                             'recommendation_status': 'REQUIRES_NEW_COUPON_VALIDATION',
                             'samples': samples}
        dimensions[feature] = {'nominal_mm': mean_actual, 'min_mm': lower, 'max_mm': upper,
                               'basis': 'calibrated',
                               'source': f"{report['evidence']['path']} sha256:{actual_hash}; sample envelope at nominal {nominal} mm"}
    report.update(status='PASS', features=features, tolerance_dimensions=dimensions)
    return report
