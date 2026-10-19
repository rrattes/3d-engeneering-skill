# Product engineering workflow

Scale rigor to consequence. Before the existing gates, understand the requested outcome and compare concepts where the architecture is open; see `functional_design_intelligence.md` and `concept_selection.md`. This enriches, rather than replaces, the V1.4 workflow. For a simple noncritical part, a short purpose/concept/assumptions note is enough; for assemblies and flow systems use all phase gates. A product contract lives at `.cad3d/engineering.yaml` and is validated by `cad3d architecture validate`.

1. Requirements and concept: function, context, interactions, verified measurements vs assumptions, hard constraints vs preferences/suggested solutions, acceptance, external interfaces, risks, alternatives and selected concept. Budget occupied, functional, access/reserved and unexplained space.
2. Functional architecture: subsystems, input/output, physical flows, modes and failure modes. Demonstrate conceptual operation without CAD; allocate functions to components before modeling.
3. Mechanical architecture: datums, constraints, attachment/retention, fits, service access, disassembly sequence and print splits. Review concept, interfaces, space, unknowns, manufacturing and failures before CAD.
4. Modeling: only after phases 1–3 validate; parametric parts, placed assembly, interfaces and early views.
5. System review: requirements evidence, interfaces, retention, assembly/removal, access, channels, manufacturing and residual risks.
6. Fabrication: orient and assess, optional OrcaSlicer, export, prototype plan and dimensional inspection.

Critical FAIL or required NOT_EVALUATED blocks subsequent approval. Warnings need disposition. CAD B-rep validity, assembly validity, manufacturing assessment, slicing success, printer compatibility and physical validation are separate claims.
