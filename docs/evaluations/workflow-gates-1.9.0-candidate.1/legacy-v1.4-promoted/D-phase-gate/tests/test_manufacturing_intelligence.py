import json
import sys
from pathlib import Path

import pytest
from build123d import Box, Pos

sys.path.insert(0, '/opt/cad3d')
from validation import (assembly_path_check, interface_face_check, local_thickness,
                        component_position, pair_check)
from manufacturing import evaluate_orientations, generate_calibration_coupons
from calibration import (compare_calibration_identity, make_calibration_record,
                         write_calibration_record)
from slicer_bridge import run_slice


def test_geometric_wall_thickness_passes_when_sampled_above_minimum():
    result=local_thickness(Box(10,10,10),1.2,samples_per_axis=2)
    assert result['status']=='PASS'
    assert result['minimum_sampled_mm']==pytest.approx(10)
    assert result['coverage']=='sampled_not_complete'


def test_real_subminimum_hollow_wall_is_detected():
    shell=Box(10,10,10)-Pos(0,0,.8)*Box(8.4,8.4,9.2)
    result=local_thickness(shell,1.0,samples_per_axis=2)
    assert result['status']=='FAIL'
    assert result['minimum_sampled_mm']==pytest.approx(.8,abs=1e-5)
    assert any(f['status']=='FAIL' for f in result['faces'])


def test_thickness_region_without_ray_hit_is_not_evaluated():
    result=local_thickness(Box(10,10,10),1.0,samples_per_axis=2,max_ray_mm=.1)
    assert result['status']=='NOT_EVALUATED'
    assert result['measured_samples']==0


def test_selected_thickness_region_is_geometric_and_missing_face_is_not_evaluated():
    face={'ref':'outer-wall-x-positive','surface':'plane','center_mm':[5,0,0],
          'normal':[1,0,0],'center_tolerance_mm':.01}
    result=local_thickness(Box(10,10,10),1,samples_per_axis=2,face_selectors=[face])
    assert result['status']=='PASS' and result['faces'][0]['face_ref']==face['ref']
    missing=local_thickness(Box(10,10,10),1,face_selectors=[{**face,'center_mm':[99,0,0]}])
    assert missing['status']=='NOT_EVALUATED'


def _face(ref,center,normal):
    return {'ref':ref,'surface':'plane','center_mm':center,'normal':normal,'center_tolerance_mm':.01}


def test_assembly_pose_translation_alias_is_honored_and_conflicts_rejected():
    assert component_position({'translation_mm':[4,5,6]})==[4,5,6]
    assert component_position({'position_mm':[4,5,6]})==[4,5,6]
    with pytest.raises(ValueError):
        component_position({'position_mm':[0,0,0],'translation_mm':[1,0,0]})


def test_functional_interface_measures_selected_face_gap():
    a=Box(10,10,10)
    b=Pos(10.3,0,0)*Box(10,10,10)
    interface={'id':'guide-001','type':'sliding','clearance_mm':.3,'tolerance_mm':.05,
               'face_a':_face('housing-guide',(5,0,0),(1,0,0)),
               'face_b':_face('slider-side',(5.3,0,0),(-1,0,0))}
    result=interface_face_check(a,b,interface,{'fit_clearance_mm':.3})
    assert result['status']=='PASS' and result['measured_gap_mm']==pytest.approx(.3)
    assert result['face_a']['ref']=='housing-guide'


def test_functional_interface_detects_wrong_local_clearance_and_overlap():
    a=Box(10,10,10)
    b=Pos(10.6,0,0)*Box(10,10,10)
    interface={'id':'guide-002','type':'sliding','clearance_mm':.3,'tolerance_mm':.05,
               'face_a':_face('housing-guide',(5,0,0),(1,0,0)),
               'face_b':_face('slider-side',(5.6,0,0),(-1,0,0))}
    assert interface_face_check(a,b,interface,{})['status']=='FAIL'
    overlapping=Pos(9.5,0,0)*Box(10,10,10)
    interference={**interface,'face_b':_face('slider-side',(4.5,0,0),(-1,0,0))}
    signed=interface_face_check(a,overlapping,interference,{})
    assert signed['status']=='FAIL' and signed['classification']=='INTERFERENCE' and signed['measured_gap_mm']<0
    assert pair_check(a,Pos(9.5,0,0)*Box(10,10,10))['classification']=='VOLUMETRIC_COLLISION'


def test_linear_assembly_insertion_passes_clear_path():
    placed={'moving':Pos(11,0,0)*Box(4,4,4),'obstacle':Pos(0,30,0)*Box(10,10,10)}
    result=assembly_path_check(placed,{'id':'insert','moving_component':'moving','direction_mm':[1,0,0],
                                       'travel_mm':10,'samples':10})
    assert result['status']=='PASS' and result['samples_requested']==11
    assert result['coverage']=='sampled_not_continuous'


def test_linear_assembly_insertion_finds_intermediate_blocker():
    placed={'moving':Pos(11,0,0)*Box(4,4,4),'obstacle':Pos(5,0,0)*Box(4,8,8)}
    result=assembly_path_check(placed,{'id':'insert-blocked','moving_component':'moving','direction_mm':[1,0,0],
                                       'travel_mm':10,'samples':10})
    assert result['status']=='FAIL' and result['blockages']


def test_orientation_assessment_passes_fit_and_reports_excess_envelope():
    shape=Box(300,20,10)
    rotations=[(0,0,0),(0,90,0)]
    fits=evaluate_orientations(shape,rotations,[256,256,300])
    assert fits['status']=='WARNING' and fits['chosen_rotation_deg']==[0,90,0]
    too_large=evaluate_orientations(shape,rotations,[256,256,256])
    assert too_large['status']=='FAIL' and too_large['chosen_rotation_deg'] is None
    assert all(c['method']=='orthogonal_candidate_heuristic' for c in fits['candidates'])
    measured=evaluate_orientations(Box(10,10,10),[(0,0,0)],[20,20,20],density_g_cm3=1.2,infill_fraction=.25)
    assert measured['candidates'][0]['material_estimate']['estimated_mass_g']==pytest.approx(.3)


def test_calibration_coupons_generate_all_requested_witness_families():
    shapes,params=generate_calibration_coupons({'clearances_mm':[.2,.3], 'wall_thicknesses_mm':[.8,1.2],
        'bridge_spans_mm':[5,10], 'overhang_angles_deg':[45,60]})
    assert set(shapes)=={'clearance_pins','clearance_holes','wall_steps','bridge_spans','overhang_steps'}
    assert all(s.is_valid and s.volume>0 for s in shapes.values())
    assert params['fit_values_are_uncalibrated_labels'] is True


def test_calibration_measurements_are_versioned_and_opt_in(tmp_path):
    payload={'identity':{'printer':'Test fixture only','nozzle_diameter_mm':.4,'material':'PLA',
                         'process_settings_sha256':'a'*64},
             'measured_at':'2026-10-12','method':'automated record schema fixture',
             'measurements':{'pin_diameter_mm':[4.01,4.02],'hole_diameter_mm':[4.30]},
             'confirmed_physical_measurements':False}
    target,record=write_calibration_record(payload,tmp_path)
    assert target.is_file() and record['status']=='RECORDED_UNCONFIRMED' and not record['calibrated']
    assert json.loads(json.dumps(record))['measurements']['pin_diameter_mm']==[4.01,4.02]
    bad={**payload,'identity':{**payload['identity'],'process_settings_sha256':'bad'}}
    with pytest.raises(ValueError): make_calibration_record(bad)
    record=make_calibration_record({**payload,'confirmed_physical_measurements':True,'evidence':'fixture.csv'})
    project={'name':'Test fixture only','nozzle_diameter_mm':.4,'process_settings_sha256':'a'*64}
    params={'material':{'profile':'pla'}}
    assert compare_calibration_identity(record['identity'],project,params)['status']=='PASS'
    assert compare_calibration_identity(record['identity'],{**project,'nozzle_diameter_mm':.6},params)['status']=='FAIL'


def test_slicer_without_explicit_profiles_is_not_evaluated(tmp_path):
    code,report=run_slice(tmp_path)
    assert code==4 and report['status']=='NOT_EVALUATED'
    assert report['reason']=='explicit_slicer_profile_missing'
    assert (tmp_path/'build/slicer/slice-report.json').is_file()
