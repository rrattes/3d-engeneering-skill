import sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from model import build


def test_configured_parts_are_valid_nonzero_breps():
    p=yaml.safe_load(Path('.cad3d/params.yaml').read_text())
    parts=build(p)
    assert isinstance(parts,dict) and parts
    for name,shape in parts.items():
        assert isinstance(name,str) and name.strip()
        assert shape.is_valid and shape.volume>0
        bounds=shape.bounding_box()
        assert min(bounds.size.X,bounds.size.Y,bounds.size.Z)>0
