# CAD3D solution knowledge

This is a small, reviewable Git library of reusable engineering concepts. It is not a dimension/tolerance standard and does not prove a pattern will work in a new design. Load only entries relevant to the task; applicability, material, printer, loads and interfaces must be rechecked.

## Evidence states

- `CONCEPT_PROPOSED`: candidate and rationale recorded; no project-specific verification.
- `GEOMETRICALLY_VALIDATED`: named CAD build/check and artifacts support the stated geometric claim only.
- `PHYSICALLY_TESTED`: named specimen, setup, material/process and measurements are recorded.
- `REJECTED`: concept failed for the stated conditions; do not generalize failure beyond them.
- `NOT_EVALUATED`: no evidence sufficient for the claim.

Every entry distinguishes observed failures from predicted risks. Evidence should link to a repository, test artifact or report and include date/version. Never promote evidence status by copying a concept into another model.

## Entries

- [Removable modular trays](removable-modular-trays.md)
- [Removable guided support](removable-guided-support.md)
- [Three-chamber passive flow](three-chamber-passive-flow.md)

Add an entry only when a recurring decision or validated finding is worth retaining. Keep it to purpose, alternatives, selection conditions, interfaces, risks, evidence status and links.
