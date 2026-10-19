"""Bounded isolated parameter campaigns using native CAD build+validation."""
import copy,hashlib,itertools,json,math,os,shutil,subprocess,sys,tempfile,uuid
from pathlib import Path
import yaml
from source_fingerprint import project_fingerprint

EXCLUDED={'build','dist','reports','renders','exports','artifacts','.git','__pycache__','.pytest_cache','.superpowers'}


def _relative(value):
    p=Path(value)
    if p.is_absolute() or '..' in p.parts:raise ValueError('variant project paths must be project-relative')
    return p


def _assign(params,key,value):
    if not isinstance(key,str) or not key or any(not k or not k.replace('_','').replace('-','').isalnum() for k in key.split('.')):raise ValueError('invalid parameter path')
    parts=key.split('.');node=params
    for part in parts[:-1]:
        if not isinstance(node,dict) or part not in node:raise ValueError('unknown parameter path: '+key)
        node=node[part]
    if not isinstance(node,dict) or parts[-1] not in node:raise ValueError('unknown parameter path: '+key)
    json.dumps(value,allow_nan=False);node[parts[-1]]=copy.deepcopy(value)


def run_campaign(root,config):
    root=Path(root).resolve();cfg=yaml.safe_load((root/'.cad3d/project.yaml').read_text())['project'];parameter_path=Path('.cad3d')/_relative(cfg.get('parameters','params.yaml'))
    _relative(cfg['model']);_relative(cfg.get('output','build/outputs'))
    params=yaml.safe_load((root/parameter_path).read_text());axes=config.get('axes');limit=config.get('max_cases',32);timeout=config.get('timeout_seconds',180)
    if not isinstance(axes,dict) or not axes or isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=64:raise ValueError('variant axes and1..64 case budget required')
    if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not math.isfinite(timeout) or not 1<=timeout<=3600:raise ValueError('timeout must be1..3600seconds')
    count=1
    for key,values in axes.items():
        if not isinstance(values,list) or not values:raise ValueError('nonempty values required')
        count*=len(values)
        if count>limit:raise ValueError('variant campaign exceeds budget')
        for value in values:_assign(copy.deepcopy(params),key,value)
    # Bound all copied inputs, including non-code CAD assets.
    total=0;entries=0
    for directory,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=[n for n in dirs if n not in EXCLUDED]
        for name in dirs+files:
            path=Path(directory)/name
            if path.is_symlink():raise ValueError('variant inputs cannot follow symlinks')
        for name in files:
            entries+=1;total+=(Path(directory)/name).stat().st_size
            if entries>10000 or total>256*1024*1024:raise ValueError('variant input copy budget exceeded')
    initial=project_fingerprint(root);destination=root/'build/variants'/uuid.uuid4().hex;destination.mkdir(parents=True)
    cases=[];script="""import sys
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1]);import cad3d
cad3d.build(None)
code=cad3d.validate(SimpleNamespace(assembly=None))
if code==0:cad3d.write_manifest()
raise SystemExit(code)
"""
    for index,values in enumerate(itertools.product(*axes.values())):
        overrides=dict(zip(axes,values));case=destination/('case-'+str(index+1).zfill(3));case.mkdir()
        with tempfile.TemporaryDirectory(prefix='cad3d-variant-') as folder:
            clone=Path(folder)/'project'
            def ignore(directory,names):
                for name in names:
                    if name not in EXCLUDED and (Path(directory)/name).is_symlink():raise ValueError('variant inputs cannot follow symlinks')
                return [n for n in names if n in EXCLUDED]
            shutil.copytree(root,clone,ignore=ignore)
            variant=copy.deepcopy(params)
            for key,value in overrides.items():_assign(variant,key,value)
            (clone/parameter_path).write_text(yaml.safe_dump(variant,sort_keys=False))
            (case/'parameters.yaml').write_text(yaml.safe_dump(variant,sort_keys=False))
            try:
                r=subprocess.run([sys.executable,'-c',script,str(Path(__file__).resolve().parent)],cwd=clone,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
                (case/'run.log').write_text(r.stdout);out=clone/cfg.get('output','build/outputs')
                if out.exists():shutil.copytree(out,case/'outputs')
                report_path=out/'validation.json';validation=json.loads(report_path.read_text()) if report_path.exists() else None
                state='PASS' if r.returncode==0 and validation and validation.get('status')=='PASS' else 'FAIL'
                if validation and validation.get('assembly_applicability')!='NOT_APPLICABLE' and validation['states'].get('assembly_validity')=='NOT_EVALUATED' and not any(v=='FAIL' for v in validation['states'].values()):state='NOT_EVALUATED'
                cases.append({'id':case.name,'overrides':overrides,'status':state,'native_returncode':r.returncode,'states':validation.get('states') if validation else None,'artifacts':str(case.relative_to(root))})
            except subprocess.TimeoutExpired as exc:
                (case/'run.log').write_text(str(exc));cases.append({'id':case.name,'overrides':overrides,'status':'NOT_EVALUATED','reason':'timeout','artifacts':str(case.relative_to(root))})
    unchanged=project_fingerprint(root)==initial
    statuses=[c['status'] for c in cases];status='FAIL' if not unchanged or 'FAIL' in statuses else 'NOT_EVALUATED' if 'NOT_EVALUATED' in statuses else 'PASS'
    report={'status':status,'method':'isolated_native_build_and_validation','cases':cases,'source_unchanged':unchanged,'input_fingerprint':initial,'output':str(destination.relative_to(root)),'physical_validation':'NOT_EVALUATED','scope':'declared combinations only; no interpolation or automatic publication'}
    (destination/'campaign.json').write_text(json.dumps(report,indent=2)+'\n');return report
