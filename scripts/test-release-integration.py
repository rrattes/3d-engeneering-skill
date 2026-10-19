#!/usr/bin/env python3
"""Exercise the real release pipeline with CAD artifacts and negative gates."""
import contextlib,io,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
import cad3d
class Release(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  old=Path.cwd();os.chdir(self.tmp.name);self.addCleanup(os.chdir,old)
  Path('.cad3d').mkdir()
  Path('.cad3d/project.yaml').write_text(yaml.safe_dump({'project':{'name':'release-fixture','model':'model.py','parameters':'params.yaml'}}))
  Path('.cad3d/params.yaml').write_text('size: 10\nprinter: {profile: bambu-a1}\n')
  Path('model.py').write_text('from build123d import Box\ndef build(p): return {"block":Box(p["size"],10,10)}\n')
 def release(self):
  with contextlib.redirect_stdout(io.StringIO()):return cad3d.release(SimpleNamespace(target='cad-prototype',assembly=None))
 def test_single_part_and_actual_thin_wall_rejection(self):
  self.assertEqual(self.release(),0)
  pointer=Path('build/delivery/current.json');previous=pointer.read_bytes()
  delivery=Path(json.loads(previous)['directory'])
  from build123d import import_step
  self.assertTrue(import_step(str(delivery/'block.step')).is_valid)
  self.assertTrue((delivery/'block.stl').is_file())
  Path('.cad3d/params.yaml').write_text('size: 0.4\nprinter: {profile: bambu-a1}\n')
  with self.assertRaises(ValueError):self.release()
  self.assertEqual(pointer.read_bytes(),previous)
 def test_unknown_service_cannot_publish(self):
  config={'components':[{'id':'block','part':'block'}],'assembly_steps':[{'id':'unknown','moving_ids':['block'],'direction_mm':[0,0,0],'travel_mm':10,'samples':4}]}
  Path('.cad3d/assembly.yaml').write_text(yaml.safe_dump(config))
  with self.assertRaises(ValueError):self.release()
  self.assertFalse(Path('build/delivery/current.json').exists())
 def test_native_helical_report_and_blocked_release(self):
  step={'id':'unscrew','moving_ids':['block'],'samples':1,'motion':{'type':'helical','axis_origin_mm':[0,0,0],'axis_direction':[0,0,1],'pitch_mm':3,'handedness':'right','travel_mm':3}}
  config={'components':[{'id':'block','part':'block','position_mm':[15,0,0]}],'assembly_steps':[step]}
  Path('.cad3d/assembly.yaml').write_text(yaml.safe_dump(config))
  self.assertEqual(self.release(),0)
  pointer=Path('build/delivery/current.json');previous=pointer.read_bytes();delivery=Path(json.loads(previous)['directory'])
  report=json.loads((delivery/'validation.json').read_text());path=report['assembly']['assembly_sequence']['steps'][0]
  self.assertEqual(path['method'],'sampled_helical_OCP_BREP');self.assertEqual(path['pose_count'],5)
  self.assertEqual(path['physical_validation'],'NOT_EVALUATED')
  config['components'].append({'id':'stop','part':'block','position_mm':[0,15,.75]})
  Path('.cad3d/assembly.yaml').write_text(yaml.safe_dump(config))
  with self.assertRaises(ValueError):self.release()
  self.assertEqual(pointer.read_bytes(),previous)
 def test_tolerance_bounds_unknown_and_assumed_block_release(self):
  dimensions={'hole':{'nominal_mm':10.4,'minus_mm':.1,'plus_mm':.1,'basis':'measured','source':'fixture'},'shaft':{'nominal_mm':10,'minus_mm':.1,'plus_mm':.1,'basis':'supplier','source':'drawing'}}
  stack={'id':'fit','terms':[{'dimension':'hole','coefficient':1},{'dimension':'shaft','coefficient':-1}],'allowed_mm':[.15,.65]}
  config={'components':[{'id':'block','part':'block'}],'tolerance_dimensions':dimensions,'tolerance_stacks':[stack]}
  path=Path('.cad3d/assembly.yaml');path.write_text(yaml.safe_dump(config));self.assertEqual(self.release(),0)
  pointer=Path('build/delivery/current.json');previous=pointer.read_bytes();report=json.loads((Path(json.loads(previous)['directory'])/'validation.json').read_text())
  self.assertEqual(report['assembly']['tolerance_stacks'][0]['status'],'PASS')
  import copy
  for mode in ('fails','assumed','unknown'):
   variant=copy.deepcopy(config)
   if mode=='fails':variant['tolerance_stacks'][0]['allowed_mm']=[.3,.65]
   elif mode=='assumed':variant['tolerance_dimensions']['hole']['basis']='assumed'
   else:variant['tolerance_dimensions']['hole'].pop('plus_mm')
   path.write_text(yaml.safe_dump(variant))
   with self.assertRaises(ValueError):self.release()
   self.assertEqual(pointer.read_bytes(),previous)
 def test_corrupt_final_step_export_cannot_publish(self):
  import build123d
  original=build123d.export_step
  def corrupt(shape,path,*args,**kwargs):
   result=original(shape,path,*args,**kwargs)
   if str(path).endswith('assembly.step'):Path(path).write_text('invalid final export')
   return result
  with patch('build123d.export_step',side_effect=corrupt):
   with self.assertRaises(Exception):self.release()
  self.assertFalse(Path('build/delivery/current.json').exists())
if __name__=='__main__':unittest.main()
