#!/usr/bin/env python3
import hashlib,json,sys,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cli'))
import cad3d
from source_fingerprint import project_fingerprint
class Publication(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);(self.root/'.cad3d').mkdir()
  (self.root/'.cad3d/project.yaml').write_text('project: {name: test, model: model.py, parameters: params.yaml, output: build/outputs}\n');(self.root/'.cad3d/params.yaml').write_text('{}');(self.root/'model.py').write_text('# fixture')
  self.inputs=project_fingerprint(self.root)
 def stage(self,name,content='part'):
  p=self.root/'build/runs'/name;p.mkdir(parents=True);(p/'part.step').write_text(content)
  from build123d import Box
  from component_catalog import resolve_catalog,export_catalog
  shapes={'part':Box(2,2,2)};catalog=resolve_catalog(shapes,{})
  export_catalog(shapes,catalog,p)
  (p/'validation.json').write_text(json.dumps({'status':'PASS','states':{'geometric_validity':'PASS','assembly_validity':'PASS','manufacturing_assessment':'WARNING'}}))
  files=[{'path':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in p.iterdir()]
  (p/'manifest.json').write_text(json.dumps({'project_inputs':self.inputs,'artifacts':files}));return p
 def rehash(self,p):
  manifest=json.loads((p/'manifest.json').read_text());manifest['artifacts']=[{'path':f.relative_to(p).as_posix(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in p.rglob('*') if f.is_file() and f.name!='manifest.json'];(p/'manifest.json').write_text(json.dumps(manifest))
 def test_unknown_service_cannot_publish(self):
  p=self.stage('unknown');r=json.loads((p/'validation.json').read_text());r['assembly']={'assembly_sequence':{'status':'NOT_EVALUATED','steps':[{'id':'lift','status':'NOT_EVALUATED'}]}};(p/'validation.json').write_text(json.dumps(r));self.rehash(p)
  with self.assertRaises(ValueError):self.publish(p)
 def test_manifest_without_export_evidence_cannot_publish(self):
  p=self.stage('noexport');(p/'export-validation.json').unlink();self.rehash(p)
  with self.assertRaises(ValueError):self.publish(p)
 def publish(self,p):
  if not hasattr(cad3d,'release'):self.fail('release pipeline is not implemented')
  from artifact_publication import publish_run
  return publish_run(self.root,p,self.inputs)
 def test_success_and_obsolete_files_not_mixed(self):
  a=self.publish(self.stage('one','old'));b=self.publish(self.stage('two','new'))
  self.assertNotEqual(a['run_id'],b['run_id']);pointer=json.loads((self.root/'build/delivery/current.json').read_text());self.assertEqual(pointer['run_id'],'two')
  self.assertTrue((self.root/pointer['directory']/'part.step').read_text().startswith('ISO-10303'))
 def test_corrupt_late_export_keeps_previous_pointer(self):
  self.publish(self.stage('one'));previous=(self.root/'build/delivery/current.json').read_bytes();p=self.stage('bad');(p/'part.step').write_text('corrupt')
  with self.assertRaises(ValueError):self.publish(p)
  self.assertEqual((self.root/'build/delivery/current.json').read_bytes(),previous)
 def test_interrupted_pointer_swap_preserves_previous_delivery(self):
  import artifact_publication
  self.publish(self.stage('prior'));previous=(self.root/'build/delivery/current.json').read_bytes();pending=self.stage('interrupted')
  original=artifact_publication.os.replace
  def interrupted(source,destination):
   if Path(destination).name=='current.json':raise KeyboardInterrupt('synthetic interruption before pointer swap')
   return original(source,destination)
  with patch('artifact_publication.os.replace',side_effect=interrupted):
   with self.assertRaises(KeyboardInterrupt):self.publish(pending)
  self.assertEqual((self.root/'build/delivery/current.json').read_bytes(),previous)
  self.assertFalse(list((self.root/'build/delivery').glob('.current-*.tmp')))
 def test_source_changed_rejects(self):
  p=self.stage('changed');(self.root/'model.py').write_text('# changed')
  with self.assertRaises(ValueError):self.publish(p)
 def test_manufacturing_fail_rejects(self):
  p=self.stage('thin');r=json.loads((p/'validation.json').read_text());r['states']['manufacturing_assessment']='FAIL';(p/'validation.json').write_text(json.dumps(r));self.rehash(p)
  with self.assertRaises(ValueError):self.publish(p)
 def test_concurrent_publications_are_complete(self):
  paths=[self.stage('r'+str(i),str(i)) for i in range(3)]
  with ThreadPoolExecutor(3) as ex:results=list(ex.map(self.publish,paths))
  self.assertEqual(len(results),3);d=json.loads((self.root/'build/delivery/current.json').read_text());self.assertTrue((self.root/d['directory']/'manifest.json').exists())
if __name__=='__main__':unittest.main()
