# Manufacturing intelligence reference

## Local wall thickness

`cad3d validate` reports `geometric_thickness` per part. The current OCP algorithm samples points inside each trimmed B-rep face, computes the oriented surface normal, casts a ray into the solid with `IntCurvesFace_ShapeIntersector`, and records the first later B-rep face hit. The measured value is a local normal chord, not the declared nominal parameter and not the all-direction medial-axis minimum. Report coverage is `sampled_not_complete`; narrow features between sample points may be missed. A sub-limit sample is `FAIL`; unresolved samples are `NOT_EVALUATED` and a partly covered face cannot be called a pass. Adjust `.cad3d/printer.yaml` `min_wall_mm` and `thickness_samples_per_axis`, or put `thickness_regions` selectors by part under `.cad3d/params.yaml` to focus sampling on semantically chosen faces. Selector fields are `ref`, `surface`, `center_mm`, `normal`, and geometric tolerances. Face ordinals are ephemeral report diagnostics only.

## Print orientation report

`orientation_assessment` compares six orthogonal candidates. It reports useful envelope, approximate triangulated bed-contact area, STL downward-face area heuristic, configured functional axes relative to build Z, and an optional mass estimate only when both density and infill fraction were explicitly configured. Ranking is a heuristic; it makes no strength prediction and does not replace slicing or test prints. The top-level print fit remains separate from recommendation.

Configure optional project assumptions in `.cad3d/printer.yaml`:

```yaml
min_wall_mm: 1.2
thickness_samples_per_axis: 3
infill_fraction: 0.2
process_settings_sha256: <sha256-of-explicit-process-profile>
```

The wall and process values are project decisions, not universal defaults. Use known material/printer profiles and update only from measured evidence.

## OrcaSlicer (optional host integration)

The slicer is not installed in or required by the CAD container. `cad3d slice` reads `.cad3d/slicer.json`, needs an installed host `orca-slicer` executable and three exported JSON presets:

```json
{
  "executable": "orca-slicer",
  "model": "build/outputs/calibration_block.stl",
  "profiles": {
    "machine": "/path/to/exported-machine.json",
    "process": "/path/to/exported-process.json",
    "filament": "/path/to/exported-filament.json"
  }
}
```

Each preset must be a JSON object with a non-empty `name`; a supplied `type` must match its role. Sliced 3MF and `slice-report.json` go to `build/slicer/`, separate from CAD outputs. Missing executable/configuration is `NOT_EVALUATED`; process errors are `FAIL`. The bridge never sends output to a printer and does not emit G-code. See [OrcaSlicer CLI mode](https://github.com/OrcaSlicer/OrcaSlicer/wiki/cli_mode) and [CLI actions](https://github.com/OrcaSlicer/OrcaSlicer/wiki/cli_actions).

## Calibration coupons and records

Run `cad3d calibration generate` to write STEP/STL witnesses and `calibration-coupons.json` under `build/calibration-coupons/`. Values in the coupon manifest are design labels, not learned tolerances. After a physical print, submit a JSON record containing `identity` (`printer`, `nozzle_diameter_mm`, `material`, `process_settings_sha256`), `measurements`, `measured_at`, and `method`:

```sh
cad3d calibration record measurements.json
```

Records append under `profiles/calibrations/`; existing files are never overwritten. An unconfirmed record has status `RECORDED_UNCONFIRMED` and does not affect validation. Set `confirmed_physical_measurements: true` and point `evidence` to an existing measurement evidence file to mark it calibrated. To use it, explicitly set `calibration_profile` in `.cad3d/printer.yaml`; validation only applies its fit ranges if printer, nozzle, material and process SHA-256 all match. No other project is rewritten.

Selective thickness configuration example:

```yaml
thickness_regions:
  bracket:
    - ref: guide-wall-inner
      surface: plane
      center_mm: [10, 0, 4]
      normal: [-1, 0, 0]
      center_tolerance_mm: 0.2
```

A missing or ambiguous selector is reported `NOT_EVALUATED`; it is not silently replaced by a whole-part pass.
