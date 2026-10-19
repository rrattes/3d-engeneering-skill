#!/usr/bin/env python3
"""Package an explicit portable source inventory, never arbitrary workspace contents."""
from pathlib import Path
import argparse,hashlib,json,shutil,stat,zipfile
ROOT=Path(__file__).resolve().parents[1]
def package_kit(destination:Path)->Path:
    destination=Path(destination)
    if destination.exists() and any(destination.iterdir()):raise FileExistsError('destination must be empty/new')
    kit=destination/'CAD3D_Kit';kit.mkdir(parents=True)
    trees=['cli','profiles','templates','skills/3d-engineering','licenses','scripts','examples/product-engineering','examples/evolution','examples/assembly-demo','examples/calibration-box']
    files=['Dockerfile','Dockerfile.orca','Dockerfile.patch','compose.yaml','compose.dev.yaml','requirements/requirements.lock','docs/INSTALL.md']
    for tree in trees:
        source=ROOT/tree
        if not source.is_dir():continue
        for path in source.rglob('*'):
            if path.is_symlink():raise ValueError('package inventory must not contain symlinks')
            if not path.is_file() or any(p in ('__pycache__','.pytest_cache','build','outputs','.git') for p in path.relative_to(source).parts) or path.suffix in ('.pyc','.pyo'):continue
            target=kit/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    for name in files:
        source=ROOT/name;target=kit/name
        if not source.is_file():raise FileNotFoundError(name)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for host in ('.agents','.claude'):
        target=kit/host/'skills/3d-engineering';target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(kit/'skills/3d-engineering',target)
    common='''# CAD3D local engineering workflow
Read docs/INSTALL.md and skills/3d-engineering/SKILL.md before design work. The current user brief defines this product. Use ./scripts/cad3d through its resolved path, or add scripts to session PATH. All CAD runs in Docker; never install CAD packages on host by default. Keep independent products in separate folders. Do not reuse dimensions/material/printer from examples. Separate geometry, assembly, manufacture, slicing and physical validation. Do not send files to a printer. New templates include mandatory dependency gates; migrate existing projects with `cad3d workflow init`. Advance only when `cad3d workflow check --gate <gate>` returns PASS in the documented order. Capture only evidence actually observed; no database required. Ordinary authorized work should proceed without repeated confirmations.
'''
    (kit/'AGENTS.md').write_text(common);(kit/'CLAUDE.md').write_text('Read AGENTS.md and docs/INSTALL.md.\n'+common)
    (kit/'README.md').write_text('# CAD3D Kit\n\nStart with [installation](docs/INSTALL.md). Runtime1.9.0; Linuxx86_64 first target. Source kit contains no image archive, credentials or private product history.\n')
    manifest={'schema':'cad3d-kit-inventory-v1','files':[],'agent_discovery':'NOT_EVALUATED unless separately evidenced','physical_validation':'NOT_EVALUATED'}
    for path in sorted(kit.rglob('*')):
        if path.is_file():manifest['files'].append({'path':path.relative_to(kit).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (kit/'FILE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=destination/'CAD3D_Kit.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(kit.rglob('*')):
            if path.is_file():z.write(path,path.relative_to(destination))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise ValueError('corrupt archive')
        for row in manifest['files']:
            if hashlib.sha256(z.read('CAD3D_Kit/'+row['path'])).hexdigest()!=row['sha256']:raise ValueError('archive hash mismatch')
    return archive
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(package_kit(a.output))
