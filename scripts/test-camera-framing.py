#!/usr/bin/env python3
import itertools,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
import pyvista as pv
import numpy as np
from cad3d_visualization import _camera,_bounds
class Framing(unittest.TestCase):
 def test_isometric_model_stays_inside_its_legend_viewport(self):
  mesh=pv.Box(bounds=(0,83,0,83,0,3))
  pl=pv.Plotter(off_screen=True,window_size=(1600,1200),shape=(1,2))
  self.addCleanup(pl.close);pl.renderers[0].viewport=(0,0,.72,1);pl.renderers[1].viewport=(.72,0,1,1);pl.subplot(0,0);pl.add_mesh(mesh)
  low,high,center,half=_bounds([mesh]);_camera(pl,'iso',center,half);pl.render()
  renderer=pl.renderer
  for point in itertools.product(*zip(low,high)):
   renderer.SetWorldPoint(*point,1);renderer.WorldToDisplay();x,y,_=renderer.GetDisplayPoint()
   self.assertGreaterEqual(x,10);self.assertLessEqual(x,1142)
   self.assertGreaterEqual(y,10);self.assertLessEqual(y,1190)
if __name__=='__main__':unittest.main()
