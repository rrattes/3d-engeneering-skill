"""Opt-in CLI adapters for engineering capabilities; no printer side effects."""
import functools,hashlib,json,uuid
from pathlib import Path
import yaml


def _load(path):
    value=yaml.safe_load(Path(path).read_text())
    if not isinstance(value,dict):raise ValueError('configuration mapping required')
    return value


def _save(path,report):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['status']=='PASS' else 3


def interfaces(args):
    from interface_library import generate_interface
    from component_catalog import resolve_catalog,export_catalog
    shapes,report=generate_interface(_load(args.config));out=Path(args.output or 'build/interfaces/'+uuid.uuid4().hex)
    if out.exists() and any(out.iterdir()):raise ValueError('interface output must be new or empty')
    out.mkdir(parents=True,exist_ok=True)
    catalog=resolve_catalog(shapes,{'parts':{n:{'kind':'manufactured','process':'fdm','material':args.material or 'NOT_SELECTED'} for n in shapes}})
    export_catalog(shapes,catalog,out);report['output']=str(out)
    return _save(out/'interface-report.json',report)


def drawings(args,loader):
    from technical_drawings import generate_drawings
    from component_catalog import resolve_catalog
    from source_fingerprint import project_fingerprint
    cfg,params,shapes,out=loader();assembly=_load('.cad3d/assembly.yaml') if Path('.cad3d/assembly.yaml').exists() else {}
    catalog=resolve_catalog(shapes,assembly);selected={n:s for n,s in shapes.items() if catalog['parts'][n]['kind']=='manufactured'}
    report=generate_drawings(selected,Path(args.output or out/'drawings'),_load(args.config) if args.config else None)
    report['project_inputs']=project_fingerprint(Path.cwd())
    return _save(Path(args.output or out/'drawings')/'drawing-report.json',report)


def variants(args):
    from variant_campaign import run_campaign
    report=run_campaign(Path.cwd(),_load(args.config));print(json.dumps(report,indent=2));return 0 if report['status']=='PASS' else 3


def structure(args):
    from structural_screening import cantilever_screen
    report=cantilever_screen(_load(args.config));return _save(Path(args.output or 'build/structural/'+uuid.uuid4().hex+'/report.json'),report)


def calibration_fit(args):
    from fit_calibration import derive_fit_calibration
    report=derive_fit_calibration(_load(args.record),_load(args.identity),Path.cwd())
    report['expected_identity_basis']='explicit identity file; applying to a project requires revalidation against current project settings'
    return _save(Path(args.output or 'build/fit-calibration/'+uuid.uuid4().hex+'/report.json'),report)


def assembly_capabilities(placed,config,printer_config,parameters):
    from access_checks import evaluate_access
    from structural_screening import cantilever_screen
    from fit_calibration import derive_fit_calibration
    access=evaluate_access(placed,config.get('access_checks',[]));records=config.get('structural_checks',[])
    if not isinstance(records,list):raise ValueError('structural_checks must be list')
    ids=[r.get('id') for r in records]
    if any(not isinstance(n,str) or not n for n in ids) or len(set(ids))!=len(ids):raise ValueError('unique structural check IDs required')
    structures=[]
    for spec in records:
        required=spec.get('required',True)
        if not isinstance(required,bool):raise ValueError('required must be boolean')
        structures.append({**cantilever_screen(spec),'required':required})
    fit=None
    if 'fit_calibration' in config:
        path=config['fit_calibration']
        if not isinstance(path,str) or Path(path).is_absolute() or '..' in Path(path).parts:raise ValueError('fit calibration must be project-relative file')
        pc=printer_config if isinstance(printer_config,dict) else {}
        process=pc.get('process_settings_file');expected=None
        if isinstance(process,str) and not Path(process).is_absolute() and '..' not in Path(process).parts:
            process_path=Path(process).resolve()
            if process_path.is_relative_to(Path.cwd().resolve()) and process_path.is_file() and process_path.stat().st_size<=10*1024*1024:
                process_hash=hashlib.sha256(process_path.read_bytes()).hexdigest()
                expected={'printer':pc.get('name'),'nozzle_mm':pc.get('nozzle_diameter_mm'),
                          'material':parameters.get('material',{}).get('profile'),
                          'printer_profile':parameters.get('printer',{}).get('profile'),
                          'process_sha256':process_hash,'orientation':pc.get('fit_orientation')}
                if parameters.get('material',{}).get('lot') is not None:expected['material_lot']=parameters['material']['lot']
                if not isinstance(expected['printer_profile'],str) or not expected['printer_profile'].strip():expected=None
                if pc.get('process_settings_sha256') is not None and pc['process_settings_sha256']!=process_hash:
                    fit={'status':'FAIL','issues':['current_process_file_hash_mismatch'],'physical_fit_validation':'NOT_EVALUATED'}
        if fit is None:
            fit=derive_fit_calibration(_load(path),expected,Path.cwd())
            fit['expected_identity_basis']='current printer config, project printer/material profiles, and SHA256 of selected process file'

    statuses=[r['status'] for r in access+structures if r['required']]+([fit['status']] if fit else [])
    return {'access_checks':access,'structural_checks':structures,'measured_fit_calibration':fit},statuses


def register(sub,loader):
    p=sub.add_parser('interfaces',help='generate reusable nominal CAD interface parts');p.add_argument('--config',required=True);p.add_argument('--output');p.add_argument('--material');p.set_defaults(func=interfaces)
    p=sub.add_parser('drawings',help='generate CAD orthographic SVG/PDF sheets');p.add_argument('--config');p.add_argument('--output');p.set_defaults(func=functools.partial(drawings,loader=loader))
    p=sub.add_parser('variants',help='run isolated native validation across parameter combinations');p.add_argument('--config',default='.cad3d/variants.yaml');p.set_defaults(func=variants)
    p=sub.add_parser('structure',help='preliminary declared cantilever screening');p.add_argument('--config',required=True);p.add_argument('--output');p.set_defaults(func=structure)
