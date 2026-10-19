# Evolution regression registry

Requirements: docs/evaluations/review-20261017/AVALIACAO.md A01–A10 and docs/superpowers/plans/2026-10-17-evolucao-3d-engineering.md. Executable assertions, not this registry, are evidence. Logs identify source/packaged mode and image IDs.

| TEST-ID / family | Script | Protected behavior |
|---|---|---|
| ENG2-CAL-01/02, PROFILE-01 | scripts/test-calibration-profile-regression.py | Calibration initialization/identity, unknown printer |
| ENG2-CAT-01/02/03 | scripts/test-component-catalog.py | FDM/commercial selection, instances/quantities, invalid metadata |
| ENG2-PUB-01/02/03/04 | scripts/test-artifact-publication.py | Failure isolation, current pointer, input freshness, concurrency |
| ENG2-REL-01/02/03 | scripts/test-release-integration.py | Real release, thin geometry, corrupted final STEP, unknown service |
| ENG2-PAR-01/02/03 | scripts/test-parametric-propagation.py | Real BREP variations, supported constraints and screw stack |
| ENG2-SVC-01/02/03/04 | scripts/test-service-states.py | Retained hardware, grouped connectors, counterhold, unknown, nominal stack |
| ENG2-VIS-01/02/03/04 | scripts/test-presentation-catalog.py | Separate viewport, explicit colors, actual part gallery; manual image review still required |
| ENG2-VIS-05 | scripts/test-camera-framing.py | Actual projected bounds stay inside model viewport |
| ENG2-COM-01/02/03 | scripts/test-commercial-provenance.py | Source scope, revision lock, body vs plug collision |
| ENG2-KIT-01/02 | scripts/test-portable-kit.py | Package scope/projections/paths, separate runtime limitations |
| ENG2-SKILL-01 | docs/evaluations/evolution-20261017/scenarios/PROTOCOL.md | Planned behavioral generation, actual runs recorded separately |
| WF-01–11 | scripts/test-workflow-gates.py | Dependency ordering, unresolved critical requirements, stale/missing evidence, warning disposition, AIO-style colored interface views, product-design prerequisite, prototype-vs-physical claim boundary |
| WF-12–17 | scripts/test-workflow-commands.py | Migration/init, missing contract, path containment, physical evidence hashes, malformed records and WARNING preservation |
| WF-18–20 | scripts/test-mandatory-workflow-gate.py | Stops model import before required phases; missing contract and missing requirements evidence stay blocked |

Legacy entrypoints: scripts/test-v14-acceptance.py; scripts/test-source-fingerprint.py; scripts/test-product-geometry-gate.py; scripts/test-export-current.py; scripts/test-interface-render.py; scripts/test-preflight.py; scripts/test-fastener-envelope-regression.py; template/assembly-demo tests. Historical counts are not current proof.

Runner: `python scripts/run-evolution-regressions.py --mode source|packaged --suite smoke|targeted|integration|full --output <new-empty-dir>`. CAD runs only in Docker. Packaged mode imports image CLI, not worktree CLI. Full V1.4 acceptance is a separate host orchestrator with unique CAD3D_V14_ACCEPTANCE_DIR and wrapper PATH; results must not be silently omitted.

NOT_EVALUATED: physical fit/load/temperature, real printer, real torque, complete thickness/continuous motion, unavailable host agents. Architecture proposals (SQLite/Qdrant/RunContext redesign) were explicitly deferred by user and are not implemented.
