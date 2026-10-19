#!/usr/bin/env python3
"""Regression controls for helical transforms and native service dispatch."""
import importlib
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
from build123d import Box,Pos

class Helical(unittest.TestCase):
 def module(self):
  try:return importlib.import_module('helical_motion')
  except ModuleNotFoundError:self.fail('native helical motion evaluator missing')
 def motion(self,**kwargs):
  return {'type':'helical','axis_origin_mm':[0,0,0],'axis_direction':[0,0,1],'pitch_mm':3,'handedness':'right','travel_mm':3,**kwargs}
 def step(self,**kwargs):return {'id':'unscrew','moving_ids':['screw'],'motion':self.motion(),'samples':4,**kwargs}
 def test_transform_rotation_translation_offset_axis_and_left_hand(self):
  m=self.module();shape=Pos(11,0,0)*Box(1,1,1)
  for hand,travel,expected in [('right',.75,(10,1,.75)),('left',.75,(10,-1,.75)),('right',-.75,(10,-1,-.75))]:
   motion=self.motion(axis_origin_mm=[10,0,0],travel_mm=travel,handedness=hand)
   c=m.helical_pose(shape,motion,1).center()
   for a,b in zip(c,expected):self.assertAlmostEqual(a,b,places=6)
 def test_arbitrary_axis_and_multistart_lead(self):
  m=self.module();motion=self.motion(axis_direction=[0,2,0],travel_mm=1.5,starts=2)
  c=m.helical_pose(Pos(1,0,0)*Box(1,1,1),motion,1).center()
  for a,b in zip(c,(0,1.5,-1)):self.assertAlmostEqual(a,b,places=6)
 def test_oblique_world_axis_and_offset(self):
  m=self.module();origin=(7,-2,5);unit=[x/math.sqrt(14) for x in (1,2,3)]
  # Radius vector (2,-1,0) is orthogonal to (1,2,3). Rodrigues at +90deg.
  radial=(2,-1,0);cross=(3/math.sqrt(14),6/math.sqrt(14),-5/math.sqrt(14))
  motion=self.motion(axis_origin_mm=list(origin),axis_direction=[1,2,3],travel_mm=.75)
  point=[a+b for a,b in zip(origin,radial)]
  c=m.helical_pose(Pos(*point)*Box(1,1,1),motion,1).center()
  for actual,o,r,u in zip(c,origin,cross,unit):self.assertAlmostEqual(actual,o+r+.75*u,places=6)
 def test_sampling_includes_endpoints_and_no_full_turn_alias(self):
  m=self.module();r=m.helical_path_check({'screw':Box(1,1,1)},self.step(samples=1))
  self.assertEqual(r['status'],'PASS');self.assertEqual(r['pose_count'],5)
  self.assertEqual(r['poses'][0]['translation_mm'],0);self.assertEqual(r['poses'][-1]['rotation_deg'],360)
 def test_invalid_motion_fails_closed(self):
  m=self.module()
  for change in ({'pitch_mm':0},{'pitch_mm':True},{'travel_mm':float('nan')},{'travel_mm':0},{'axis_direction':[0,0,0]},{'axis_direction':[0,0,True]},{'handedness':'unknown'},{'starts':1.5},{'axis_origin_mm':[0,0]},{'travel_mm':1e12}):
   with self.subTest(change=change),self.assertRaises(ValueError):m.helical_path_check({'screw':Box(1,1,1)},self.step(motion=self.motion(**change)))
  for samples in (0,-1,True,1.5,1000000):
   with self.subTest(samples=samples),self.assertRaises(ValueError):m.helical_path_check({'screw':Box(1,1,1)},self.step(samples=samples))
 def test_quarter_turn_obstacle_blocks_despite_free_endpoints(self):
  m=self.module();placed={'screw':Pos(3,0,0)*Box(.6,.6,.6),'stop':Pos(0,3,.75)*Box(.7,.7,.7)}
  r=m.helical_path_check(placed,self.step(samples=1))
  self.assertEqual(r['status'],'FAIL');self.assertTrue(any(f['sample']==1 for f in r['blockages']))
 def test_declared_contact_never_waives_positive_volume(self):
  m=self.module();p={'screw':Box(2,2,2),'support':Box(2,2,2)}
  r=m.helical_path_check(p,self.step(allowed_contact_pairs=['screw::support']))
  self.assertEqual(r['status'],'FAIL')
 def test_contact_allowance_is_per_original_instance(self):
  m=self.module();p={'screw':Pos(4,0,0)*Box(1,1,1),'head':Box(1,1,1),'support':Pos(1,0,0)*Box(1,1,1)}
  r=m.helical_path_check(p,self.step(moving_ids=['screw','head'],allowed_contact_pairs=['screw::support']))
  self.assertEqual(r['status'],'FAIL')
 def test_unknown_kernel_is_not_pass(self):
  m=self.module();p={'screw':Box(1,1,1),'support':Pos(1,0,0)*Box(1,1,1)}
  with patch('helical_motion._distance',side_effect=RuntimeError('synthetic_kernel_failure')):
   self.assertEqual(m.helical_path_check(p,self.step())['status'],'NOT_EVALUATED')
 def test_imported_compound_checks_atomic_solids(self):
  import tempfile
  from build123d import Compound,export_step,import_step
  m=self.module()
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'moving.step'
   export_step(Compound(children=[Box(2,2,2)]),str(path))
   moving=import_step(str(path))
  for allowed in ([],['screw::support']):
   with self.subTest(allowed=allowed):
    r=m.helical_path_check({'screw':Pos(10,0,0)*moving,'support':Pos(10,0,0)*Box(2,2,2)},self.step(motion=self.motion(axis_origin_mm=[10,0,0]),allowed_contact_pairs=allowed))
    self.assertEqual(r['status'],'FAIL')
 def test_compound_collision_only_in_second_solid(self):
  from build123d import Compound
  m=self.module();moving=Pos(10,0,0)*Compound(children=[Box(1,1,1),Pos(5,0,0)*Box(1,1,1)])
  r=m.helical_path_check({'screw':moving,'support':Pos(15,0,0)*Box(1,1,1)},self.step(motion=self.motion(axis_origin_mm=[10,0,0]),allowed_contact_pairs=['screw::support']))
  self.assertEqual(r['status'],'FAIL')
 def test_positive_clearance_is_enforced(self):
  m=self.module()
  for gap,expected in ((.2,'FAIL'),(.8,'PASS')):
   r=m.helical_path_check({'screw':Box(1,1,1),'support':Pos(1+gap,0,0)*Box(1,1,1)},self.step(clearance_mm=.5))
   self.assertEqual(r['status'],expected)
 def test_invalid_solid_is_not_pass_even_without_obstacles(self):
  from build123d import Compound
  m=self.module();r=m.helical_path_check({'screw':Compound(children=[])},self.step())
  self.assertEqual(r['status'],'NOT_EVALUATED')
 def test_native_service_dispatch_and_unknown_type_rejected(self):
  m=self.module();import service_states as service
  r=service.evaluate_steps({'screw':Box(1,1,1)},[self.step()])[0]
  self.assertEqual(r['method'],'sampled_helical_OCP_BREP');self.assertEqual(r['status'],'PASS')
  with self.assertRaises(ValueError):service.evaluate_steps({'screw':Box(1,1,1)},[self.step(motion={'type':'magic'})])
 def test_short_helix_cannot_prove_prerequisite_removal(self):
  self.module();import service_states as service
  from build123d import Cylinder
  support=Cylinder(4,10)-Cylinder(2,12)
  p={'screw':Cylinder(1,5),'support':support,'lid':Pos(20,0,0)*Box(1,1,1)}
  first=self.step(motion=self.motion(travel_mm=.2))
  second={'id':'lift','moving_ids':['lid'],'removed_ids':['screw'],'prerequisite_step_ids':['unscrew'],'direction_mm':[0,0,-1],'travel_mm':3,'samples':2}
  r=service.evaluate_steps(p,[first,second]);self.assertEqual(r[0]['status'],'PASS');self.assertFalse(r[0]['removal_proven']);self.assertEqual(r[1]['status'],'NOT_EVALUATED')
 def test_full_helix_can_release_dependent_operation(self):
  self.module();import service_states as service
  from build123d import Cylinder
  p={'screw':Cylinder(1,5),'support':Cylinder(4,10)-Cylinder(2,12),'lid':Pos(20,0,0)*Box(1,1,1)}
  first=self.step(motion=self.motion(travel_mm=12),samples=4)
  second={'id':'lift','moving_ids':['lid'],'removed_ids':['screw'],'prerequisite_step_ids':['unscrew'],'direction_mm':[0,0,-1],'travel_mm':3,'samples':2}
  r=service.evaluate_steps(p,[first,second]);self.assertTrue(r[0]['removal_proven']);self.assertEqual(r[1]['status'],'PASS')
if __name__=='__main__':unittest.main()
