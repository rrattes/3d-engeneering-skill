import sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from model import build


def test_calibration_box_geometry():
    p=yaml.safe_load(Path('.cad3d/params.yaml').read_text())
    parts=build(p)
    assert set(parts)=={'body','lid'}
    assert all(s.is_valid and s.volume>0 for s in parts.values())
