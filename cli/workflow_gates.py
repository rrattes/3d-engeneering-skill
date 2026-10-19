"""Fail-closed, dependency-ordered workflow gates for product CAD projects."""
from __future__ import annotations

import hashlib
from pathlib import Path

GATE_DEPENDENCIES = {
    'requirements': (),
    'functional_architecture': ('requirements',),
    'mechanical_architecture': ('functional_architecture',),
    'modeling': ('mechanical_architecture',),
    'system_verification': ('modeling',),
    'visual_review': ('system_verification',),
    'product_design': ('visual_review',),
    'manufacturing': ('system_verification', 'visual_review'),
    'slicing': ('manufacturing',),
    'physical_validation': ('manufacturing',),
    'prototype_release': ('modeling', 'system_verification', 'visual_review'),
}
PHASE_FOR_GATE = {
    'requirements': 'requirements',
    'functional_architecture': 'functional_architecture',
    'mechanical_architecture': 'mechanical_architecture',
    'system_verification': 'system_verification',
}
REQUIRED_VIEWS = ('iso', 'top', 'front', 'side', 'section', 'exploded', 'hidden')
ACCEPTED_DISPOSITION = 'accepted_with_followup'


def _finding_list(architecture, phase):
    phase_id = phase.replace('_', '-') + '-phase'
    summary = next((item for item in architecture.get('checks', [])
                    if item.get('id') == phase_id), None)
    detail = summary.get('detail', []) if summary else []
    return [item for item in detail if isinstance(item, dict)]


def _phase_gate(architecture, phase, dispositions):
    state = architecture.get('phases', {}).get(phase, 'NOT_EVALUATED')
    if state == 'PASS':
        return {'status': 'PASS', 'observed_status': state, 'dispositions': []}
    if state in ('FAIL', 'NOT_EVALUATED'):
        return {'status': state, 'observed_status': state,
                'reason': 'phase_must_pass_before_advancement'}
    if state != 'WARNING':
        return {'status': 'FAIL', 'observed_status': state, 'reason': 'unknown_phase_status'}

    details = _finding_list(architecture, phase)
    unresolved = [item for item in details
                  if item.get('status') in ('FAIL', 'NOT_EVALUATED')]
    unsupported = [item for item in details
                   if item.get('status') not in ('PASS', 'WARNING', 'FAIL',
                                                 'NOT_EVALUATED', 'NOT_APPLICABLE')]
    if unresolved or unsupported:
        blockers = unresolved + unsupported
        return {'status': 'FAIL' if any(item.get('status') == 'FAIL' for item in blockers)
                else 'BLOCKED', 'observed_status': state,
                'reason': 'phase_contains_unresolved_evidence',
                'unresolved_critical_ids': [item.get('id', '<missing-id>') for item in blockers]}
    findings = [item for item in details if item.get('status') == 'WARNING']
    by_id = {item.get('check_id', item.get('id')): item for item in dispositions
             if isinstance(item, dict)}
    unresolved = []
    accepted = []
    for finding in findings:
        ident = finding.get('id')
        disposition = by_id.get(ident)
        valid = (finding.get('severity') != 'critical' and disposition is not None
                 and disposition.get('decision') == ACCEPTED_DISPOSITION
                 and all(str(disposition.get(field, '')).strip()
                         for field in ('rationale', 'owner', 'follow_up')))
        if valid:
            accepted.append(ident)
        else:
            unresolved.append(ident)
    if not findings or unresolved:
        return {'status': 'BLOCKED', 'observed_status': state,
                'reason': 'warnings_need_noncritical_disposition',
                'unresolved_warning_ids': unresolved or ['phase_warning_details_missing']}
    return {'status': 'PASS', 'observed_status': state, 'dispositions': accepted,
            'reason': 'warnings_explicitly_dispositioned'}


def _simple_gate(status, *, reason=None, extra=None, dispositions=(), check_id=None):
    if status == 'PASS':
        result = {'status': 'PASS'}
    elif status == 'WARNING':
        accepted = next((item for item in dispositions if isinstance(item, dict)
                         and item.get('check_id') == check_id
                         and item.get('decision') == ACCEPTED_DISPOSITION
                         and all(str(item.get(field, '')).strip()
                                 for field in ('rationale', 'owner', 'follow_up'))), None)
        result = ({'status': 'PASS', 'observed_status': 'WARNING',
                   'dispositions': [check_id], 'reason': 'warning_explicitly_dispositioned'}
                  if accepted else {'status': 'BLOCKED',
                                    'reason': reason or 'warning_needs_disposition',
                                    'required_disposition': check_id})
    elif status in ('FAIL', 'NOT_EVALUATED'):
        result = {'status': status, 'reason': reason or 'required_evidence_not_passed'}
    else:
        result = {'status': 'FAIL', 'reason': reason or 'unsupported_evidence_status'}
    if extra:
        result.update(extra)
    return result


def _visual_gate(views, visual_review, image_hashes, manifest_sha256, critical_interfaces):
    if not isinstance(views, dict) or views.get('status') != 'PASS':
        return _simple_gate(views.get('status', 'NOT_EVALUATED') if isinstance(views, dict) else 'NOT_EVALUATED',
                            reason='engineering_views_not_passed')
    by_view = {item.get('view'): item for item in views.get('views', []) if isinstance(item, dict)}
    missing_generated = [name for name in REQUIRED_VIEWS if name not in by_view]
    if missing_generated:
        return {'status': 'FAIL', 'reason': 'required_engineering_views_missing',
                'missing_views': missing_generated}
    components = views.get('components', [])
    colors = views.get('component_colors', {})
    uncolored = [name for name in components if name not in colors]
    if len(components) > 1 and uncolored:
        return {'status': 'FAIL', 'reason': 'assembly_component_colors_missing',
                'uncolored_components': uncolored}
    if not isinstance(visual_review, dict):
        return {'status': 'NOT_EVALUATED', 'reason': 'visual_review_record_missing'}
    if not str(visual_review.get('reviewer', '')).strip():
        return {'status': 'FAIL', 'reason': 'visual_reviewer_missing'}
    if not manifest_sha256 or visual_review.get('source_manifest_sha256') != manifest_sha256:
        return {'status': 'FAIL', 'reason': 'visual_review_model_revision_stale'}
    reviewed = {item.get('view'): item for item in visual_review.get('views', []) if isinstance(item, dict)}
    missing_reviewed = []
    stale = []
    not_inspected = []
    unresolved = []
    required = list(REQUIRED_VIEWS)
    for ident in critical_interfaces or []:
        key = f'interface:{ident}'
        required.append(key)
    for name in required:
        entry = reviewed.get(name)
        generated = by_view.get(name) if not name.startswith('interface:') else next(
            (item for item in views.get('views', []) if item.get('view') == 'interfaces'
             and item.get('interface') == name.split(':', 1)[1]), None)
        if entry is None or generated is None:
            missing_reviewed.append(name)
            continue
        path = generated.get('path')
        if entry.get('path') != path or entry.get('sha256') != (image_hashes or {}).get(path):
            stale.append(name)
        if entry.get('inspected') is not True:
            not_inspected.append(name)
        findings = entry.get('findings', [])
        if any(not isinstance(item, dict) or item.get('status') != 'resolved'
               for item in findings):
            unresolved.append(name)
    if missing_reviewed or stale or not_inspected or unresolved:
        return {'status': 'FAIL', 'reason': 'visual_evidence_incomplete_or_stale',
                'missing_views': missing_reviewed, 'stale_views': stale,
                'not_inspected': not_inspected, 'unresolved_findings': unresolved}
    return {'status': 'PASS', 'reviewer': visual_review['reviewer'],
            'reviewed_views': required, 'source_manifest_sha256': manifest_sha256,
            'scope': 'CAD image legibility and interface visibility only; not physical fit/function proof'}


def evaluate_workflow(*, architecture, validation=None, views=None, visual_review=None,
                      image_hashes=None, manifest_sha256=None, dispositions=(),
                      critical_interfaces=(), slicing_status='NOT_EVALUATED',
                      physical_validation_status='NOT_EVALUATED', requested_gate=None):
    """Compute every gate from current evidence; never trust a user-set gate PASS."""
    gates = {}
    for gate, dependencies in GATE_DEPENDENCIES.items():
        blocked_by = [name for name in dependencies if gates[name]['status'] != 'PASS']
        if blocked_by:
            gates[gate] = {'status': 'BLOCKED', 'blocked_by': blocked_by}
            continue
        if gate in PHASE_FOR_GATE:
            gates[gate] = _phase_gate(architecture or {}, PHASE_FOR_GATE[gate], dispositions)
        elif gate == 'modeling':
            if not isinstance(validation, dict):
                gates[gate] = _simple_gate('NOT_EVALUATED', reason='cad_validation_missing')
            else:
                states = validation.get('states', {})
                geom = states.get('geometric_validity', 'NOT_EVALUATED')
                assembly = states.get('assembly_validity', 'NOT_EVALUATED')
                assembly_ok = assembly == 'PASS' or validation.get('assembly_applicability') == 'NOT_APPLICABLE'
                gates[gate] = _simple_gate('PASS' if geom == 'PASS' and assembly_ok else
                                           'FAIL' if geom == 'FAIL' or assembly == 'FAIL' else 'NOT_EVALUATED',
                                           reason='geometry_or_assembly_not_closed',
                                           extra={'geometric_validity': geom, 'assembly_validity': assembly})
        elif gate == 'system_verification':
            gates[gate] = _phase_gate(architecture or {}, 'system_verification', dispositions)
        elif gate == 'visual_review':
            gates[gate] = _visual_gate(views, visual_review, image_hashes, manifest_sha256,
                                       critical_interfaces)
        elif gate == 'product_design':
            gates[gate] = {'status': 'PASS', 'scope': 'engineering and visual gates permit optional style work'}
        elif gate == 'manufacturing':
            state = (validation or {}).get('states', {}).get('manufacturing_assessment', 'NOT_EVALUATED')
            gates[gate] = _simple_gate(state, reason='manufacturing_assessment_not_closed',
                                       dispositions=dispositions, check_id='manufacturing_assessment')
        elif gate == 'slicing':
            gates[gate] = _simple_gate(slicing_status, reason='slicing_not_closed',
                                       dispositions=dispositions, check_id='slicing')
        elif gate == 'physical_validation':
            gates[gate] = _simple_gate(physical_validation_status, reason='physical_validation_not_closed',
                                       dispositions=dispositions, check_id='physical_validation')
        elif gate == 'prototype_release':
            gates[gate] = {'status': 'PASS', 'scope': 'CAD prototype only'}

    requested = gates.get(requested_gate) if requested_gate else None
    overall = 'FAIL' if any(value['status'] == 'FAIL' for value in gates.values()) else (
        'PASS' if all(value['status'] == 'PASS' for value in gates.values()) else 'INCOMPLETE')
    return {'schema': 'cad3d-workflow-gates-v1', 'status': overall,
            'requested_gate': requested_gate, 'requested_gate_status': requested,
            'dependencies': {key: list(value) for key, value in GATE_DEPENDENCIES.items()},
            'gates': gates,
            'claims': {'physical_validation': (validation or {}).get('states', {}).get(
                'physical_validation', 'NOT_EVALUATED')},
            'limitations': ['gate status is derived from declared checks and linked current evidence',
                            'visual review does not prove physical fit, retention, flow, or strength']}


def sha256_file(project_root: Path, relative_path: str) -> str:
    path = Path(relative_path)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('evidence paths must be project-relative')
    full = (Path(project_root) / path).resolve()
    if not full.is_relative_to(Path(project_root).resolve()) or not full.is_file():
        raise ValueError(f'evidence file missing or outside project: {relative_path}')
    return hashlib.sha256(full.read_bytes()).hexdigest()
