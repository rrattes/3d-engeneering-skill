"""Small explicit-dimension nominal interfaces. Millimetres, installed poses, no fit certification."""
from __future__ import annotations
import math
from brep_pairs import check_pair
from build123d import Align, Box, Cylinder, Face, Helix, Pos, Wire, sweep


def _positive(spec, key, zero=False):
    v = spec.get(key)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or (v < 0 if zero else v <= 0):
        raise ValueError(key + ' must be a finite ' + ('nonnegative' if zero else 'positive') + ' number')
    if v > 10000:
        raise ValueError(key + ' exceeds library 10000 mm budget')
    return float(v)


def _box(x, y, z, dx=0, dy=0, dz=0):
    return Pos(dx, dy, dz) * Box(x, y, z, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _cyl(r, h, z=0):
    return Pos(0, 0, z) * Cylinder(r, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _thread(radius, depth, pitch, length, hand, clearance=0):
    # Triangular custom profile: broad root, sharp crest, deliberately not ISO metric.
    root = radius - depth
    path = Helix(pitch, length + 2 * pitch, root, center=(0, 0, -pitch), lefthand=hand == 'left')
    face = Face(Wire.make_polygon([(root-.05,0,-pitch-.35*pitch-clearance),
                                  (radius+clearance,0,-pitch),
                                  (root-.05,0,-pitch+.35*pitch+clearance)], close=True))
    rib = sweep(face, path=path, is_frenet=True)
    core = _cyl(root+clearance, length)
    trimmed = rib & _box(2*(radius+clearance+1), 2*(radius+clearance+1), length)
    return core + trimmed


def generate_interface(spec):
    """Return ({part_id: build123d.Part}, report); every dimension is caller supplied.

    Types: thread_pair, pin_hinge, sliding_rail. No fastener retention, end stops,
    loads, tolerance distribution or manufacturing process is inferred.
    """
    if not isinstance(spec, dict):
        raise ValueError('interface specification must be a mapping')
    kind = spec.get('type')
    fields = {
        'thread_pair': {'major_diameter_mm','pitch_mm','length_mm','thread_depth_mm','radial_clearance_mm','wall_mm','handedness'},
        'pin_hinge': {'pin_diameter_mm','barrel_outer_diameter_mm','length_mm','leaf_width_mm','leaf_thickness_mm','radial_clearance_mm','axial_clearance_mm'},
        'sliding_rail': {'length_mm','width_mm','height_mm','wall_mm','clearance_mm'},
    }
    if kind not in fields or set(spec) - (fields[kind] | {'type'}):
        raise ValueError('unknown interface type or parameter')
    p = {k:_positive(spec,k,zero='clearance' in k) for k in fields[kind] if k != 'handedness'}
    report = {'type':kind,'units':'mm','parameters':dict(spec),'physical_validation':'NOT_EVALUATED',
              'fit_validation':'NOT_EVALUATED','manufacturing_validation':'NOT_EVALUATED',
              'scope':'nominal CAD solids; caller dimensions, no standard fit or physical qualification'}
    if kind == 'thread_pair':
        radius=p['major_diameter_mm']/2; pitch=p['pitch_mm']; length=p['length_mm']; depth=p['thread_depth_mm']; c=p['radial_clearance_mm']; wall=p['wall_mm']; hand=spec.get('handedness')
        if hand not in ('right','left') or depth >= radius or c >= min(depth*.5,pitch*.15) or length/pitch > 64 or pitch > length:
            raise ValueError('thread needs right/left hand, depth < radius, clearance < min(depth/2,0.15*pitch), 1..64 turns')
        male=_thread(radius,depth,pitch,length,hand)
        cutter=_thread(radius,depth,pitch,length,hand,c)
        female=_cyl(radius+c+wall,length)-cutter
        shapes={'male':male,'female':female}
        report.update(handedness=hand,pitch_mm=pitch,starts=1,lead_mm=pitch,profile='custom triangular 0.70-pitch root width; not ISO',clearance_scope='radial crest/root and axial flank cutter expansion; not uniform normal clearance')
    elif kind == 'pin_hinge':
        r=p['barrel_outer_diameter_mm']/2; pin=p['pin_diameter_mm']/2; c=p['radial_clearance_mm']; gap=p['axial_clearance_mm']; length=p['length_mm']; width=p['leaf_width_mm']; thick=p['leaf_thickness_mm']
        segment=(length-2*gap)/3
        if pin+c >= r or segment <= 0 or thick >= 2*r or width <= r*.3+c:
            raise ValueError('hinge needs positive barrel wall, three positive knuckles, leaf thickness < barrel diameter and adequate leaf width')
        def knuckle(z):return _cyl(r,segment,z)-_cyl(pin+c,segment,z)
        # A leaf bridges both end knuckles outside the centre knuckle radius.
        leaf_a=_box(width,thick,length,r+c+width/2)
        bridge_x=(r*.7+r+c+1)/2; bridge_w=r+c+1-r*.7
        for z in (0,2*(segment+gap)):
            leaf_a=leaf_a+knuckle(z)+_box(bridge_w,thick,segment,bridge_x,dz=z)
        z=segment+gap
        leaf_b=knuckle(z)+_box(width+r*.3,thick,segment,-(r+width+r*.7)/2,dz=z)
        hole=_cyl(pin+c,length)
        shapes={'leaf_a':leaf_a-hole,'leaf_b':leaf_b-hole,'pin':_cyl(pin,length)}
        report.update(pin_retention='NOT_EVALUATED; plain pin without head or clip',rotation_axis={'origin_mm':[0,0,0],'direction':[0,0,1]})
    else:
        length=p['length_mm']; w=p['width_mm']; h=p['height_mm']; wall=p['wall_mm']; c=p['clearance_mm']
        if c >= min(w,h)/4:
            raise ValueError('rail clearance must be less than quarter of width and height')
        rail=_box(w*.5,length,h*.5)+_box(w,length,h*.5,dz=h*.5)
        stock=_box(w+2*(wall+c),length,h+wall+c)
        cavity=_box(w*.5+2*c,length+2,h*.5+c+1,dz=-1)+_box(w+2*c,length+2,h*.5+2*c,dz=h*.5-c)
        shapes={'rail':rail,'carriage':stock-cavity}
        report.update(profile='T rail open along Y; carriage open underneath',end_retention='NOT_EVALUATED; no end stops',translation_axis=[0,1,0])
    if not all(s.is_valid and len(s.solids()) == 1 and math.isfinite(s.volume) and s.volume > 0 for s in shapes.values()):
        raise ValueError('interface generated invalid or disconnected CAD')
    pairs=[check_pair(a,b,pair_id=ka+'::'+kb) for i,(ka,a) in enumerate(shapes.items()) for kb,b in list(shapes.items())[i+1:]]
    nominal='FAIL' if any(x['status']=='FAIL' for x in pairs) else 'NOT_EVALUATED' if any(x['status']=='NOT_EVALUATED' for x in pairs) else 'PASS'
    report.update(nominal_interference={'status':nominal,'pairs':pairs})
    report.update(status=nominal,cad_validity='PASS',parts={k:{'volume_mm3':s.volume,'solid_count':len(s.solids())} for k,s in shapes.items()})
    return shapes,report
