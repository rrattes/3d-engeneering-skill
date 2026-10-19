"""Machine-readable product engineering contracts and evidence-based reviews.

This module checks traceability and CAD evidence. It deliberately does not
pretend that a complete YAML file proves function, retention strength, flow,
printability, or physical performance.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

STATES = {"PASS", "FAIL", "WARNING", "NOT_EVALUATED"}
RETENTION_METHODS = {
    "monolithic", "fastener", "snap_fit", "captured_rail", "dovetail",
    "press_fit", "gravity_seat", "gravity_seat_and_sliding_clearance",
    "gravity_seat_sliding_fit", "adhesive", "clamp", "intentional_free",
    "fixed_to_datum", "other",
}


def _read_yaml(path):
    import yaml
    return yaml.safe_load(Path(path).read_text()) or {}


def _status(checks):
    states = [x["status"] for x in checks]
    if "FAIL" in states:
        return "FAIL"
    if "WARNING" in states:
        return "WARNING"
    if "NOT_EVALUATED" in states:
        return "NOT_EVALUATED"
    return "PASS"


def _check(checks, ident, title, status, *, evidence=None, detail=None,
           severity="major", kind="automated", recommendation=None):
    checks.append({"id": ident, "title": title, "status": status,
                   "severity": severity, "kind": kind, "evidence": evidence,
                   "detail": detail, "recommendation": recommendation})


def _get_pointer(value, pointer):
    if pointer in ("", "/"):
        return value
    current = value
    for token in pointer.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        else:
            current = current[token]
    return current


def _evidence_result(project_root, evidence):
    """Return an observed JSON value; never trust a status written in YAML."""
    path = Path(evidence.get("path", ""))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("evidence paths must be project-relative and cannot escape the project")
    full = project_root / path
    if not full.is_file():
        raise FileNotFoundError(str(path))
    payload = json.loads(full.read_text())
    observed = _get_pointer(payload, evidence.get("json_pointer", ""))
    digest = hashlib.sha256(full.read_bytes()).hexdigest()
    return observed, {"path": path.as_posix(), "json_pointer": evidence.get("json_pointer", ""),
                     "observed": observed, "sha256": digest}


def _unique(items, key, label, checks):
    ids = [str(item.get(key, "")) for item in items if isinstance(item, dict)]
    dup = sorted({value for value in ids if not value or ids.count(value) > 1})
    _check(checks, f"unique-{label}", f"IDs únicos: {label}",
           "FAIL" if dup else "PASS", detail={"invalid_or_duplicate_ids": dup},
           severity="critical", recommendation=f"Declare IDs não vazios e únicos em {label}.")
    return set(ids)


def validate_architecture(project_root: Path, *, shapes=None, placed_shapes=None):
    """Validate `.cad3d/engineering.yaml` structure and CAD-linked evidence."""
    root = Path(project_root).resolve()
    contract_path = root / ".cad3d/engineering.yaml"
    if not contract_path.is_file():
        return {"status": "NOT_EVALUATED", "reason": "engineering_contract_missing",
                "contract": str(contract_path), "phases": {}, "checks": []}
    contract = _read_yaml(contract_path)
    eng = contract.get("engineering", {})
    project = eng.get("project", {})
    level = eng.get("workflow_level", "product")
    checks = []
    expected_project = ("name", "class", "purpose", "units")
    missing = [field for field in expected_project if not project.get(field) or
               str(project.get(field)).strip().lower() in ("todo", "tbd", "unknown")]
    _check(checks, "project-identity", "Identidade e propósito do produto",
           "FAIL" if missing else "PASS", detail={"missing": missing}, severity="critical",
           recommendation="Defina nome, classe, função do produto e unidades explícitas.")

    reqs = eng.get("requirements", []) or []
    subsystems = (eng.get("functional_architecture", {}) or {}).get("subsystems", []) or []
    components = (eng.get("mechanical_architecture", {}) or {}).get("components", []) or []
    interfaces = (eng.get("mechanical_architecture", {}) or {}).get("interfaces", []) or []
    req_ids = _unique(reqs, "id", "requirements", checks)
    subsystem_ids = _unique(subsystems, "id", "subsystems", checks)
    component_ids = _unique(components, "id", "components", checks)
    interface_ids = _unique(interfaces, "id", "interfaces", checks)
    assembly_path = root / ".cad3d/assembly.yaml"
    assembly = _read_yaml(assembly_path) if assembly_path.is_file() else {}
    assembly_components = {str(item.get("id")): item for item in assembly.get("components", [])}
    assembly_pairs = {frozenset((str(item.get("a")), str(item.get("b")))): item
                      for item in assembly.get("interfaces", [])}

    phase_checks = {"requirements": [], "functional_architecture": [], "mechanical_architecture": [],
                    "modeling": [], "system_verification": [], "manufacturing": []}
    for field in ("operating_conditions", "measurements", "external_interfaces",
                  "acceptance_criteria", "risks_and_unknowns"):
        value = eng.get(field, [])
        minimum = 1 if level == "product" else (0 if field in ("operating_conditions", "risks_and_unknowns") else 1)
        ok = bool(value) and isinstance(value, list) if minimum else isinstance(value, list)
        _check(phase_checks["requirements"], f"requirements-{field}", field.replace("_", " ").title(),
               "PASS" if ok else "FAIL", detail={"item_count": len(value) if isinstance(value, list) else 0},
               severity="critical", recommendation=f"Registre {field.replace('_', ' ')} antes de fechar a arquitetura.")
    measurements = eng.get("measurements", []) or []
    unclassified_measurements = [m.get("id", "<missing-id>") for m in measurements
        if m.get("confidence") not in ("verified", "assumption") or
        (m.get("confidence") == "verified" and not m.get("source")) or
        (m.get("confidence") == "assumption" and not m.get("uncertainty"))]
    _check(phase_checks["requirements"], "measurement-evidence", "Medições separadas de hipóteses",
           "FAIL" if unclassified_measurements else ("PASS" if measurements else "NOT_EVALUATED"),
           detail={"unclassified": unclassified_measurements}, severity="critical",
           recommendation="Classifique cada medida como verified com source, ou assumption com uncertainty.")
    empty_criteria = [x.get("id", "<missing-id>") for x in eng.get("acceptance_criteria", []) or []
                      if not x.get("method") or not x.get("threshold")]
    _check(phase_checks["requirements"], "acceptance-criteria-defined", "Critérios de aceitação mensuráveis",
           "FAIL" if empty_criteria else ("PASS" if eng.get("acceptance_criteria") else "NOT_EVALUATED"),
           detail={"incomplete": empty_criteria}, severity="critical",
           recommendation="Defina método de verificação e limiar observável para cada critério.")
    _check(checks, "requirements-phase", "Fase 1: requisitos", _status(phase_checks["requirements"]),
           detail=phase_checks["requirements"], severity="critical")

    min_subsystems = 1 if level == "lightweight" else 2
    _check(phase_checks["functional_architecture"], "functional-subsystems", "Subsistemas com função",
           "WARNING" if len(subsystems) >= min_subsystems and all(x.get("purpose") for x in subsystems) else "FAIL",
           detail={"count": len(subsystems), "minimum": min_subsystems}, severity="critical",
           kind="engineering_judgment",
           recommendation="Revise se as funções declaradas cobrem conceitualmente a operação; presença de campos não comprova funcionamento.")
    flows = (eng.get("functional_architecture", {}) or {}).get("flows", []) or []
    flow_ids = _unique(flows, "id", "flows", phase_checks["functional_architecture"])
    for flow in flows:
        route = flow.get("path", [])
        known_nodes = subsystem_ids | component_ids
        unknown = [str(node) for node in route if str(node) not in known_nodes]
        status = "WARNING" if len(route) >= 2 and not unknown else "FAIL"
        _check(phase_checks["functional_architecture"], f"flow-{flow.get('id')}",
               f"Fluxo funcional {flow.get('id')}", status,
               detail={"path": route, "unknown_nodes": unknown,
                       "evidence_limit": "declared topology only; conceptual operation needs engineering review"},
               severity="critical", kind="engineering_judgment",
               recommendation="Verifique se portas, estados e transições formam uma sequência funcional real.")
    fa = eng.get("functional_architecture", {}) or {}
    for key in ("operating_modes", "failure_modes"):
        ok = bool(fa.get(key))
        _check(phase_checks["functional_architecture"], f"functional-{key}", key.replace("_", " ").title(),
               ("WARNING" if ok else "FAIL"), detail={"item_count": len(fa.get(key, []) or []),
               "evidence_limit": "declared cases require engineering review"},
               severity="critical", kind="engineering_judgment",
               recommendation=f"Revise a cobertura e plausibilidade de {key.replace('_', ' ')}; a lista não comprova comportamento.")
    _check(checks, "functional-architecture-phase", "Fase 2: arquitetura funcional",
           _status(phase_checks["functional_architecture"]), detail=phase_checks["functional_architecture"], severity="critical")

    if not assembly_components and components:
        _check(phase_checks["mechanical_architecture"], "assembly-manifest", "Instâncias CAD de montagem",
               "FAIL", severity="critical", recommendation="Declare as instâncias posicionadas em .cad3d/assembly.yaml.")
    for comp in components:
        ident = str(comp.get("id"))
        retention = comp.get("retention") or {}
        method = retention.get("method")
        evidence = {"assembly_component": assembly_components.get(ident),
                    "part": comp.get("part"), "function": comp.get("function"),
                    "retention": retention}
        if ident not in assembly_components:
            st = "FAIL"; reason = "component_not_present_in_cad_assembly"
        elif not comp.get("part") or not comp.get("function"):
            st = "FAIL"; reason = "part_or_function_missing"
        elif not method:
            st = "FAIL"; reason = "retention_method_missing"
        elif method not in RETENTION_METHODS:
            st = "FAIL"; reason = "unknown_retention_method"
        elif method == "intentional_free":
            st = "PASS" if retention.get("reason") else "FAIL"
            reason = "intentional_free_documented" if st == "PASS" else "intentional_free_requires_reason"
        elif method == "monolithic":
            solid_count = len((shapes or {}).get(comp.get("part"), []).solids()) if shapes and comp.get("part") in shapes else None
            st = "PASS" if solid_count == 1 else ("WARNING" if solid_count is None else "FAIL")
            reason = "single_connected_brep" if st == "PASS" else ("single-body verification deferred until CAD build" if st == "WARNING" else "monolithic_solid_not_proven")
        elif method == "fixed_to_datum":
            st = "WARNING" if retention.get("datum") and retention.get("fastener_interface") else "FAIL"
            reason = "external_fixing_interface_declared_but_load_not_analyzed" if st == "WARNING" else "datum_or_fixing_interface_missing"
        else:
            referenced = retention.get("interface_ids", []) or []
            missing_refs = [x for x in referenced if x not in interface_ids]
            connected = [i for i in interfaces if i.get("id") in referenced and ident in (i.get("components") or [])]
            pair_refs = [i for i in connected if len(i.get("components", [])) == 2 and
                         frozenset(map(str, i["components"])) in assembly_pairs]
            if not referenced or missing_refs or not connected or len(pair_refs) != len(connected):
                st = "FAIL"; reason = "retention_has_no_complete_positioned_interface"
            else:
                st = "WARNING"; reason = "retention_geometry_declared; load_or_capture_strength_not_proven"
        _check(phase_checks["mechanical_architecture"], f"retention-{ident}",
               f"Retenção de {ident}", st, evidence={"component": evidence, "reason": reason},
               severity="critical" if st == "FAIL" else "major",
               recommendation="Declare o método e relacione interfaces CAD posicionadas; valide força/retensão com método apropriado.")

    for interface in interfaces:
        iid = str(interface.get("id")); ends = list(map(str, interface.get("components", [])))
        unknown = [x for x in ends if x not in component_ids or x not in assembly_components]
        cad_pair = frozenset(ends) in assembly_pairs if len(ends) == 2 else False
        has_tolerance = interface.get("tolerance_mm") is not None or interface.get("tolerance_profile") is not None
        has_datum = bool(interface.get("positioning") or interface.get("datums"))
        st = "PASS" if len(ends) == 2 and not unknown and cad_pair and interface.get("kind") and has_tolerance and has_datum else "FAIL"
        _check(phase_checks["mechanical_architecture"], f"interface-{iid}",
               f"Interface {iid} vinculada ao assembly", st,
               evidence={"components": ends, "cad_pair_found": cad_pair, "unknown_components": unknown,
                         "tolerance_defined": has_tolerance, "positioning_defined": has_datum},
               severity="critical", recommendation="Vincule interface aos componentes e ao assembly; defina datum/posicionamento e tolerância nominal ou perfil.")
    mech = eng.get("mechanical_architecture", {}) or {}
    for field in ("maintenance_access", "assembly_steps", "print_split"):
        value = mech.get(field, [])
        _check(phase_checks["mechanical_architecture"], f"mechanical-{field}", field.replace("_", " ").title(),
               "WARNING" if value else "FAIL",
               detail={"item_count": len(value) if isinstance(value, list) else 1 if value else 0,
                       "evidence_limit": "declaration completeness only; outcome is not physically verified"},
               severity="major", kind="engineering_judgment",
               recommendation=f"Revise a viabilidade real de {field.replace('_', ' ')} e vincule a uma evidência executada.")
    _check(checks, "mechanical-architecture-phase", "Fase 3: arquitetura mecânica",
           _status(phase_checks["mechanical_architecture"]), detail=phase_checks["mechanical_architecture"], severity="critical")

    flow_results = []
    flow_shapes = placed_shapes if placed_shapes is not None else shapes
    if flows and flow_shapes is not None:
        flow_results = validate_flow_paths(flow_shapes, flows)
        for result in flow_results:
            _check(phase_checks["system_verification"], f"flow-geometry-{result['id']}",
                   f"Percurso físico {result['id']}", result["status"], evidence=result,
                   severity="critical" if result["status"] == "FAIL" else "major",
                   recommendation="Corrija a obstrução da rota declarada ou marque o caminho como não avaliado.")
    elif flows:
        for item in flows:
            _check(phase_checks["system_verification"], f"flow-geometry-{item.get('id')}",
                   f"Percurso físico {item.get('id')}", "NOT_EVALUATED", severity="critical",
                   recommendation="Execute cad3d architecture validate com a geometria paramétrica carregada.")
    for req in reqs:
        rid = str(req.get("id")); ver = req.get("verification") or {}
        missing_refs = [x for x in req.get("components", []) or [] if x not in component_ids]
        if not req.get("description") or req.get("subsystem") not in subsystem_ids or missing_refs or not ver.get("method"):
            observed = "FAIL"
            ev = {"unknown_components": missing_refs, "subsystem": req.get("subsystem"), "method": ver.get("method")}
        elif ver.get("method") == "flow_path" and ver.get("target"):
            target = next((x for x in flow_results if x["id"] == ver["target"]), None)
            observed = target["status"] if target else "NOT_EVALUATED"
            ev = {"flow_result": target}
        elif ver.get("evidence"):
            evs = []
            for item in ver.get("evidence", []):
                try:
                    value, proof = _evidence_result(root, item); proof["expected"] = item.get("expected")
                    proof["status"] = "PASS" if value == item.get("expected") else "FAIL"
                    evs.append(proof)
                except Exception as exc:
                    evs.append({"path": item.get("path"), "status": "NOT_EVALUATED", "detail": str(exc)})
            observed = "PASS" if evs and all(x["status"] == "PASS" for x in evs) else (
                "FAIL" if any(x["status"] == "FAIL" for x in evs) else "NOT_EVALUATED")
            ev = {"items": evs}
        else:
            observed = "NOT_EVALUATED"; ev = {"reason": "no_machine_readable_evidence"}
        declared = str(ver.get("status", "NOT_EVALUATED")).upper()
        if declared not in STATES:
            declared = "FAIL"
        status = observed
        if declared == "PASS" and observed != "PASS":
            status = "FAIL"
        _check(phase_checks["system_verification"], f"requirement-{rid}",
               f"Requisito {rid}: {req.get('description', '')}", status,
               evidence={"declared_status_not_trusted": declared, "observed": observed, **ev},
               severity="critical" if req.get("critical", True) else "major",
               recommendation="Produza evidência observável que corresponda ao método de verificação do requisito.")
    open_risks = [r for r in eng.get("risks_and_unknowns", []) or [] if r.get("status", "open") != "closed"]
    critical_open = [r for r in open_risks if str(r.get("severity", "major")).lower() == "critical"]
    _check(phase_checks["system_verification"], "residual-risks", "Riscos residuais classificados",
           "FAIL" if critical_open else ("WARNING" if open_risks else "PASS"),
           evidence={"open_risks": open_risks}, severity="critical" if critical_open else "major",
           kind="engineering_judgment", recommendation="Reduza riscos críticos antes da aprovação; mantenha riscos não fechados no relatório.")
    _check(checks, "system-verification-phase", "Fase 5: verificação sistêmica",
           _status(phase_checks["system_verification"]), detail=phase_checks["system_verification"], severity="critical")

    model_missing = []
    if shapes is not None:
        model_missing = [x.get("id") for x in components if not x.get("part") or x.get("part") not in shapes]
    model_state = "NOT_EVALUATED" if shapes is None else ("FAIL" if model_missing else "PASS")
    _check(phase_checks["modeling"], "component-model-links", "Fase 4: peças e componentes modelados",
           model_state, evidence={"missing_parts": model_missing, "shape_names": sorted(shapes) if shapes is not None else None},
           severity="critical", recommendation="Gere ou corrija as peças paramétricas referenciadas no contrato.")
    _check(checks, "modeling-phase", "Fase 4: modelagem", _status(phase_checks["modeling"]),
           detail=phase_checks["modeling"], severity="critical")

    validation_path = root / "build/outputs/validation.json"
    validation = json.loads(validation_path.read_text()) if validation_path.is_file() else None
    manifest_path = root / "build/outputs/manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else None
    freshness = {"status": "NOT_EVALUATED", "reason": "manifest_missing"}
    if validation is not None and manifest is not None:
        try:
            from source_fingerprint import SCHEMA, project_fingerprint
            recorded_inputs = manifest.get("project_inputs")
            if not isinstance(recorded_inputs, dict) or recorded_inputs.get("schema") != SCHEMA:
                freshness = {"status": "NOT_EVALUATED", "reason": "manifest_dependency_fingerprint_missing_or_unsupported"}
            else:
                current_inputs = project_fingerprint(root)
                artifact_hashes = {x.get("path"): x.get("sha256") for x in manifest.get("artifacts", [])}
                mismatched = []
                if current_inputs != recorded_inputs:
                    mismatched.append("project_inputs")
                if artifact_hashes.get("validation.json") != hashlib.sha256(validation_path.read_bytes()).hexdigest():
                    mismatched.append("validation_sha256")
                before = {x["path"]: x["sha256"] for x in recorded_inputs.get("files", [])}
                after = {x["path"]: x["sha256"] for x in current_inputs["files"]}
                freshness = {"status": "FAIL" if mismatched else "PASS",
                             "reason": "model_or_validation_artifact_stale" if mismatched else "project_input_and_validation_hashes_match",
                             "mismatched_hashes": mismatched,
                             "changed_inputs": sorted(k for k in before.keys() & after.keys() if before[k] != after[k]),
                             "added_inputs": sorted(after.keys() - before.keys()),
                             "deleted_inputs": sorted(before.keys() - after.keys()),
                             "scope": current_inputs["scope"]}
        except Exception as exc:
            freshness = {"status": "NOT_EVALUATED", "reason": "freshness_check_failed", "detail": str(exc)}
    if validation is None:
        st = "NOT_EVALUATED"
    elif freshness["status"] == "FAIL":
        st = "FAIL"
    elif freshness["status"] == "NOT_EVALUATED":
        st = "NOT_EVALUATED"
    elif validation.get("states", {}).get("geometric_validity") == "FAIL" or validation.get("states", {}).get("assembly_validity") == "FAIL":
        st = "FAIL"
    elif validation.get("states", {}).get("assembly_validity") == "NOT_EVALUATED" and len(assembly_components) > 1:
        st = "NOT_EVALUATED"
    else:
        st = "PASS"
    _check(phase_checks["system_verification"], "cad-review-input", "Relatório CAD atual presente e sem falha crítica",
           st, evidence={"path": "build/outputs/validation.json" if validation else None,
                         "states": validation.get("states") if validation else None,
                         "source_freshness": freshness}, severity="critical",
           recommendation="Execute cad3d validate depois da última mudança de geometria ou pose.")
    profile = (eng.get("manufacturing", {}) or {})
    physical = profile.get("physical_validation", "NOT_EVALUATED")
    fab_status = "NOT_EVALUATED" if physical == "NOT_EVALUATED" else str(physical).upper()
    if fab_status not in STATES:
        fab_status = "NOT_EVALUATED"
    _check(phase_checks["manufacturing"], "physical-validation", "Validação física", fab_status,
           evidence=profile.get("physical_evidence"), severity="major",
           kind="engineering_judgment", recommendation="Registre resultados dimensionais e funcionais de protótipo quando houver impressão física.")
    _check(checks, "manufacturing-phase", "Fase 6: fabricação", _status(phase_checks["manufacturing"]),
           detail=phase_checks["manufacturing"], severity="major")

    phase_summary = {name: _status(items) for name, items in phase_checks.items()}
    return {"status": _status(checks), "workflow_level": level,
            "contract": ".cad3d/engineering.yaml", "phases": phase_summary,
            "requirements": {str(x.get("id")): next((c["status"] for c in phase_checks["system_verification"] if c["id"] == f"requirement-{x.get('id')}"), "NOT_EVALUATED") for x in reqs},
            "checks": checks, "flow_paths": flow_results,
            "limits": ["contract completeness is not engineering proof",
                       "contact-free CAD pairs do not prove structural retention or joint strength",
                       "judgment, loads, seals, physical fit and functional behavior require review/test"]}


def validate_flow_paths(shapes, flows):
    """Sample declared physical corridors against actual B-rep material.

    This checks geometric clearance along a declared path. It is not CFD and
    does not calculate flow rate, pressure loss, sealing, or system behavior.
    """
    from build123d import Vector
    results = []
    for flow in flows:
        ident = str(flow.get("id", "flow")); spec = flow.get("geometry_check", {}) or {}
        points = spec.get("centerline_mm", [])
        radius = float(spec.get("clearance_radius_mm", 0.0))
        step = float(spec.get("sample_step_mm", 1.0))
        domain = spec.get("domain_bbox_mm")
        if len(points) < 2 or radius < 0 or step <= 0 or not domain or len(domain) != 2:
            results.append({"id": ident, "status": "NOT_EVALUATED", "method": "B-rep path sampling",
                            "reason": "centerline_radius_or_domain_missing"}); continue
        lo, hi = [list(map(float, x)) for x in domain]
        material = []
        for shape in shapes.values():
            material.extend(shape.solids())
        samples = []
        blocked = None
        for segment_index, (aa, bb) in enumerate(zip(points, points[1:])):
            a = Vector(*map(float, aa)); b = Vector(*map(float, bb)); delta = b - a
            length = delta.length
            if length <= 1e-9:
                continue
            direction = delta.normalized()
            trial = Vector(1, 0, 0) if abs(direction.X) < .8 else Vector(0, 1, 0)
            u = direction.cross(trial).normalized(); v = direction.cross(u).normalized()
            nsteps = max(1, int(math.ceil(length / step)))
            for i in range(nsteps + 1):
                t = min(1.0, i / nsteps)
                c = a + delta * t
                ring = [Vector(0, 0, 0)]
                if radius > 0:
                    ring.extend((u * math.cos(k * math.tau / 8) + v * math.sin(k * math.tau / 8)) * radius
                                for k in range(8))
                for offset in ring:
                    q = c + offset
                    xyz = [q.X, q.Y, q.Z]
                    if any(xyz[j] < lo[j] - 1e-7 or xyz[j] > hi[j] + 1e-7 for j in range(3)):
                        blocked = {"segment": segment_index, "point_mm": xyz, "reason": "outside_declared_domain"}; break
                    for solid in material:
                        if solid.is_inside(q, tolerance=1e-5):
                            blocked = {"segment": segment_index, "point_mm": xyz, "reason": "intersects_solid_brep"}; break
                    if blocked:
                        break
                    samples.append(xyz)
                if blocked:
                    break
            if blocked:
                break
        results.append({"id": ident, "status": "FAIL" if blocked else "PASS",
                        "method": "sampled centerline plus 8-point cross-section against actual OCP B-rep solids",
                        "sample_step_mm": step, "clearance_radius_mm": radius,
                        "sampled_points": len(samples), "blocking_sample": blocked,
                        "limitations": ["approximate swept clearance; between-sample defects may remain",
                                        "no CFD, pressure-drop, flow-rate, turbulence, seal, pump, or priming analysis"]})
    return results


def write_architecture_report(project_root: Path, *, shapes=None, placed_shapes=None):
    report = validate_architecture(project_root, shapes=shapes, placed_shapes=placed_shapes)
    output = Path(project_root) / "build/outputs/architecture-review.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report, output


def write_design_review(project_root: Path, *, shapes=None, placed_shapes=None):
    report, output = write_architecture_report(project_root, shapes=shapes, placed_shapes=placed_shapes)
    checks = report["checks"]
    findings = []
    for c in checks:
        if c["status"] != "PASS":
            findings.append({"problem": c["title"], "evidence": c.get("evidence") or c.get("detail"),
                             "impact": c.get("detail"), "severity": c.get("severity"),
                             "status": c["status"], "correction": c.get("recommendation"),
                             "verification_needed": c["kind"] != "automated"})
    final = {**report, "review_type": "automated_traceability_plus_explicit_engineering_judgment_limits",
             "reviewer_independence": "NOT_CLAIMED; use a fresh Codex context for adversarial review",
             "findings": findings,
             "approval": "BLOCKED" if report["status"] == "FAIL" else
                         ("PENDING_EVIDENCE" if report["status"] == "NOT_EVALUATED" else
                          "CONDITIONAL_REVIEW" if report["status"] == "WARNING" else "PASS"),
             "outputs": {"architecture_report": str(output.relative_to(project_root))}}
    path = Path(project_root) / "build/outputs/design-review.json"
    path.write_text(json.dumps(final, indent=2) + "\n")
    return final, path
