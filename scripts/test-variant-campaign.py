#!/usr/bin/env python3
import importlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
class Variants(unittest.TestCase):
 def module(self):
  try:return importlib.import_module('variant_campaign')
  except ModuleNotFoundError:self.fail('native variant campaign missing')
 def test_full_native_validation_isolated_and_failing_variant(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as folder:
   r=Path(folder);(r/'.cad3d').mkdir();(r/'.cad3d/project.yaml').write_text('project: {name: fixture, model: model.py, parameters: params.yaml, output: build/outputs}\n');(r/'.cad3d/params.yaml').write_text('size: 4\nprinter: {profile: bambu-a1}\n')
   (r/'model.py').write_text('from build123d import Box\ndef build(p): return {"block":Box(p["size"],4,4)}\n')
   before=(r/'.cad3d/params.yaml').read_bytes();result=m.run_campaign(r,{'axes':{'size':[4,.4]},'max_cases':4})
   self.assertEqual(result['status'],'FAIL');self.assertEqual([c['status'] for c in result['cases']],['PASS','FAIL']);self.assertEqual((r/'.cad3d/params.yaml').read_bytes(),before);self.assertFalse((r/'build/delivery/current.json').exists())
 def test_cartesian_budget_and_missing_path_rejected(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as folder:
   r=Path(folder);(r/'.cad3d').mkdir();(r/'.cad3d/project.yaml').write_text('project: {name: fixture, model: model.py, parameters: params.yaml}\n');(r/'.cad3d/params.yaml').write_text('size: 4\n');(r/'model.py').write_text('')
   for config in ({'axes':{'size':list(range(65))}},{'axes':{'unknown':[1,2]}}):
    with self.assertRaises(ValueError):m.run_campaign(r,config)
if __name__=='__main__':unittest.main()
