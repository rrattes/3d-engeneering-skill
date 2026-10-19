# Interferences, geometric references and tolerances — CAD3D 1.7.0+

## Robust BREP checks

Static, linear service and tool checks share the same atomic-solid primitive used
by helical paths. Located/imported Compounds are decomposed after placement. Every
solid pair is checked; permitted contact never waives positive common volume or required clearance.
Contact classification tolerance does not replace a requested minimum gap.
Separation inside an annular void can be valid even when bounding boxes overlap.
Static reports retain exact global minimum distances when all pairs were evaluated;
partial distance data cannot establish a global minimum. A known collision dominates
an unknown result in another pair. Invalid BREP or kernel uncertainty never yields PASS.
Summed pair overlap is diagnostic, not a union-volume or structural-strength result.
Helical zero-gap contact may omit exact distance as documented in helical_motion.md.

## Stable face references

Legacy `center_mm` selectors retain their centroid semantics and original tolerance.
Prefer a datum-derived `point_mm` when topology changes move a face centroid:

```yaml
face_a:
  ref: support-outer-side
  surface: plane
  point_mm: [35, 55, 85]
  point_tolerance_mm: 0.05
  normal: [1, 0, 0]
  normal_dot_min: 0.95
```

The point is tested against the **finite trimmed face**, not its infinite supporting
plane; a point in a hole is not on the face. Coordinates refer to the actual shape
being queried: local model coordinates for per-part thickness, world coordinates
for placed interface checks. Derive points from parameters/datums, not copied face
ordinals. Optional `radius_mm`/`radius_tolerance_mm` and
`area_mm2`/`area_tolerance_mm2` help distinguish candidates. Do not combine point and
centroid anchors. Equal nearest candidates remain NOT_EVALUATED; no silent widening
or arbitrary topology-index fallback. Reports expose rejection counts and up to five
nearest candidates for diagnosis. `ref` is an intent label, not persistent CAD identity.

If some requested thickness faces cannot be selected, measured remaining faces do
not make the whole scoped check PASS. Partial coverage is WARNING; no measurement
is NOT_EVALUATED. Point selection does not make thickness sampling exhaustive.

## Signed worst-case tolerance chains

Configure optional top-level assembly fields:

```yaml
tolerance_dimensions:
  opening:
    nominal_mm: 10.4
    minus_mm: 0.15
    plus_mm: 0.15
    basis: measured
    source: "measurement record / instrument and date"
  shaft:
    min_mm: 9.9
    max_mm: 10.1
    basis: supplier
    source: "drawing identifier and revision"
tolerance_stacks:
  - id: running-clearance
    terms:
      - {dimension: opening, coefficient: 1}
      - {dimension: shaft, coefficient: -1}
    offset_mm: 0
    allowed_mm: [0.2, 0.7]
```

Nominal gap0.4mm becomes0.15..0.65mm; it fails the required minimum0.2mm.
For negative coefficients, lower/upper contributions are reversed. Repeated use of
one dimension ID means **the same variable**, so coefficients are combined before
propagating uncertainty. Independent physical dimensions must use distinct IDs.
Only linear dimensional chains are supported; nonlinear fits, general GD&T,
thermal models and statistical yield need separate analysis.

Each dimension uses either min/max bounds or nominal with both minus/plus deviations
(nonnegative). A missing deviation is unknown, never silently zero. Exact fixed
terms may use equal explicit bounds with `basis: exact` and a source. Other bases:
measured, supplier, calibrated or assumed. Bounds require a nonempty source; declared
provenance is recorded, not independently authenticated by the evaluator.

A complete bounded calculation inside the allowed range gives PASS; outside gives
FAIL. Missing bounds/provenance yield NOT_EVALUATED when no bounded failure is
already established. Assumed bounds inside the range yield WARNING. Existing release
gates require assembly PASS, so missing evidence/assumed bounds cannot silently
publish as verified. Reports expose `bounded_arithmetic_status` separately from the
overall status and always leave `physical_fit_validation: NOT_EVALUATED`.

Without tolerance_stacks the old contract remains unchanged. These calculations do
not replace interference, calibration or physical fit/load testing.
