"""Publish immutable complete runs; filesystem pointer is canonical, no database."""
from __future__ import annotations
import contextlib,fcntl,hashlib,json,os,time,uuid
from pathlib import Path
from source_fingerprint import project_fingerprint

def _relative_file(root,value):
    path=Path(value)
    if path.is_absolute() or '..' in path.parts or not path.parts:raise ValueError('unsafe artifact path')
    current=root
    for part in path.parts:
        current=current/part
        if current.is_symlink():raise ValueError('symlink artifact not allowed')
    if not current.is_file():raise ValueError('missing artifact: '+value)
    return current

@contextlib.contextmanager
def publication_lock(directory,timeout=10):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.publish.lock').open('a') as f:
        deadline=time.monotonic()+timeout
        while True:
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if time.monotonic()>=deadline:raise TimeoutError('publication lock busy')
                time.sleep(.02)
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)

def verify_cad_evidence(stage, validation):
    """Reopen required fabrication artifacts instead of trusting a supplied inventory."""
    import math
    import trimesh
    from build123d import import_step

    required=('part-index.json','export-validation.json','assembly-export-validation.json',
              'assembly.step','BOM.csv')
    for name in required:
        _relative_file(stage,name)
    index=json.loads((stage/'part-index.json').read_text())
    exports=json.loads((stage/'export-validation.json').read_text())
    if not isinstance(index,list) or not index or not isinstance(exports,list):
        raise ValueError('missing part export evidence')
    by_id={row['component']:row for row in exports}
    ids=[row['id'] for row in index]
    if len(set(ids))!=len(ids) or set(ids)!=set(by_id):
        raise ValueError('export evidence/catalog mismatch')
    expected_solids=0
    for part in index:
        evidence=by_id[part['id']]
        step=import_step(str(_relative_file(stage,part['step'])))
        solids=list(step.solids())
        volume=sum(body.volume for body in solids)
        if (not step.is_valid or not solids or evidence.get('step_matches_source') is not True
            or evidence.get('step_reopened') is not True
            or len(solids)!=evidence.get('step_solid_count')
            or not math.isclose(volume,evidence.get('step_solid_volume_mm3',-1),rel_tol=1e-6,abs_tol=1e-4)):
            raise ValueError('invalid STEP evidence: '+part['id'])
        quantity=part.get('quantity')
        if isinstance(quantity,bool) or not isinstance(quantity,int) or quantity<1:
            raise ValueError('invalid catalog quantity')
        expected_solids+=len(solids)*quantity
        if part.get('process')=='fdm':
            mesh=trimesh.load(str(_relative_file(stage,part['stl'])),force='mesh')
            if not mesh.is_watertight or len(mesh.split(only_watertight=False))!=1:
                raise ValueError('printed STL not closed/connected')
    assembly=import_step(str(stage/'assembly.step'))
    assembly_evidence=json.loads((stage/'assembly-export-validation.json').read_text())
    if (not assembly.is_valid or len(assembly.solids())!=expected_solids
        or assembly_evidence.get('status')!='PASS'
        or assembly_evidence.get('source_solids')!=expected_solids
        or assembly_evidence.get('reopened_solids')!=expected_solids):
        raise ValueError('assembly export mismatch')
    sequence=validation.get('assembly',{}).get('assembly_sequence',{})
    if sequence.get('steps') and (sequence.get('status')!='PASS' or any(
        step.get('status')!='PASS' or any(tool.get('status')!='PASS' for tool in step.get('tool_findings',[]))
        for step in sequence['steps'])):
        raise ValueError('required service sequence not evaluated successfully')
    single=(len(index)==1 and index[0]['quantity']==1 and expected_solids==1)
    if validation.get('states',{}).get('assembly_validity')!='PASS' and not (
        single and validation.get('assembly_applicability')=='NOT_APPLICABLE'):
        raise ValueError('assembly validity required')

def publish_run(project_root: Path, run_directory: Path, expected_inputs: dict,target: str='cad-prototype') -> dict:
    if target!='cad-prototype':raise ValueError('only CAD prototype target is implemented')
    root=Path(project_root).resolve();stage=Path(run_directory).resolve()
    if not stage.is_relative_to(root/'build/runs') or stage==(root/'build/runs'):raise ValueError('run must be in project build/runs')
    if any(p.is_symlink() for p in stage.rglob('*')):raise ValueError('run must not contain symlinks')
    manifest=json.loads((stage/'manifest.json').read_text());validation=json.loads((stage/'validation.json').read_text())
    if manifest.get('project_inputs')!=expected_inputs:raise ValueError('run inputs do not match expected inputs')
    states=validation.get('states',{})
    if validation.get('status')!='PASS' or any(states.get(k)!='PASS' for k in ('geometric_validity',)) or states.get('manufacturing_assessment') not in ('PASS','WARNING','NOT_EVALUATED'):raise ValueError('run not eligible for prototype publication')
    if validation.get('unknown_collision_checks') or validation.get('tool_unknown_checks'):raise ValueError('required geometry check unknown')
    declared=manifest.get('artifacts',[])
    if not declared:raise ValueError('manifest has no artifacts')
    paths=set()
    for record in declared:
        if record['path'] in paths:raise ValueError('duplicate artifact')
        paths.add(record['path']);file=_relative_file(stage,record['path'])
        if hashlib.sha256(file.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('artifact hash mismatch: '+record['path'])
    actual={p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file() and p.name!='manifest.json'}
    if actual!=paths or 'validation.json' not in paths:raise ValueError('manifest does not describe complete run')
    verify_cad_evidence(stage,validation)
    final=root/'build/delivery';destination=final/'releases'/stage.name
    with publication_lock(final):
        if project_fingerprint(root)!=expected_inputs:raise ValueError('inputs changed before publication')
        if destination.exists():raise FileExistsError('run id already published')
        destination.parent.mkdir(parents=True,exist_ok=True)
        for file in stage.rglob('*'):
            if file.is_file():
                with file.open('rb') as stream:os.fsync(stream.fileno())
        os.replace(stage,destination)
        directory_fd=os.open(destination.parent,os.O_DIRECTORY)
        try:os.fsync(directory_fd)
        finally:os.close(directory_fd)
        pointer={'schema':'cad3d-delivery-v1','run_id':stage.name,'directory':destination.relative_to(root).as_posix(),'target':target,'manifest_sha256':hashlib.sha256((destination/'manifest.json').read_bytes()).hexdigest(),'physical_validation':'NOT_EVALUATED'}
        temp=final/('.current-'+uuid.uuid4().hex+'.tmp')
        try:
            with temp.open('x') as f:f.write(json.dumps(pointer,indent=2)+'\n');f.flush();os.fsync(f.fileno())
            os.replace(temp,final/'current.json')
            directory_fd=os.open(final,os.O_DIRECTORY)
            try:os.fsync(directory_fd)
            finally:os.close(directory_fd)
        finally:
            if temp.exists():temp.unlink()
    return pointer
