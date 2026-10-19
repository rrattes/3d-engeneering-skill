#!/usr/bin/env python3
"""ENG2-CAL/P R O F I L E: real validate path, candidate module in container."""
import contextlib,io,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
import cad3d
from build123d import Box
class Profiles(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.old=Path.cwd();os.chdir(self.tmp.name);self.addCleanup(os.chdir,self.old)
  Path('.cad3d').mkdir();Path('out').mkdir();self.params={'printer':{'profile':'unknown-printer'},'material':{'profile':'pla'}}
 def call(self,pc=None):
  if pc is not None:Path('.cad3d/printer.yaml').write_text(yaml.safe_dump(pc))
  with patch.object(cad3d,'project_files',return_value=({},self.params,{'block':Box(10,10,10)},Path('out'))),contextlib.redirect_stdout(io.StringIO()):cad3d.validate(SimpleNamespace(assembly=None))
  return json.loads(Path('out/validation.json').read_text())
 def test_missing_profile_is_not_printer_compatibility(self):
  r=self.call();self.assertEqual(r['states'].get('printer_compatibility'),'NOT_EVALUATED');self.assertEqual(r['printer_profile']['status'],'NOT_EVALUATED')
 def calibrated(self,record_material='pla',explicit=False):
  pc={'name':'Fixture','nozzle_diameter_mm':.4,'process_settings_sha256':'a'*64,'calibration_profile':'cal.yaml'}
  if explicit:pc['min_wall_mm']=1.3
  identity={k:pc[k] for k in ('nozzle_diameter_mm','process_settings_sha256')};identity.update(printer='Fixture',material=record_material)
  Path('cal.yaml').write_text(yaml.safe_dump({'calibrated':True,'identity':identity,'min_wall_mm':1.6,'shrinkage_percent':99}))
  return self.call(pc)
 def test_machined_process_does_not_claim_manufacturing_pass(self):
  from component_catalog import resolve_catalog
  self.params['printer']['profile']='bambu-a1'
  catalog=resolve_catalog({'block':Box(10,10,10)},{'parts':{'block':{'kind':'manufactured','process':'machined'}}})
  with patch.object(cad3d,'project_catalog',return_value=catalog):r=self.call()
  self.assertNotEqual(r['states']['manufacturing_assessment'],'PASS')
 def test_fit_checks_declared_stl_rotation(self):
  from component_catalog import resolve_catalog
  self.params['printer']['profile']='local'
  Path('profiles/printers').mkdir(parents=True)
  Path('profiles/printers/local.yaml').write_text(yaml.safe_dump({'build_volume_mm':[50,100,100],'operational_margin_mm':[0,0,0]}))
  shapes={'block':Box(80,40,10)}
  catalog=resolve_catalog(shapes,{'parts':{'block':{'kind':'manufactured','process':'fdm','print_rotation_deg':[0,0,0]}}})
  with patch.object(cad3d,'project_catalog',return_value=catalog),patch.object(cad3d,'project_files',return_value=({},self.params,shapes,Path('out'))),contextlib.redirect_stdout(io.StringIO()):
   cad3d.validate(SimpleNamespace(assembly=None))
  r=json.loads(Path('out/validation.json').read_text())
  self.assertEqual(r['components'][0]['print_fit']['status'],'FAIL')
 def test_calibrated_without_local_minimum_has_no_unbound_variable(self):self.assertEqual(self.calibrated()['calibration_profile']['status'],'PASS')
 def test_calibrated_with_local_minimum(self):self.assertEqual(self.calibrated(explicit=True)['calibration_profile']['status'],'PASS')
 def test_mismatched_identity_does_not_apply_record(self):self.assertEqual(self.calibrated('asa')['calibration_profile']['status'],'FAIL')
if __name__=='__main__':unittest.main()
