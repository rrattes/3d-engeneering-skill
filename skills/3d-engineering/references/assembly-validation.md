# Assembly validation contract

`.cad3d/assembly.yaml` is optional for V1 projects. When present, `cad3d build` runs it as part of the validation gate; `cad3d validate --assembly PATH` selects an alternate assembly manifest. IDs are unique persistent component identifiers, `part` references a key returned by `build(params)`, translations use mm, and rotations use XYZ degrees. The documented pose field is `position_mm`; `translation_mm` is accepted as an alias for agents/configurations using that name. If both are present they must agree. Interface endpoints reference component IDs.

Example interface:

```yaml
interfaces:
  - id: guide-001
    a: bracket-001
    b: slider-001
    type: sliding
    clearance_mm: 0.30
    intentional_contact: false
```

The pair analysis uses AABBs as a broad phase and OCP B-rep common volume plus `BRepExtrema_DistShapeShape` distance for overlapping bounds. A positive intersection volume is always `FAIL`. Zero-volume contact is accepted only when `intentional_contact: true` and no positive minimum clearance is required. Unintentional contact is `FAIL`. A separated pair can still fail its minimum-clearance requirement. The measured distance is the global minimum for the component pair; it is not limited to selected mating surfaces, so report an interface as geometrically validated only when that approximation matches the design intent.

`fit_ranges_mm` in a material profile are uncalibrated nominal bands. Add `male_size_mm` and `female_size_mm` to check `female - male` against a fit band. This declared-dimension check supplements the placed B-rep collision check; it is not a pressure/contact solver. If required nominal fit dimensions are absent, the fit check is `NOT_EVALUATED`.

Assembly retention has a separate product-level review contract. A positioned component without a declared retention method fails; captured joints and fastener/snap interfaces remain warnings until their strength/load path is verified. See [mechanical_assemblies.md](mechanical_assemblies.md).

Geometric wall thickness is sampled in selected normal directions on the B-rep. The result is sampled and non-exhaustive; it is not a guaranteed global minimum. A component can declare local nominal wall checks:

```yaml
wall_checks:
  - id: cover-wall
    nominal_mm: 1.6
    minimum_mm: 1.2
```

This compares declared parameters only. It does not sample the B-rep or establish a geometrically measured minimum thickness. General wall thickness, force, fatigue, deflection, kinematics, physical fit, and print success remain outside this implementation.

Per-part reports include the local B-rep dimensions, orthogonal orientation envelope candidates, STL connected-component count and a downward-face support heuristic. The support heuristic ignores the bottom layer and reports a rough area; it does not model slicer support generation, bridging, anisotropy, or process settings. Treat it as a review warning, never as a printability guarantee.

## Functional face references and local clearance

An interface may add selectors instead of relying only on global component distance:

```yaml
interfaces:
  - id: sliding-guide-001
    a: bracket-001
    b: slider-001
    type: sliding
    clearance_mm: 0.25
    tolerance_mm: 0.05
    face_a:
      ref: bracket-guide-inner
      surface: plane
      center_mm: [10, 0, 0]
      normal: [1, 0, 0]
      center_tolerance_mm: 0.10
    face_b:
      ref: slider-guide-side
      surface: plane
      center_mm: [10.25, 0, 0]
      normal: [-1, 0, 0]
      center_tolerance_mm: 0.10
```

`ref` is a stable design-intent label; the geometric constraints select a face without relying on changing face ordinals. For opposed planar faces, validation uses signed projection and reports a negative value as interference. Cylindrical/unsupported pairs use unsigned face distance and are explicitly labeled as such; use `male_size_mm`/`female_size_mm` plus the selected material profile's dimensional fit range for pin/hole or press-fit checks. Full-solid collision analysis always remains independent and can fail even when nominal fit dimensions pass.

## Sampled insertion/removal

```yaml
assembly_steps:
  - id: slider-insertion
    moving_component: slider-001
    direction_mm: [0, 0, 1]
    travel_mm: 18
    samples: 24
```

The direction points from the declared start toward the final pose already present in `components`; the validator checks the reverse trajectory from final pose to start, so it works for both insertion and removal path specifications when the correct vector is declared. CAD3D samples `samples + 1` translations, including both endpoints, against other components. A sampled intersection/contact is a blockage. Empty trajectories or malformed vectors are `NOT_EVALUATED`; passing samples do not prove collision-free motion between samples or ergonomic assembly.

## Helical service paths (CAD3D 1.6.0+)

Explicit `moving_ids` steps may set `motion.type: helical` for coupled rotation and
translation. See [contract, example and limits](helical_motion.md). Linear steps keep
their previous behavior when `motion` is absent. Unknown motion types are rejected.

## Reliability extensions (1.7.0+)

[Shared BREP checks, point anchors and bounded tolerance chains](reliability.md)
extend the existing contract; centroid selection and linear paths remain supported.
