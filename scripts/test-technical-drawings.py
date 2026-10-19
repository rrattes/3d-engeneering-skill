#!/usr/bin/env python3
import sys, unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
from build123d import Box, Cylinder, Pos
from technical_drawings import generate_drawings
class Drawings(unittest.TestCase):
 def test_actual_views_and_dimensions_and_files(self):
  shape=Pos(4,8,12)*(Box(10,20,6)-Cylinder(2,10))
  with tempfile.TemporaryDirectory() as folder:
   r=generate_drawings({'bracket':shape},Path(folder))
   self.assertEqual(r['status'],'PASS');self.assertEqual(len(r['parts'][0]['views']),3)
   self.assertEqual(r['parts'][0]['overall_mm'],{'x':10.,'y':20.,'z':6.})
   self.assertTrue(all(v['visible_edges']>0 for v in r['parts'][0]['views']))
   svg=(Path(folder)/'bracket.svg').read_text();self.assertIn('10.00 mm',svg)
   self.assertTrue((Path(folder)/'bracket.pdf').read_bytes().startswith(b'%PDF'))
 def test_real_section_and_measured_features(self):
  shape=Box(10,20,6)-Cylinder(2,10)
  config={'sections':[{'name':'cut_z','part':'bracket','axis':'z','at_mm':0}],
   'feature_dimensions':[{'name':'bore','part':'bracket','type':'diameter','selector':{'surface':'cylinder','radius_mm':2}},
    {'name':'thickness','part':'bracket','type':'minimum_distance','first':{'surface':'plane','normal':[0,0,1]},'second':{'surface':'plane','normal':[0,0,-1]}}]}
  with tempfile.TemporaryDirectory() as folder:
   r=generate_drawings({'bracket':shape},Path(folder),config)
   self.assertEqual(r['status'],'PASS');self.assertAlmostEqual(r['sections'][0]['area_mm2'],200-3.141592653589793*4,places=5)
   self.assertAlmostEqual(r['feature_dimensions'][0]['value_mm'],4,places=6);self.assertAlmostEqual(r['feature_dimensions'][1]['value_mm'],6,places=6)
   self.assertIn('bore: diameter = 4.000 mm',(Path(folder)/'bracket.svg').read_text())
   for ext in ('svg','pdf'):self.assertTrue((Path(folder)/('bracket-section-cut_z.'+ext)).stat().st_size>100)
 def test_unresolved_feature_is_not_a_valid_dimension(self):
  with tempfile.TemporaryDirectory() as folder:
   r=generate_drawings({'block':Box(10,20,6)},Path(folder),{'feature_dimensions':[{'name':'ambiguous','part':'block','type':'minimum_distance','first':{'surface':'plane'},'second':{'surface':'plane'}}]})
   self.assertEqual(r['status'],'NOT_EVALUATED');self.assertNotIn('value_mm',r['feature_dimensions'][0])
   for item in ({'name':'invented','part':'block','type':'diameter','selector':{'surface':'cylinder'},'value_mm':4}, {'name':'../unsafe','part':'block','type':'diameter','selector':{'surface':'cylinder'}}):
    with self.assertRaises(ValueError):generate_drawings({'block':Box(10,20,6)},Path(folder),{'feature_dimensions':[item]})
 def test_empty_section_rejected(self):
  with tempfile.TemporaryDirectory() as folder:
   with self.assertRaises(ValueError):generate_drawings({'block':Box(10,20,6)},Path(folder),{'sections':[{'name':'empty','part':'block','axis':'z','at_mm':100}]})
   self.assertEqual(list(Path(folder).iterdir()),[])
 def test_invalid_inputs_and_no_partial_unsafe_name(self):
  with tempfile.TemporaryDirectory() as folder:
   for shapes,config in [({'../evil':Box(1,2,3)},None),({},None),({'ok':Box(1,2,3)},{'samples_per_edge':True}),({'ok':Box(1,2,3)},{'unknown':1})]:
    with self.subTest(shapes=list(shapes)),self.assertRaises(ValueError):generate_drawings(shapes,Path(folder),config)
   self.assertEqual(list(Path(folder).iterdir()),[])
if __name__=='__main__':unittest.main()
