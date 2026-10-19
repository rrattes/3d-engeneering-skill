# CAD3D Engineering V1.4 technical decisions

## Staged product contract

`engineering.yaml` provides a flexible, project-local contract that joins requirements, functional subsystem/flow maps, mechanical components/interfaces, acceptance evidence, assumptions, risks and manufacturing status. It does not certify a design by being syntactically complete. `cad3d architecture validate` checks phased completeness and evidence; `cad3d build` gates product-level geometry generation on requirements, functional architecture and mechanical architecture. Projects without this file preserve V1.3 behavior. Lightweight projects can opt into a smaller contract.

Evidence is read from project-relative JSON pointers and fingerprinted. Geometry checks use the live B-rep where implemented. Unavailable proofs stay `NOT_EVALUATED`; measured/physical behavior cannot be inferred from CAD. The review report is sequential and explicitly does not claim reviewer independence.

## Renderer

Selected PyVista 0.49.1 and VTK 9.6.2, pinned with the other CAD dependencies. The official [PyVista Docker guidance](https://docs.pyvista.org/extras/docker) describes headless rendering, and [VTK runtime settings](https://docs.vtk.org/en/latest/advanced/runtime_settings.html) document EGL selection. The renderer tessellates live build123d/OCP solids, applies the assembly placement manifest, and renders with CPU EGL in the existing CAD image. It does not replace the B-rep or add a CAD kernel. `libegl1` and `libgl1` are pinned in the existing CAD image; no third image, host GUI package, web viewer, resident service, or Orca change is needed. Renderings are off-screen PNG artifacts with component colors, fixed legend, shared model coordinate frame, parallel camera projection, and standard orthographic/section/exploded/interface views.

Runtime smoke uses the real PyVista/VTK window and writes a PNG. Output images remain review evidence, not dimensional or mechanical evidence. The renderer currently provides static pictures rather than interactive picking/section manipulation. Section views show tessellated plane-intersection outlines, not synthetic caps, so void regions cannot be filled by generic mesh triangulation. They are not a B-rep drawing export and do not include section hatching.

## State semantics and limits

`PASS`, `FAIL`, `WARNING`, `NOT_EVALUATED` are retained. Geometric validity, assembly placement/collision, manufacturing assessment, slicing, printer compatibility, and physical validation are distinct. Flow path sampling against B-rep checks a sampled swept corridor only; it is not CFD or a leak test. Linear removal paths use discrete samples and do not prove continuous motion, retention strength or fatigue. Manufacturing heuristics do not guarantee a print.
