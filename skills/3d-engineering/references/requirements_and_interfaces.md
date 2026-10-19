# Requirements and interfaces

Create the contract with `cad3d architecture init --level product` inside an initialized project, then edit `.cad3d/engineering.yaml`. Stable IDs connect requirements, subsystems, components, interfaces, dependencies, verification method, evidence and status. Evidence uses a project-relative JSON file and JSON Pointer; the validator reads it and fingerprints its value. A claimed implementation is not verification. PASS needs current, identifiable evidence; unknown evidence is NOT_EVALUATED.

Record measurement provenance and label every dimension `verified` or `assumption`. Never silently promote assumptions. Interfaces state participants, reference geometry, datum, intended relation, fit class and selected printer/material/calibration tolerance. Report unavailable geometry checks as NOT_EVALUATED. Use physical validation status separately.

For each acceptance criterion state the checked object/revision, method, bounds and
evidence needed to close it. Hardware fit, tool access, retention, service independence
and tolerance margin are different criteria when relevant. Record supplemental
calculations/reviews as project artifacts and link their results through existing evidence
fields; adding prose or unsupported manifest keys does not create an automated check.
After any model, parameter, imported geometry, profile or evidence change, regenerate
affected results before relying on previous PASS. Inspect actual source dependencies
instead of assuming the adapter model alone determines the product.

Build manifests inventory local `.py`, `.json`, `.yaml`, `.yml`, `.toml`, `.ini`
and `.cfg` files, including `.cad3d/project.yaml`, imported local Python modules
and root `parameters.json`. Review compares the current inventory with the build
manifest and checks the validation artifact hash. Changed, added and deleted
inventoried files invalidate freshness. Old manifests without this inventory are
NOT_EVALUATED; regenerate affected results and a manifest before claiming freshness.

Declare other local inputs in `.cad3d/project.yaml`, for example imported STEP
references or measurements used by the model:

```yaml
project:
  name: example
  model: src/model.py
  source_inputs:
    - references/vendor-envelope.step
    - measurements/interface.csv
```

`source_inputs` accepts exact project-relative files, not globs or directories.
Absolute paths, `..` escapes, symlinks on declared paths and declarations inside
excluded paths are rejected. Inventory excludes the configured output directory,
`build`, `dist`, `reports`, `renders`, `exports`, `artifacts`, caches,
`node_modules`, `venv`, `env` and hidden paths except `.cad3d`. Keep authoritative
inputs outside these generated directories. Bounds are 50,000 scanned entries,
10,000 input files, depth 20 and 32 MiB total input bytes; exceeding them prevents
a freshness claim. The scan is conservative: changing an unused local source or
configuration file can also invalidate freshness. Other formats require explicit
declarations. External modules/files, environment values and runtime state are
outside this source fingerprint; it does not prove reproducibility or physical
validity.

In product workflows the initial architecture gate runs before every CLI model
load, including export, render, validate, report, review and architecture validation
with geometry. `model_gate: false` does not disable it. Architecture validation
without geometry and contract-only review remain available to diagnose blockers.
This gate checks requirements and architecture readiness; physical validation
remains a separate requirement for release.

## Part catalog and fabrication selection

`build(params)` continues to return `{part_name: Shape}`. Optional `.cad3d/assembly.yaml` `parts` is a map keyed by those part names. Fields: `kind` (`manufactured`, `commercial`, `hardware`), `process` (`fdm`, `machined`, `none`), `material`, `color` (#RRGGBB), `export_formats` and `print_rotation_deg`. Commercial/hardware process is `none`; manufactured uses `fdm`/`machined`. STEP is required for roundtrip evidence; STL is permitted only for FDM. Explicit FDM STL is rotated and normalized to bed origin; STEP retains assembly coordinates.

`components` remain placed instances with unique `id` and `part` reference. Quantities come from instances; repeated instances do not create duplicate fabrication files. All modeled parts remain in assembly checks even if not printed. `part-index.json`, `BOM.csv` and `assembly.step` are generated from the same catalog. Missing metadata preserves legacy FDM behavior with a warning, not physical approval. Do not classify components by filename prefixes.
