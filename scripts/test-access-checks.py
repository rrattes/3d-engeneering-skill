#!/usr/bin/env python3
import importlib,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
from build123d import Box,Pos
class Access(unittest.TestCase):
 def module(self):
  try:return importlib.import_module('access_checks')
  except ModuleNotFoundError:self.fail('access envelope evaluator missing')
 def test_tool_target_exclusion_is_narrow(self):
  m=self.module();p={'screw':Box(1,1,1),'rib':Pos(0,0,3)*Box(2,2,2)}
  c={'id':'driver','kind':'cylinder','origin_mm':[0,0,0],'direction':[0,0,1],'radius_mm':1,'length_mm':6,'target_id':'screw'}
  r=m.evaluate_access(p,[c])[0];self.assertEqual(r['status'],'FAIL');self.assertEqual(r['excluded_target'],'screw')
 def test_box_hand_envelope_and_approach(self):
  m=self.module();c={'id':'hand','kind':'box','center_mm':[0,0,0],'size_mm':[2,2,2],'motion':{'type':'translation','vector_mm':[5,0,0]}}
  self.assertEqual(m.evaluate_access({'rib':Pos(3,0,0)*Box(1,1,1)},[c])[0]['status'],'FAIL')
 def test_cable_bend_and_capsule_collision(self):
  m=self.module();c={'id':'cable','kind':'cable','points_mm':[[0,0,0],[20,0,0],[20,20,0]],'diameter_mm':2,'bend_radius_mm':5,'minimum_bend_radius_mm':4}
  r=m.evaluate_access({'rib':Pos(18.5,1.5,0)*Box(2,2,2)},[c])[0];self.assertEqual(r['status'],'FAIL')
  c['minimum_bend_radius_mm']=8;r=m.evaluate_access({},[c])[0];self.assertEqual(r['status'],'FAIL')
 def test_unknown_target_and_overlapping_bends_rejected(self):
  m=self.module()
  for c in ({'id':'x','kind':'box','center_mm':[0,0,0],'size_mm':[1,1,1],'target_id':'missing'},{'id':'c','kind':'cable','points_mm':[[0,0,0],[2,0,0],[2,2,0]],'diameter_mm':2,'bend_radius_mm':5,'minimum_bend_radius_mm':4}):
   with self.assertRaises(ValueError):m.evaluate_access({},[c])
if __name__=='__main__':unittest.main()
