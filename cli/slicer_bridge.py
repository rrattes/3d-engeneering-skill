"""Import-safe V1.2 compatibility entry for the retired in-process slicer bridge.

Actual slicing remains isolated in the separately versioned cad3d-orca image.
This module deliberately does not try to run that engine or fabricate results.
"""
from __future__ import annotations

import json
from pathlib import Path


def run_slice(project_root=".", *_args, **_kwargs):
    root = Path(project_root).resolve()
    output = root / "build/slicer/slice-report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "NOT_EVALUATED",
        "reason": "explicit_slicer_profile_missing",
        "detail": "Host-side slicer bridge retired in V1.3; use cad3d-orca with explicit printer, material and process profiles.",
        "host_slicer_execution": False,
        "printer_communication": "NOT_PERFORMED",
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    return 4, report
