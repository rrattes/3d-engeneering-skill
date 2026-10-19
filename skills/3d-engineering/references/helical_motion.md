# Helical service paths — CAD3D 1.6.0+

Use for screws or rigid threaded groups with modeled mating geometry. Configure
`.cad3d/assembly.yaml`; `cad3d validate`, `build` and checked `release` use the same
service evaluator and expose results under `assembly.assembly_sequence.steps`.

```yaml
assembly_steps:
  - id: withdraw-screw
    moving_ids: [screw-001]
    removed_ids: []
    allowed_contact_pairs: ["screw-001::support-001"]
    samples: 24
    motion:
      type: helical
      axis_origin_mm: [22, 46, 80]
      axis_direction: [0, 1, 0]
      pitch_mm: 3
      starts: 1
      handedness: right
      travel_mm: -15
  - id: remove-basket
    moving_ids: [basket-001]
    removed_ids: [screw-001]
    prerequisite_step_ids: [withdraw-screw]
    direction_mm: [0, 1, 0]
    travel_mm: 60
    samples: 12
```

This is a contract illustration; use real instance IDs, geometry and datums. Both
installed screws need independent withdrawal steps before listing both as removed.
Static interface contacts/clearances remain separately configured in `interfaces`.

## Coordinates and coupling

The placed component geometry is the installed pose at fraction zero. Axes and
origins are **world coordinates**, after placement. The axis direction is normalized.
At fraction f: rotate about that world axis and translate along it by f×travel.
Positive travel follows the axis; negative travel opposes it. Positive rotation
uses the right-hand rule about the axis. For `handedness: right`, angle in degrees
is 360×travel/(pitch×starts); left-handed reverses the sign. Lead is pitch×starts.
Reversing an axis requires changing signed travel consistently.

`pitch_mm` must be positive; travel nonzero and signed; starts a positive integer;
all coordinates finite; handedness explicitly `right` or `left`. This API does not
infer thread geometry, pitch, phase or hand from a cylinder or a product name.
Match the modeled phase and lead. A wrong value may collide, but a clear dummy
cylinder cannot prove a correct thread pair.

`samples` counts intervals (default12, integer1..4096). Both endpoints are included.
The evaluator increases intervals as needed to keep angular spacing at most90°,
reducing complete-turn aliasing. Paths needing more than4096 intervals are rejected;
split the engineering operation or choose a justified scope. This bound does not
prove the absence of narrower obstructions between samples.

## Contacts, release and reports

Each original moving instance is checked against every retained instance. Moving
groups remain rigid; their internal interference is covered by the static assembly
check. Contact pairs name original moving::retained IDs; permission for one member
never permits contact for all group members. Positive overlap volume always fails.
`clearance_mm` optionally specifies a nonnegative minimum for every path pair.

Conservative bounding-box separation can establish a lower-bound gap without
computing exact distance. Overlapping bounds require BREP analysis of world-located atomic solid pairs,
including every solid of imported Compounds; allowed contact
with zero required gap is checked by common volume. Kernel failure/invalid geometry
is NOT_EVALUATED. Tools retain their existing seated-pose cylinder checks; the tool
does not automatically follow the helix. Grip/access/torque remain separate.

Reports identify normalized axis, pitch/starts/lead, total rotation, requested and
actual sample spacing, each sampled pose and collision/unknown findings. A sampled
PASS alone does not establish complete withdrawal. `removal_proven` additionally
requires terminal conservative bounds separated from every retained component;
this is sufficient but conservative and can remain false for a genuinely released
part. A dependent step cannot omit a screw based on a helical prerequisite without
that proof. Invalid/failed/uncompleted prerequisites remain blocking.

No continuous collision proof, elastic deformation, physical fit, print quality,
wear, torque, load capacity or material/biological qualification is implied. Keep
wall-thickness evaluation separate; this capability does not fix face selectors.

Legacy steps without `motion` remain linear and retain the historical direction
convention. Explicit `motion: {type: linear}` also uses that convention. Helical
steps require `moving_ids`; unknown motion types are rejected, never treated as
linear silently.
