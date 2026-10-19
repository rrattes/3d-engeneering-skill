# Requirements and interfaces

Edit the extensible YAML contract at `.cad3d/engineering.yaml`. `cad3d architecture init --level product` creates the scaffold; it does not generate a complete schema example. The validator expects maps/lists with the shapes below; plain strings inside these record lists can raise errors.

```yaml
engineering:
  schema_version: 1
  workflow_level: product
  model_gate: true
  project: {name: example, class: mechanical_product, purpose: "...", units: mm}
  operating_conditions: [{id: USE-1, condition: "..."}]
  measurements: [{id: ENV-1, confidence: verified, source: user, value_mm: [100, 80, 50]}]
  external_interfaces: [{id: EXT-1, type: mounting, description: "..."}]
  acceptance_criteria: [{id: AC-1, method: bounding_box, threshold: "within specified envelope"}]
  risks_and_unknowns: [{id: U-1, description: "...", status: NOT_EVALUATED, resolution: "..."}]
  requirements:
    - id: REQ-1
      description: "..."
      subsystem: inlet
      components: [base, insert]
      verification: {method: assembly_removal_path, status: NOT_EVALUATED}
  functional_architecture:
    subsystems:
      - {id: inlet, purpose: "...", components: [base]}
      - {id: outlet, purpose: "...", components: [insert]}
    flows: [{id: FLOW-1, path: [inlet, outlet], medium: object, status: NOT_EVALUATED}]
    operating_modes: [{id: normal, description: "..."}]
    failure_modes: [{id: F-1, description: "...", detection: "..."}]
  mechanical_architecture:
    components:
      - {id: base, part: base, function: "...", retention: {method: monolithic}}
      - {id: insert, part: insert, function: "...", retention: {method: captured_rail, interface_ids: [I-1]}}
    interfaces: [{id: I-1, components: [base, insert], kind: rail, datums: [base_top], tolerance_profile: calibrated_fit}]
    assembly_steps: [{id: A-1, action: "..."}]
    maintenance_access: [{id: M-1, action: "..."}]
    print_split: [{part: base, reason: "..."}]
```

Before geometry, define the planned component IDs and create `.cad3d/assembly.yaml` containing an instance for every planned part and a corresponding pair entry for each two-part interface. Requirement component IDs must match `mechanical_architecture.components`; subsystem `purpose`, flow `path`, interface participant pairs, datum/tolerance, and supported retention methods must match actual validator expectations. `assembly.yaml` interface pairs use `a`/`b`; engineering interface records use `components: [a, b]`.

Run `cad3d architecture validate`. A PASS in the first three phase checks permits modeling; WARNING is reviewable but is not evidence of physical function. If the command reports malformed records or FAIL, fix the contract and rerun it before editing functional geometry. Do not downgrade a structural/flow product to lightweight to evade a gate.

Stable IDs connect requirements, subsystems, components, interfaces, dependencies, verification method, evidence and status. Evidence uses a project-relative JSON file and JSON Pointer; the validator reads it and fingerprints its value. A claimed implementation is not verification. PASS needs current, identifiable evidence; unknown evidence is NOT_EVALUATED.

Record measurement provenance and label every dimension `verified` or `assumption`. Never silently promote assumptions. Interfaces state participants, reference geometry, datum, intended relation, fit class and selected printer/material/calibration tolerance. Report unavailable geometry checks as NOT_EVALUATED. Use physical validation status separately.
# FDM and DFAM

Use declared printer, nozzle, material and process profiles. Treat uncalibrated values as starting estimates, never universal tolerances. Check per-axis build envelope for candidate orientations, wall features, disconnected bodies, overhang/support heuristics, interface orientation relative to layers and slicer estimates. These are assessments, not print guarantees. Choose orientation with explicit tradeoffs; fastest is not necessarily strongest.

Use calibration specimens for clearance, pins/holes, walls, sliding fits, bridges and overhangs. Record measured results against exact printer/nozzle/material/process profile revision. Do not silently propagate a calibration to old project contracts. After printing, record dimensions and physical fit results separately.
