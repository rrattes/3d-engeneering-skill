"""Sampled rigid helical service paths; nominal BREP, never physical thread approval."""
from __future__ import annotations

import math
from build123d import Axis, Pos
from validation import _distance

MAX_INTERVALS = 4096


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + ' must be a finite number')
    return float(value)


def _vector(value, name):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(name + ' must have three coordinates')
    return tuple(_number(x, name) for x in value)


def motion_parameters(motion, samples=12):
    """Validate explicit world coordinates and bound the sampling budget."""
    if not isinstance(motion, dict) or motion.get('type') != 'helical':
        raise ValueError('expected motion.type=helical')
    origin = _vector(motion.get('axis_origin_mm'), 'axis_origin_mm')
    direction = _vector(motion.get('axis_direction'), 'axis_direction')
    magnitude = math.hypot(*direction)
    if not math.isfinite(magnitude) or magnitude == 0:
        raise ValueError('axis_direction must have a finite nonzero length')
    direction = tuple(x / magnitude for x in direction)
    pitch = _number(motion.get('pitch_mm'), 'pitch_mm')
    travel = _number(motion.get('travel_mm'), 'travel_mm')
    starts = motion.get('starts', 1)
    hand = motion.get('handedness')
    if pitch <= 0 or travel == 0 or hand not in ('right', 'left'):
        raise ValueError('positive pitch, nonzero travel and right/left handedness required')
    if isinstance(starts, bool) or not isinstance(starts, int) or starts < 1:
        raise ValueError('starts must be a positive integer')
    if isinstance(samples, bool) or not isinstance(samples, int) or not 1 <= samples <= MAX_INTERVALS:
        raise ValueError('samples must be an integer from 1 to ' + str(MAX_INTERVALS))
    try:
        lead = pitch * starts
        turns = travel / lead
    except OverflowError as exc:
        raise ValueError('helical lead outside numeric range') from exc
    if not math.isfinite(lead) or not math.isfinite(turns) or abs(turns) > MAX_INTERVALS / 4:
        raise ValueError('helical path exceeds sampling budget')
    intervals = max(samples, math.ceil(abs(turns) * 4))
    return {'origin': origin, 'direction': direction, 'lead': lead, 'pitch': pitch,
            'starts': starts, 'handedness': hand, 'travel': travel,
            'angle': (1 if hand == 'right' else -1) * turns * 360,
            'intervals': intervals, 'requested_intervals': samples}


def _pose(shape, parameters, fraction):
    axis = Axis(parameters['origin'], parameters['direction'])
    displacement = [x * parameters['travel'] * fraction for x in parameters['direction']]
    return Pos(*displacement) * shape.rotate(axis, parameters['angle'] * fraction)


def helical_pose(shape, motion, fraction):
    """fraction=0 is installed; fraction=1 is the declared signed terminal pose."""
    fraction = _number(fraction, 'fraction')
    if not 0 <= fraction <= 1:
        raise ValueError('fraction must be in [0,1]')
    return _pose(shape, motion_parameters(motion), fraction)


def _bounds(shape):
    # Nonoptimal boxes conservatively enclose the BREP; exact distance is not claimed.
    box = shape.bounding_box(optimal=False)
    return tuple((getattr(box.min, c), getattr(box.max, c)) for c in 'XYZ')


def _gap(first, second):
    return math.hypot(*(max(a[0] - b[1], b[0] - a[1], 0) for a, b in zip(first, second)))


def _usable(shape):
    return shape.is_valid and bool(shape.solids()) and all(math.isfinite(s.volume) and s.volume > 0 for s in shape.solids())


def _solid_pair(first, second, gap, permitted, clearance, pair_id):
    from brep_pairs import solid_pair
    return solid_pair(first,second,gap,permitted,clearance,pair_id,distance_fn=_distance)


def _pair(first, second, gap, permitted, clearance, pair_id):
    if gap > max(clearance, 1e-5):
        return {'pair': pair_id, 'status': 'PASS', 'clearance_lower_bound_mm': gap,
                'method': 'conservative_AABB_separation', 'exact_distance': 'NOT_EVALUATED'}
    # Located/imported Compound booleans can lose parent placement. Extract the
    # world-located atomic solids before either common-volume or distance checks.
    results = [_solid_pair(a, b, _gap(_bounds(a), _bounds(b)), permitted, clearance, pair_id)
               for a in first.solids() for b in second.solids()]
    statuses = [r['status'] for r in results]
    status = 'FAIL' if 'FAIL' in statuses else 'NOT_EVALUATED' if 'NOT_EVALUATED' in statuses or not results else 'PASS'
    return {'pair': pair_id, 'status': status, 'method': 'OCP_atomic_solid_pairs',
            'solid_pair_count': len(results),
            'intersection_volume_mm3': sum(r.get('intersection_volume_mm3', 0) for r in results),
            'findings': [r for r in results if r['status'] != 'PASS']}


def helical_path_check(placed, step):
    """Check each original moving instance against all retained instances.

    Moving groups preserve their relative transforms. Their internal fit is the
    responsibility of the static assembly check. Contact allowances are directed
    original moving::retained IDs, never a group-wide contact waiver.
    """
    parameters = motion_parameters(step.get('motion'), step.get('samples', 12))
    moving = step.get('moving_ids')
    if (not isinstance(moving, list) or not moving or any(not isinstance(x, str) for x in moving)
            or len(set(moving)) != len(moving) or set(moving) - set(placed)):
        raise ValueError('moving_ids must identify distinct existing instances')
    removed = step.get('removed_ids', [])
    if (not isinstance(removed, list) or any(not isinstance(x, str) for x in removed)
            or len(set(removed)) != len(removed) or set(removed) - set(placed) or set(removed) & set(moving)):
        raise ValueError('removed_ids must identify distinct nonmoving instances')
    retained = [x for x in placed if x not in moving and x not in removed]
    contacts = step.get('allowed_contact_pairs', [])
    if not isinstance(contacts, list):
        raise ValueError('allowed_contact_pairs must be a list')
    for pair in contacts:
        if not isinstance(pair, str) or pair.count('::') != 1:
            raise ValueError('contact must be moving::retained')
        first, second = pair.split('::')
        if first not in moving or second not in retained:
            raise ValueError('contact must identify original moving and retained instances')
    contacts = set(contacts)
    clearance = _number(step.get('clearance_mm', 0), 'clearance_mm')
    if clearance < 0:
        raise ValueError('clearance_mm must be nonnegative')
    base = {'id': step.get('id'), 'method': 'sampled_helical_OCP_BREP',
            'coverage': 'sampled_not_continuous', 'moving_ids': moving, 'retained_ids': retained,
            'axis_origin_mm': list(parameters['origin']), 'axis_direction_unit': list(parameters['direction']),
            'pitch_mm': parameters['pitch'], 'starts': parameters['starts'], 'lead_mm': parameters['lead'],
            'handedness': parameters['handedness'], 'travel_mm': parameters['travel'],
            'rotation_deg': parameters['angle'], 'intervals_requested': parameters['requested_intervals'],
            'pose_count': parameters['intervals'] + 1,
            'sample_spacing_mm': abs(parameters['travel']) / parameters['intervals'],
            'sample_spacing_deg': abs(parameters['angle']) / parameters['intervals'],
            'min_clearance_required_mm': clearance, 'allowed_contact_pairs': sorted(contacts),
            'physical_validation': 'NOT_EVALUATED',
            'scope': 'sampled nominal rigid BREP path; no continuous clearance, thread fit, force, torque or strength proof'}
    poses, findings = [], []
    try:
        if not all(_usable(placed[x]) for x in moving + retained):
            return {**base, 'status': 'NOT_EVALUATED', 'reason': 'invalid_or_zero_volume_input', 'removal_proven': False}
        obstacles = {x: _bounds(placed[x]) for x in retained}
        final_clear = True
        for index in range(parameters['intervals'] + 1):
            fraction = index / parameters['intervals']
            statuses = []
            for ident in moving:
                at = _pose(placed[ident], parameters, fraction)
                if not _usable(at):
                    raise ValueError('transformed BREP invalid')
                bounds = _bounds(at)
                for other in retained:
                    gap = _gap(bounds, obstacles[other])
                    pair_id = ident + '::' + other
                    result = _pair(at, placed[other], gap, pair_id in contacts, clearance, pair_id)
                    statuses.append(result['status'])
                    if result['status'] != 'PASS':
                        findings.append({'sample': index, 'translation_mm': parameters['travel'] * fraction,
                                         'rotation_deg': parameters['angle'] * fraction, **result})
                    if index == parameters['intervals'] and gap <= 1e-5:
                        final_clear = False
            status = 'FAIL' if 'FAIL' in statuses else 'NOT_EVALUATED' if 'NOT_EVALUATED' in statuses else 'PASS'
            poses.append({'sample': index, 'translation_mm': parameters['travel'] * fraction,
                          'rotation_deg': parameters['angle'] * fraction, 'status': status})
        statuses = [x['status'] for x in poses]
        status = 'FAIL' if 'FAIL' in statuses else 'NOT_EVALUATED' if 'NOT_EVALUATED' in statuses else 'PASS'
        return {**base, 'status': status, 'poses': poses, 'blockages': findings,
                'removal_proven': status == 'PASS' and final_clear,
                'removal_proof_scope': 'terminal conservative bounds separated from every retained instance; sufficient but not necessary'}
    except Exception as exc:
        return {**base, 'status': 'FAIL' if any(r['status'] == 'FAIL' for r in findings) else 'NOT_EVALUATED',
                'reason': 'brep_analysis_error', 'detail': str(exc), 'poses': poses,
                'blockages': findings, 'removal_proven': False}
