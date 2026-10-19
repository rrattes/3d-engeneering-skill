#!/usr/bin/env python3
import hashlib,importlib.util,json,sys,tempfile,unittest,zipfile
from pathlib import Path
class Kit(unittest.TestCase):
 def test_portable_archive_projections_and_inventory(self):
  root=Path(__file__).resolve().parents[1];script=root/'scripts/package-kit.py';self.assertTrue(script.is_file(),'portable packager is missing')
  spec=importlib.util.spec_from_file_location('packager',script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory(prefix='cad kit with spaces ') as d:
   archive=m.package_kit(Path(d)/'delivery');self.assertTrue(archive.is_file())
   with zipfile.ZipFile(archive) as z:
    self.assertIsNone(z.testzip());names=z.namelist();self.assertFalse(any('/.git/' in n or n.endswith('/.env') or 'preserved-projects' in n for n in names))
    a=z.read('CAD3D_Kit/.agents/skills/3d-engineering/SKILL.md');b=z.read('CAD3D_Kit/.claude/skills/3d-engineering/SKILL.md');self.assertEqual(a,b)
    self.assertNotIn(b'/home/rrattes',z.read('CAD3D_Kit/docs/INSTALL.md'))
    manifest=json.loads(z.read('CAD3D_Kit/FILE_MANIFEST.json'))
    for row in manifest['files']:self.assertEqual(hashlib.sha256(z.read('CAD3D_Kit/'+row['path'])).hexdigest(),row['sha256'])
    z.extractall(Path(d)/'new location')
    self.assertTrue((Path(d)/'new location/CAD3D_Kit/cli/component_catalog.py').is_file())
if __name__=='__main__':unittest.main()
