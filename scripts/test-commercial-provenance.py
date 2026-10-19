#!/usr/bin/env python3
import hashlib,importlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
from build123d import Box,Pos
class Commercial(unittest.TestCase):
 def module(self):
  try:return importlib.import_module('commercial_components')
  except ModuleNotFoundError:self.fail('commercial provenance validator missing')
 def record(self):return {'id':'fan80','revision':'a','units':'mm','record_kind':'component','measurement_target':'component','evidence_kind':'documented','dimensions':{'width':80,'height':80,'depth':25},'source':{'url':'https://example.test/drawing','kind':'manufacturer_drawing','date':'2026-10-17'}}
 def test_documented_dimensions_do_not_claim_physical_approval(self):
  r=self.module().validate_commercial_record(self.record());self.assertEqual(r['status'],'PASS');self.assertEqual(r['physical_validation'],'NOT_EVALUATED')
 def test_enclosure_dimension_and_photo_not_drilling_template(self):
  for change in [{'measurement_target':'enclosure'},{'source':{'kind':'photo_without_scale','url':'https://example.test/photo'}}]:
   r=self.module().validate_commercial_record({**self.record(),**change});self.assertFalse(r['usable_for_drilling_template']);self.assertNotEqual(r['status'],'PASS')
 def test_revision_lock_mismatch_detected(self):
  m=self.module();a=self.record();lock={'id':a['id'],'revision':'a','sha256':m.record_hash(a)}
  self.assertEqual(m.validate_component_selection(a,lock)['status'],'PASS');b={**a,'revision':'b'};self.assertEqual(m.validate_component_selection(b,lock)['status'],'FAIL')
 def test_body_clear_but_plug_collides(self):
  m=self.module();r=m.check_commercial_keepouts(Box(3,3,3),{'plug':Pos(10,0,0)*Box(3,3,3)},{'wall':Pos(10,0,0)*Box(1,1,1)})
  self.assertEqual(r['body']['status'],'PASS');self.assertEqual(r['status'],'FAIL')
 def test_invalid_units_and_nonfinite_dimensions(self):
  m=self.module()
  for change in [{'units':'pixels'},{'dimensions':{'width':float('nan')}}]:self.assertEqual(m.validate_commercial_record({**self.record(),**change})['status'],'FAIL')
if __name__=='__main__':unittest.main()
