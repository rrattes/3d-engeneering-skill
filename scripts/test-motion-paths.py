#!/usr/bin/env python3
import importlib,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
from build123d import Box,Pos
class Motion(unittest.TestCase):
 def module(self):
  try:return importlib.import_module('motion_paths')
  except ModuleNotFoundError:self.fail('rotation/composite evaluator missing')
 def test_rotation_checks_intermediate_pose(self):
  m=self.module();p={'lid':Pos(3,0,0)*Box(.5,.5,.5),'stop':Pos(0,3,0)*Box(.7,.7,.7)}
  s={'id':'open','moving_ids':['lid'],'motion':{'type':'rotation','axis_origin_mm':[0,0,0],'axis_direction':[0,0,1],'angle_deg':180,'samples':1}}
  r=m.path_check(p,s);self.assertEqual(r['status'],'FAIL');self.assertGreaterEqual(r['pose_count'],5)
 def test_composite_cumulative_transforms(self):
  m=self.module();p={'lid':Pos(3,0,0)*Box(.5,.5,.5)}
  s={'id':'move','moving_ids':['lid'],'motion':{'type':'composite','segments':[{'type':'translation','vector_mm':[0,0,5],'samples':2},{'type':'rotation','axis_origin_mm':[0,0,5],'axis_direction':[0,0,1],'angle_deg':90,'samples':2}]}}
  r=m.path_check(p,s);self.assertEqual(r['status'],'PASS')
  for a,b in zip(r['terminal_centers_mm']['lid'],[0,3,5]):self.assertAlmostEqual(a,b,places=6)
 def test_invalid_motion_and_budget_rejected(self):
  m=self.module()
  for motion in ({'type':'composite','segments':[]},{'type':'rotation','axis_origin_mm':[0,0,0],'axis_direction':[0,0,0],'angle_deg':90},{'type':'translation','vector_mm':[0,0,0]}):
   with self.assertRaises(ValueError):m.path_check({'lid':Box(1,1,1)},{'id':'bad','moving_ids':['lid'],'motion':motion})
 def test_native_dispatch_and_release_proof(self):
  self.module();from service_states import evaluate_steps
  p={'lid':Box(1,1,1),'stop':Pos(4,0,0)*Box(1,1,1)}
  s={'id':'move','moving_ids':['lid'],'motion':{'type':'composite','segments':[{'type':'translation','vector_mm':[0,0,4]}]}}
  r=evaluate_steps(p,[s])[0];self.assertEqual(r['status'],'PASS');self.assertTrue(r['removal_proven'])
 def test_contacts_do_not_waive_volume(self):
  m=self.module();r=m.path_check({'lid':Box(2,2,2),'stop':Box(2,2,2)},{'id':'x','moving_ids':['lid'],'allowed_contact_pairs':['lid::stop'],'motion':{'type':'translation','vector_mm':[0,0,4]}})
  self.assertEqual(r['status'],'FAIL')
if __name__=='__main__':unittest.main()
