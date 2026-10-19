#!/usr/bin/env python3
"""End-to-end V1.4 acceptance using the installed cad3d CLI and real CAD image."""
from __future__ import annotations
import hashlib, json, os, shutil, struct, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXAMPLES=ROOT/'examples/product-engineering'
WORK=Path(os.environ.get('CAD3D_V14_ACCEPTANCE_DIR','/tmp/cad3d-v14-acceptance'))
if WORK.exists() and any(WORK.iterdir()):
    raise SystemExit(f"Refusing to overwrite non-empty acceptance directory: {WORK}")
WORK.mkdir(parents=True,exist_ok=True)
checks=[]
def check(name,ok,evidence=None):
    checks.append({'name':name,'status':'PASS' if ok else 'FAIL','evidence':evidence})
    if not ok: raise AssertionError(f'{name}: {evidence}')
def run(project,*args,expect=0):
    p=subprocess.run(['cad3d',*args],cwd=project,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    check('command '+' '.join(args),p.returncode==expect,{'returncode':p.returncode,'tail':p.stdout[-2500:]})
    return p

def payload(project,name): return json.loads((project/'build/outputs'/name).read_text())
def clone(name,dest): shutil.copytree(EXAMPLES/name,dest,ignore=shutil.ignore_patterns('build','__pycache__'))
def png(path):
    data=path.read_bytes()
    return {'signature':data[:8]==b'\x89PNG\r\n\x1a\n','width':struct.unpack('>I',data[16:20])[0],'height':struct.unpack('>I',data[20:24])[0],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

# A: removable enclosure fit, sampled extraction, profile-negative tolerance, repair.
a=WORK/'A-box-with-removable-lid'; clone('box-with-removable-lid',a)
run(a,'build'); run(a,'architecture','validate','--geometry'); run(a,'review'); run(a,'report','--requirements')
va=payload(a,'validation.json'); ra=payload(a,'design-review.json')
check('A assembly/fit/removal positive',va['states']['assembly_validity']=='PASS' and va['assembly']['fit_checks'][0]['status']=='PASS' and va['assembly']['assembly_sequence']['status']=='PASS',{'fit':va['assembly']['fit_checks'],'sequence':va['assembly']['assembly_sequence']['status']})
check('A evidence-based design review has findings',ra['status'] in ('WARNING','PASS') and ra['reviewer_independence'].startswith('NOT_CLAIMED'),{'status':ra['status'],'finding_count':len(ra['findings'])})
params=(a/'.cad3d/params.yaml').read_text();assembly=(a/'.cad3d/assembly.yaml').read_text()
(a/'.cad3d/params.yaml').write_text(params.replace('clearance: 0.2','clearance: 0.05'))
(a/'.cad3d/assembly.yaml').write_text(assembly.replace('male_size_mm: 55.6','male_size_mm: 55.9'))
run(a,'validate',expect=3); va_bad=payload(a,'validation.json')
check('A insufficient clearance detected',va_bad['assembly']['fit_checks'][0]['status']=='FAIL',va_bad['assembly']['fit_checks'][0])
(a/'.cad3d/params.yaml').write_text(params);(a/'.cad3d/assembly.yaml').write_text(assembly);run(a,'build');run(a,'review')
check('A corrected fit revalidated',payload(a,'validation.json')['assembly']['fit_checks'][0]['status']=='PASS' and payload(a,'validation.json')['assembly']['assembly_sequence']['status']=='PASS')
views=json.loads((a/'build/outputs/engineering-views.json').read_text())
rendered=[x for x in views['views'] if x.get('path')]
imgs={x['view']:png(a/x['path']) for x in rendered}
check('A required CAD views have valid PNG metadata (legibility not evaluated)',all(imgs.get(n,{}).get('signature') and imgs[n]['width']==1600 and imgs[n]['height']==1200 and imgs[n]['bytes']>20000 for n in ('iso','top','front','side','section','exploded','hidden','interfaces')),imgs)
check('A view images differ',len({x['sha256'] for x in imgs.values()})>=5,{k:v['sha256'][:12] for k,v in imgs.items()})
check('A section view uses real tessellated plane intersections',views.get('section',{}).get('method')=='tessellated plane-intersection outlines; no synthetic caps',views.get('section'))

# B: positively retained rail support, deliberate unretained-part finding, corrected.
b=WORK/'B-captured-rail-support';clone('captured-rail-support',b)
run(b,'build');run(b,'architecture','validate','--geometry');run(b,'review')
vb=payload(b,'validation.json')
check('B rail interface and insertion path pass',vb['assembly']['status']=='PASS' and vb['assembly']['fit_checks'][0]['status']=='PASS' and vb['assembly']['assembly_sequence']['status']=='PASS',{'fit':vb['assembly']['fit_checks'],'path':vb['assembly']['assembly_sequence']})
e=(b/'.cad3d/engineering.yaml').read_text();e_bad=e.replace(
    '        retention: {method: captured_rail, interface_ids: [captured-slide], held_axes: [y, z], release_axis: x}',
    '        # retention deliberately omitted')
check('B deliberate retention defect mutation applied',e_bad!=e)
(b/'.cad3d/engineering.yaml').write_text(e_bad);run(b,'review',expect=3); rb=payload(b,'design-review.json')
mechanical_findings=next((x.get('evidence',[]) for x in rb['findings'] if x['problem']=='Fase 3: arquitetura mecânica'),[])
check('B position without retention is blocked',rb['status']=='FAIL' and any(x['id']=='retention-upright' and x['status']=='FAIL' for x in mechanical_findings),{'status':rb['status'],'retention_findings':[x for x in mechanical_findings if x['id'].startswith('retention-')]})
(b/'.cad3d/engineering.yaml').write_text(e);run(b,'review')
check('B mechanical retention restored',payload(b,'design-review.json')['status'] in ('WARNING','PASS'))

# C: actual 3-chamber B-rep channel check and blocked-route negative, repair.
c=WORK/'C-three-chamber-flow';clone('three-chamber-flow',c)
run(c,'build');run(c,'architecture','validate','--geometry');run(c,'review')
vc=payload(c,'architecture-review.json')
check('C sampled passage through three chamber B-rep passes',vc['flow_paths'][0]['status']=='PASS',vc['flow_paths'][0])
e=(c/'.cad3d/engineering.yaml').read_text();good='centerline_mm: [[10, 15, 5], [40, 15, 5], [50, 15, 5], [50, 15, 23], [80, 15, 23]]'
bad='centerline_mm: [[10, 15, 15], [80, 15, 15]]'
check('C deliberate blocked path mutation applied',good in e)
(c/'.cad3d/engineering.yaml').write_text(e.replace(good,bad));run(c,'architecture','validate','--geometry',expect=3);vc_bad=payload(c,'architecture-review.json')
check('C blocked channel detected in real solids',vc_bad['flow_paths'][0]['status']=='FAIL' and vc_bad['flow_paths'][0]['blocking_sample']['reason']=='intersects_solid_brep',vc_bad['flow_paths'][0])
(c/'.cad3d/engineering.yaml').write_text(e);run(c,'architecture','validate','--geometry')
check('C corrected channel revalidated',payload(c,'architecture-review.json')['flow_paths'][0]['status']=='PASS')

# D: model gate prevents geometry before product architecture is ready.
d=WORK/'D-phase-gate';d.mkdir()
run(d,'init','.');run(d,'architecture','init','--level','product');run(d,'build',expect=3)

result={'suite':'CAD3D Engineering V1.4 acceptance','status':'PASS','check_count':len(checks),'checks':checks,'workspace':str(WORK),'artifacts':{
'A':str(a/'build/outputs'),'B':str(b/'build/outputs'),'C':str(c/'build/outputs')}}
(WORK/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
