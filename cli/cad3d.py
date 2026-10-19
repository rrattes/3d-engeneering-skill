#!/usr/bin/env python3
"""Project-local CAD build, validation and reporting CLI."""
import argparse, hashlib, importlib.util, json, math, os, shutil, sys, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validation import (assembly_path_check, fit_dimension_check, interface_face_check,
                        component_position, local_thickness, mesh_components, nominal_wall_check,
                        oriented_dimensions, pair_check, print_fit, support_heuristic,
                        transform_shape)

ROOT = Path('/opt/cad3d')
CAD3D_VERSION = '1.9.0'
EXIT_ERROR, EXIT_VALIDATION = 2, 3
_OUTPUT_OVERRIDE = None

class ProductArchitectureGateError(RuntimeError):
    """Product model execution is blocked until initial architecture is ready."""
    def __init__(self, payload):
        self.payload = payload
        super().__init__(payload['reason'])


def require_product_architecture():
    from product_engineering import validate_architecture
    import yaml
    project_path = Path('.cad3d/project.yaml')
    project_cfg = yaml.safe_load(project_path.read_text()) if project_path.is_file() else {}
    workflow_version = (project_cfg or {}).get('project', {}).get('workflow_schema_version')
    gate_path = Path('.cad3d/engineering.yaml')
    if not gate_path.is_file():
        if workflow_version == 1:
            raise ProductArchitectureGateError({
                'status': 'FAIL', 'reason': 'mandatory_engineering_contract_missing',
                'next_step': 'Run cad3d architecture init --level product and complete the first three engineering phases.'})
        return
    contract = yaml.safe_load(gate_path.read_text()) or {}
    engineering = contract.get('engineering', {})
    if engineering.get('workflow_level', 'product') != 'product':
        return
    if workflow_version == 1 and not Path('.cad3d/workflow.yaml').is_file():
        raise ProductArchitectureGateError({
            'status': 'FAIL', 'reason': 'mandatory_workflow_contract_missing',
            'next_step': 'Run cad3d workflow init; the product workflow cannot advance without its gate contract.'})
    architecture = validate_architecture(Path.cwd())
    if workflow_version == 1:
        from workflow_gates import evaluate_workflow
        gate_report = evaluate_workflow(
            architecture=architecture,
            dispositions=engineering.get('workflow_dispositions', []),
            requested_gate='mechanical_architecture')
        gate = gate_report['requested_gate_status'] or {}
        if gate.get('status') != 'PASS':
            raise ProductArchitectureGateError({
                'status': 'FAIL', 'reason': 'mandatory_workflow_gate_blocked',
                'requested_gate': 'mechanical_architecture', 'gate': gate,
                'gates': gate_report['gates'],
                'next_step': 'Feche requisitos, arquitetura funcional e mecânica; dê disposição explícita a warnings não críticos.'})
        return
    required = ('requirements', 'functional_architecture', 'mechanical_architecture')
    if any(architecture['phases'].get(phase, 'NOT_EVALUATED') in ('FAIL', 'NOT_EVALUATED') for phase in required):
        raise ProductArchitectureGateError({
            'status': 'FAIL', 'reason': 'product_architecture_gate_incomplete',
            'required_phases': list(required), 'phase_states': architecture['phases'],
            'next_step': 'Complete .cad3d/engineering.yaml and .cad3d/assembly.yaml, then run cad3d architecture validate.'})


def project_files():
    import yaml
    cfg_path = Path('.cad3d/project.yaml')
    if not cfg_path.exists(): raise FileNotFoundError('Projeto CAD3D ausente; execute cad3d init')
    require_product_architecture()
    cfg = yaml.safe_load(cfg_path.read_text())['project']
    params_path = Path('.cad3d') / cfg.get('parameters', 'params.yaml')
    params = yaml.safe_load(params_path.read_text())
    spec = importlib.util.spec_from_file_location('cad3d_project_model', cfg['model'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    shapes = module.build(params)
    if not isinstance(shapes, dict) or not shapes: raise ValueError('build(params) deve retornar dict {nome: shape}')
    out = Path(_OUTPUT_OVERRIDE or cfg.get('output','build/outputs')); out.mkdir(parents=True, exist_ok=True)
    return cfg, params, shapes, out

def doctor(_):
    import build123d, trimesh, numpy, scipy, matplotlib, yaml, pyvista, vtk
    from importlib.metadata import version
    from build123d import Box
    shape = Box(2,3,4)
    if not shape.is_valid or abs(shape.volume-24)>1e-7: raise RuntimeError('Smoke geométrico falhou')
    from cad3d_visualization import _tessellate
    import tempfile
    preview=_tessellate(shape)
    with tempfile.NamedTemporaryFile(suffix='.png') as output:
        plotter=pyvista.Plotter(off_screen=True,window_size=(96,96));plotter.add_mesh(preview,color='#356f9f')
        plotter.screenshot(output.name,return_img=False);plotter.close()
        if Path(output.name).stat().st_size < 1000: raise RuntimeError('Smoke render offscreen falhou')
    print(json.dumps({'status':'PASS','cad3d':CAD3D_VERSION,'python':sys.version.split()[0],'build123d':build123d.__version__,'trimesh':trimesh.__version__,'numpy':numpy.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__,'pyvista':pyvista.__version__,'vtk':vtk.vtkVersion.GetVTKVersion(),'headless_visualization':'PASS','ocp':'available','ocp_package':version('cadquery-ocp-novtk'),'smoke_volume_mm3':shape.volume},indent=2))

def project_catalog(shapes, assembly=None):
    import yaml
    from component_catalog import resolve_catalog
    path=Path(assembly) if assembly else Path('.cad3d/assembly.yaml')
    config=(yaml.safe_load(path.read_text()) or {}) if path.is_file() else {}
    return resolve_catalog(shapes,config)


def build(_):
    cfg,params,shapes,out=project_files()
    from component_catalog import export_catalog
    export_catalog(shapes,project_catalog(shapes),out)
    print(f'PASS: {len(shapes)} components built; fabrication selected by catalog')
    return cfg,params,shapes,out


def validate(args):
    import trimesh, yaml
    from manufacturing import evaluate_orientations
    cfg,params,shapes,out=project_files(); results=[]
    candidates=[Path('profiles/printers')/(params.get('printer',{}).get('profile','').replace('-pla','')+'.yaml'),Path('/opt/cad3d/profiles/printers')/(params.get('printer',{}).get('profile','').replace('-pla','')+'.yaml')]
    profile_path=next((p for p in candidates if p.is_file()),None)
    profile=yaml.safe_load(profile_path.read_text()) if profile_path else {'build_volume_mm':[256,256,256],'operational_margin_mm':[5,5,5]}
    profile_evidence={'status':'PASS' if profile_path else 'NOT_EVALUATED','requested':params.get('printer',{}).get('profile'),'path':str(profile_path) if profile_path else None,'basis':'selected_CAD_profile' if profile_path else 'conceptual_budget_only_not_selected_printer'}
    printer_cfg_path=Path('.cad3d/printer.yaml')
    printer_cfg=yaml.safe_load(printer_cfg_path.read_text()) if printer_cfg_path.exists() else {}
    calibration_report={'status':'NOT_EVALUATED','reason':'no_calibration_profile_selected'}
    calibration_path=printer_cfg.get('calibration_profile') if isinstance(printer_cfg,dict) else None
    if calibration_path:
        from calibration import compare_calibration_identity
        cp=Path(calibration_path)
        if cp.exists():
            calibration=yaml.safe_load(cp.read_text()) or {}
            if calibration.get('calibrated') is True:
                identity_check=compare_calibration_identity(calibration.get('identity',{}),printer_cfg,params)
                if identity_check['status']=='PASS':
                    profile={**profile,**{k:v for k,v in calibration.items() if k in ('fit_ranges_mm','fit_clearance_mm','min_wall_mm','shrinkage_percent','interface_tolerance_mm') and v is not None}}
                calibration_report={**identity_check,'path':str(cp),'calibration_id':calibration.get('id'),'profile_identity':calibration.get('identity')}
            else:
                calibration_report={'status':'NOT_EVALUATED','path':str(cp),'reason':'record_not_confirmed_as_physical_calibration'}
        else:
            calibration_report={'status':'NOT_EVALUATED','path':str(cp),'reason':'selected_calibration_file_missing'}
    vol=[a-b for a,b in zip(profile['build_volume_mm'],profile.get('operational_margin_mm',[0,0,0]))]
    min_wall=float(printer_cfg.get('min_wall_mm',profile.get('min_wall_mm',1.2))) if isinstance(printer_cfg,dict) else float(profile.get('min_wall_mm',1.2))
    catalog=project_catalog(shapes,getattr(args,'assembly',None))
    part_reports = {}
    for name,s in shapes.items():
        bb=s.bounding_box(); dims=[bb.size.X,bb.size.Y,bb.size.Z]
        valid=bool(s.is_valid); nonzero=sum(solid.volume for solid in s.solids())>0
        mesh_path=out/f'{name}.stl'; mesh=trimesh.load(mesh_path,force='mesh') if mesh_path.exists() else None
        watertight=bool(mesh.is_watertight) if mesh is not None else False
        rotations=[(0,0,0),(90,0,0),(0,90,0),(0,0,90),(90,90,0),(180,0,0)]
        candidate_dims=oriented_dimensions(s,rotations); fit=print_fit(candidate_dims,vol)
        if catalog['parts'][name]['classification_basis']=='explicit':
            # Fit of the delivered STL, not the best alternative orientation.
            delivered=catalog['parts'][name]['print_rotation_deg']
            fit=print_fit(oriented_dimensions(s,[delivered]),vol)
        thickness=local_thickness(s,min_wall,samples_per_axis=int(printer_cfg.get('thickness_samples_per_axis',3)) if isinstance(printer_cfg,dict) else 3,
                                 face_selectors=params.get('thickness_regions',{}).get(name))
        orientation=evaluate_orientations(s,rotations,vol,overhang_degrees=profile.get('max_overhang_degrees',45),
                      functional_axes=params.get('functional_axes',[]),density_g_cm3=profile.get('density_g_cm3'),
                      infill_fraction=printer_cfg.get('infill_fraction') if isinstance(printer_cfg,dict) else None)
        part_reports[name]={'component':name,'solid_valid':valid,'volume_mm3':sum(solid.volume for solid in s.solids()),'dimensions_mm':[round(x,5) for x in dims],
            'nonzero_volume':nonzero,'print_fit':fit,'orientation_assessment':orientation,'geometric_thickness':thickness,
            'nominal_wall_parameter':'NOT_EVALUATED unless explicitly declared','stl_watertight':watertight,
            'connected_mesh':mesh_components(mesh) if mesh is not None else {'status':'NOT_EVALUATED'},
            'brep_solid_count':len(s.solids()),'support_risk':support_heuristic(s,profile.get('max_overhang_degrees',45))}
        part_reports[name]['manufacturing_applicable']=catalog['parts'][name]['process']=='fdm'
        if not part_reports[name]['manufacturing_applicable']:
            for field in ('print_fit','orientation_assessment','geometric_thickness','connected_mesh'):
                part_reports[name][field]={'status':'NOT_APPLICABLE','reason':'non_FDM_component'}
            part_reports[name]['stl_watertight']=None
        results.append(part_reports[name])
    assembly_path=Path(args.assembly).resolve() if getattr(args,'assembly',None) else Path('.cad3d/assembly.yaml')
    assembly_report={'status':'NOT_EVALUATED','components':[],'pairs':[],'relations':[],'reason':'assembly_not_configured'}
    if assembly_path.exists():
        config=yaml.safe_load(assembly_path.read_text()) or {}
        components=config.get('components',[])
        if not components: raise ValueError('Assembly precisa declarar ao menos um componente')
        material=params.get('material',{}).get('profile','pla')
        mat_candidates=[Path('profiles/materials')/(material+'.yaml'),Path('/opt/cad3d/profiles/materials')/(material+'.yaml')]
        mat=next((yaml.safe_load(p.read_text()) for p in mat_candidates if p.exists()),{})
        placed={}; entries={}
        for item in components:
            ident=item['id']; part=item['part']
            if ident in placed: raise ValueError(f'ID de componente duplicado: {ident}')
            if part not in shapes: raise ValueError(f'{ident}: peça inexistente: {part}')
            placed[ident]=transform_shape(shapes[part],component_position(item),item.get('rotation_deg',(0,0,0)))
            entries[ident]=item
        relations={}
        for interface in config.get('interfaces',[]):
            a,b=interface['a'],interface['b']
            if interface.get('type') not in (None,'sliding','press_fit','press','pin_hole','removable_cover','rail_guide'):
                raise ValueError(f"Interface {interface.get('id', '<sem id>')}: tipo desconhecido {interface.get('type')}")
            if a==b or a not in placed or b not in placed:
                raise ValueError(f"Interface {interface.get('id', '<sem id>')}: endpoints precisam ser IDs distintos existentes")
            pair_key=frozenset((a,b))
            if pair_key in relations: raise ValueError(f"Mais de uma interface para o par {a} / {b}")
            relations[pair_key]=interface
        if calibration_report['status']=='PASS':
            mat={**mat,**{k:v for k,v in profile.items() if k in ('fit_ranges_mm','fit_clearance_mm','min_wall_mm','interface_tolerance_mm')}}
        pairs=[]; fit_checks=[]; face_checks=[]
        ids=list(placed)
        for i,a in enumerate(ids):
            for b in ids[i+1:]:
                interface=relations.get(frozenset((a,b)),{})
                ftype=interface.get('type')
                fit_values=mat.get('fit_clearances_mm',{})
                min_gap=float(interface.get('clearance_mm',fit_values.get(ftype,mat.get('fit_clearance_mm',0)) if ftype else 0))
                pair=pair_check(placed[a],placed[b],min_clearance=min_gap,
                                contact_tolerance=float(config.get('contact_tolerance_mm',0.01)),
                                intentional_contact=bool(interface.get('intentional_contact',False)),pair_id=f'{a}::{b}')
                if interface:
                    pair['interface']={'id':interface.get('id'),'type':ftype,'required_clearance_mm':min_gap}
                    fit_check=fit_dimension_check(interface,mat)
                    if fit_check['status']!='NOT_EVALUATED' or ftype in ('press_fit','press') or 'male_size_mm' in interface or 'female_size_mm' in interface:
                        fit_checks.append(fit_check)
                    if interface.get('face_a') and interface.get('face_b'):
                        face_check=interface_face_check(placed[a],placed[b],interface,mat)
                        face_check['components']=[a,b]
                        face_checks.append(face_check)
                pairs.append(pair)
        min_wall=float(config.get('min_wall_mm',min_wall)); wall_results=[]; component_instances=[]
        for item in components:
            ident=item['id']; entry={**part_reports[item['part']],'component_id':ident,'position_mm':component_position(item),'rotation_deg':item.get('rotation_deg',[0,0,0])}
            component_instances.append(entry)
            for wall in item.get('wall_checks',[]):
                result=nominal_wall_check(wall,min_wall); result['component_id']=ident; wall_results.append(result)
        from service_states import evaluate_steps
        path_results=evaluate_steps(placed,config.get('assembly_steps',[]))
        from service_states import check_fastener_stack
        stack_results=[check_fastener_stack(r) for r in config.get('fastener_stacks',[])]
        from tolerance_stack import evaluate_stacks
        tolerance_results=evaluate_stacks(config.get('tolerance_stacks',[]),config.get('tolerance_dimensions',{}))
        from capability_commands import assembly_capabilities
        capability_report,capability_statuses=assembly_capabilities(placed,config,printer_cfg,params)
        allstatus=capability_statuses+[r['status'] for r in tolerance_results]+[r['status'] for r in stack_results]+[p['status'] for p in pairs]+[w['status'] for w in wall_results]+[f['status'] for f in fit_checks]+[f['status'] for f in face_checks]
        as_status='FAIL' if 'FAIL' in allstatus else ('NOT_EVALUATED' if any(x=='NOT_EVALUATED' for x in allstatus) else 'WARNING' if 'WARNING' in allstatus else 'PASS')
        path_status='FAIL' if any(x['status']=='FAIL' for x in path_results) else ('NOT_EVALUATED' if not path_results or any(x['status']=='NOT_EVALUATED' for x in path_results) else 'PASS')
        assembly_report={'id':config.get('id','assembly'),'status':as_status,'components':component_instances,'pairs':pairs,
                         **capability_report,'fastener_stacks':stack_results,'tolerance_stacks':tolerance_results,'fit_checks':fit_checks,'functional_face_checks':face_checks,'wall_checks':wall_results,
                         'assembly_sequence':{'status':path_status,'steps':path_results},'constraints':config.get('constraints',[]),
                         'physical_print_validation':'NOT_EVALUATED'}
    unresolved_assembly=assembly_path.exists() and assembly_report['status']=='NOT_EVALUATED'
    geo_status='PASS' if all(r['solid_valid'] and r['nonzero_volume'] for r in results) else 'FAIL'
    sequence_status=assembly_report.get('assembly_sequence',{}).get('status','NOT_EVALUATED')
    sequence_required=bool(assembly_report.get('assembly_sequence',{}).get('steps'))
    assembly_status='FAIL' if assembly_report['status']=='FAIL' or sequence_status=='FAIL' else assembly_report['status']
    if sequence_required and sequence_status=='NOT_EVALUATED' and assembly_status!='FAIL':
        assembly_status='NOT_EVALUATED'
    unresolved_assembly=assembly_path.exists() and assembly_status=='NOT_EVALUATED'
    single_part=not assembly_path.exists() and len(catalog['instances'])==1 and len(shapes)==1
    assembly_applicability='NOT_APPLICABLE' if single_part else 'APPLICABLE'
    fdm_results=[r for r in results if r['manufacturing_applicable']]
    thickness_statuses=[r['geometric_thickness']['status'] for r in fdm_results]
    status='PASS' if all(r['solid_valid'] and r['nonzero_volume'] and r['print_fit']['status']=='PASS' and r['stl_watertight'] and r['brep_solid_count']==1 and r['geometric_thickness']['status']!='FAIL' for r in fdm_results) and geo_status=='PASS' and assembly_status!='FAIL' and not unresolved_assembly and calibration_report['status']!='FAIL' else 'FAIL'
    manufacturing_status='FAIL' if 'FAIL' in thickness_statuses or calibration_report['status']=='FAIL' else ('NOT_EVALUATED' if 'NOT_EVALUATED' in thickness_statuses or calibration_path and calibration_report['status']=='NOT_EVALUATED' else ('WARNING' if any(r['orientation_assessment']['status']=='WARNING' or r['geometric_thickness']['coverage']=='sampled_not_complete' for r in fdm_results) else 'PASS'))
    if (profile_path is None or any(p['process']=='machined' for p in catalog['parts'].values())) and manufacturing_status!='FAIL':
        manufacturing_status='NOT_EVALUATED'
    report={'status':status,'printer_profile':profile_evidence,'catalog_findings':catalog['findings'],'states':{'geometric_validity':geo_status,'assembly_validity':assembly_status,
        'manufacturing_assessment':manufacturing_status,'printer_compatibility':'NOT_EVALUATED','slicing':'NOT_EVALUATED','physical_validation':'NOT_EVALUATED'},
        'assembly_applicability':assembly_applicability,'manufacturing_readiness':'NOT_EVALUATED','calibration_profile':calibration_report,'units':'mm','components':results,
        'assembly':assembly_report,'assembly_collision':assembly_report['status'] if assembly_report['status']!='NOT_EVALUATED' else 'NOT_EVALUATED',
        'physical_print_validation':'NOT_EVALUATED','wall_thickness_scope':'Sampled B-rep inward-normal ray distances. Directional and not exhaustive; nominal wall declarations remain separate.'}
    report_path=out/'validation.json'
    if getattr(args,'assembly',None): report_path=out/f'validation-{assembly_path.stem}.json'
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2)); return 0 if status=='PASS' else EXIT_VALIDATION

def render(args):
    from cad3d_visualization import render_views,render_parts_catalog
    import yaml
    cfg,params,shapes,out=project_files()
    args = args or type('RenderArgs', (), {})()
    assembly_path=Path(getattr(args,'assembly',None) or '.cad3d/assembly.yaml')
    ac=yaml.safe_load(assembly_path.read_text()) or {} if assembly_path.exists() else None
    contract_path=Path('.cad3d/engineering.yaml')
    contract=yaml.safe_load(contract_path.read_text()) or {} if contract_path.exists() else {}
    view=getattr(args,'view',None)
    if view is None: view='engineering' if ac and ac.get('components') else 'iso'
    if view=='parts':
        print(json.dumps(render_parts_catalog(Path.cwd(),shapes,project_catalog(shapes),output=out),indent=2));return 0
    if view=='preview': view='iso'
    hidden=[]
    for group in (getattr(args,'hide',[]) or []): hidden.extend(x.strip() for x in group.split(',') if x.strip())
    manifest,manifest_path=render_views(Path.cwd(),shapes,assembly_config=ac,contract=contract,view=view,
        section_axis=getattr(args,'section_axis','x'),section_at=getattr(args,'section_at',None),hide=hidden or None,
        interface_id=getattr(args,'interface',None),explode_mm=getattr(args,'explode_mm',None),output=out)
    if getattr(args,'view',None) is None:
        render_parts_catalog(Path.cwd(),shapes,project_catalog(shapes),output=out)
        render_views(Path.cwd(),shapes,assembly_config=ac,view='presentation',output=out)
    print(json.dumps({"status":manifest["status"],"manifest":str(manifest_path),
        "views":manifest.get("views",[{"view":view,"path":manifest.get("path")}])},indent=2))

def export(_):
    cfg,params,shapes,out=project_files()
    from component_catalog import export_catalog
    checks=export_catalog(shapes,project_catalog(shapes),out)
    print(json.dumps(checks,indent=2))


def report(args):
    cfg,params,shapes,out=project_files(); records=[]
    for n,s in shapes.items():
        b=s.bounding_box(); records.append({'name':n,'volume_mm3':sum(solid.volume for solid in s.solids()),'bbox_mm':[b.size.X,b.size.Y,b.size.Z],'valid':bool(s.is_valid)})
    data={'project':cfg['name'],'units':'mm','components':records,'validation':json.loads((out/'validation.json').read_text()) if (out/'validation.json').exists() else None}
    if getattr(args,'requirements',False):
        data['design_review']=json.loads((out/'design-review.json').read_text()) if (out/'design-review.json').exists() else None
    (out/'report.json').write_text(json.dumps(data,indent=2)+'\n'); print(json.dumps(data,indent=2))

def test(_):
    import pytest
    return pytest.main(['-q','tests'])

def calibration(args):
    from manufacturing import generate_calibration_coupons
    from calibration import write_calibration_record
    import yaml
    if args.action == 'generate':
        source=Path(args.config or '.cad3d/calibration.yaml')
        config=yaml.safe_load(source.read_text()) if source.exists() else {}
        shapes,parameters=generate_calibration_coupons(config or {})
        output=Path(args.output or 'build/calibration-coupons'); output.mkdir(parents=True,exist_ok=True)
        from build123d import export_step, export_stl
        records=[]
        for name,shape in shapes.items():
            step,stl=output/f'{name}.step',output/f'{name}.stl'
            export_step(shape,str(step)); export_stl(shape,str(stl),tolerance=.08,angular_tolerance=.1)
            records.append({'name':name,'volume_mm3':float(shape.volume),'valid':bool(shape.is_valid),
                            'step':str(step),'stl':str(stl)})
        manifest={'status':'PASS','parameters':parameters,'parts':records,
                  'physical_calibration':'NOT_EVALUATED; printed measurements have not been supplied'}
        (output/'calibration-coupons.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(json.dumps(manifest,indent=2)); return 0
    payload=json.loads(Path(args.record).read_text())
    target,record=write_calibration_record(payload)
    print(json.dumps({'status':record['status'],'calibrated':record['calibrated'],'path':str(target),'id':record['id']},indent=2))
    return 0

def product_review(args):
    from product_engineering import write_design_review, validate_architecture
    try:
        cfg,params,shapes,out=project_files()
    except ProductArchitectureGateError as exc:
        report,path=write_design_review(Path.cwd())
        report['geometry_gate']=exc.payload
        path.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
        return EXIT_VALIDATION
    assembly_path=Path('.cad3d/assembly.yaml')
    placed={}
    if assembly_path.is_file():
        import yaml
        ac=yaml.safe_load(assembly_path.read_text()) or {}
        for item in ac.get('components',[]):
            placed[item['id']]=transform_shape(shapes[item['part']],component_position(item),item.get('rotation_deg',(0,0,0)))
    report,path=write_design_review(Path.cwd(),shapes=shapes,placed_shapes=placed or shapes)
    print(json.dumps(report,indent=2))
    return EXIT_VALIDATION if report['status']=='FAIL' else 0

def architecture_validate(args):
    from product_engineering import write_architecture_report
    shapes=None
    assembly_path=Path('.cad3d/assembly.yaml')
    placed={}
    if getattr(args,'geometry',False):
        cfg,params,shapes,out=project_files()
    if shapes is not None and assembly_path.is_file():
        import yaml
        ac=yaml.safe_load(assembly_path.read_text()) or {}
        for item in ac.get('components',[]):
            placed[item['id']]=transform_shape(shapes[item['part']],component_position(item),item.get('rotation_deg',(0,0,0)))
    report,path=write_architecture_report(Path.cwd(),shapes=shapes,placed_shapes=placed or shapes)
    print(json.dumps(report,indent=2))
    return EXIT_VALIDATION if report['status']=='FAIL' else 0

def architecture_init(args):
    import yaml
    target=Path('.cad3d/engineering.yaml')
    if target.exists():
        raise FileExistsError(f'{target} já existe; não será sobrescrito')
    if not Path('.cad3d').is_dir():
        raise FileNotFoundError('Projeto CAD3D ausente; execute cad3d init primeiro')
    data={'engineering':{'schema_version':1,'workflow_level':args.level,'model_gate':args.level=='product',
        'project':{'name':Path.cwd().name,'class':'TODO','purpose':'TODO','units':'mm'},
        'operating_conditions':[],'measurements':[],'external_interfaces':[],'acceptance_criteria':[],
        'risks_and_unknowns':[], 'requirements':[],
        'functional_architecture':{'subsystems':[],'flows':[],'operating_modes':[],'failure_modes':[]},
        'mechanical_architecture':{'components':[],'interfaces':[],'assembly_steps':[],
            'maintenance_access':[],'print_split':[]},
        'workflow_dispositions':[],
        'manufacturing':{'physical_validation':'NOT_EVALUATED'},
        'visualization':{'hidden_components':[],'critical_interfaces':[]}}}
    target.write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True))
    print(f'Contrato criado: {target}; complete arquitetura antes de executar cad3d build.' if args.level=='product' else f'Contrato criado: {target}')

def init(args):
    dest=Path(args.project).resolve()
    if dest.exists(): raise FileExistsError(f'{dest} já existe; não será sobrescrito')
    shutil.copytree('/opt/cad3d/template',dest); print(f'Projeto criado: {dest}')

def write_manifest():
    from source_fingerprint import project_fingerprint
    project_inputs = project_fingerprint(Path.cwd())
    cfg, params, shapes, out = project_files()
    if cfg.get('drawings') is not None and cfg.get('drawings') is not False:
        from technical_drawings import generate_drawings
        catalog=project_catalog(shapes)
        drawing_report=generate_drawings({n:shape for n,shape in shapes.items() if catalog['parts'][n]['kind']=='manufactured'},out/'drawings',cfg['drawings'])
        (out/'drawings'/'drawing-report.json').write_text(json.dumps(drawing_report,indent=2)+'\n')
        if drawing_report['status']!='PASS':raise ValueError('requested drawing references unresolved; previous delivery preserved')
    model_path = Path(cfg['model'])
    parameter_path = Path('.cad3d') / cfg.get('parameters', 'params.yaml')
    artifacts = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path != out/'manifest.json':
            artifacts.append({'path':path.relative_to(out).as_posix(),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    assembly_path=Path('.cad3d/assembly.yaml')
    contract_path=Path('.cad3d/engineering.yaml')
    manifest={'project':cfg['name'],'units':'mm','engine':'build123d 0.11.1 / OCP 7.9','source_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),'parameters_sha256':hashlib.sha256(parameter_path.read_bytes()).hexdigest(),'assembly_sha256':hashlib.sha256(assembly_path.read_bytes()).hexdigest() if assembly_path.exists() else None,'engineering_sha256':hashlib.sha256(contract_path.read_bytes()).hexdigest() if contract_path.exists() else None,'artifacts':artifacts,'project_inputs':project_inputs}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'PASS: manifesto {out}/manifest.json')

def release(args):
    """Prototype publication only; original build/export commands remain work outputs."""
    global _OUTPUT_OVERRIDE
    from source_fingerprint import project_fingerprint
    from artifact_publication import publish_run
    import uuid
    require_product_architecture()
    import yaml
    project_path=Path('.cad3d/project.yaml')
    project_cfg=yaml.safe_load(project_path.read_text()) if project_path.is_file() else {}
    if (project_cfg or {}).get('project', {}).get('workflow_schema_version') == 1:
        from workflow_commands import evaluate_project
        gates=evaluate_project(Path.cwd(),requested_gate='prototype_release')
        requested=gates.get('requested_gate_status') or {}
        if requested.get('status')!='PASS':
            raise ProductArchitectureGateError({
                'status':'FAIL','reason':'prototype_release_gate_blocked',
                'requested_gate':'prototype_release','gate':requested,
                'gates':gates.get('gates'),
                'next_step':'Passe por modelagem, revisão sistêmica e inspeção visual da revisão CAD atual antes de publicar o protótipo.'})
    root=Path.cwd().resolve();inputs=project_fingerprint(root)
    run=root/'build/runs'/uuid.uuid4().hex;run.mkdir(parents=True)
    previous=_OUTPUT_OVERRIDE;_OUTPUT_OVERRIDE=run
    try:
        build(args)
        if validate(args)!=0:raise ValueError('validation failed; diagnostic run retained, delivery unchanged')
        render(None)
        write_manifest()
        pointer=publish_run(root,run,inputs,target=args.target)
        print(json.dumps(pointer,indent=2));return 0
    finally:_OUTPUT_OVERRIDE=previous


def main():
    p=argparse.ArgumentParser(prog='cad3d',description='CAD paramétrico e DfAM em container')
    sub=p.add_subparsers(dest='command',required=True)
    for name,fn in [('doctor',doctor),('build',build),('validate',validate),('render',render),('export',export),('report',report),('test',test)]:
        q=sub.add_parser(name)
        if name in ('validate','render'): q.add_argument('--assembly',help='YAML de montagem; por padrão .cad3d/assembly.yaml')
        if name=='render':
            q.add_argument('--view',choices=('preview','iso','top','front','side','section','exploded','hidden','interfaces','engineering','presentation','parts'))
            q.add_argument('--section-axis',choices=('x','y','z'),default='x')
            q.add_argument('--section-at',type=float)
            q.add_argument('--hide',action='append',help='IDs de componente a ocultar; pode repetir ou separar por vírgula')
            q.add_argument('--interface',help='ID de interface para destacar')
            q.add_argument('--explode-mm',type=float)
        if name=='report': q.add_argument('--requirements',action='store_true',help='incorpora design-review.json')
        q.set_defaults(func=fn)
    q=sub.add_parser('architecture',help='validar contrato e sequência das fases de engenharia')
    aq=q.add_subparsers(dest='architecture_action',required=True)
    ai=aq.add_parser('init');ai.add_argument('--level',choices=('lightweight','product'),default='product');ai.set_defaults(func=architecture_init)
    av=aq.add_parser('validate');av.add_argument('--geometry',action='store_true',help='também amostra percursos declarados na geometria B-rep');av.set_defaults(func=architecture_validate)
    q=sub.add_parser('release',help='publish validated CAD prototype without overwriting prior delivery')
    q.add_argument('--target',choices=['cad-prototype'],default='cad-prototype');q.set_defaults(func=release)
    q=sub.add_parser('review',help='revisão automática de traceabilidade e evidências de engenharia')
    q.set_defaults(func=product_review)
    q=sub.add_parser('workflow',help='gates de engenharia dependentes e evidência atual')
    wq=q.add_subparsers(dest='action',required=True)
    wi=wq.add_parser('init',help='ativar contrato obrigatório de gates no projeto')
    wi.set_defaults(func=lambda args: __import__('workflow_commands').workflow_command(args))
    wc=wq.add_parser('check',help='avaliar dependências e evidências de um gate')
    from workflow_gates import GATE_DEPENDENCIES
    wc.add_argument('--gate',choices=tuple(GATE_DEPENDENCIES),required=True)
    wc.set_defaults(func=lambda args: __import__('workflow_commands').workflow_command(args))
    q=sub.add_parser('init'); q.add_argument('project'); q.set_defaults(func=init)
    q=sub.add_parser('calibration',help='gerar cupons ou registrar medições dimensionais')
    cal=q.add_subparsers(dest='action',required=True)
    gen=cal.add_parser('generate'); gen.add_argument('--config'); gen.add_argument('--output'); gen.set_defaults(func=calibration)
    rec=cal.add_parser('record'); rec.add_argument('record'); rec.set_defaults(func=calibration)
    fit=cal.add_parser('fit');fit.add_argument('record');fit.add_argument('--identity',required=True);fit.add_argument('--output')
    from capability_commands import register,calibration_fit
    fit.set_defaults(func=calibration_fit)
    register(sub,project_files)
    a=p.parse_args()
    try:
        result=a.func(a)
        if isinstance(result,int): return result
        if a.command=='build':
            validation_status=validate(a)
            if validation_status != 0: return validation_status
            render(None); report(None); export(None); write_manifest()
        return 0
    except ProductArchitectureGateError as exc:
        print(json.dumps(exc.payload,indent=2),file=sys.stderr)
        return EXIT_VALIDATION
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        if os.environ.get('CAD3D_DEBUG'): traceback.print_exc()
        return EXIT_ERROR
if __name__=='__main__': sys.exit(main())
