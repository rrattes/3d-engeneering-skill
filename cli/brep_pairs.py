"""Shared atomic-solid interference checks, including located imported Compounds."""
import math
from OCP.BRepExtrema import BRepExtrema_DistShapeShape


def distance(first, second):
    calc = BRepExtrema_DistShapeShape(first.wrapped, second.wrapped)
    calc.Perform()
    if not calc.IsDone():
        raise RuntimeError('OCP distance unavailable')
    value = float(calc.Value())
    if not math.isfinite(value) or value < 0:
        raise ValueError('invalid OCP distance')
    return value


def common_volume(first, second):
    common = first.intersect(second)
    pieces = [] if common is None else list(common) if isinstance(common, (list, tuple)) else [common]
    if any(not piece.is_valid for piece in pieces):
        raise ValueError('invalid OCP common shape')
    volume = sum(s.volume for p in pieces for s in p.solids())
    if not math.isfinite(volume) or volume < 0:
        raise ValueError('invalid OCP common volume')
    return volume


def solid_pair(first, second, gap, permitted, clearance, pair_id,
               *, contact_tolerance=1e-5, exact_distance=False, distance_fn=None):
    result = {'pair': pair_id, 'intentional_contact': permitted}
    try:
        if gap > max(clearance, contact_tolerance) and not exact_distance:
            return {**result, 'status': 'PASS', 'clearance_lower_bound_mm': gap,
                    'method': 'conservative_AABB_separation', 'exact_distance': 'NOT_EVALUATED'}
        volume = 0.0 if gap > 0 else common_volume(first, second)
        result.update(intersection_volume_mm3=volume, method='OCP_atomic_solid_common')
        if volume > 0:
            return {**result, 'status': 'FAIL', 'surface_distance_mm': 0.0,
                    'classification': 'VOLUMETRIC_COLLISION', 'reason': 'positive_intersection_volume'}
        if permitted and clearance == 0 and not exact_distance:
            return {**result, 'status': 'PASS', 'exact_distance': 'NOT_EVALUATED'}
        d = (distance_fn or distance)(first, second)
        if not math.isfinite(d) or d < 0:
            raise ValueError('invalid OCP distance')
        contact = d <= contact_tolerance
        ok = permitted and d + 1e-7 >= clearance if contact else d + 1e-7 >= clearance
        return {**result, 'status': 'PASS' if ok else 'FAIL', 'surface_distance_mm': d,
                'classification': 'SURFACE_CONTACT' if contact else 'PROXIMITY' if clearance > 0 else 'SEPARATED',
                'reason': ('declared_contact' if ok else 'undeclared_contact_or_clearance_required') if contact else ('clearance_met' if ok else 'clearance_below_minimum')}
    except Exception as exc:
        return {**result, 'status': 'NOT_EVALUATED', 'reason': 'brep_analysis_error', 'detail': str(exc)}


def bounds(shape):
    b = shape.bounding_box(optimal=False)
    return tuple((getattr(b.min, c), getattr(b.max, c)) for c in 'XYZ')


def bounds_gap(a, b):
    return math.hypot(*(max(x[0]-y[1], y[0]-x[1], 0) for x, y in zip(a, b)))


def check_pair(first, second, *, min_clearance=0.0, contact_tolerance=1e-5,
               intentional_contact=False, pair_id=None):
    out = {'pair': pair_id, 'method': 'atomic_solids_OCP_BREP',
           'clearance_scope': 'global minimum across world-located atomic solid pairs; sampled paths remain separate'}
    try:
        for value in (min_clearance, contact_tolerance):
            if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or value < 0:
                raise ValueError('clearance and contact tolerance must be finite nonnegative numbers')
        out.update(min_clearance_required_mm=float(min_clearance), intentional_contact=bool(intentional_contact))
        if first is None or second is None or not first.is_valid or not second.is_valid:
            raise ValueError('invalid input BREP')
        a, b = list(first.solids()), list(second.solids())
        if not a or not b or any(not s.is_valid or not math.isfinite(s.volume) or s.volume <= 0 for s in a+b):
            raise ValueError('invalid or zero-volume solid')
        ab, bb = [bounds(s) for s in a], [bounds(s) for s in b]
        checks = [solid_pair(x,y,bounds_gap(ab[i],bb[j]),intentional_contact,min_clearance,pair_id,
                             contact_tolerance=contact_tolerance,exact_distance=True)
                  for i,x in enumerate(a) for j,y in enumerate(b)]
        statuses = [c['status'] for c in checks]
        status = 'FAIL' if 'FAIL' in statuses else 'NOT_EVALUATED' if 'NOT_EVALUATED' in statuses else 'PASS'
        volume = sum(c.get('intersection_volume_mm3',0) for c in checks)
        distances = [c['surface_distance_mm'] for c in checks if 'surface_distance_mm' in c]
        selected=[c for c in checks if c['status']==status]
        decisive=next((c for c in checks if c.get('classification')=='VOLUMETRIC_COLLISION'),
                      min(selected,key=lambda c:c.get('surface_distance_mm',float('inf'))))
        out.update(status=status, solid_pair_count=len(checks), intersection_volume_mm3=volume,
                   classification=decisive.get('classification'),reason=decisive.get('reason'),
                   broad_phase='OVERLAP' if any(bounds_gap(x,y)==0 for x in ab for y in bb) else 'DISJOINT',
                   findings=[c for c in checks if c['status']!='PASS'])
        # Partial distances cannot establish a global minimum if a pair is unknown.
        if len(distances)==len(checks) or volume>0:out['surface_distance_mm']=0.0 if volume>0 else min(distances)
        else:out['surface_distance_mm']=None
        return out
    except Exception as exc:
        return {**out,'status':'NOT_EVALUATED','reason':'brep_analysis_error','detail':str(exc)}
