#!/usr/bin/env python3
"""Display the current slicer JSON report without contacting Docker or a printer."""
import json
import sys
from pathlib import Path

report = Path.cwd() / "build/slicer/slice-report.json"
if not report.is_file():
    print(json.dumps({"status": "NOT_EVALUATED", "reason": "report_missing", "expected": str(report)}, indent=2))
    sys.exit(4)
print(report.read_text())
