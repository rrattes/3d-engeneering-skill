"""Mechanical checks backed by build123d/OCP B-rep operations.

This module intentionally does not infer physical print success or general wall
thickness from a watertight mesh.
"""
from __future__ import annotations

from math import radians

from OCP.BRepExtrema import BRepExtrema_DistShapeShape


def _bounds(shape):
    b = shape.bounding_box()
    return ((b.min.X, b.min.Y, b.min.Z), (b.max.X, b.max.Y, b.max.Z))


def _bbox_overlap(a, b):
    amin, amax = _bounds(a)
    bmin, bmax = _bounds(b)
    return all(min(amax[i], bmax[i]) - max(amin[i], bmin[i]) > 0.0 for i in range(3))


def _distance(a, b):
    calc = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    calc.Perform()
    if not calc.IsDone():
        raise RuntimeError("OCP não concluiu a distância mínima")
    return float(calc.Value())


def pair_check(a, b, *, min_clearance=0.0, contact_tolerance=1e-5,
               intentional_contact=False, pair_id=None):
    """Exact solid-pair checks; located Compound wrappers are never Boolean operands."""
    from brep_pairs import check_pair
    return check_pair(a,b,min_clearance=min_clearance,contact_tolerance=contact_tolerance,
                      intentional_contact=intentional_contact,pair_id=pair_id)


def transform_shape(shape, position_mm=(0, 0, 0), rotation_deg=(0, 0, 0)):
    from build123d import Pos, Rot
    x, y, z = position_mm
    rx, ry, rz = rotation_deg
    return Pos(x, y, z) * Rot(rx, ry, rz) * shape


def component_position(item):
    """Read the documented V1.1 field and the common translation alias."""
    position=item.get('position_mm')
    translation=item.get('translation_mm')
    if position is not None and translation is not None and tuple(position)!=tuple(translation):
        raise ValueError('position_mm and translation_mm disagree for the same component')
    return position if position is not None else (translation if translation is not None else (0,0,0))


def oriented_dimensions(shape, rotations):
    from build123d import Rot
    result = []
    for angles in rotations:
        rotated = Rot(*angles) * shape
        b = rotated.bounding_box()
        result.append({"rotation_deg": list(angles), "dimensions_mm": [b.size.X, b.size.Y, b.size.Z]})
    return result


def print_fit(oriented, limits):
    for candidate in oriented:
        if all(d <= lim + 1e-7 for d, lim in zip(candidate["dimensions_mm"], limits)):
            return {"status": "PASS", "selected_rotation_deg": candidate["rotation_deg"],
                    "dimensions_mm": candidate["dimensions_mm"], "limits_mm": limits}
    return {"status": "FAIL", "selected_rotation_deg": None,
            "candidates": oriented, "limits_mm": limits}


def nominal_wall_check(check, profile_minimum):
    nominal = float(check["nominal_mm"])
    minimum = float(check.get("minimum_mm", profile_minimum))
    return {"id": check.get("id", "wall"), "status": "PASS" if nominal >= minimum else "FAIL",
            "nominal_parameter_mm": nominal, "required_parameter_mm": minimum,
            "geometric_thickness_calculated": "NOT_EVALUATED",
            "basis": "declared_parametric_dimension; not a general geometric thickness measurement"}


def fit_dimension_check(interface, profile):
    """Compare declared nominal mating feature sizes with a material fit band."""
    kind = interface.get("type")
    if kind == "press":
        kind = "press_fit"
    ranges = profile.get("fit_ranges_mm", {})
    if kind not in ranges or "male_size_mm" not in interface or "female_size_mm" not in interface:
        return {"id": interface.get("id"), "type": kind, "status": "NOT_EVALUATED",
                "reason": "mating_feature_dimensions_or_profile_range_missing"}
    male, female = float(interface["male_size_mm"]), float(interface["female_size_mm"])
    clearance = female - male
    lo, hi = map(float, ranges[kind])
    return {"id": interface.get("id"), "type": kind,
            "status": "PASS" if lo <= clearance <= hi else "FAIL",
            "male_nominal_mm": male, "female_nominal_mm": female,
            "nominal_clearance_mm": clearance, "allowed_range_mm": [lo, hi],
            "basis": "declared_parametric_dimensions; B-rep interference remains independently checked"}


def support_heuristic(shape, max_overhang_degrees=45.0):
    """Coarse triangulated downward-face estimate; never a print guarantee."""
    try:
        import trimesh
        from build123d import export_stl
        import tempfile, os
        fd, name = tempfile.mkstemp(suffix=".stl")
        os.close(fd)
        try:
            export_stl(shape, name, tolerance=0.1, angular_tolerance=0.15)
            mesh = trimesh.load(name, force="mesh")
            normals = mesh.face_normals
            # Faces whose normal points substantially downward may require support.
            threshold = -__import__('math').sin(radians(max_overhang_degrees))
            centroids = mesh.triangles_center
            above_bed = centroids[:, 2] > float(mesh.bounds[0, 2]) + 1e-5
            area = float(mesh.area_faces[(normals[:, 2] < threshold) & above_bed].sum())
            return {"status": "WARNING", "method": "STL_face_normal_heuristic",
                    "potential_downward_area_mm2": area,
                    "interpretation": "heuristic_only; orientation, bridges and slicer rules are not fully modeled"}
        finally:
            os.unlink(name)
    except Exception as exc:
        return {"status": "NOT_EVALUATED", "reason": str(exc)}


def mesh_components(mesh):
    try:
        chunks = mesh.split(only_watertight=False)
        return {"status": "PASS" if len(chunks) == 1 else "WARNING",
                "connected_components": len(chunks),
                "reason": "single_mesh_component" if len(chunks) == 1 else "disconnected_mesh_components"}
    except Exception as exc:
        return {"status": "NOT_EVALUATED", "reason": str(exc)}


def local_thickness(shape, minimum_mm, *, samples_per_axis=3, max_ray_mm=None, face_selectors=None):
    """Sample B-rep material thickness along inward face normals.

    Each sample starts on a trimmed face and casts a ray into the solid. The
    first subsequent B-rep intersection is the local normal chord. This is a
    sampled directional thickness estimate, not an exhaustive medial-axis or
    all-directions minimum-wall proof.
    """
    import math
    from OCP.BRepTools import BRepTools
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepLProp import BRepLProp_SLProps
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.TopAbs import TopAbs_IN, TopAbs_ON
    from OCP.gp import gp_Pnt, gp_Pnt2d, gp_Dir, gp_Lin

    report = {"status": "NOT_EVALUATED", "minimum_required_mm": float(minimum_mm),
              "method": "OCP_inward_normal_ray_sample", "coverage": "sampled_not_complete",
              "samples_per_face_axis": int(samples_per_axis), "faces": [],
              "limitations": ["normal-direction samples only", "not exhaustive over face area or all directions",
                              "thin features between sample points may be missed"]}
    try:
        if not shape.is_valid or not shape.solids() or any(s.volume <= 0 for s in shape.solids()):
            report["reason"] = "invalid_or_zero_volume_shape"
            return report
        resolution = max(1, int(samples_per_axis))
        ray_limit = float(max_ray_mm or max(shape.bounding_box().size) * 2 + 1)
        intersector = IntCurvesFace_ShapeIntersector()
        intersector.Load(shape.wrapped, 1e-7)
        face_statuses, measured = [], []
        selected=[]; selector_results=[]
        if face_selectors is not None:
            for selector in face_selectors:
                chosen,result=select_face(shape,selector)
                selector_results.append(result)
                if chosen is not None: selected.append((selector.get('ref'),chosen,result))
            if not selected:
                report.update(reason='no_requested_thickness_region_was_selected',face_selection=selector_results)
                return report
        else:
            selected=[(None,face,None) for face in shape.faces()]
        for face_number, (face_ref,face,selection_result) in enumerate(selected, 1):
            u0, u1, v0, v1 = BRepTools.UVBounds_s(face.wrapped)
            surf = BRepAdaptor_Surface(face.wrapped, True)
            face_samples = []
            for iu in range(resolution):
                u = u0 + (iu + .5) / resolution * (u1 - u0)
                for iv in range(resolution):
                    v = v0 + (iv + .5) / resolution * (v1 - v0)
                    classifier = BRepClass_FaceClassifier(face.wrapped, gp_Pnt2d(u, v), 1e-7)
                    if classifier.State() not in (TopAbs_IN, TopAbs_ON):
                        continue
                    props = BRepLProp_SLProps(surf, u, v, 1, 1e-7)
                    if not props.IsNormalDefined():
                        face_samples.append({"status": "NOT_EVALUATED", "reason": "surface_normal_undefined",
                                             "sample_uv_fraction":[(iu+.5)/resolution,(iv+.5)/resolution]})
                        continue
                    point, normal = props.Value(), props.Normal()
                    # Face topology orientation converts the underlying surface normal to solid outward.
                    if str(face.wrapped.Orientation()).endswith("REVERSED"):
                        normal.Reverse()
                    inward = gp_Dir(-normal.X(), -normal.Y(), -normal.Z())
                    intersector.Perform(gp_Lin(point, inward), 1e-5, ray_limit)
                    hits = []
                    if intersector.IsDone():
                        for hit_index in range(1, intersector.NbPnt() + 1):
                            hit = intersector.Pnt(hit_index)
                            distance = point.Distance(hit)
                            if distance > 1e-4:
                                hits.append(float(distance))
                    if not hits:
                        face_samples.append({"status": "NOT_EVALUATED", "reason": "no_inward_opposing_surface",
                                             "sample_uv_fraction":[(iu+.5)/resolution,(iv+.5)/resolution]})
                        continue
                    thickness = min(hits)
                    result = {"status": "PASS" if thickness + 1e-7 >= minimum_mm else "FAIL",
                              "thickness_mm": thickness,
                              "sample_uv_fraction": [(iu + .5) / resolution, (iv + .5) / resolution]}
                    face_samples.append(result)
                    measured.append(thickness)
            values = [s["thickness_mm"] for s in face_samples if "thickness_mm" in s]
            failures = [s for s in face_samples if s.get("status") == "FAIL"]
            unevaluated = sum(s.get("status") == "NOT_EVALUATED" for s in face_samples)
            status = "FAIL" if failures else ("PASS" if values and not unevaluated else ("WARNING" if values else "NOT_EVALUATED"))
            face_statuses.append(status)
            if face_samples:
                face_report={"face_ordinal_ephemeral": face_number,"face_ref":face_ref,
                    "surface_type": str(face.geom_type).split(".")[-1], "status": status,
                    "measured_samples": len(values), "unevaluated_samples": unevaluated,
                    "minimum_sampled_mm": min(values) if values else None,
                    "maximum_sampled_mm": max(values) if values else None,
                    "below_minimum_samples": failures,
                    "unevaluated_regions":[s for s in face_samples if s.get('status')=='NOT_EVALUATED']}
                if face_selectors is not None: face_report['face_selection']=selection_result
                report["faces"].append(face_report)
        if face_selectors is not None:
            report['face_selection']=selector_results
            face_statuses.extend('NOT_EVALUATED' for item in selector_results if item['status']!='PASS')
        report.update(measured_samples=len(measured), minimum_sampled_mm=min(measured) if measured else None,
                      maximum_sampled_mm=max(measured) if measured else None)
        report["status"] = ("FAIL" if "FAIL" in face_statuses else
                            "NOT_EVALUATED" if not measured else
                            "WARNING" if any(x in ("WARNING", "NOT_EVALUATED") for x in face_statuses) else "PASS")
        return report
    except Exception as exc:
        report["reason"] = "brep_thickness_analysis_error"
        report["detail"] = str(exc)
        return report


def _face_surface(face):
    from face_references import surface
    return surface(face)


def select_face(shape, selector):
    from face_references import select_face as resolve
    return resolve(shape,selector)


def interface_face_check(shape_a, shape_b, interface, profile):
    """Measure selected functional face gap, separate from full-solid collision analysis."""
    out = {"id":interface.get("id"),"method":"selected_BREP_faces_distance",
           "status":"NOT_EVALUATED","basis":"geometric_face_selection; distance between selected finite faces"}
    fa, ra = select_face(shape_a, interface.get("face_a", {}))
    fb, rb = select_face(shape_b, interface.get("face_b", {}))
    out["face_a"],out["face_b"] = ra,rb
    if fa is None or fb is None:
        out["reason"]="functional_face_selection_unavailable"
        return out
    calc=BRepExtrema_DistShapeShape(fa.wrapped,fb.wrapped); calc.Perform()
    if not calc.IsDone():
        out["reason"]="ocp_face_distance_failed"; return out
    measured=float(calc.Value())
    kind=interface.get("type")
    nominal=float(interface.get("clearance_mm",profile.get("fit_clearances_mm",{}).get(kind,profile.get("fit_clearance_mm",0))))
    tolerance=float(interface.get("tolerance_mm",profile.get("interface_tolerance_mm",.1)))
    # For parallel planes, signed separation distinguishes clearance from overlap;
    # unsigned face distance alone cannot tell which side of the mating plane a face lies on.
    if ra['surface']=='plane' and rb['surface']=='plane':
        from math import sqrt
        na=fa.normal_at(fa.center()); nb=fb.normal_at(fb.center())
        opposition=sum(a*b for a,b in zip((na.X,na.Y,na.Z),(nb.X,nb.Y,nb.Z)))
        delta=[b-a for a,b in zip(ra['center_mm'],rb['center_mm'])]
        signed=sum(d*n for d,n in zip(delta,(na.X,na.Y,na.Z)))
        if opposition > -.95:
            out.update(status='NOT_EVALUATED',reason='selected_plane_normals_not_opposed',normal_dot=opposition)
            return out
        if abs(measured-abs(signed))>tolerance+1e-7:
            out.update(status='NOT_EVALUATED',reason='selected_finite_faces_do_not_confirm_projected_gap',
                       signed_center_gap_mm=signed,unsigned_face_distance_mm=measured)
            return out
        status='PASS' if abs(signed-nominal)<=tolerance+1e-7 else 'FAIL'
        out.update(status=status,measured_gap_mm=signed,unsigned_face_distance_mm=measured,
                   expected_gap_mm=nominal,tolerance_mm=tolerance,deviation_mm=signed-nominal,
                   classification='INTERFERENCE' if signed<0 else ('CONTACT' if abs(signed)<=1e-5 else 'LOCAL_CLEARANCE'))
    else:
        status='PASS' if abs(measured-nominal)<=tolerance else 'FAIL'
        out.update(status=status,measured_gap_mm=measured,expected_gap_mm=nominal,tolerance_mm=tolerance,
                   deviation_mm=measured-nominal,classification='CONTACT' if measured<=1e-5 else 'LOCAL_CLEARANCE',
                   note='unsigned minimum distance; signed local gap unsupported for this surface pair')
    return out


def assembly_path_check(placed, step, *, samples_default=12, tolerance=1e-7):
    """Linearly move a component from its final pose backwards along insertion vector."""
    import math
    ident=step.get("moving_component")
    if ident not in placed:
        return {"id":step.get("id"),"status":"NOT_EVALUATED","reason":"moving_component_missing"}
    direction=step.get("direction_mm")
    if not direction or len(direction)!=3:
        return {"id":step.get("id"),"status":"NOT_EVALUATED","reason":"insertion_direction_missing"}
    length=math.sqrt(sum(float(x)**2 for x in direction))
    travel=float(step.get("travel_mm",0)); count=int(step.get("samples",samples_default))
    if length<=0 or travel<=0 or count<1:
        return {"id":step.get("id"),"status":"NOT_EVALUATED","reason":"invalid_trajectory_parameters"}
    unit=[float(x)/length for x in direction]
    # Recover the component's original pose via the signed translation applied to the final shape.
    from build123d import Pos
    allowed_contacts={str(x) for x in step.get("allowed_contact_pairs", [])}
    final=placed[ident]; checks=[]
    for index in range(count+1):
        remaining=travel*(count-index)/count
        at=Pos(-unit[0]*remaining,-unit[1]*remaining,-unit[2]*remaining)*final
        for other_id,other in placed.items():
            if other_id==ident: continue
            pair_id=f"{ident}::{other_id}"
            pair=pair_check(at,other,intentional_contact=pair_id in allowed_contacts,pair_id=pair_id)
            if pair["status"]=="NOT_EVALUATED":
                checks.append({"sample":index,"other_component":other_id,"status":"NOT_EVALUATED","detail":pair.get("reason")})
            elif pair.get("status")=="FAIL" or pair.get("intersection_volume_mm3",0)>tolerance:
                checks.append({"sample":index,"other_component":other_id,"status":"FAIL","distance_mm":pair.get("surface_distance_mm"),"intersection_volume_mm3":pair.get("intersection_volume_mm3",0)})
    status="FAIL" if any(x["status"]=="FAIL" for x in checks) else "NOT_EVALUATED" if checks else "PASS"
    return {"id":step.get("id"),"status":status,"moving_component":ident,"direction_unit":unit,
            "travel_mm":travel,"samples_requested":count+1,"allowed_contact_pairs":sorted(allowed_contacts),"blockages":checks,
            "method":"sampled_linear_translation_OCP_BREP","coverage":"sampled_not_continuous"}
