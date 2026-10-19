"""Declared rigid hand/tool/cable keep-outs; not ergonomic or elastic validation."""
import math
from build123d import Align,Box,Compound,Cylinder,Plane,Pos,Sphere
from component_catalog import vector3
from brep_pairs import check_pair
from motion_paths import path_check


def _positive(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError('positive finite envelope dimension required')
    return float(value)


def _cable(spec):
    raw=spec.get('points_mm')
    if not isinstance(raw,list) or not 2<=len(raw)<=64:raise ValueError('cable needs2..64 waypoints')
    points=[vector3(p,'cable waypoint') for p in raw];radius=_positive(spec.get('diameter_mm'))/2
    bend=_positive(spec.get('bend_radius_mm'));minimum=_positive(spec.get('minimum_bend_radius_mm'))
    lengths=[math.dist(a,b) for a,b in zip(points,points[1:])]
    if min(lengths)<=1e-7:raise ValueError('distinct cable points required')
    corners={};tangent=[0.]*len(points);inflation=0.
    for i in range(1,len(points)-1):
        u=[(points[i][k]-points[i-1][k])/lengths[i-1] for k in range(3)];v=[(points[i+1][k]-points[i][k])/lengths[i] for k in range(3)]
        dot=max(-1,min(1,sum(a*b for a,b in zip(u,v))));angle=math.acos(dot)
        if angle<1e-8:continue
        if math.pi-angle<1e-6:raise ValueError('cable reversal cannot be filleted')
        t=bend*math.tan(angle/2);tangent[i]=t;w=[(v[k]-u[k]*dot)/math.sin(angle) for k in range(3)]
        count=math.ceil(angle/math.radians(10));inflation=max(inflation,bend*(1-math.cos(angle/count/2)))
        start=[points[i][k]-u[k]*t for k in range(3)]
        arc=[[start[k]+bend*(math.sin(angle*j/count)*u[k]+(1-math.cos(angle*j/count))*w[k]) for k in range(3)] for j in range(count+1)]
        corners[i]=arc
    if any(tangent[i]+tangent[i+1]>length+1e-7 for i,length in enumerate(lengths)):raise ValueError('adjacent cable bend tangent lengths exceed segment')
    route=[points[0]]
    for i in range(1,len(points)-1):route.extend(corners.get(i,[points[i]]))
    route.append(points[-1]);inflated=radius+inflation+1e-6
    pieces=[Pos(*p)*Sphere(inflated) for p in route]
    for a,b in zip(route,route[1:]):
        length=math.dist(a,b)
        if length>1e-7:pieces.append(Plane(origin=a,z_dir=tuple(b[k]-a[k] for k in range(3)))*Cylinder(inflated,length,align=(Align.CENTER,Align.CENTER,Align.MIN)))
    return Compound(children=pieces),{'bend_radius_mm':bend,'minimum_bend_radius_mm':minimum,'bend_status':'PASS' if bend>=minimum and bend>=radius else 'FAIL','route_samples':len(route),'envelope_inflation_mm':inflation+1e-6,'scope':'rounded centerline with conservative capsule envelope; no flexural force/strain or connector fit proof'}


def envelope(spec):
    kind=spec.get('kind')
    if kind=='cable':return _cable(spec)
    if kind=='box':
        size=vector3(spec.get('size_mm'),'envelope size');[_positive(x) for x in size]
        return Pos(*vector3(spec.get('center_mm'),'envelope center'))*Box(*size),{}
    if kind=='cylinder':
        origin=vector3(spec.get('origin_mm'),'envelope origin');direction=vector3(spec.get('direction'),'envelope direction')
        if math.hypot(*direction)==0:raise ValueError('nonzero envelope axis required')
        return Plane(origin=origin,z_dir=direction)*Cylinder(_positive(spec.get('radius_mm')),_positive(spec.get('length_mm')),align=(Align.CENTER,Align.CENTER,Align.MIN)),{}
    raise ValueError('unsupported access envelope kind')


def evaluate_access(placed,checks):
    if not isinstance(checks,list):raise ValueError('access_checks must be a list')
    ids=[c.get('id') for c in checks]
    if any(not isinstance(n,str) or not n for n in ids) or len(ids)!=len(set(ids)):raise ValueError('unique access check IDs required')
    results=[]
    for spec in checks:
        target=spec.get('target_id')
        if target is not None and target not in placed:raise ValueError('unknown access target')
        required=spec.get('required',True)
        if not isinstance(required,bool):raise ValueError('required must be boolean')
        shape,details=envelope(spec);obstacles={n:s for n,s in placed.items() if n!=target}
        if '__access_envelope__' in obstacles:raise ValueError('reserved access ID')
        if 'motion' in spec:
            r=path_check({**obstacles,'__access_envelope__':shape},{'id':spec['id'],'moving_ids':['__access_envelope__'],'motion':spec['motion']})
        else:
            pairs=[check_pair(shape,s,pair_id='access::'+n) for n,s in obstacles.items()];statuses=[p['status'] for p in pairs]
            r={'status':'FAIL' if 'FAIL' in statuses else 'NOT_EVALUATED' if 'NOT_EVALUATED' in statuses else 'PASS','pairs':pairs}
        if details.get('bend_status')=='FAIL':r['status']='FAIL'
        results.append({**r,'id':spec['id'],'required':required,'excluded_target':target,'envelope':spec,'details':details,'physical_access_validation':'NOT_EVALUATED','scope':'declared geometric keep-out and sampled approach; named target excluded for engagement, not proof of drive/connector/grip compatibility'})
    return results
