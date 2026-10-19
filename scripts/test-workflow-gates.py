#!/usr/bin/env python3
"""Behavioral contract for dependency-ordered product workflow gates."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cli'))
from workflow_gates import evaluate_workflow


def base_architecture():
    return {
        'status': 'PASS',
        'phases': {
            'requirements': 'PASS',
            'functional_architecture': 'PASS',
            'mechanical_architecture': 'PASS',
            'modeling': 'PASS',
            'system_verification': 'PASS',
            'manufacturing': 'NOT_EVALUATED',
        },
        'checks': [],
    }


def base_validation():
    return {'status': 'PASS', 'states': {
        'geometric_validity': 'PASS', 'assembly_validity': 'PASS',
        'manufacturing_assessment': 'WARNING', 'slicing': 'NOT_EVALUATED',
        'physical_validation': 'NOT_EVALUATED',
    }, 'assembly_applicability': 'APPLICABLE'}


def base_views():
    names = ('shell', 'tray', 'basket')
    return {'status': 'PASS', 'components': list(names),
            'component_colors': {'shell': '#667788', 'tray': '#4488AA', 'basket': '#55AA77'},
            'views': [
        {'view': name, 'path': f'renders/{name}.png'}
        for name in ('iso', 'top', 'front', 'side', 'section', 'exploded', 'hidden')
    ]}


def base_visual():
    return {
        'reviewer': 'reviewer-id',
        'source_manifest_sha256': 'manifest-hash',
        'views': [
            {'view': name, 'path': f'renders/{name}.png', 'sha256': f'{name}-hash',
             'inspected': True, 'findings': []}
            for name in ('iso', 'top', 'front', 'side', 'section', 'exploded', 'hidden')
        ],
    }


class WorkflowGateTests(unittest.TestCase):
    def evaluate(self, **overrides):
        data = {
            'architecture': base_architecture(), 'validation': base_validation(),
            'views': base_views(), 'visual_review': base_visual(),
            'image_hashes': {f'renders/{name}.png': f'{name}-hash' for name in
                             ('iso', 'top', 'front', 'side', 'section', 'exploded', 'hidden')},
            'manifest_sha256': 'manifest-hash', 'dispositions': [],
        }
        data.update(overrides)
        return evaluate_workflow(**data)

    def test_each_later_gate_is_blocked_when_earlier_gate_is_not_passed(self):
        architecture = base_architecture()
        architecture['phases']['mechanical_architecture'] = 'NOT_EVALUATED'
        report = self.evaluate(architecture=architecture)
        self.assertEqual(report['gates']['modeling']['status'], 'BLOCKED')
        self.assertIn('mechanical_architecture', report['gates']['modeling']['blocked_by'])
        self.assertEqual(report['gates']['system_verification']['status'], 'BLOCKED')
        self.assertEqual(report['gates']['product_design']['status'], 'BLOCKED')

    def test_user_written_pass_does_not_bypass_failed_evidence(self):
        validation = base_validation()
        validation['states']['geometric_validity'] = 'FAIL'
        report = self.evaluate(validation=validation)
        self.assertEqual(report['gates']['modeling']['status'], 'FAIL')
        self.assertNotEqual(report['gates']['product_design']['status'], 'PASS')

    def test_warning_requires_complete_noncritical_disposition(self):
        architecture = base_architecture()
        architecture['phases']['functional_architecture'] = 'WARNING'
        architecture['checks'] = [{'id': 'functional-architecture-phase', 'detail': [
            {'id': 'flow-1', 'status': 'WARNING', 'severity': 'major'}]}]
        report = self.evaluate(architecture=architecture)
        self.assertEqual(report['gates']['functional_architecture']['status'], 'BLOCKED')
        dispositions = [{'check_id': 'flow-1', 'decision': 'accepted_with_followup',
                         'rationale': 'limite conhecido', 'owner': 'engenharia',
                         'follow_up': 'medir vazao no prototipo'}]
        report = self.evaluate(architecture=architecture, dispositions=dispositions)
        self.assertEqual(report['gates']['functional_architecture']['status'], 'PASS')
        architecture['checks'][0]['detail'][0]['severity'] = 'critical'
        report = self.evaluate(architecture=architecture, dispositions=dispositions)
        self.assertEqual(report['gates']['functional_architecture']['status'], 'BLOCKED')

    def test_dispositioned_warning_cannot_hide_critical_not_evaluated_requirement(self):
        architecture = base_architecture()
        architecture['phases']['system_verification'] = 'WARNING'
        architecture['checks'] = [{'id': 'system-verification-phase', 'detail': [
            {'id': 'residual-risks', 'status': 'WARNING', 'severity': 'major'},
            {'id': 'requirement-REQ-LAMP', 'status': 'NOT_EVALUATED', 'severity': 'critical'},
        ]}]
        disposition = [{'check_id': 'residual-risks', 'decision': 'accepted_with_followup',
                        'rationale': 'risco registrado', 'owner': 'engenharia',
                        'follow_up': 'ensaiar protótipo'}]
        report = self.evaluate(architecture=architecture, dispositions=disposition)
        self.assertEqual(report['gates']['system_verification']['status'], 'BLOCKED')
        self.assertIn('requirement-REQ-LAMP',
                      report['gates']['system_verification']['unresolved_critical_ids'])

    def test_visual_gate_requires_inspected_hash_matched_critical_views(self):
        visual = base_visual()
        visual['views'][0]['sha256'] = 'old-image-hash'
        report = self.evaluate(visual_review=visual)
        self.assertEqual(report['gates']['visual_review']['status'], 'FAIL')

    def test_aio_style_colored_assembly_and_interface_view_remain_supported(self):
        views = base_views()
        views['views'].append({'view': 'interfaces', 'interface': 'seat_bio',
                               'path': 'renders/interface-seat-bio.png'})
        visual = base_visual()
        visual['views'].append({'view': 'interface:seat_bio',
                                'path': 'renders/interface-seat-bio.png',
                                'sha256': 'interface-hash', 'inspected': True, 'findings': []})
        hashes = {f'renders/{name}.png': f'{name}-hash' for name in
                  ('iso', 'top', 'front', 'side', 'section', 'exploded', 'hidden')}
        hashes['renders/interface-seat-bio.png'] = 'interface-hash'
        report = self.evaluate(views=views, visual_review=visual, image_hashes=hashes,
                               critical_interfaces=['seat_bio'])
        self.assertEqual(report['gates']['visual_review']['status'], 'PASS')
        self.assertEqual(report['gates']['visual_review']['reviewed_views'][-1],
                         'interface:seat_bio')

    def test_multicomponent_assembly_without_distinct_color_keys_fails_visual_gate(self):
        views = base_views()
        views['component_colors'].pop('basket')
        report = self.evaluate(views=views)
        self.assertEqual(report['gates']['visual_review']['status'], 'FAIL')
        visual = base_visual()
        visual['views'] = [entry for entry in visual['views'] if entry['view'] != 'section']
        report = self.evaluate(visual_review=visual)
        self.assertEqual(report['gates']['visual_review']['status'], 'FAIL')
        visual = base_visual()
        visual['views'][0]['inspected'] = False
        report = self.evaluate(visual_review=visual)
        self.assertEqual(report['gates']['visual_review']['status'], 'FAIL')

    def test_product_design_requires_engineering_and_visual_gates(self):
        views = base_views()
        views['status'] = 'FAIL'
        report = self.evaluate(views=views)
        self.assertEqual(report['gates']['visual_review']['status'], 'FAIL')
        self.assertEqual(report['gates']['product_design']['status'], 'BLOCKED')

    def test_prototype_release_does_not_claim_physical_validation(self):
        report = self.evaluate()
        self.assertEqual(report['gates']['prototype_release']['status'], 'PASS')
        self.assertEqual(report['claims']['physical_validation'], 'NOT_EVALUATED')
        self.assertEqual(report['gates']['manufacturing']['status'], 'BLOCKED')

    def test_manufacturing_warning_needs_recorded_owner_and_followup_to_advance(self):
        disposition = [{'check_id': 'manufacturing_assessment',
                        'decision': 'accepted_with_followup', 'rationale': 'prototipo de bancada',
                        'owner': 'equipe', 'follow_up': 'medir dimensoes apos impressao'}]
        report = self.evaluate(dispositions=disposition)
        self.assertEqual(report['gates']['manufacturing']['status'], 'PASS')
        self.assertEqual(report['gates']['manufacturing']['observed_status'], 'WARNING')
        self.assertEqual(report['claims']['physical_validation'], 'NOT_EVALUATED')

    def test_simple_part_can_disposition_assembly_as_not_applicable(self):
        validation = base_validation()
        validation['assembly_applicability'] = 'NOT_APPLICABLE'
        validation['states']['assembly_validity'] = 'NOT_EVALUATED'
        report = self.evaluate(validation=validation)
        self.assertEqual(report['gates']['modeling']['status'], 'PASS')


if __name__ == '__main__':
    unittest.main()
