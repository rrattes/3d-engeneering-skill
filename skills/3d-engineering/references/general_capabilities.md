# Reusable engineering capabilities — CAD3D 1.8.0+

Use only the relevant sections. These are explicit, bounded engineering tools,
not automatic certification, a general mechanism solver or a printer controller.

## Interface library

`from interface_library import generate_interface` returns `(shapes, report)`.
Every dimension is caller-supplied; select an interface from current function and
load/retention requirements. Do not inherit another product's dimensions/material.

`cad3d interfaces --config interface.json --material PETG` exports real individual
STEP/STL, assembly STEP, BOM and report to a fresh build/interfaces run. It does not
claim print-profile compatibility. Specifications:

- `type: thread_pair`: major_diameter_mm, pitch_mm, length_mm, thread_depth_mm,
  radial_clearance_mm, wall_mm, handedness right|left. Actual custom single-start
  helical geometry,1..64 turns; not ISO threads. Root/crest and flank allowances
  are not uniform normal clearance. Add heads/seats/retention for the actual use.
- `type: pin_hinge`: pin_diameter_mm, barrel_outer_diameter_mm, length_mm,
  leaf_width_mm, leaf_thickness_mm, radial_clearance_mm, axial_clearance_mm.
  Three knuckles and a plain pin; pin head/clip/end retention is not provided.
- `type: sliding_rail`: length_mm, width_mm, height_mm, wall_mm, clearance_mm.
  T rail and carriage, open along Y, without end stops.

Reports separate solid validity from nominal interference and physical fit.
Inspect printed orientation, clearance, retention, walls and actual service motion
before integrating any template into a product. Template generation alone is not
an assembly/load/print approval.

## Rotation and composite service paths

Explicit assembly_steps with moving_ids support rotation, translation and composite
motions in addition to the existing linear/helical contracts:

```yaml
assembly_steps:
  - id: lift-then-turn
    moving_ids: [lid]
    removed_ids: []
    motion:
      type: composite
      segments:
        - {type: translation, vector_mm: [0, 0, 15], samples: 12}
        - type: rotation
          axis_origin_mm: [0, 0, 15]
          axis_direction: [0, 1, 0]
          angle_deg: 90
          samples: 12
```

Segments apply cumulatively to the previous segment's terminal pose. Axes/origins
are world coordinates and are not automatically transported with the group. A
segment may also use the helical contract. One operation moves a rigid group;
internal group interference belongs to the static assembly check. Original
moving::retained contact permissions remain narrow. Positive volume always fails.

Rotations sample at most45° intervals; helices at most90°. Max32 segments and4096
intervals total; endpoints included. Reports include sampled poses and terminal
centres. Terminal bounds separation is additionally needed to prove removal for
prerequisites. A rotated but still attached lid is not automatically removed.

This is not a planner that preserves arbitrary held-open poses across separate
service operations. Separate steps retain the original installed basis plus
proven removals. Represent a continuous compound operation explicitly; do not
claim a later operation was checked with an earlier lid held open unless modeled
in that operation's obstacle geometry. No continuous-motion/force proof.

## Variant campaigns

`cad3d variants --config .cad3d/variants.yaml` runs actual native CAD build and
validation in an isolated project copy for each Cartesian combination:

```yaml
axes:
  basket.width: [100, 110]
  mount.glass_thickness: [4, 5]
max_cases: 8
timeout_seconds: 180
```

Parameter paths must already exist. Default32 cases, max64; inputs limited to10000
files/256MiB and cannot follow symlinks; each case timeout1..3600seconds. Native
solid/mesh, assembly, manufacturing and declared service checks run; this is not
only parameter arithmetic. Results/parameters/logs/artifacts go to unique
build/variants runs. Originals and selected delivery are not overwritten or
published. Timeout/unknown checks remain explicit. Only sampled combinations are
covered; successful end variants do not prove the entire parameter interval.
Copies/subprocesses isolate work state, not untrusted code execution security.

## Measured fit calibration

Standalone: `cad3d calibration fit measurements.json --identity identity.json`.
Reports compare the explicitly supplied identity and write recommendations;
applying them to a project requires revalidation against current settings.

Payload fields: identity, confirmed_measured=true, measured_at and valid_until
(timezone-aware ISO timestamps), evidence={path,sha256}, measurements list of
{feature,nominal_mm,actual_mm,uncertainty_mm}. Evidence must be an actual local
project file with matching SHA256. Each feature is limited to its exact nominal;
no extrapolation to different dimensions. Identity requires printer, nozzle_mm,
material, process_sha256 and orientation; any extra fields also participate.

Native assembly integration:

```yaml
# .cad3d/assembly.yaml
fit_calibration: measurements.json
```

The expected identity is derived from current project configuration, not copied
from the measurement record:

- .cad3d/printer.yaml: name, nozzle_diameter_mm, fit_orientation,
  process_settings_file (existing project-relative file); optional
  process_settings_sha256 must match that file's actual hash.
- parameters: printer.profile and material.profile; optional material.lot.
- Measurement identity must also contain matching printer_profile, and
  material_lot when a lot is selected. process_sha256 is computed from the selected
  process file. Missing current identity/evidence/validity stays unknown;
  mismatches fail and cannot replace the selected delivery.

Outputs include mean feature bias, observed intervals including measurement
uncertainty and recommendations for new coupons. No preset is silently modified.
An observed sample envelope is not a guaranteed bound of future production, a
statistical confidence interval or proof of physical fit. Hashes preserve file
integrity, not instrument truth or transcription accuracy. Coupon orientation
identity does not qualify every part orientation in a mixed assembly.

## Assembly access and cable routes

Top-level assembly access_checks accepts unique IDs, kind box|cylinder|cable and
optional target_id/required (defaulttrue). Only the named engagement target is
excluded; nearby ribs/parts remain obstacles. Exclusion is not proof that the
drive cavity/connector mates. Boxes/cylinders can approximate fingers, tools and
counterholds, not universal ergonomic dimensions.

- Box: center_mm and size_mm.
- Cylinder: origin_mm, direction, radius_mm, length_mm.
- Cable: points_mm, diameter_mm, bend_radius_mm, minimum_bend_radius_mm.
  Adjacent circular fillets must fit; tighter-than-declared minimum bends fail.
  The curve envelope uses chord capsules inflated by arc sagitta, conservatively
  covering the rounded centreline. No cable stiffness/strain/connector load proof.

Optional motion uses the rotation/translation/composite schema to check sampled
approach, instead of only the final tool pose. Declared required access failures
or unknowns block assembly qualification. No automatic hand model, free-space
route search, insertion force or soft-body simulation.

## Technical drawings

`cad3d drawings` generates three actual CAD orthographic HLR views per manufactured
part, overall dimensions and SVG/PDF. For inclusion in the immutable release,
set project.drawings in .cad3d/project.yaml to a config mapping. Drawing references
requested but unresolved block publication. Optional configuration:

```yaml
title: Support detail
sections:
  - {name: centre-cut, part: support, axis: z, at_mm: 0}
feature_dimensions:
  - name: bore
    part: support
    type: diameter
    selector: {surface: cylinder, radius_mm: 2}
```

Sections are actual CAD plane cuts, exported as separate named sheets; an empty
cut fails. Diameter derives from a selected cylindrical face. minimum_distance
uses first and second face selectors and measures their actual minimum BREP
distance; it is not inferred hole-centre spacing or an arbitrary typed value.
Ambiguous/missing faces stay NOT_EVALUATED without a number. Max8 feature dimensions
per part and64 total. Selectors use the queried part's CAD coordinates.

Visible/hidden edges come from CAD; curves are sampled only for vector rendering.
Numeric overall bounds govern; view scales are independent and paper measurement
is not valid. Sheets identify parts/sections and dimension results, but are not a
complete ISO/GD&T fabrication specification, tolerance assignment or surface-finish
callout set. Review exported sheets visually and add the manufacturing requirements.

## Preliminary structural screening

`cad3d structure --config beam.json` or assembly structural_checks supports only
model=rectangular_cantilever_end_load and units=N-mm-MPa. Required dimensions/load:
length_mm,width_mm,thickness_mm,load_n,elastic_modulus_mpa,allowable_stress_mpa,
max_deflection_mm,safety_factor; unique id in assembly, optional required (defaulttrue).

Both material properties need provenance keyed by their field names with
{basis: measured|supplier|assumed,source}. Confirm assumptions fixed_support,
transverse_tip_load,prismatic_solid_section,linear_elastic_homogeneous=true. Missing
inputs/confirmation are unknown; assumed material properties give WARNING even
when the numerical limits pass. No default PETG modulus/strength is supplied.

The calculation uses I=b*h^3/12, stress=F*L*h/(2I), deflection=F*L^3/(3EI).
Compare stress with allowable/safety_factor and service-load deflection with its
supplied limit. Declared dimensions are not automatically measured from CAD;
confirm the actual component matches this idealization. Small-deflection and beam
slenderness heuristics may add warnings. Physical load validation remains unknown.
No joint/anchorage, shear qualification, creep, fatigue, buckling, thermal effects,
notches, FDM anisotropy/infill or safety certification is implied.

Primary equations: [MIT cantilever displacement](https://ocw.mit.edu/courses/1-050-solid-mechanics-fall-2004/fd4eff39aec922b8c07660006f40686e_pset04_11.pdf),
[MIT beam bending stress](https://ocw.mit.edu/courses/3-11-mechanics-of-materials-fall-1999/96d839b02e4a6c63cf8031800e89cccd_MIT3_11F99_bstress.pdf).
