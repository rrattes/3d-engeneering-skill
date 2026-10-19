# Commercial components

Capture vendor, exact part number/revision, source/document date, measured/verified dimensions, uncertainty and keep-out envelope. Model an envelope from the best available drawing; label unverified details as assumptions. Record connector, mounting datums, access, cable/hose path and removal path. Do not infer hidden geometry, loads, materials or sealing from a bounding box. Recheck procurement revision and fit against the physical item before release; do not modify the commercial item model to make it appear compatible.

Represent functional mounting geometry and obstructions that affect the interface:
housing, mounting holes/seats, selected hardware heads, connector engagement and
cable/hose bends. Keep manufactured adaptors distinct from commercial references.
An envelope clearing a cavity proves neither retention nor service access. Define
locating surfaces, restraints/load path and release using
[mechanical_assemblies.md](mechanical_assemblies.md); preserve the real commercial
geometry while correcting the manufactured support or arrangement. Procurement
availability, source dimensions and physical fit are separate evidence states.

## Revision records and selections

The catalog can carry an inline `commercial_record` and `selection_lock` (id, revision, SHA256). Use the `commercial_components` validator for declared provenance, units and selected revision. A schema-valid record is not proof that a drawing was read correctly. Enclosure dimensions and photographs without scale cannot establish PCB dimensions or drilling coordinates. Keep uncertainty and coordinate datum attached to mounting data.

Optional commercial keep-out checks compare separate body/plug/cable envelopes with actual BREP blockers. A modeled cable reservation is not a measured minimum bend radius. Changes to a selected record invalidate its matching lock; a newer library entry must not silently replace the project selection. Do not auto-promote previous-project supports or agent memory to verified component geometry.
