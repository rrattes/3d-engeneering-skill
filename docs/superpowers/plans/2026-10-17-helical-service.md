# Helical service verification implementation plan

> Execution: inline, using executing-plans; preserve the existing evolution worktree and prior documentation changes.

**Goal:** Incorporate sampled helical BREP service paths into CAD3D and its engineering skill.
**Architecture:** A focused cli/helical_motion.py evaluator supplies transforms and conservative collision broad phase; service_states.py dispatches explicit motion types and preserves legacy linear paths. Reports flow through the existing validation/publication pipeline.
**Tech stack:** Existing Python/build123d/OCP Docker environment; no new dependencies.
**Spec:** User-approved incorporation described in this conversation; real-world basis: Cesta_Anemonas_Rev_C/scripts/validate_printed_fasteners.py.

## Scope and impact

Add an optional motion object to explicit assembly_steps: type=helical, world axis_origin_mm/axis_direction, positive pitch_mm, handedness=right|left, optional starts=1, signed travel_mm. Positive travel follows the axis; right-handed positive travel gives positive right-hand rotation. Coupling uses lead=pitch*starts. Top-level samples specifies intervals; increase sampling to at most 90 degrees per interval (bounded budget, reject invalid/nonfinite/bool/oversized input).

Single components or rigid moving groups use original instance contacts; no group-wide waiver. Initial and final poses included. Conservative AABB separation may prove a lower-bound gap; overlapping boxes require actual BREP checks. Positive intersection volume always fails. Kernel uncertainty is NOT_EVALUATED. No continuous-motion, fit, force or strength claim.

A helical PASS only proves the sampled path. Prerequisite removal requires a separate conservative terminal-bounds separation proof; a short successful motion cannot silently remove an engaged screw from the next operation.

Affected: cli/helical_motion.py, cli/service_states.py, regression scripts, CLI version/container packaging, skill entrypoint/references, platform README and workspace workflow documentation. Existing product sources, immutable deliveries, dependencies and Orca unchanged. Preserve cad3d-engineering:1.5.0 for rollback; package additive feature as1.6.0, activate only after checks pass.

## Tasks

- [x] 1. Add and run failing controls for transforms, arbitrary/offset axes, handedness, signed travel, pitch/starts, malformed input and sampling; implement motion evaluator.
- [x] 2. Verify real collisions/contact/unknown kernel, blocked screws, original contact identities, retained obstacles and prerequisite release; integrate service evaluator without changing default linear behavior.
- [x] 3. Update skill contract/examples, source and packaged regression inventory; build1.6.0 without new dependencies. Run source/packaged regression plus actual helical-thread fixture and native CLI report integration.
- [x] 4. Review final diff, record evidence/limitations, activate verified image defaults and synchronize workflow documentation. Preserve1.5.0 and existing basket deliveries.

## Evidence ledger

Initial impact: cad3d.validate → service_states.evaluate_steps → check_service_step → assembly_path_check. The new evaluator is additive; publication consumes the existing assembly_sequence results. Prior uncommitted promotion-document edit is preserved. No project-specific geometry is copied into the platform runtime. No architectural database work.

Progress: tasks1–3 complete. Source and packaged full regression18/18 each; helical controls16/16 each. Imported Compound translation false PASS reproduced RED and corrected GREEN. Actual STEP probe right PASS/wrong hand FAIL/mirrored-left PASS,21 poses each. Native release integration covers accepted path and blocked publication with previous delivery preserved. Independent static review completed; no remaining blocker reported after atomic-solid correction. Eixo oblíquo e Compound com dois sólidos incluídos nos controles. Legacy acceptance pending; final evidence/closeout follows.

Task4 complete: acceptance35/35 PASS; doctor1.6.0 PASS; source/container hashes identical; portable kit CRC+inventory hashes PASS; baseline image1.5.0 unchanged; selected basket delivery unchanged. EVIDENCIAS.json records final state. No database/dependency/Orca changes. Final static review found no blocker after correction; no deferred minor remains from that review.
