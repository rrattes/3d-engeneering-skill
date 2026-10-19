"""Part/instance catalog. Metadata classifies manufacture, never engineering approval."""
from __future__ import annotations
from collections import Counter
import csv,json,math,re
from pathlib import Path

def vector3(value, name):
    if not isinstance(value,(list,tuple)) or len(value)!=3 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in value):
        raise ValueError(f'{name}: expected three finite numbers')
    return list(value)

def resolve_catalog(shapes: dict, assembly_config: dict) -> dict:
    if not isinstance(assembly_config,dict):raise ValueError('assembly must be mapping')
    specs=assembly_config.get('parts',{})
    if not isinstance(specs,dict) or set(specs)-set(shapes):raise ValueError('parts must reference generated shapes')
    components=assembly_config.get('components')
    if components is None:components=[{'id':n,'part':n} for n in shapes]
    if not isinstance(components,list) or not components:raise ValueError('components must be a nonempty list')
    instances={}
    for item in components:
        ident=item.get('id');part=item.get('part')
        if not isinstance(ident,str) or not ident or ident in instances or part not in shapes:raise ValueError('invalid component id or missing part')
        from validation import component_position
        instances[ident]={**item,'position_mm':vector3(component_position(item),'position_mm'),'rotation_deg':vector3(item.get('rotation_deg',[0,0,0]),'rotation_deg')}
    counts=Counter(x['part'] for x in instances.values());parts={};findings=[]
    for name in shapes:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',name):raise ValueError('part name must be safe filename')
        explicit=name in specs;spec=specs.get(name,{})
        if not isinstance(spec,dict):raise ValueError('part metadata must be mapping')
        kind=spec.get('kind','manufactured');process=spec.get('process','fdm' if kind=='manufactured' else 'none')
        if kind not in ('manufactured','commercial','hardware') or process not in ('fdm','machined','none'):raise ValueError('unknown part kind/process')
        if (kind!='manufactured' and process!='none') or (kind=='manufactured' and process=='none'):raise ValueError('incompatible kind/process')
        formats=spec.get('export_formats',['step','stl'] if process=='fdm' else ['step'])
        if not isinstance(formats,list) or not formats or set(formats)-{'step','stl'} or ('stl' in formats and process!='fdm'):raise ValueError('invalid export formats')
        if 'step' not in formats:raise ValueError('STEP required for CAD roundtrip evidence')
        color=spec.get('color','#62778a')
        if not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('color must be #RRGGBB')
        if spec.get('commercial_record') is not None:
            from commercial_components import validate_commercial_record,validate_component_selection
            provenance=validate_commercial_record(spec['commercial_record'])
            if provenance['status']=='FAIL':raise ValueError('invalid commercial record: '+name)
            if provenance['status']!='PASS':findings.append({'id':name,**provenance})
            if spec.get('selection_lock') is not None and validate_component_selection(spec['commercial_record'],spec['selection_lock'])['status']!='PASS':raise ValueError('commercial revision lock mismatch: '+name)
        parts[name]={**spec,'id':name,'kind':kind,'process':process,'material':spec.get('material','NOT_SELECTED'),'export_formats':formats,'print_rotation_deg':vector3(spec.get('print_rotation_deg',[0,0,0]),'print_rotation_deg'),'quantity':counts[name],'classification_basis':'explicit' if explicit else 'legacy_assumption','color':color}
        if not explicit:findings.append({'id':name,'status':'WARNING','reason':'legacy_part_assumed_fdm_not_physical_approval'})
    return {'schema':'cad3d-component-catalog-v1','parts':parts,'instances':instances,'findings':findings}

def placed_shapes(shapes,catalog):
    from validation import transform_shape
    return {n:transform_shape(shapes[x['part']],x['position_mm'],x['rotation_deg']) for n,x in catalog['instances'].items()}

def export_catalog(shapes,catalog,out):
    from build123d import Compound,Pos,Color,export_step,import_step,export_stl
    from validation import transform_shape
    import trimesh
    out=Path(out);out.mkdir(parents=True,exist_ok=True);checks=[];index=[]
    for name,shape in shapes.items():
        if not shape.is_valid or not shape.solids():raise ValueError(f'{name}: invalid/empty solid')
        spec=catalog['parts'][name];shape.label=name;shape.color=Color(spec['color'])
        step=out/f'{name}.step';export_step(shape,str(step));back=import_step(str(step))
        va=sum(x.volume for x in shape.solids());vb=sum(x.volume for x in back.solids())
        ba=shape.bounding_box();bb=back.bounding_box()
        match=(back.is_valid and len(shape.solids())==len(back.solids()) and math.isclose(va,vb,rel_tol=1e-6,abs_tol=1e-5) and all(math.isclose(getattr(a,c),getattr(b,c),rel_tol=1e-6,abs_tol=1e-5) for a,b in ((ba.min,bb.min),(ba.max,bb.max)) for c in 'XYZ'))
        row={**spec,'step':step.name};check={'component':name,'step_reopened':bool(back.is_valid),'step_matches_source':bool(match),'source_solid_count':len(shape.solids()),'step_solid_count':len(back.solids()),'source_solid_volume_mm3':va,'step_solid_volume_mm3':vb,'step_bytes':step.stat().st_size,'stl_watertight':None,'stl_applicable':spec['process']=='fdm','scope':'current roundtrip; not physical approval'}
        if 'stl' in spec['export_formats']:
            if len(shape.solids())!=1 and spec['classification_basis']=='explicit':raise ValueError(f'{name}: printed part must be one solid')
            # Preserve legacy STL coordinates; explicit catalog exports in print orientation.
            oriented=shape
            if spec['classification_basis']=='explicit':
                oriented=transform_shape(shape,(0,0,0),spec['print_rotation_deg']);b=oriented.bounding_box();oriented=Pos(-b.min.X,-b.min.Y,-b.min.Z)*oriented
            stl=out/f'{name}.stl';export_stl(oriented,str(stl),tolerance=.08,angular_tolerance=.1)
            mesh=trimesh.load(stl,force='mesh');connected=len(mesh.split(only_watertight=False))==1
            check.update(stl_watertight=bool(mesh.is_watertight),stl_connected=connected,stl_bytes=stl.stat().st_size)
            row.update(stl=stl.name,print_dimensions_mm=list(map(float,mesh.extents)))
            if not mesh.is_watertight or (not connected and spec['classification_basis']=='explicit'):raise ValueError('STL not closed/connected: '+name)
        if not match:raise ValueError('STEP roundtrip mismatch: '+name)
        checks.append(check);index.append(row)
    placed=placed_shapes(shapes,catalog)
    assembly=Compound(children=[s for s in placed.values()],label='assembly');export_step(assembly,str(out/'assembly.step'))
    back=import_step(str(out/'assembly.step'));before=[s for shape in placed.values() for s in shape.solids()];after=list(back.solids())
    if len(before)!=len(after) or not back.is_valid or not math.isclose(sum(s.volume for s in before),sum(s.volume for s in after),rel_tol=1e-6,abs_tol=1e-4):raise ValueError('assembly roundtrip mismatch')
    def solid_signature(solid):
        bounds=solid.bounding_box()
        return [solid.volume]+[getattr(point,axis) for point in (bounds.min,bounds.max) for axis in 'XYZ']
    original=sorted(solid_signature(s) for s in before)
    reopened=sorted(solid_signature(s) for s in after)
    if any(not math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-4) for first,second in zip(original,reopened) for a,b in zip(first,second)):
        raise ValueError('assembly solid poses/bounds mismatch')
    (out/'assembly-export-validation.json').write_text(json.dumps({'status':'PASS','source_solids':len(before),'reopened_solids':len(after),'solid_poses_bounds_match':True},indent=2)+'\n')
    (out/'part-index.json').write_text(json.dumps(index,indent=2)+'\n')
    with (out/'BOM.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['part','quantity','kind','process','material']);w.writerows([[r[k] for k in ('id','quantity','kind','process','material')] for r in index])
    (out/'export-validation.json').write_text(json.dumps(checks,indent=2)+'\n')
    return checks
