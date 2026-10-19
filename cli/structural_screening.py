"""Preliminary Euler-Bernoulli screening; no physical load qualification.

Only a solid rectangular prismatic beam, clamped at one end, with a static
transverse force at its free tip is represented. N, mm, MPa (= N/mm²).
"""
import math

REFERENCES = [
    'https://ocw.mit.edu/courses/1-050-solid-mechanics-fall-2004/fd4eff39aec922b8c07660006f40686e_pset04_11.pdf',
    'https://ocw.mit.edu/courses/3-11-mechanics-of-materials-fall-1999/96d839b02e4a6c63cf8031800e89cccd_MIT3_11F99_bstress.pdf',
]
ASSUMPTIONS = ('fixed_support', 'transverse_tip_load', 'prismatic_solid_section', 'linear_elastic_homogeneous')
NUMBERS = ('length_mm', 'width_mm', 'thickness_mm', 'load_n', 'elastic_modulus_mpa',
           'allowable_stress_mpa', 'max_deflection_mm', 'safety_factor')


def cantilever_screen(record):
    """Calculate nominal bending stress and tip deflection for a declared model.

    Material values require provenance[key]={basis,source}; basis is measured,
    supplier or assumed. Limits are supplied by the caller. An analytical PASS
    only means these nominal results meet the supplied limits.
    """
    if not isinstance(record, dict):
        raise ValueError('structural record must be a mapping')
    if record.get('model') != 'rectangular_cantilever_end_load':
        raise ValueError('unsupported structural model')
    if record.get('units') != 'N-mm-MPa':
        raise ValueError('units must be N-mm-MPa')
    report = {'id': record.get('id'), 'status': 'NOT_EVALUATED',
              'method': 'euler_bernoulli_rectangular_cantilever_tip_load', 'units': 'N-mm-MPa',
              'physical_load_validation': 'NOT_EVALUATED', 'preliminary_only': True,
              'issues': [], 'references': list(REFERENCES),
              'scope': 'nominal elastic bending only; no anchorage, shear qualification, buckling, stress concentrations, joints, creep, fatigue, thermal effects, FDM anisotropy/infill or physical capacity qualification'}
    missing = [key for key in NUMBERS if key not in record]
    if missing:
        report['issues'].append({'missing_inputs': missing})
        return report
    values = {}
    for key in NUMBERS:
        value = record[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('invalid ' + key)
        if value < 0 or (key != 'load_n' and value == 0) or (key == 'safety_factor' and value < 1):
            raise ValueError('out of range ' + key)
        values[key] = float(value)
    provenance = record.get('provenance')
    if not isinstance(provenance, dict):
        report['issues'].append('material_provenance_missing')
        return report
    assumed = []
    for key in ('elastic_modulus_mpa', 'allowable_stress_mpa'):
        source = provenance.get(key)
        if not isinstance(source, dict) or not isinstance(source.get('source'), str) or not source['source'].strip():
            report['issues'].append('material_provenance_missing:' + key)
            return report
        if source.get('basis') not in ('measured', 'supplier', 'assumed'):
            report['issues'].append('material_basis_missing_or_invalid:' + key)
            return report
        if source['basis'] == 'assumed':
            assumed.append(key)
    assumptions = record.get('assumptions')
    if not isinstance(assumptions, dict) or any(assumptions.get(key) is not True for key in ASSUMPTIONS):
        report['issues'].append('model_assumptions_not_confirmed')
        return report
    length, width, thickness, load = (values[k] for k in ('length_mm', 'width_mm', 'thickness_mm', 'load_n'))
    try:
        inertia = width * thickness**3 / 12
        moment = load * length
        stress = moment * (thickness / 2) / inertia
        deflection = load * length**3 / (3 * values['elastic_modulus_mpa'] * inertia)
        stress_limit = values['allowable_stress_mpa'] / values['safety_factor']
        achieved_factor = values['allowable_stress_mpa'] / stress if stress else None
        ratio = deflection / length
        slenderness = length / thickness
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError('structural result outside numeric range') from exc
    if not all(math.isfinite(v) for v in (inertia, moment, stress, deflection, stress_limit, ratio, slenderness)) or inertia <= 0 or stress_limit <= 0:
        raise ValueError('structural result outside numeric range')
    if achieved_factor is not None and not math.isfinite(achieved_factor):
        raise ValueError('safety factor outside numeric range')
    stress_pass = stress <= stress_limit
    deflection_pass = deflection <= values['max_deflection_mm']
    if assumed:
        report['issues'].append({'assumed_material_values': assumed})
    # These are explicit screening heuristics, not standard-certified boundaries.
    if ratio > .05:
        report['issues'].append('deflection_exceeds_5_percent_span_linear_model_review_required')
    if slenderness < 10:
        report['issues'].append('span_to_thickness_below_10_shear_deformation_review_required')
    report.update(status='FAIL' if not (stress_pass and deflection_pass) else 'WARNING' if report['issues'] else 'PASS',
                  inputs=values, provenance={key: dict(provenance[key]) for key in ('elastic_modulus_mpa', 'allowable_stress_mpa')},
                  assumptions=dict(assumptions), second_moment_mm4=inertia, fixed_end_moment_n_mm=moment,
                  max_bending_stress_mpa=stress, tip_deflection_mm=deflection,
                  stress_limit_mpa=stress_limit, requested_stress_safety_factor=values['safety_factor'],
                  achieved_stress_safety_factor=achieved_factor,
                  stress_status='PASS' if stress_pass else 'FAIL',
                  deflection_status='PASS' if deflection_pass else 'FAIL',
                  deflection_to_span=ratio, span_to_thickness=slenderness)
    return report
