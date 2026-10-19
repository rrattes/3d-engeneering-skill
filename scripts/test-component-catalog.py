#!/usr/bin/env python3
import contextlib,io,json,os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
import cad3d,yaml
from build123d import import_step
class Catalog(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);old=Path.cwd();os.chdir(self.tmp.name);self.addCleanup(os.chdir,old)
  Path('.cad3d').mkdir();Path('model.py').write_text('from build123d import Box\ndef build(params):return {"support":Box(10,10,3),"fan":Box(8,8,4)}\n')
  Path('.cad3d/project.yaml').write_text(yaml.safe_dump({'project':{'name':'mixed','model':'model.py','parameters':'params.yaml'}}));Path('.cad3d/params.yaml').write_text('{}')
  self.ac={'parts':{'support':{'kind':'manufactured','process':'fdm','material':'pla','color':'#123456'},'fan':{'kind':'commercial','process':'none','material':'commercial'}},'components':[{'id':'s1','part':'support','position_mm':[0,0,0]},{'id':'s2','part':'support','position_mm':[20,0,0]},{'id':'f','part':'fan','position_mm':[40,0,0]}]};self.save()
 def save(self):Path('.cad3d/assembly.yaml').write_text(yaml.safe_dump(self.ac))
 def call(self,fn):
  with contextlib.redirect_stdout(io.StringIO()):fn(None)
 def test_build_skips_commercial_stl(self):
  self.call(cad3d.build);self.assertTrue(Path('build/outputs/support.stl').is_file());self.assertFalse(Path('build/outputs/fan.stl').exists())
 def test_repeated_instance_has_one_part_and_two_bom_quantity(self):
  self.call(cad3d.export);rows=json.loads(Path('build/outputs/part-index.json').read_text());self.assertEqual(next(x for x in rows if x['id']=='support')['quantity'],2)
  s=import_step('build/outputs/assembly.step');self.assertEqual(len(s.solids()),3)
  centers=sorted(round(body.center().X,5) for body in s.solids());self.assertEqual(centers,[0,20,40])
 def test_unknown_process_rejected(self):
  self.ac['parts']['fan']['process']='fake';self.save()
  with self.assertRaises(ValueError):self.call(cad3d.build)
 def test_unknown_part_rejected(self):
  self.ac['components'][0]['part']='missing';self.save()
  with self.assertRaises(ValueError):self.call(cad3d.build)
if __name__=='__main__':unittest.main()
