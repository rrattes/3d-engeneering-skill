#!/usr/bin/env python3
import importlib,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
from build123d import Box,Pos
class Service(unittest.TestCase):
 def module(self):
  try:return importlib.import_module('service_states')
  except ModuleNotFoundError:self.fail('explicit service state evaluator not implemented')
 def step(self,**kwargs):return {'id':'lift','moving_ids':['lid'],'removed_ids':[],'direction_mm':[0,0,-1],'travel_mm':20,'samples':4,**kwargs}
 def test_retained_fastener_blocks_and_only_correct_removal_releases(self):
  m=self.module();placed={'lid':Box(10,10,1),'screw':Pos(0,0,5)*Box(2,2,2),'other':Pos(20,0,0)*Box(2,2,2)}
  self.assertEqual(m.check_service_step(m.resolve_service_state(placed,self.step()),self.step())['status'],'FAIL')
  step=self.step(removed_ids=['screw']);state=m.resolve_service_state(placed,step);self.assertIn('other',state['placed']);self.assertEqual(m.check_service_step(state,step)['status'],'PASS')
 def test_connector_must_move_with_assembly(self):
  m=self.module();p={'lid':Box(2,2,1),'plug':Pos(5,0,0)*Box(2,2,1),'rib':Pos(5,0,10)*Box(2,2,1)};s=self.step(moving_ids=['lid','plug'])
  self.assertEqual(m.check_service_step(m.resolve_service_state(p,s),s)['status'],'FAIL')
 def test_unknown_or_overlapping_ids_fail(self):
  m=self.module()
  for s in [self.step(removed_ids=['missing']),self.step(removed_ids=['lid'])]:
   with self.assertRaises(ValueError):m.resolve_service_state({'lid':Box(1,1,1)},s)
 def test_counterhold_and_unknown_kernel(self):
  m=self.module();p={'lid':Box(1,1,1),'rib':Pos(10,0,3)*Box(2,2,2)}
  s=self.step(tools=[{'id':'counterhold','origin_mm':[10,0,0],'direction_mm':[0,0,1],'radius_mm':2,'length_mm':8}])
  self.assertEqual(m.check_service_step(m.resolve_service_state(p,s),s)['status'],'FAIL')
  with patch('service_states.pair_check',return_value={'status':'NOT_EVALUATED','reason':'synthetic_kernel_failure'}):self.assertEqual(m.check_service_step(m.resolve_service_state(p,s),s)['status'],'NOT_EVALUATED')
 def test_nominal_fastener_stack_detects_short_bottomed_and_unseated(self):
  m=self.module();self.assertTrue(hasattr(m,'check_fastener_stack'),'nominal engagement/seat evaluator missing')
  base={'length_mm':10,'grip_mm':6,'required_engagement_mm':3,'blind_depth_mm':6,'head_to_seat_gap_mm':0,'seat_tolerance_mm':.01}
  self.assertEqual(m.check_fastener_stack(base)['status'],'PASS')
  for change in [{'length_mm':7},{'length_mm':14},{'head_to_seat_gap_mm':.2}]:self.assertEqual(m.check_fastener_stack({**base,**change})['status'],'FAIL')
 def test_unsuccessful_prerequisite_cannot_release_next_part(self):
  m=self.module();p={'lid':Box(3,3,1),'screw':Pos(5,0,0)*Box(1,1,1)}
  a=self.step(id='remove-screw',moving_ids=['screw'],direction_mm=[0,0,0]);b=self.step(removed_ids=['screw'],prerequisite_step_ids=['remove-screw'])
  r=m.evaluate_steps(p,[a,b]);self.assertNotEqual(r[1]['status'],'PASS')
 def test_cycle_is_rejected(self):
  m=self.module();steps=[self.step(prerequisite_step_ids=['two']),self.step(id='two',prerequisite_step_ids=['lift'])]
  with self.assertRaises(ValueError):m.validate_service_plan(steps)
if __name__=='__main__':unittest.main()
