#!/usr/bin/env python3
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
from interface_library import generate_interface

class Interfaces(unittest.TestCase):
 def test_thread_both_hands(self):
  for hand in ('right','left'):
   s,r=generate_interface(dict(type='thread_pair',major_diameter_mm=12,pitch_mm=2,length_mm=6,thread_depth_mm=.8,radial_clearance_mm=.2,wall_mm=2,handedness=hand))
   self.assertEqual(r['nominal_interference']['status'],'PASS');self.assertEqual(set(s),{'male','female'}); self.assertEqual(r['handedness'],hand)
   for x in s.values():self.assertTrue(x.is_valid);self.assertEqual(len(x.solids()),1)
   self.assertLess(sum(x.volume for x in (s['male'] & s['female']).solids()),1e-5)
   # The male must actually contain a helical surface, and extend beyond its root.
   self.assertGreater(s['male'].volume,3.14159*(6-.8)**2*6)
   self.assertTrue(any('BSPLINE' in str(f.geom_type) for f in s['male'].faces()))
   sign=1 if hand=='right' else -1
   self.assertTrue(s['male'].is_inside((0,sign*5.8,.5)))
   self.assertFalse(s['male'].is_inside((0,-sign*5.8,.5)))
 def test_hinge_and_rail_nominal_no_overlap(self):
  for spec,names in [(dict(type='pin_hinge',pin_diameter_mm=4,barrel_outer_diameter_mm=10,length_mm=24,leaf_width_mm=16,leaf_thickness_mm=3,radial_clearance_mm=.2,axial_clearance_mm=.4),{'leaf_a','leaf_b','pin'}),(dict(type='sliding_rail',length_mm=30,width_mm=10,height_mm=8,wall_mm=2,clearance_mm=.2),{'rail','carriage'})]:
   s,r=generate_interface(spec);self.assertEqual(set(s),names)
   for x in s.values():self.assertTrue(x.is_valid);self.assertEqual(len(x.solids()),1)
   parts=list(s.values())
   for i,a in enumerate(parts):
    for b in parts[i+1:]:self.assertLess(sum(x.volume for x in (a&b).solids()),1e-5)
   self.assertEqual(r['physical_validation'],'NOT_EVALUATED');self.assertEqual(r['nominal_interference']['status'],'PASS')
 def test_native_helical_path_right_and_wrong_hands(self):
  from helical_motion import helical_path_check
  s,unused=generate_interface(dict(type='thread_pair',major_diameter_mm=12,pitch_mm=2,length_mm=6,thread_depth_mm=.8,radial_clearance_mm=.2,wall_mm=2,handedness='right'))
  for hand,expected in [('right','PASS'),('left','FAIL')]:
   step={'moving_ids':['male'],'samples':2,'motion':dict(type='helical',axis_origin_mm=[0,0,0],axis_direction=[0,0,1],pitch_mm=2,handedness=hand,travel_mm=.5)}
   self.assertEqual(helical_path_check(s,step)['status'],expected)
 def test_parameter_variation_propagates(self):
  a,unused=generate_interface(dict(type='sliding_rail',length_mm=20,width_mm=10,height_mm=8,wall_mm=2,clearance_mm=.2))
  b,unused=generate_interface(dict(type='sliding_rail',length_mm=40,width_mm=10,height_mm=8,wall_mm=2,clearance_mm=.2))
  for key in a:self.assertAlmostEqual(b[key].volume,2*a[key].volume,places=5)
 def test_fail_closed(self):
  good=dict(type='sliding_rail',length_mm=30,width_mm=10,height_mm=8,wall_mm=2,clearance_mm=.2)
  for change in ({'type':'magic'},{'width_mm':True},{'length_mm':float('nan')},{'clearance_mm':-1},{'wall_mm':0},{'typo':3}):
   with self.subTest(change=change),self.assertRaises(ValueError):generate_interface({**good,**change})
  with self.assertRaises(ValueError):generate_interface(dict(type='thread_pair'))
if __name__=='__main__':unittest.main()
