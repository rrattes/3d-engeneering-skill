# Reliability foundation — implementation plan

**Goal:** Incorporate robust BREP pair checks, datum/point face references and signed worst-case tolerance stacks. User authorized these three fronts, reusing regression controls. Execute inline; concise tool output and targeted reads; no parallel agent implementation or duplicated full-context exploration.

**Architecture/impact:** Shared cli/brep_pairs.py supplies solid-pair checks to validation.py and helical_motion.py; face_references.py extends selector compatibility and diagnostics; tolerance_stack.py evaluates declared bounded linear chains, integrated into assembly reporting/release. Skill references explain contracts and limits. No dependencies, database, product geometry or Orca changes. Preserve the current uncommitted1.6.0 files and immutable image/deliveries; release additive1.7.0 after verification.

**Scope:** Exact static distance retained; zero-clearance allowed contact can omit costly distance in helical paths. Parent-located Compound handled by solid decomposition. Unknown operations never pass; observed collisions dominate unknowns. Face point selector uses actual trimmed face distance and ambiguity handling; existing center selectors preserved without silent widening. Partial face-selection failures prevent overall thickness PASS. Tolerance chains use signed coefficients and explicit dimension intervals, combine duplicate dimension references, distinguish assumed/unqualified bounds, preserve evidence source, and cannot claim physical fit.

## Tasks/evidence

- [x] 1. Write failing controls for imported/nested multi-solid Compounds, void separation, contacts, minimum gaps and unknown kernel. Share atomic BREP primitive; preserve linear/helical behavior and report fields.
- [x] 2. Write controls for trimmed point references, moved centroids, ambiguity, malformed selectors and partial thickness selection. Implement diagnostics and validate against actual basket bracket STEP without changing its delivery.
- [x] 3. Write controls for symmetric/asymmetric intervals, signed worst cases, duplicate references, unknown uncertainties, invalid input and assumed bounds. Integrate native CLI success/fail/unknown release gates.
- [x] 4. Update skill, contracts and version packaging; run targeted/source+packaged full regressions once stable, legacy acceptance, image/source checks and portable inventory. Independent review scoped to new modules/contracts when useful. Record evidence and update workflow.

## Token-use policy

Use focused reads; keep long output in logs; one combined new regression entrypoint. Reuse existing fixtures/runners. Run cheap targeted controls after changes and full suites only at the integration gate. Cache durable decisions here, not repeated chat explanations. Report actual counts; do not estimate a token-saving percentage without measurement.

Tasks1–3 complete:16 targeted controls PASS. Real bracket point references and scoped thickness PASS; wrong-phase static collision correctly FAIL. Review found contact-tolerance loophole, reproduced RED and corrected; nearest-candidate semantics documented. Full source/packaged/legacy regression pending. Runtime packaging matches all source module hashes;1.6.0 image unchanged. Portable inventory verified.

Task4 complete:19/19 source +19/19 packaged entrypoints;35 legacy acceptance controls;16 new foundation tests,16 retained helical tests and5 release integration tests per mode PASS. Native1.7.0 doctor/source-image equality/portable inventory PASS. Prior1.6.0 image and original basket selected delivery unchanged. No scope expansion beyond authorized reliability foundations and necessary shared primitive consolidation.
