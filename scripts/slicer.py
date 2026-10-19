#!/usr/bin/env python3
"""V1.2 compatibility notice: slicing moved from host to isolated cad3d-orca Docker engine."""
import json
import sys
from pathlib import Path

report_dir = Path.cwd() / "build/slicer"
report_dir.mkdir(parents=True, exist_ok=True)
report = {
    "status": "NOT_EVALUATED",
    "reason": "host_slicer_bridge_retired_in_v1_3",
    "detail": "Use the isolated engine: cad3d slicer doctor; cad3d slice --printer elegoo-cc2 --material petg --model <project STL/3MF>",
    "host_slicer_execution": False,
    "printer_communication": "NOT_PERFORMED",
}
(report_dir / "slice-report.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
sys.exit(4)
