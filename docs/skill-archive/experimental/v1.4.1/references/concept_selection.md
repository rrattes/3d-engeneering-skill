# Concept selection and pre-CAD review

## When to compare concepts

If two materially different architectures could plausibly meet the need, compare at least two **before** selecting geometry. Examples include side-by-side vs stacked modules, removable insert vs access door, screw vs snap-fit, fixed vs sliding support, or open gravity transfer vs enclosed channels. Do not manufacture alternatives for a simple shape whose solution is effectively determined; state the reason for direct selection briefly.

For each concept, say how it works, the interfaces it needs, its space/access implications, manufacturing and service implications, and its main failure modes. Evaluate only criteria relevant to the project: function, space, mechanics, maintenance, fabrication, reliability, cost and operational risk. Use concise qualitative tradeoffs or a small table. Do not invent precise weighted scores or measured performance without evidence. More parts or higher cost can be justified when function, service or reliability improves.

Select one architecture and record why it best balances the important criteria, what it gives up, and what unresolved assumption could reverse the choice. User-suggested solutions remain candidates; compare them fairly to alternatives and explain any deviation.

The existing flexible `.cad3d/engineering.yaml` can carry a compact record next to the current requirements, subsystems and interfaces. These extra keys are a skill convention, not fields currently enforced by the V1.4 validator; never report them as validator-approved:

```yaml
design_study:
  need_types:
    - {id: NEED-1, kind: user_need, description: "..."}
    - {id: REQ-1, kind: functional_requirement, acceptance: "..."}
    - {id: C-1, kind: hard_constraint, source: user, value: "..."}
    - {id: PREF-1, kind: preference, description: "..."}
    - {id: SOL-1, kind: suggested_solution, disposition: evaluated_candidate}
    - {id: U-1, kind: assumption, status: NOT_EVALUATED, resolution: "..."}
  concepts:
    - id: concept-a
      description: "..."
      tradeoffs: {function: "...", space: "...", service: "...", fabrication: "...", risk: "..."}
    - id: concept-b
      description: "..."
      tradeoffs: {function: "...", space: "...", service: "...", fabrication: "...", risk: "..."}
  selection: {concept: concept-a, rationale: "...", sacrifices: "...", reversal_condition: "..."}
  space_budget:
    - {id: usable_envelope, state: estimated, dimensions_mm: [0, 0, 0], source: "..."}
    - {id: service_access, state: NOT_EVALUATED, purpose: "..."}
  functions:
    - {id: FN-1, subsystem: module, inputs: [], outputs: [], mode: normal, failure_modes: [], verification: NOT_EVALUATED}
```

Continue linking formal requirements to subsystems, components, interfaces, dependencies and verification using the V1.4-supported contract fields described in `requirements_and_interfaces.md`. Keep evidence of actual checks in reports; the descriptive concept block is not itself evidence.

## Budget space before feature detail

Allocate the available envelope among main subsystems and interfaces. Record overall and usable dimensions, component envelope, moving/flow envelope, access/removal volume, wall/joint allowance, required safety gaps and residual free volume. Flag ambiguity between internal and external limits. Once CAD exists, replace estimates with measurable bounding boxes/volumes where the chosen checks support it; label actual CAD volume separately from useful/functional volume. A volume ratio alone is not a concept score.

## Review selected concept before CAD

Answer these briefly, with a reference to requirement/function/evidence or mark NOT_EVALUATED:

1. Does the concept satisfy the primary user outcome and operating context?
2. Was a viable simpler or materially different concept considered?
3. Does every component have a function or explicit secondary reason?
4. Are large reserved spaces functional, service-related, safety-related or unexplained?
5. Are critical external and internal interfaces defined or identified as unknown?
6. Can the product be installed, assembled, retained, serviced and disassembled?
7. Are requirements contradictory or based on dimensions that are only assumptions?
8. Does the concept suit the selected fabrication process and envelope?
9. What failures can currently be checked, and what requires engineering judgment or physical testing?

Resolve critical contradictions and architecture risks before detailed CAD. A concept can advance with noncritical unknowns only when their impact, owner/test and reversibility are clear. Record the selected architecture before implementation so review is not rewritten to rationalize an already-modeled solution.

## Proportionality

For a low-risk, obvious bracket/spacer, a compact note listing purpose, envelope, concept and assumptions is enough; use the lightweight V1.4 project level. For products with several plausible arrangements, load paths, maintenance paths or material/fluid flows, use the product contract and full review. Do not require formal scoring tables, complete reports or two artificial concepts for every trivial CAD request.
