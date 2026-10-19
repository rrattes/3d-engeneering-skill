import sys
from pathlib import Path

import pytest
from build123d import Align, Box, export_step, import_step
from OCP.Standard import Standard_DomainError

for parent in Path(__file__).resolve().parents:
    candidate = parent / 'cli'
    if (candidate / 'validation.py').is_file():
        sys.path.insert(0, str(candidate))
        break
from validation import nominal_wall_check, pair_check, transform_shape


def test_separated_parts_pass():
    r = pair_check(Box(10, 10, 10), Box(10, 10, 10).translate((20, 0, 0)))
    assert r['status'] == 'PASS' and r['classification'] == 'SEPARATED'


def test_volume_collision_fails_with_volume():
    a, b = Box(10, 10, 10), Box(10, 10, 10).translate((8, 0, 0))
    r = pair_check(a, b)
    assert r['status'] == 'FAIL' and r['classification'] == 'VOLUMETRIC_COLLISION'
    assert r['intersection_volume_mm3'] == pytest.approx(200)


def test_surface_contact_requires_declaration():
    a, b = Box(10, 10, 10), Box(10, 10, 10).translate((10, 0, 0))
    assert pair_check(a, b)['status'] == 'FAIL'
    r = pair_check(a, b, intentional_contact=True)
    assert r['status'] == 'PASS' and r['classification'] == 'SURFACE_CONTACT'


def test_sliding_clearance_pass_and_insufficient_fails():
    block, slider = Box(20, 20, 4), Box(5, 5, 3)
    good = pair_check(block, transform_shape(slider, (12.8, 0, 0)), min_clearance=.25)
    bad = pair_check(block, transform_shape(slider, (12.6, 0, 0)), min_clearance=.25)
    assert good['status'] == 'PASS' and good['surface_distance_mm'] == pytest.approx(.3)
    assert bad['status'] == 'FAIL' and bad['classification'] == 'PROXIMITY'


def test_transformed_assembly_introduces_collision():
    r = pair_check(Box(20, 20, 4), transform_shape(Box(5, 5, 3), (12.2, 0, 0)))
    assert r['status'] == 'FAIL' and r['intersection_volume_mm3'] > 0


def test_declared_wall_is_not_misreported_as_geometric_measurement():
    assert nominal_wall_check({'id': 'thin', 'nominal_mm': .8}, 1.2)['status'] == 'FAIL'
    r = nominal_wall_check({'nominal_mm': 2.0}, 1.2)
    assert r['status'] == 'PASS' and r['geometric_thickness_calculated'] == 'NOT_EVALUATED'


def test_parametric_press_fit_range():
    from validation import fit_dimension_check
    profile = {'fit_ranges_mm': {'press_fit': [-.25, -.05]}}
    good = fit_dimension_check({'id': 'press-pin', 'type': 'press_fit', 'male_size_mm': 10, 'female_size_mm': 9.85}, profile)
    bad = fit_dimension_check({'id': 'press-pin', 'type': 'press_fit', 'male_size_mm': 10, 'female_size_mm': 9.98}, profile)
    assert good['status'] == 'PASS' and good['nominal_clearance_mm'] == pytest.approx(-.15)
    assert bad['status'] == 'FAIL'


def test_print_envelope_and_orientation_alternatives():
    from validation import oriented_dimensions, print_fit
    shape = Box(300, 20, 10, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    candidates = oriented_dimensions(shape, [(0, 0, 0), (0, 90, 0)])
    result = print_fit(candidates, [256, 256, 350])
    assert result['status'] == 'PASS' and result['selected_rotation_deg'] == [0, 90, 0]
    assert print_fit(oriented_dimensions(shape, [(0, 0, 0)]), [256, 256, 256])['status'] == 'FAIL'


def test_step_export_and_reimport(tmp_path):
    original = Box(11, 7, 3)
    path = tmp_path / 'calibration.step'
    export_step(original, str(path))
    reopened = import_step(str(path))
    assert reopened.is_valid and reopened.volume == pytest.approx(original.volume, rel=1e-7)


def test_invalid_degenerate_geometry_is_rejected():
    with pytest.raises(Standard_DomainError):
        Box(0, 10, 5)
    unavailable = pair_check(None, Box(1, 1, 1))
    assert unavailable['status'] == 'NOT_EVALUATED'
