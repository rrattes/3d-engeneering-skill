"""Bounded, cumulative world-axis rigid motions; sampled geometry, not mechanics."""
import math
from build123d import Axis,Pos
from component_catalog import vector3
from brep_pairs import bounds,bounds_gap,check_pair
from helical_motion import motion_parameters,helical_pose

MAX_INTERVALS=4096

def _number(x):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):raise ValueError('finite motion number required')
    return float(x)


def segments(motion):
    if not isinstance(motion,dict):raise ValueError('motion must be mapping')
    specs=motion.get('segments') if motion.get('type')=='composite' else [motion]
    if not isinstance(specs,list) or not 1<=len(specs)<=32:raise ValueError('1..32 motion segments required')
    result=[];budget=0
    for spec in specs:
        kind=spec.get('type');samples=spec.get('samples',12)
        if isinstance(samples,bool) or not isinstance(samples,int) or not 1<=samples<=MAX_INTERVALS:raise ValueError('invalid motion samples')
        item=dict(spec)
        if kind=='translation':
            v=vector3(spec.get('vector_mm'),'translation vector')
            if math.hypot(*v)==0:raise ValueError('nonzero translation required')
            item['vector_mm']=v
        elif kind=='rotation':
            item['axis_origin_mm']=vector3(spec.get('axis_origin_mm'),'rotation origin')
            d=vector3(spec.get('axis_direction'),'rotation direction');length=math.hypot(*d)
            if not math.isfinite(length) or length==0:raise ValueError('nonzero rotation axis required')
            item['axis_direction']=[x/length for x in d];angle=_number(spec.get('angle_deg'))
            if angle==0 or abs(angle)>MAX_INTERVALS*45:raise ValueError('rotation outside sampling budget')
            item['angle_deg']=angle;samples=max(samples,math.ceil(abs(angle)/45))
        elif kind=='helical':samples=motion_parameters(spec,samples)['intervals']
        else:raise ValueError('unsupported segment type')
        budget+=samples
        if budget>MAX_INTERVALS:raise ValueError('compound path exceeds sampling budget')
        item['samples']=samples;result.append(item)
    return result


def _pose(shape,segment,fraction):
    kind=segment['type']
    if kind=='translation':return Pos(*(x*fraction for x in segment['vector_mm']))*shape
    if kind=='rotation':return shape.rotate(Axis(segment['axis_origin_mm'],segment['axis_direction']),segment['angle_deg']*fraction)
    return helical_pose(shape,segment,fraction)


def path_check(placed,step):
    specs=segments(step.get('motion'));moving=step.get('moving_ids');removed=step.get('removed_ids',[])
    if not isinstance(moving,list) or not moving or any(not isinstance(n,str) for n in moving) or len(set(moving))!=len(moving) or set(moving)-set(placed):raise ValueError('distinct existing moving IDs required')
    if not isinstance(removed,list) or len(set(removed))!=len(removed) or set(removed)-set(placed) or set(removed)&set(moving):raise ValueError('invalid removed IDs')
    retained=[n for n in placed if n not in moving+removed];contacts=step.get('allowed_contact_pairs',[])
    if not isinstance(contacts,list):raise ValueError('contact list required')
    for pair in contacts:
        if not isinstance(pair,str) or pair.count('::')!=1:raise ValueError('invalid contact pair')
        a,b=pair.split('::')
        if a not in moving or b not in retained:raise ValueError('contact must name original moving::retained IDs')
    clearance=_number(step.get('clearance_mm',0))
    if clearance<0:raise ValueError('negative clearance')
    base={'id':step.get('id'),'method':'sampled_compound_OCP_BREP','coverage':'sampled_not_continuous','moving_ids':moving,'retained_ids':retained,'segments':specs,'physical_validation':'NOT_EVALUATED','scope':'rigid world-axis paths; no deformation, force, ergonomic or continuous-motion proof'}
    findings=[];poses=[];current={n:placed[n] for n in moving}
    try:
        if any(not placed[n].is_valid or not placed[n].solids() or any(not math.isfinite(s.volume) or s.volume<=0 for s in placed[n].solids()) for n in moving+retained):raise ValueError('invalid solid input')
        for index,segment in enumerate(specs):
            start=current
            for sample in range(segment['samples']+1):
                if index and sample==0:continue
                fraction=sample/segment['samples'];current={n:_pose(shape,segment,fraction) for n,shape in start.items()};statuses=[]
                for ident,shape in current.items():
                    for other in retained:
                        pair=ident+'::'+other;r=check_pair(shape,placed[other],min_clearance=clearance,intentional_contact=pair in contacts,pair_id=pair)
                        statuses.append(r['status'])
                        if r['status']!='PASS':findings.append({'segment':index,'sample':sample,**r})
                status='FAIL' if 'FAIL' in statuses else 'NOT_EVALUATED' if 'NOT_EVALUATED' in statuses else 'PASS'
                poses.append({'segment':index,'sample':sample,'fraction':fraction,'status':status})
        statuses=[p['status'] for p in poses];status='FAIL' if 'FAIL' in statuses else 'NOT_EVALUATED' if 'NOT_EVALUATED' in statuses else 'PASS'
        clear=all(bounds_gap(bounds(shape),bounds(placed[n]))>1e-5 for shape in current.values() for n in retained)
        return {**base,'status':status,'poses':poses,'pose_count':len(poses),'blockages':findings,'removal_proven':status=='PASS' and clear,'terminal_centers_mm':{n:list(s.center()) for n,s in current.items()},'removal_proof_scope':'terminal conservative bounds separated from every retained shape'}
    except Exception as exc:return {**base,'status':'FAIL' if any(r['status']=='FAIL' for r in findings) else 'NOT_EVALUATED','reason':str(exc),'poses':poses,'blockages':findings,'removal_proven':False}
