#!/usr/bin/env python3
import importlib.util,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
class Parametric(unittest.TestCase):
 def model(self):
  p=Path(__file__).resolve().parents[1]/'examples/evolution/parametric-enclosure/src/model.py'
  self.assertTrue(p.is_file(),'parametric fixture with derived datums is missing')
  s=importlib.util.spec_from_file_location('fixture',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
 def cfg(self,size=80,wall=3):return {'case':{'width':300,'depth':210,'height':70,'wall':wall,'floor':4},'fan':{'size':size,'pitch':71.5 if size==80 else 105,'height':25},'psu':{'length':100,'width':60,'height':40},'clearance':3}
 def test_fan_change_moves_real_holes_and_opening(self):
  m=self.model()
  for size in (80,120):
   p=self.cfg(size);l=m.derive_layout(p);parts=m.build(p);plate=parts['fan_plate'];self.assertAlmostEqual(plate.bounding_box().size.X,size+12);self.assertEqual(len(parts['mounting_hardware'].solids()),4)
   for x,y in l['fan_holes']:self.assertFalse(plate.is_inside((x,y,l['plate_z']+1)))
   self.assertFalse(plate.is_inside((*l['fan_center'],l['plate_z']+1)))
 def test_wall_height_change_propagates_geometry(self):
  m=self.model();a=self.cfg();b=self.cfg(wall=4);b['case']['height']=80
  aa=m.build(a)['chassis'];bb=m.build(b)['chassis'];self.assertGreater(sum(s.volume for s in bb.solids()),sum(s.volume for s in aa.solids()));self.assertAlmostEqual(bb.bounding_box().size.Z,80)
  self.assertEqual(m.build(b)['mounting_hardware'].bounding_box().size.Z-m.build(a)['mounting_hardware'].bounding_box().size.Z,1)
  self.assertEqual(m.derive_layout(b)['fan_center'][0]-m.derive_layout(a)['fan_center'][0],1)
 def test_psu_variant_and_incompatible_cavity(self):
  m=self.model();a=self.cfg();b=self.cfg();b['psu']['length']=150
  self.assertEqual(m.build(b)['psu_reference'].bounding_box().size.Y-m.build(a)['psu_reference'].bounding_box().size.Y,50)
  b['case']['width']=100
  with self.assertRaisesRegex(ValueError,'cavity'):m.build(b)
if __name__=='__main__':unittest.main()
