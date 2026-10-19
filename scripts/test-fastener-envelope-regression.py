#!/usr/bin/env python3
"""Regression fixtures for head and driver access, using candidate OCP checks.

Run inside the existing CAD image; imports cli/validation.py from this checkout.
These synthetic dimensions are fixtures, not a fastener standard or product design.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cli"))
from build123d import Align, Box, Cylinder, Pos
from validation import pair_check


def run():
    # Datum z=0, screw shank ends at z=8 and head occupies z=8..11.
    shank = Cylinder(1.5, 8, align=(Align.CENTER, Align.CENTER, Align.MIN))
    head = Pos(0, 0, 8) * Cylinder(3, 3, align=(Align.CENTER, Align.CENTER, Align.MIN))
    driver_approach = Pos(0, 0, 11) * Cylinder(4, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # Rib clears the shank but invades the larger head.
    head_rib = Pos(3, 0, 9.5) * Box(2, 2, 3)
    # Upper rib clears actual installed hardware but obstructs its driver.
    tool_rib = Pos(4.5, 0, 21) * Box(2, 2, 6)
    clear_rib = Pos(7, 0, 21) * Box(2, 2, 6)
    fixtures = [
        ("shank_only_misses_blocked_head", shank, head_rib, "PASS"),
        ("head_hits_rib", head, head_rib, "FAIL"),
        ("installed_head_clear_but_tool_blocked", head, tool_rib, "PASS"),
        ("driver_approach_hits_upper_rib", driver_approach, tool_rib, "FAIL"),
        ("head_clear_control", head, clear_rib, "PASS"),
        ("driver_approach_clear_control", driver_approach, clear_rib, "PASS"),
    ]
    results = []
    for ident, envelope, obstacle, expected in fixtures:
        result = pair_check(envelope, obstacle, pair_id=ident)
        results.append({"id": ident, "expected": expected, "result": result})
        assert result["status"] == expected, (ident, result)
        if expected == "FAIL":
            assert result["intersection_volume_mm3"] > 0, (ident, result)
    print(json.dumps({
        "regression_status": "PASS",
        "candidate_validation_module": str(Path(sys.modules["validation"].__file__).resolve()),
        "checks": results,
        "scope": "Static fixture head and straight cylindrical driver keep-out B-rep collisions only; no torque, hand access, load, retention, tolerance or physical validation.",
    }, indent=2))


if __name__ == "__main__":
    run()
