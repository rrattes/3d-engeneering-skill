---
name: 3d-engineering
description: >-
  Engineer parametric mechanical parts and assemblies with the CAD3D platform. Use
  for product design, enclosures, supports, mechanisms, interfaces, fluid paths,
  build123d/OCP, STEP/STL, FDM/DFAM, and OrcaSlicer workflows. Do not use for
  unrelated software tasks or general 3D art.
---

# CAD3D product engineering

Use the existing global `cad3d` CLI; it runs the CAD engine (`build123d`/OCP) and,
optionally, the isolated OrcaSlicer manufacturing engine. Do not install CAD Python
packages on the host. Start with `cad3d --help` and `cad3d doctor` when needed.

## Workflow

Before CAD, understand the job the product must do. Separate user needs, functional
requirements, hard constraints, preferences, suggested solutions, and unknowns. Map
functions and physical flows, and compare at least two materially different concepts
when more than one is plausible. For a genuinely simple part, state why direct
selection is enough. Choose for the relevant tradeoffs, not merely fewest parts or
lowest cost; check the space budget and challenge unassigned volume. Load
[functional_design_intelligence.md](references/functional_design_intelligence.md)
and [concept_selection.md](references/concept_selection.md) for this step.

Then continue the existing V1.4 gates: requirements → functional architecture →
mechanical architecture → parametric geometry → system review → manufacturing.
For product-level work, create `.cad3d/engineering.yaml` and planned interfaces/
poses in `.cad3d/assembly.yaml` first, then validate with `cad3d architecture
validate`. Do not edit geometry source or call `cad3d build` while any of the first
three phases is FAIL; correct the contract and repeat the validation. Never change a
product project to `lightweight` merely to get past a failing gate. Use lightweight
only for a genuinely obvious, low-risk part without load, fluid, motion or unresolved
functional interfaces. See [requirements_and_interfaces.md](references/requirements_and_interfaces.md)
for field types and assembly links. Product contracts may retain `WARNING` where
judgment/evidence remains open; review and report it honestly.

Model from explicit datums, units, interfaces and parameters. Map each component to a
function, positioning relation and retention method; explicitly declare intended free
parts. Validate geometry and assemblies using `cad3d build`, then run
`cad3d architecture validate --geometry`, `cad3d review`, and
`cad3d report --requirements`. Correct FAIL results and rerun the relevant checks.
PASS requires traceable evidence; declaration or a generated solid alone is not proof.
Treat WARNING and NOT_EVALUATED as unresolved review items. A CAD-valid assembly is
not thereby mechanically stable, printable, physically validated, or ready to release.

Generate technical views with `cad3d render --view engineering`: opaque isometric,
orthographic top/front/side, section, exploded, plus configured hidden-component and
critical-interface views. Review the actual images for occlusion and legibility.
Export with `cad3d export`. For FDM use the versioned printer/material/process
profiles. Run `cad3d slice --printer elegoo-cc2 --material petg` when slicing or a
manufacturing estimate is requested and the applicable profile is known; inspect
`cad3d slice-report`. For a CAD concept/model request, geometric envelope/orientation
assessment and export may be sufficient. Slicing is an estimate, not printer
compatibility or physical validation. Never start a print or transmit a file to a
printer. Stop once requested acceptance criteria and blocking findings are resolved;
do not repeat full builds or read large logs without a specific question to resolve.

## Load references by project class

- General product phases and gates: [product_engineering.md](references/product_engineering.md)
- Understand function and unknowns: [functional_design_intelligence.md](references/functional_design_intelligence.md)
- Compare architectures and budget space: [concept_selection.md](references/concept_selection.md)
- Reusable concepts with evidence status: [solution_knowledge/README.md](references/solution_knowledge/README.md)
- Requirements, YAML contract, interfaces and evidence: [requirements_and_interfaces.md](references/requirements_and_interfaces.md)
- Assemblies, retention, fit and service: [mechanical_assemblies.md](references/mechanical_assemblies.md)
- FDM design and profiles: [dfam.md](references/dfam.md)
- Passive channels and fluid paths: [fluid_systems.md](references/fluid_systems.md)
- Adversarial/system review: [design_review.md](references/design_review.md)
- Professional view generation: [visual_validation.md](references/visual_validation.md)
- Commercial part envelopes: [commercial_components.md](references/commercial_components.md)
- Existing CAD checks: [assembly-validation.md](references/assembly-validation.md)
- OrcaSlicer engine and its limits: [orcaslicer-engine.md](references/orcaslicer-engine.md)

Choose relevant references; do not load every topic for a simple part. Keep requirement
implementation distinct from verification, engineering judgment distinct from automated
checks, and physical validation distinct from CAD/slicer evidence. For adversarial review,
use a fresh Codex context when available. A sequential checklist is not an independent
review; report that limitation explicitly.
