#!/usr/bin/env python3
"""Real CLI artifacts and release gates across opt-in1.8 capabilities."""
import contextlib,copy,io,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
import cad3d
class Integration(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);old=Path.cwd();os.chdir(self.tmp.name);self.addCleanup(os.chdir,old)
  Path('.cad3d').mkdir();Path('.cad3d/project.yaml').write_text('project: {name: capabilities, model: model.py, parameters: params.yaml, output: build/outputs, drawings: {title: Fixture}}\n');Path('.cad3d/params.yaml').write_text('size: 4\nprinter: {profile: bambu-a1}\n');Path('model.py').write_text('from build123d import Box\ndef build(p): return {"part":Box(p["size"],4,4)}\n')
 def release(self):
  with contextlib.redirect_stdout(io.StringIO()):return cad3d.release(SimpleNamespace(target='cad-prototype',assembly=None))
 def test_drawings_in_immutable_release_and_access_gate(self):
  self.assertEqual(self.release(),0);p=Path('build/delivery/current.json');old=p.read_bytes();out=Path(json.loads(old)['directory'])
  self.assertTrue((out/'drawings/part.svg').is_file());self.assertTrue((out/'drawings/part.pdf').read_bytes().startswith(b'%PDF'))
  config={'components':[{'id':'part','part':'part'}],'access_checks':[{'id':'grip','kind':'box','center_mm':[0,0,0],'size_mm':[1,1,1]}]}
  Path('.cad3d/assembly.yaml').write_text(yaml.safe_dump(config))
  with self.assertRaises(ValueError):self.release()
  self.assertEqual(p.read_bytes(),old)
 def test_unresolved_requested_drawing_dimension_blocks_publication(self):
  self.assertEqual(self.release(),0);pointer=Path('build/delivery/current.json');before=pointer.read_bytes()
  project={'project':{'name':'capabilities','model':'model.py','parameters':'params.yaml','output':'build/outputs','drawings':{'feature_dimensions':[{'name':'bore','part':'part','type':'diameter','selector':{'surface':'cylinder','radius_mm':2}}]}}}
  Path('.cad3d/project.yaml').write_text(yaml.safe_dump(project))
  with self.assertRaises(ValueError):self.release()
  self.assertEqual(pointer.read_bytes(),before)
 def test_structural_warning_and_unknown_block_publication(self):
  from structural_screening import ASSUMPTIONS
  r={'id':'arm','model':'rectangular_cantilever_end_load','units':'N-mm-MPa','length_mm':100,'width_mm':20,'thickness_mm':10,'load_n':10,'elastic_modulus_mpa':2000,'allowable_stress_mpa':12,'max_deflection_mm':2,'safety_factor':2,'provenance':{k:{'basis':'supplier','source':'fixture'} for k in ('elastic_modulus_mpa','allowable_stress_mpa')},'assumptions':{k:True for k in ASSUMPTIONS}}
  c={'components':[{'id':'part','part':'part'}],'structural_checks':[r]};Path('.cad3d/assembly.yaml').write_text(yaml.safe_dump(c));self.assertEqual(self.release(),0);p=Path('build/delivery/current.json');old=p.read_bytes()
  for mode in ('warning','unknown','fail'):
   v=copy.deepcopy(c)
   if mode=='warning':v['structural_checks'][0]['provenance']['elastic_modulus_mpa']['basis']='assumed'
   elif mode=='unknown':v['structural_checks'][0].pop('provenance')
   else:v['structural_checks'][0]['load_n']=1000
   Path('.cad3d/assembly.yaml').write_text(yaml.safe_dump(v))
   with self.assertRaises(ValueError):self.release()
   self.assertEqual(p.read_bytes(),old)
 def test_cli_drawings_and_fit_calibration_and_identity_gate(self):
  from datetime import datetime,timedelta,timezone
  from unittest.mock import patch
  import hashlib
  now=datetime.now(timezone.utc);identity={'printer':'fixture','nozzle_mm':.4,'material':'fixture-petg','process_sha256':'a'*64,'orientation':'Z'}
  Path('process.yaml').write_text('layer: 0.2\n')
  identity['process_sha256']=hashlib.sha256(Path('process.yaml').read_bytes()).hexdigest();identity['printer_profile']='bambu-a1'
  Path('.cad3d/params.yaml').write_text('size: 4\nprinter: {profile: bambu-a1}\nmaterial: {profile: fixture-petg}\n')
  Path('measure.csv').write_text('nominal,actual\n10,10.2\n')
  payload={'identity':identity,'confirmed_measured':True,'measured_at':(now-timedelta(days=1)).isoformat(),'valid_until':(now+timedelta(days=1)).isoformat(),'evidence':{'path':'measure.csv','sha256':hashlib.sha256(Path('measure.csv').read_bytes()).hexdigest()},'measurements':[{'feature':'hole','nominal_mm':10,'actual_mm':10.2,'uncertainty_mm':.05}]}
  Path('record.json').write_text(json.dumps(payload));Path('identity.json').write_text(json.dumps(identity))
  for argv in (['cad3d','drawings','--output','build/sheets'],['cad3d','calibration','fit','record.json','--identity','identity.json','--output','build/fit.json']):
   with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(cad3d.main(),0)
  self.assertTrue(Path('build/sheets/part.svg').exists());self.assertEqual(json.loads(Path('build/fit.json').read_text())['status'],'PASS')
  config={'components':[{'id':'part','part':'part'}],'fit_calibration':'record.json'};Path('.cad3d/assembly.yaml').write_text(yaml.safe_dump(config));pc={'name':'fixture','nozzle_diameter_mm':.4,'fit_orientation':'Z','process_settings_file':'process.yaml','process_settings_sha256':identity['process_sha256']};Path('.cad3d/printer.yaml').write_text(yaml.safe_dump(pc))
  self.assertEqual(self.release(),0);pointer=Path('build/delivery/current.json');before=pointer.read_bytes()
  Path('.cad3d/params.yaml').write_text('size: 4\nprinter: {profile: bambu-a1}\nmaterial: {profile: OTHER}\n')
  with self.assertRaises(ValueError):self.release()
  self.assertEqual(pointer.read_bytes(),before)
  Path('.cad3d/params.yaml').write_text('size: 4\nprinter: {profile: bambu-a1}\nmaterial: {profile: fixture-petg}\n')
  for field,value in (('name','OTHER'),('nozzle_diameter_mm',.6),('fit_orientation','X')):
   Path('.cad3d/printer.yaml').write_text(yaml.safe_dump({**pc,field:value}))
   with self.assertRaises(ValueError):self.release()
   self.assertEqual(pointer.read_bytes(),before)
  Path('.cad3d/printer.yaml').write_text(yaml.safe_dump(pc));Path('process.yaml').write_text('layer: 0.3\n')
  with self.assertRaises(ValueError):self.release()
  self.assertEqual(pointer.read_bytes(),before)
 def test_interfaces_actual_export(self):
  from capability_commands import interfaces
  Path('interface.json').write_text(json.dumps({'type':'sliding_rail','length_mm':30,'width_mm':10,'height_mm':8,'wall_mm':2,'clearance_mm':.3}))
  with contextlib.redirect_stdout(io.StringIO()):code=interfaces(SimpleNamespace(config='interface.json',output='build/interface',material='PETG'))
  self.assertEqual(code,0);self.assertEqual(len(list(Path('build/interface').glob('*.stl'))),2)
  from build123d import import_step
  self.assertTrue(import_step('build/interface/assembly.step').is_valid)
if __name__=='__main__':unittest.main()
