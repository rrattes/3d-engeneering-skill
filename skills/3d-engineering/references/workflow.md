# CAD3D project workflow reference

Projects use `.cad3d/project.yaml`, `.cad3d/params.yaml`, `src/model.py` returning `{component_name: build123d.Shape}`, optional `.cad3d/assembly.yaml` and `.cad3d/engineering.yaml`, project profiles/tests, and generated `build/outputs/`.

For a product contract, use the staged gates in [product_engineering.md](product_engineering.md); for a simple part use a proportionate lightweight workflow. `cad3d build` gates product geometry and then validates/exports STEP/STL, renders, reports and manifests. `cad3d architecture validate --geometry` samples declared physical paths against actual B-rep solids. `cad3d review` reports requirement evidence and review limits. Exit codes: 0 command passed, 2 invocation/runtime error, 3 validation failure. A command succeeding is not a claim beyond the specific checks it executed.

See [mechanical_assemblies.md](mechanical_assemblies.md), [dfam.md](dfam.md), [fluid_systems.md](fluid_systems.md), [design_review.md](design_review.md) and [visual_validation.md](visual_validation.md) for relevant limits.
