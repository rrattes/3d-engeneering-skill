#!/usr/bin/env python3
"""Host orchestrator; CAD suites execute only inside the selected Docker image."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['source','packaged'],required=True);p.add_argument('--suite',choices=['smoke','targeted','integration','full'],required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--image',default=os.environ.get('CAD3D_IMAGE','cad3d-engineering:1.9.0'));a=p.parse_args()
 if a.output.exists() and any(a.output.iterdir()):p.error('output must be new/empty')
 a.output.mkdir(parents=True,exist_ok=True)
 legacy=['source-fingerprint','product-geometry-gate','export-current','interface-render','preflight','fastener-envelope-regression']
 new=['calibration-profile-regression','component-catalog','artifact-publication','release-integration','parametric-propagation','service-states','helical-motion','reliability-foundation','interface-library','technical-drawings','fit-calibration','structural-screening','motion-paths','access-checks','variant-campaign','capabilities-integration','presentation-catalog','camera-framing','commercial-provenance','portable-kit','workflow-gates','workflow-commands','mandatory-workflow-gate']
 names=[] if a.suite=='smoke' else (new if a.suite=='targeted' else legacy+new)
 source_before={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'cli').glob('*.py')}
 records=[]
 code='''import pathlib,shutil,subprocess,sys
root=pathlib.Path('/candidate')
if sys.argv[1]=='packaged':
 root=pathlib.Path('/tmp/packaged-suite');root.mkdir()
 for name in ['scripts','profiles','examples','templates','skills','licenses','requirements']:shutil.copytree(pathlib.Path('/candidate')/name,root/name)
 for name in ['Dockerfile','Dockerfile.orca','Dockerfile.patch','compose.yaml','compose.dev.yaml']:shutil.copy2(pathlib.Path('/candidate')/name,root/name)
 (root/'docs').mkdir();shutil.copy2('/candidate/docs/INSTALL.md',root/'docs/INSTALL.md')
 shutil.copytree('/opt/cad3d',root/'cli')
if sys.argv[2]=='doctor':cmd=['python',str(root/'cli/cad3d.py'),'doctor']
else:cmd=['python',str(root/'scripts'/('test-'+sys.argv[2]+'.py'))]
import hashlib,json
print('MODULE_ROOT',str(root/'cli'),flush=True)
print('MODULE_SHA256',json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'cli').glob('*.py')},sort_keys=True),flush=True)
raise SystemExit(subprocess.call(cmd))
'''
 for name in ['doctor']+names:
  cmd=['docker','run','--rm','--network','none','--read-only','--tmpfs','/tmp:rw,nosuid,size=1g','-e','PYVISTA_OFF_SCREEN=true','-e','VTK_DEFAULT_OPENGL_WINDOW=vtkEGLRenderWindow','-v',f'{ROOT}:/candidate:ro','--entrypoint','python',a.image,'-c',code,a.mode,name]
  r=subprocess.run(cmd,text=True,capture_output=True);(a.output/(name+'.log')).write_text(r.stdout+r.stderr)
  records.append({'id':name,'command':cmd,'returncode':r.returncode,'status':'PASS' if r.returncode==0 else 'FAIL'})
 image=subprocess.run(['docker','image','inspect',a.image,'--format','{{.Id}}'],text=True,capture_output=True)
 source_after={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'cli').glob('*.py')}
 result={'source_frozen':source_before==source_after,'source_sha256':source_before,'mode':a.mode,'suite':a.suite,'image':a.image,'image_id':image.stdout.strip(),'status':'FAIL' if (source_before!=source_after or any(x['status']=='FAIL' for x in records)) else 'PASS','checks':records,'legacy_v14_acceptance':'NOT_EVALUATED; run separately with unique CAD3D_V14_ACCEPTANCE_DIR','physical_validation':'NOT_EVALUATED'}
 (a.output/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result['status']!='PASS'
if __name__=='__main__':sys.exit(main())
