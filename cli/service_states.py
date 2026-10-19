"""Explicit service states with retained hardware and sampled BREP removal checks."""
from __future__ import annotations
import math
from build123d import Align,Compound,Cylinder,Plane,Vector
from component_catalog import vector3
from validation import assembly_path_check,pair_check

def validate_service_plan(steps):
    for step in steps:
        motion=step.get('motion')
        if 'motion' in step:
            if not isinstance(motion,dict) or motion.get('type') not in ('linear','helical','translation','rotation','composite'):raise ValueError('unknown service motion type')
            if motion['type']=='helical':
                if 'moving_ids' not in step:raise ValueError('helical motion requires explicit moving_ids')
                from helical_motion import motion_parameters
                motion_parameters(motion,step.get('samples',12))
            elif motion['type'] in ('translation','rotation','composite'):
                if 'moving_ids' not in step:raise ValueError('compound motion requires explicit moving_ids')
                from motion_paths import segments
                segments(motion)
    ids=[s.get('id') for s in steps]
    if any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids):raise ValueError('service step IDs must be unique')
    graph={s['id']:s.get('prerequisite_step_ids',[]) for s in steps};done=set();visiting=set()
    def visit(n):
        if n in visiting:raise ValueError('cyclic service prerequisites')
        if n in done:return
        if n not in graph:raise ValueError('missing service prerequisite: '+str(n))
        visiting.add(n)
        for parent in graph[n]:visit(parent)
        visiting.remove(n);done.add(n)
    for n in graph:visit(n)
    return True

def resolve_service_state(instances:dict,step:dict)->dict:
    moving=step.get('moving_ids',[]);removed=step.get('removed_ids',[])
    if not isinstance(moving,list) or not moving or not isinstance(removed,list):raise ValueError('moving/removed IDs must be lists')
    if len(set(moving))!=len(moving) or len(set(removed))!=len(removed) or set(moving)&set(removed) or (set(moving)|set(removed))-set(instances):raise ValueError('invalid moving/removed IDs')
    kept={n:s for n,s in instances.items() if n not in removed and n not in moving}
    # Stable group ID is separate from original instance IDs.
    group='__service_moving__'
    if group in instances:raise ValueError('reserved service ID')
    kept[group]=Compound(children=[instances[n] for n in moving])
    return {'placed':kept,'moving_component':group,'moving_ids':moving,'removed_ids':removed,'retained_ids':[n for n in instances if n not in removed and n not in moving],
            'original_shapes':{n:s for n,s in instances.items() if n not in removed}}

def _tool_shape(tool):
    origin=vector3(tool.get('origin_mm'),'tool origin');direction=vector3(tool.get('direction_mm'),'tool direction')
    radius=tool.get('radius_mm');length=tool.get('length_mm')
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in (radius,length)) or sum(x*x for x in direction)<=0:raise ValueError('invalid tool dimensions')
    return Plane(origin=origin,z_dir=Vector(*direction))*Cylinder(radius,length,align=(Align.CENTER,Align.CENTER,Align.MIN))

def check_service_step(state:dict,step:dict)->dict:
    placed=state['placed'];moving=state['moving_component'];path=dict(step,moving_component=moving)
    contacts=[]
    for pair in step.get('allowed_contact_pairs',[]):
        a,b=pair.split('::')
        if a not in state['moving_ids'] or b not in state['retained_ids']:raise ValueError('service contact must name moving and retained instance')
        contacts.append(moving+'::'+b)
    path['allowed_contact_pairs']=contacts
    kind=step.get('motion',{}).get('type');helical=kind=='helical';modern=kind in ('helical','translation','rotation','composite')
    if helical:
        from helical_motion import helical_path_check
        result=helical_path_check(state['original_shapes'],dict(step,removed_ids=[]))
    elif modern:
        from motion_paths import path_check
        result=path_check(state['original_shapes'],dict(step,removed_ids=[]))
    else:result=assembly_path_check(placed,path)
    tools=[]
    for tool in step.get('tools',[]):
        target=tool.get('target_id')
        if target is not None and target not in state['retained_ids']+state['moving_ids']:raise ValueError('unknown tool target')
        # Tool is evaluated at seated pose, before group translation.
        environment=dict(placed)
        for n in state['moving_ids']:
            # The group is checked unless a targeted moving instance must be excluded.
            if target==n:raise ValueError('tool target must be retained; declare separate fastener operation')
        envelope=_tool_shape(tool)
        for ident,shape in environment.items():
            if ident==target:continue
            r=pair_check(envelope,shape,pair_id='tool:'+str(tool.get('id'))+'::'+ident)
            if r['status']!='PASS':tools.append(r)
    statuses=[result['status']]+[x['status'] for x in tools]
    status='FAIL' if 'FAIL' in statuses else 'NOT_EVALUATED' if 'NOT_EVALUATED' in statuses else 'PASS'
    return {**result,'status':status,'moving_ids':state['moving_ids'],'removed_ids':state['removed_ids'],'retained_ids':state['retained_ids'],'tool_findings':tools,'tool_count':len(step.get('tools',[])),'sample_spacing_mm':result.get('sample_spacing_mm') if modern else float(step.get('travel_mm',0))/int(step.get('samples',12)) if int(step.get('samples',12))>0 else None,'scope':result.get('scope') if modern else 'nominal tool cylinders and sampled linear path; threads, grip force, torque and continuous motion NOT_EVALUATED'}

def evaluate_steps(placed,steps):
    """Legacy insertion steps are preserved. New steps declare explicit removal states."""
    validate_service_plan(steps)
    results=[]
    completed={}
    for step in steps:
        prerequisites=step.get('prerequisite_step_ids',[])
        blocked=[ident for ident in prerequisites if completed.get(ident,{}).get('status')!='PASS']
        if blocked:
            result={'id':step['id'],'status':'NOT_EVALUATED','reason':'prerequisite_not_passed_or_not_yet_evaluated','blocked_by':blocked}
        elif 'moving_ids' in step:
            # Removal is an effect of successful explicit prerequisite operations.
            ancestors=set()
            def collect(ident):
                if ident in ancestors:return
                ancestors.add(ident)
                for parent in completed[ident].get('prerequisite_step_ids',[]):collect(parent)
            for ident in prerequisites:collect(ident)
            removed={name for ident in ancestors
                     if 'removal_proven' not in completed[ident] or completed[ident].get('removal_proven') is True
                     for name in completed[ident].get('moving_ids',[])}
            unproven=set(step.get('removed_ids',[]))-removed
            if unproven:
                result={'id':step['id'],'status':'NOT_EVALUATED','reason':'removal_not_proven_by_prerequisites','unproven_removed_ids':sorted(unproven)}
            else:
                result=check_service_step(resolve_service_state(placed,step),step)
        else:result=assembly_path_check(placed,step)
        result={**result,'id':step['id'],'prerequisite_step_ids':prerequisites}
        completed[step['id']]=result
        results.append(result)
    return results

def check_fastener_stack(record:dict)->dict:
    """Arithmetic on declared dimensions; not thread/torque/strength verification."""
    keys=('length_mm','grip_mm','required_engagement_mm','head_to_seat_gap_mm','seat_tolerance_mm')
    if any(isinstance(record.get(k),bool) or not isinstance(record.get(k),(int,float)) or not math.isfinite(record[k]) for k in keys):raise ValueError('fastener stack requires finite dimensions')
    length,grip,required,gap,tolerance=[record[k] for k in keys]
    if length<=0 or grip<0 or required<=0 or tolerance<0:raise ValueError('invalid fastener stack dimensions')
    engagement=length-grip;issues=[]
    if engagement<required:issues.append('insufficient_engagement')
    if abs(gap)>tolerance:issues.append('head_not_seated')
    depth=record.get('blind_depth_mm')
    if depth is not None:
        if isinstance(depth,bool) or not isinstance(depth,(int,float)) or not math.isfinite(depth) or depth<=0:raise ValueError('invalid blind depth')
        if engagement>depth-record.get('tip_clearance_mm',0):issues.append('bottoming')
    return {'id':record.get('id'),'status':'FAIL' if issues else 'PASS','engagement_mm':engagement,'issues':issues,'method':'declared_nominal_stack_arithmetic','physical_thread_torque_validation':'NOT_EVALUATED'}
