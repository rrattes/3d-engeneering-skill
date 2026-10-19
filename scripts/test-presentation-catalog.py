#!/usr/bin/env python3
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
from build123d import Box,Pos
from component_catalog import resolve_catalog,export_catalog
import cad3d_visualization as vis
class Presentation(unittest.TestCase):
 def test_legend_separate_viewport_for_36_components(self):
  with tempfile.TemporaryDirectory() as d:
   shapes={f'part_{i}':Pos((i%6)*15,(i//6)*15,0)*Box(8,8,3) for i in range(36)}
   m,_=vis.render_views(Path(d),shapes,view='iso');self.assertEqual(m.get('annotation_layout'),'separate_legend_viewport');self.assertFalse(m.get('smooth_shading',True))
 def test_actual_parts_gallery_and_presentation_colors(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);out=root/'build/outputs';shapes={'printed':Box(10,10,3),'ref':Pos(30,0,0)*Box(5,5,5)};ac={'parts':{'printed':{'kind':'manufactured','process':'fdm','color':'#235588'},'ref':{'kind':'commercial','process':'none'}},'components':[{'id':n,'part':n} for n in shapes]};c=resolve_catalog(shapes,ac);export_catalog(shapes,c,out)
   self.assertTrue(hasattr(vis,'render_parts_catalog'),'automatic part catalog missing')
   r=vis.render_parts_catalog(root,shapes,c);self.assertEqual(r['part_ids'],['printed']);self.assertTrue((out/'parts/printed.png').is_file());self.assertTrue((out/'parts/index.html').is_file())
   m,_=vis.render_views(root,shapes,assembly_config=ac,view='presentation');self.assertEqual(m['component_colors']['printed'],'#235588')
if __name__=='__main__':unittest.main()
