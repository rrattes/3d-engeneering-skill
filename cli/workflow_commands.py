"""CLI adapters for mandatory, evidence-derived project gates."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from workflow_gates import evaluate_workflow, sha256_file

WORKFLOW_TEMPLATE = {
    'workflow': {
        'schema_version': 1,
        'required_views': ['iso', 'top', 'front', 'side', 'section', 'exploded', 'hidden'],
        'warning_dispositions_field': 'engineering.workflow_dispositions',
    }
}


def validate_physical_report(project_root: Path, report) -> dict:
    """A physical PASS needs test methods/results and immutable linked evidence."""
    if not isinstance(report, dict):
        return {'status': 'NOT_EVALUATED', 'reason': 'physical_report_missing'}
    declared = report.get('status', 'NOT_EVALUATED')
    if declared in ('FAIL', 'NOT_EVALUATED'):
        return {'status': declared, 'reason': 'physical_report_declares_nonpass'}
    if declared not in ('PASS', 'WARNING'):
        return {'status': 'FAIL', 'reason': 'physical_report_has_unsupported_status'}
    tests = report.get('tests', [])
    evidence = report.get('evidence', [])
    if not tests or not evidence:
        return {'status': 'NOT_EVALUATED', 'reason': 'physical_test_or_evidence_missing'}
    invalid_tests = [(item.get('id') or '<missing-id>') if isinstance(item, dict)
                     else '<invalid-test-record>' for item in tests
                     if not isinstance(item, dict) or not item.get('id') or not item.get('method')
                     or item.get('result') != 'PASS']
    if invalid_tests:
        return {'status': 'FAIL', 'reason': 'physical_test_results_incomplete',
                'invalid_tests': invalid_tests}
    mismatched = []
    for item in evidence:
        if not isinstance(item, dict) or not item.get('path') or not item.get('sha256'):
            mismatched.append('<invalid-evidence-record>')
            continue
        try:
            observed = sha256_file(project_root, item['path'])
        except (ValueError, OSError):
            observed = None
        if observed != item['sha256']:
            mismatched.append(item['path'])
    if mismatched:
        return {'status': 'FAIL', 'reason': 'physical_evidence_missing_or_hash_mismatch',
                'mismatched_evidence': mismatched}
    return {'status': declared, 'test_count': len(tests), 'evidence_count': len(evidence),
            'scope': 'declared tests and linked files; technical sufficiency requires review'}


def initialize_workflow(project_root: Path) -> dict:
    root = Path(project_root).resolve()
    project_path = root / '.cad3d/project.yaml'
    if not project_path.is_file():
        raise FileNotFoundError('Projeto ausente; execute cad3d init antes de ativar os gates.')
    workflow_path = root / '.cad3d/workflow.yaml'
    if workflow_path.exists():
        raise FileExistsError('.cad3d/workflow.yaml existe; não será sobrescrito.')
    project = yaml.safe_load(project_path.read_text()) or {}
    project_data = project.get('project', {})
    project_data['workflow_schema_version'] = 1
    project['project'] = project_data
    project_path.write_text(yaml.safe_dump(project, sort_keys=False, allow_unicode=True))
    workflow_path.write_text(yaml.safe_dump(WORKFLOW_TEMPLATE, sort_keys=False, allow_unicode=True))
    return {'status': 'PASS', 'workflow_schema_version': 1,
            'files': ['.cad3d/project.yaml', '.cad3d/workflow.yaml'],
            'next_step': 'Complete .cad3d/engineering.yaml, then run cad3d workflow check --gate requirements.'}


def _read_json(root: Path, relative: str):
    path = root / relative
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def _read_yaml(root: Path, relative: str):
    path = root / relative
    if not path.is_file():
        return None
    return yaml.safe_load(path.read_text()) or {}


def evaluate_project(root: Path, *, requested_gate=None) -> dict:
    root = Path(root).resolve()
    project = _read_yaml(root, '.cad3d/project.yaml') or {}
    version = (project.get('project', {}) or {}).get('workflow_schema_version')
    if version != 1:
        return {'schema': 'cad3d-workflow-gates-v1', 'status': 'FAIL',
                'requested_gate': requested_gate,
                'requested_gate_status': {'status': 'FAIL', 'reason': 'workflow_not_initialized'},
                'next_step': 'Run cad3d workflow init to enable the mandatory dependency gates.'}
    workflow = _read_yaml(root, '.cad3d/workflow.yaml') or {}
    if (workflow.get('workflow', {}) or {}).get('schema_version') != 1:
        return {'schema': 'cad3d-workflow-gates-v1', 'status': 'FAIL',
                'requested_gate': requested_gate,
                'requested_gate_status': {'status': 'FAIL', 'reason': 'workflow_contract_missing_or_unsupported'},
                'next_step': 'Restore a supported .cad3d/workflow.yaml contract.'}

    from product_engineering import validate_architecture
    architecture = validate_architecture(root)
    validation = _read_json(root, 'build/outputs/validation.json')
    views = _read_json(root, 'build/outputs/engineering-views.json')
    visual_review = _read_yaml(root, '.cad3d/visual-review.yaml')
    engineering = _read_yaml(root, '.cad3d/engineering.yaml') or {}
    engineering = engineering.get('engineering', {})
    manifest_path = root / 'build/outputs/manifest.json'
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest() if manifest_path.is_file() else None
    image_hashes = {}
    if views:
        for item in views.get('views', []):
            image_path = item.get('path')
            if image_path:
                try:
                    image_hashes[image_path] = sha256_file(root, image_path)
                except (ValueError, OSError):
                    pass
    slicing = _read_json(root, 'build/slicer/slice-report.json') or {}
    physical_raw = _read_json(root, 'build/physical/validation.json')
    physical = validate_physical_report(root, physical_raw)
    critical = (engineering.get('visualization', {}) or {}).get('critical_interfaces', [])
    critical_ids = [item.get('id') if isinstance(item, dict) else item for item in critical]
    report = evaluate_workflow(
        architecture=architecture, validation=validation, views=views,
        visual_review=visual_review.get('visual_review') if isinstance(visual_review, dict) else None,
        image_hashes=image_hashes, manifest_sha256=manifest_hash,
        dispositions=engineering.get('workflow_dispositions', []),
        critical_interfaces=critical_ids,
        slicing_status=slicing.get('status', 'NOT_EVALUATED'),
        physical_validation_status=physical.get('status', 'NOT_EVALUATED'),
        requested_gate=requested_gate)
    report['contract_version'] = version
    report['source_files'] = {
        'architecture': '.cad3d/engineering.yaml',
        'validation': 'build/outputs/validation.json',
        'views': 'build/outputs/engineering-views.json',
        'visual_review': '.cad3d/visual-review.yaml',
        'manifest': 'build/outputs/manifest.json',
    }
    return report


def workflow_command(args) -> int:
    root = Path.cwd()
    if args.action == 'init':
        report = initialize_workflow(root)
    else:
        report = evaluate_project(root, requested_gate=args.gate)
        output = root / 'build/outputs/workflow-gates.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        report['report_path'] = 'build/outputs/workflow-gates.json'
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.action == 'init':
        return 0 if report.get('status') == 'PASS' else 3
    requested = report.get('requested_gate_status') or {}
    return 0 if requested.get('status') == 'PASS' else 3
