# Product engineering workflow

Scale rigor to consequence. For a simple noncritical part, document its function, dimensions, printer envelope and fit assumptions; for assemblies and flow systems use all phase gates. A product contract lives at `.cad3d/engineering.yaml` and is validated by `cad3d architecture validate`.

1. Requirements: function, operating conditions, verified measurements vs assumptions, commercial items, acceptance, external interfaces, risks and unknowns.
2. Functional architecture: subsystems, input/output, physical flows, modes and failure modes. Demonstrate conceptual operation without CAD.
3. Mechanical architecture: datums, constraints, attachment/retention, fits, service access, disassembly sequence and print splits.
4. Modeling: only after phases 1–3 validate; parametric parts, placed assembly, interfaces and early views.
5. System review: requirements evidence, interfaces, retention, assembly/removal, access, channels, manufacturing and residual risks.
6. Fabrication: orient and assess, optional OrcaSlicer, export, prototype plan and dimensional inspection.

Critical FAIL or required NOT_EVALUATED blocks subsequent approval. Warnings need disposition. CAD B-rep validity, assembly validity, manufacturing assessment, slicing success, printer compatibility and physical validation are separate claims.
