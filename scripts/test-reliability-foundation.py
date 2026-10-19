#!/usr/bin/env python3
"""Behavioral controls for pair robustness, face references and worst-case stacks."""
import importlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
from build123d import Box,Compound,Cylinder,Pos
from validation import pair_check,select_face,local_thickness

class Pairs(unittest.TestCase):
 def test_located_compound_collision_and_second_solid(self):
  a=Pos(10,0,0)*Compound(children=[Box(1,1,1),Pos(5,0,0)*Box(1,1,1)])
  r=pair_check(a,Pos(15,0,0)*Box(1,1,1),intentional_contact=True)
  self.assertEqual(r['status'],'FAIL');self.assertGreater(r['intersection_volume_mm3'],0)
 def test_annular_void_is_separation_not_unknown(self):
  r=pair_check(Cylinder(1,5),Cylinder(4,10)-Cylinder(2,12),min_clearance=.8)
  self.assertEqual(r['status'],'PASS');self.assertAlmostEqual(r['surface_distance_mm'],1)
 def test_contact_and_positive_required_gap(self):
  a=Pos(10,0,0)*Compound(children=[Box(2,2,2)])
  for contact,gap,expected in ((True,0,'PASS'),(False,0,'FAIL'),(True,.1,'FAIL')):
   self.assertEqual(pair_check(a,Pos(12,0,0)*Box(2,2,2),intentional_contact=contact,min_clearance=gap)['status'],expected)
 def test_contact_tolerance_does_not_waive_positive_clearance(self):
  r=pair_check(Box(2,2,2),Pos(2,0,0)*Box(2,2,2),intentional_contact=True,min_clearance=.005,contact_tolerance=.01)
  self.assertEqual(r['status'],'FAIL')
 def test_kernel_uncertainty_never_passes(self):
  try:module=importlib.import_module('brep_pairs')
  except ModuleNotFoundError:self.fail('shared robust BREP module missing')
  with patch.object(module,'common_volume',side_effect=RuntimeError('kernel failure')):
   self.assertEqual(pair_check(Box(2,2,2),Box(1,1,1))['status'],'NOT_EVALUATED')
 def test_invalid_inputs(self):
  self.assertEqual(pair_check(Compound(children=[]),Box(1,1,1))['status'],'NOT_EVALUATED')
  for invalid in (float('nan'),-1,True):self.assertEqual(pair_check(Box(1,1,1),Box(1,1,1),min_clearance=invalid)['status'],'NOT_EVALUATED')

class References(unittest.TestCase):
 def selector(self,**kwargs):return {'ref':'datum-side','surface':'plane','point_mm':[10,0,0],'normal':[1,0,0],**kwargs}
 def test_point_is_not_centroid_and_survives_cut(self):
  for shape in (Box(20,20,10),Box(20,20,10)-Pos(9,5,0)*Cylinder(2,12)):
   face,r=select_face(shape,self.selector(point_mm=[10,-5,0]))
   self.assertIsNotNone(face);self.assertEqual(r['selection_basis'],'trimmed_face_point')
 def test_trimmed_hole_point_not_accepted(self):
  shape=Box(20,20,4)-Cylinder(3,6)
  face,r=select_face(shape,self.selector(point_mm=[0,0,2],normal=[0,0,1],point_tolerance_mm=.01))
  self.assertIsNone(face);self.assertEqual(r['status'],'NOT_EVALUATED')
 def test_ambiguous_point_is_not_arbitrary_first_face(self):
  shape=Compound(children=[Pos(0,-6,0)*Box(20,10,10),Pos(0,6,0)*Box(20,10,10)])
  face,r=select_face(shape,self.selector(point_tolerance_mm=2))
  self.assertIsNone(face);self.assertEqual(r['reason'],'face_selector_ambiguous')
 def test_failed_selector_diagnostics_and_invalid_number(self):
  face,r=select_face(Box(20,20,10),self.selector(point_mm=[100,0,0]))
  self.assertIsNone(face);self.assertIn('rejection_counts',r)
  for change in ({'point_tolerance_mm':-1},{'normal':[0,0,0]},{'point_mm':[True,0,0]}):
   face,r=select_face(Box(20,20,10),self.selector(**change));self.assertIsNone(face);self.assertEqual(r['status'],'NOT_EVALUATED')
 def test_partial_selection_cannot_be_thickness_pass(self):
  r=local_thickness(Box(20,20,4),1.2,samples_per_axis=1,face_selectors=[{'ref':'top','surface':'plane','center_mm':[0,0,2],'normal':[0,0,1]},{'ref':'missing','surface':'plane','center_mm':[100,100,100]}])
  self.assertEqual(r['status'],'WARNING')

class Tolerances(unittest.TestCase):
 def module(self):
  try:return importlib.import_module('tolerance_stack')
  except ModuleNotFoundError:self.fail('worst-case tolerance evaluator missing')
 def dimensions(self,basis='measured'):
  return {'hole':{'nominal_mm':10.4,'minus_mm':.15,'plus_mm':.15,'basis':basis,'source':'fixture measurement'},'shaft':{'nominal_mm':10,'minus_mm':.1,'plus_mm':.1,'basis':basis,'source':'fixture measurement'}}
 def stack(self,**kwargs):return {'id':'fit','terms':[{'dimension':'hole','coefficient':1},{'dimension':'shaft','coefficient':-1}],'allowed_mm':[.2,.7],**kwargs}
 def test_nominal_good_worst_case_fails(self):
  r=self.module().evaluate_stack(self.stack(),self.dimensions())
  self.assertEqual(r['status'],'FAIL');self.assertAlmostEqual(r['minimum_mm'],.15);self.assertAlmostEqual(r['maximum_mm'],.65)
 def test_asymmetric_and_duplicate_reference_cancellation(self):
  m=self.module();d={'x':{'min_mm':9,'max_mm':12,'basis':'supplier','source':'drawing revB'}}
  r=m.evaluate_stack(self.stack(terms=[{'dimension':'x','coefficient':1},{'dimension':'x','coefficient':-1}],offset_mm=.4),d)
  self.assertEqual(r['status'],'PASS');self.assertAlmostEqual(r['minimum_mm'],.4);self.assertAlmostEqual(r['maximum_mm'],.4)
 def test_assumed_bounds_are_warning_and_physical_unknown(self):
  r=self.module().evaluate_stack(self.stack(allowed_mm=[.1,.7]),self.dimensions('assumed'))
  self.assertEqual(r['status'],'WARNING');self.assertEqual(r['physical_fit_validation'],'NOT_EVALUATED')
 def test_missing_uncertainty_or_source_is_unknown(self):
  m=self.module();d=self.dimensions();d['hole'].pop('minus_mm')
  self.assertEqual(m.evaluate_stack(self.stack(),d)['status'],'NOT_EVALUATED')
  d=self.dimensions();d['hole'].pop('source');self.assertEqual(m.evaluate_stack(self.stack(allowed_mm=[.1,.7]),d)['status'],'NOT_EVALUATED')
 def test_invalid_bounds_coefficient_and_ids_rejected(self):
  m=self.module()
  for stack in (self.stack(allowed_mm=[1,0]),self.stack(terms=[{'dimension':'hole','coefficient':True}]),self.stack(terms=[{'dimension':'missing','coefficient':1}])):
   with self.assertRaises(ValueError):m.evaluate_stack(stack,self.dimensions())
if __name__=='__main__':unittest.main()
