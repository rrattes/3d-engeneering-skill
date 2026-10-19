---
name: 3d-engineering
description: >-
  Engineer parametric mechanical parts and assemblies with the CAD3D platform. Use
  for product design, enclosures, supports, mechanisms, interfaces, fluid paths,
  build123d/OCP, STEP/STL, FDM/DFAM, and OrcaSlicer workflows. Do not use for
  unrelated software tasks or general 3D art.
---

# CAD3D product engineering

Use the `cad3d` CLI supplied by the current kit/platform; resolve its path before use
so an older global installation cannot silently take precedence. It runs the CAD engine (`build123d`/OCP) and,
optionally, the isolated OrcaSlicer manufacturing engine. Do not install CAD Python
packages on the host. Start with `cad3d --help` and `cad3d doctor` when needed.

Begin with the current brief: function, operating conditions, hard constraints,
preferences, commercial interfaces and unknowns. Label suggested solutions as
choices to assess. Derive datums, spatial budget and form from use, access and
manufacture; compare materially different concepts when the choice is consequential.
For a simple obvious part, a short reason for direct selection is enough.

## Workflow

For product projects, use machine-enforced dependency gates in addition to engineering
checks. New templates include `.cad3d/workflow.yaml`; migrate a project with
`cad3d workflow init`. Run `cad3d workflow check --gate <gate>` in order:
`requirements` → `functional_architecture` → `mechanical_architecture` → `modeling`
→ `system_verification` → `visual_review`. Each status derives from current reports
and linked evidence; manually writing PASS cannot bypass a dependency. FAIL,
NOT_EVALUATED, or undispositioned WARNING blocks advancement. Critical WARNING cannot
be waived. Product-design depends on engineering and visual review; it is available
only when requested after those gates. Any model, parameter or assembly change
invalidates prior model/render evidence: rerun affected validation and inspect new
images before advancing.

For consequential products, proceed in gates: requirements → functional architecture
→ mechanical architecture → parametric geometry → system review → manufacturing.
Use `cad3d architecture init --level product` and edit `.cad3d/engineering.yaml`;
validate with `cad3d architecture validate` before creating functional solids. FAIL
or required NOT_EVALUATED in the first three phases blocks modeling. Disposition
WARNING findings explicitly before proceeding. Simple low-risk spacers/supports may
use the lightweight project level; match process depth to risk.

Use a single part/instance catalog to select FDM vs metal/commercial exports.
Derive datums and fixings from input parameters; verify actual geometry under meaningful
parameter variations. Diagnose root causes before changing failing interfaces; retain
negative controls and current evidence for corrected failures.

Model from explicit datums, units, interfaces and parameters. Map each component to a
function, positioning relation and retention method; explicitly declare intended free
parts. Validate geometry and assemblies using `cad3d build`, then run
`cad3d architecture validate --geometry`, `cad3d review`, and
`cad3d report --requirements`. Correct FAIL results and rerun the relevant checks.
PASS requires traceable evidence; declaration or a generated solid alone is not proof.
Treat WARNING and NOT_EVALUATED as unresolved review items. A CAD-valid assembly is
not thereby mechanically stable, printable, physically validated, or ready to release.

For assemblies, represent actual mounting and retention: locating surfaces, restrained
motions, load path and release. Include fastener heads/nuts/washers and separate tool,
cable and service keep-outs. Evaluate signed tolerance bounds and each required
independent removal sequence. Use the concrete recipe in
[mechanical_assemblies.md](references/mechanical_assemblies.md); placement and nominal
hole clearance alone do not establish these results.
For imported assemblies, stable face references and bounded tolerance chains, see
[reliability.md](references/reliability.md) (CAD3D 1.7.0+). Unresolved face selection
and missing uncertainty evidence must remain explicit; nominal fit is not worst-case fit.
For threaded service paths, use explicit helical motion in CAD3D 1.6.0 or later;
see [helical_motion.md](references/helical_motion.md). Check modeled mating threads,
axis, lead, handedness and terminal release; a sampled path PASS does not prove
thread fit, continuous clearance or strength.

Generate technical views with `cad3d render --view engineering`: opaque isometric,
orthographic top/front/side, section, exploded, plus configured hidden-component and
critical-interface views. Review the actual images for occlusion and legibility.
Assemblies with multiple components must use distinguishable component colors. Keep an
overall colored assembly view and close views of critical interfaces. The AIO filter is
the positive reference: colored assembled/exploded parts and a male/female interface
detail, with B-rep clearance recorded separately. This supports CAD assembly and
geometric interface review only; physical fit still requires a physical test. Record
the reviewer, current manifest SHA256, each image path/hash, inspection result and
resolved findings in `.cad3d/visual-review.yaml`. The visual gate requires isometric,
top/front/side, section, exploded and hidden views, plus every declared critical
interface; it rejects missing, stale or uninspected images.
Export working files with `cad3d export`; publish a checked prototype through
`cad3d release --target cad-prototype`. Read its selected immutable run from
`build/delivery/current.json`; a generated file is not a released physical product. For FDM use the versioned printer/material/process
profiles. Establish the requested combination early with
`cad3d slicer preflight --printer elegoo-cc2 --material <requested> --process standard-0.20`
when that printer/process applies; select the user's actual profiles otherwise.
Resolve unavailable presets before claiming slicing support; do not substitute materials.
When slicing is requested, run `cad3d slice` with the resolved profiles and inspect
`cad3d slice-report`. Slicing is an estimate, not printer compatibility or physical
validation. Never start a print or transmit a file to a printer.

`cad3d workflow check --gate prototype_release` gates a CAD prototype release; its
scope does not claim physical validation. Manufacturing, slicing and physical validation
are separate gates. Physical PASS requires identified tests, methods, passing results
and project-relative evidence with matching SHA256. A render, B-rep clearance, slice or
user approval cannot substitute for physical evidence.

## Additional capabilities (CAD3D 1.8.0+)

Use [general_capabilities.md](references/general_capabilities.md) when a project needs
parametric interface templates, rotations/composite service, variant campaigns,
measured fit calibration, access/cable envelopes, CAD drawing sections/dimensions,
or preliminary cantilever screening. Load the relevant section only. Respect each
supported model, input provenance and gate; these tools do not qualify physical fit,
loads or a manufacturing standard automatically.

## Load references by project class

Simple low-risk part: function/dimensions, assumptions, relevant fit, CAD and requested
manufacturing evidence. Assembly or commercial interface: add retention, hardware,
tolerance and service evidence. Multidomain product: add functional architecture,
physical flows, operating/failure states and the relevant specialty reference.

- General product phases and gates: [product_engineering.md](references/product_engineering.md)
- Requirements, YAML contract, interfaces and evidence: [requirements_and_interfaces.md](references/requirements_and_interfaces.md)
- Assemblies, retention, fit and service: [mechanical_assemblies.md](references/mechanical_assemblies.md)
- FDM design and profiles: [dfam.md](references/dfam.md)
- Passive channels and fluid paths: [fluid_systems.md](references/fluid_systems.md)
- Adversarial/system review: [design_review.md](references/design_review.md)
- Concept/parameter propagation and delivery: [concept_and_presentation.md](references/concept_and_presentation.md)
- Professional view generation: [visual_validation.md](references/visual_validation.md)
- Commercial part envelopes: [commercial_components.md](references/commercial_components.md)
- Existing CAD checks: [assembly-validation.md](references/assembly-validation.md)
- OrcaSlicer engine and its limits: [orcaslicer-engine.md](references/orcaslicer-engine.md)

Choose relevant references; do not load every topic for a simple part. Keep requirement
implementation distinct from verification, engineering judgment distinct from automated
checks, and physical validation distinct from CAD/slicer evidence. For adversarial review,
use a fresh Codex context when available. A sequential checklist is not an independent
review; report that limitation explicitly.
