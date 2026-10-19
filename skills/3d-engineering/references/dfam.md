# FDM and DFAM

Use declared printer, nozzle, material and process profiles. Treat uncalibrated values as starting estimates, never universal tolerances. Check per-axis build envelope for candidate orientations, wall features, disconnected bodies, overhang/support heuristics, interface orientation relative to layers and slicer estimates. These are assessments, not print guarantees. Choose orientation with explicit tradeoffs; fastest is not necessarily strongest.

Use calibration specimens for clearance, pins/holes, walls, sliding fits, bridges and overhangs. Record measured results against exact printer/nozzle/material/process profile revision. Do not silently propagate a calibration to old project contracts. After printing, record dimensions and physical fit results separately.

Establish slicer availability before detailed manufacturing work when slicing is in
scope: `cad3d slicer preflight --printer elegoo-cc2 --material <requested> --process standard-0.20`
for that applicable printer/process, or use the requested profiles. Read the actual
preflight findings; a registered material profile alone does not prove a usable slicer
combination. Resolve missing presets explicitly and preserve unavailable slicing as
NOT_EVALUATED. Do not replace a requested material with a different preset silently.
Preflight is configuration evidence, not slicing success or printer compatibility.
Apply measured dimensional capability to the signed tolerance stack in
[mechanical_assemblies.md](mechanical_assemblies.md), including fit orientation and
support-removal access. Keep build-envelope assessment, fabrication judgment, actual
slicer results and physical inspection as separate claims.
