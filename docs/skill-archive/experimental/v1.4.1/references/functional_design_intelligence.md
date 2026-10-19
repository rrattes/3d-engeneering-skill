# Functional design intelligence

Use before choosing part layout or creating functional solids. Keep this proportional: a simple spacer needs a short purpose/constraints note; a mechanism or flow system needs an explicit functional model.

## Understand the job

Capture, in the project's existing `.cad3d/engineering.yaml` where appropriate:

- **User need:** outcome the user wants and use context.
- **Functional requirement:** observable action/result and acceptance criterion.
- **Hard constraint:** must-fit dimensions, interfaces, materials, process, safety or cost ceiling.
- **Preference:** desirable tradeoff that can be balanced.
- **Suggested solution:** an implementation idea from the user; preserve it as a candidate and evaluate it against the need. Do not silently turn it into a requirement or discard it.
- **Assumption/unknown:** value, source, confidence, impact if wrong, and how to measure or resolve it.

Do not call a prompt-supplied limit a measured physical dimension. Distinguish available envelope, part envelope, installation allowance and internal usable space. If a distinction changes feasibility, call it out before geometry; ask the smallest blocking question or state a reversible, clearly marked concept assumption.

## Model function independently of CAD

For each relevant subsystem, identify its function, input, output, dependencies, boundary interfaces and operating modes. Trace the physical paths that matter: material/fluid, force, motion, energy, signals, access or service. List plausible failure modes and a way to detect each. Check conceptual continuity before solids; a dimensioned partition is not evidence of a working flow path.

Create a compact function/component allocation. Every component must serve a function, an interface/retention need, manufacturing or assembly, or be explicitly aesthetic. A previous revision is not justification for keeping a part.

## Spatial budget

Describe major volumes as:

- occupied by components;
- functionally required (flow, movement, tolerance, heat/air, safety);
- access/removal/service envelope;
- available but intentionally reserved;
- currently unexplained.

Use CAD bounding boxes/volumes or actual dimensions when geometry exists; before CAD, use a rough envelope budget and label it estimated. Empty space can be necessary. Challenge large unexplained regions, but do not optimize occupancy at the expense of function, access, service, safety or tolerance. Record which objects' real sizes remain unknown.

## Existing V1.4 contract

Reuse the current phase gates and validator; do not invent another workflow or treat a complete YAML as proof. Put user needs and requirement IDs in the existing requirement records; link subsystem, components, interfaces, dependencies, verification method and evidence. Supplemental concept/function/space records can live in the same flexible `engineering.yaml` or a concise `design/` note referenced by it. Mark a requirement PASS only when its actual verification has identifiable evidence; unresolved function stays WARNING/NOT_EVALUATED and blocks claims of release readiness.

The CAD workflow can check geometry, declared interfaces, sampled paths and requirement evidence. It does not establish conceptual performance, loads, usability, reliability, sealing, flow rate or physical fit without suitable calculations or tests.
