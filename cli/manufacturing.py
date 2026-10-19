"""FDM orientation heuristics and geometry-only calibration coupon generators."""
from __future__ import annotations

import math


def evaluate_orientations(shape, rotations, limits_mm, *, overhang_degrees=45.0,
                          functional_axes=None, density_g_cm3=None, infill_fraction=None):
    from build123d import Rot, export_stl
    import os, tempfile
    import trimesh
    axes = functional_axes or []
    results=[]
    for rotation in rotations:
        rotated=Rot(*rotation)*shape
        bb=rotated.bounding_box()
        dims=[float(bb.size.X),float(bb.size.Y),float(bb.size.Z)]
        fit=all(d<=float(limit)+1e-7 for d,limit in zip(dims,limits_mm))
        fd,path=tempfile.mkstemp(suffix='.stl'); os.close(fd)
        try:
            export_stl(rotated,path,tolerance=.1,angular_tolerance=.15)
            mesh=trimesh.load(path,force='mesh')
            min_z=float(mesh.bounds[0,2])
            bottom=(mesh.face_normals[:,2]<-.98)&(mesh.triangles_center[:,2]<=min_z+1e-4)
            bed_area=float(mesh.area_faces[bottom].sum())
        finally:
            os.unlink(path)
        support=__import__('validation').support_heuristic(rotated,overhang_degrees)
        functional=[]
        for axis in axes:
            d=axis.get('direction_mm',[0,0,1]); transformed=Rot(*rotation)*__import__('build123d').Vector(*d)
            norm=math.sqrt(transformed.X**2+transformed.Y**2+transformed.Z**2)
            angle=math.degrees(math.acos(min(1,abs(transformed.Z)/norm))) if norm else None
            functional.append({'id':axis.get('id'),'build_axis_angle_deg':angle,
                               'status':'WARNING','interpretation':'heuristic_layer_relation_only_not_strength_analysis'})
        volume=float(shape.volume)
        material=None
        if density_g_cm3 is not None and infill_fraction is not None:
            fill=float(infill_fraction)
            if not 0 < fill <= 1: raise ValueError('infill_fraction deve estar em (0, 1]')
            material={'estimated_mass_g':volume/1000*float(density_g_cm3)*fill,
                      'density_g_cm3':float(density_g_cm3),'infill_fraction':fill,
                      'status':'WARNING','basis':'configured_density_and_fill; excludes supports, walls, purge and process loss'}
        else:
            material={'status':'NOT_EVALUATED','reason':'explicit_density_and_infill_fraction_required'}
        score=(0 if fit else 1e9)+dims[2]*.01+float(support.get('potential_downward_area_mm2',0))*.001-bed_area*.005
        results.append({'rotation_deg':list(rotation),'dimensions_mm':dims,'envelope_status':'PASS' if fit else 'FAIL',
                        'bed_contact_area_mm2':bed_area,'support_assessment':support,'functional_interfaces':functional,
                        'material_estimate':material,'heuristic_score':score,'method':'orthogonal_candidate_heuristic'})
    viable=[r for r in results if r['envelope_status']=='PASS']
    viable.sort(key=lambda r:r['heuristic_score'])
    return {'status':'WARNING' if viable else 'FAIL','method':'comparative_FDM_orientation_heuristic',
            'chosen_rotation_deg':viable[0]['rotation_deg'] if viable else None,
            'candidates':results,'limitations':['not a strength prediction','support regions are approximate STL face heuristics',
            'no slicing or physical print validation','bed contact area is tessellated estimate']}


def generate_calibration_coupons(config):
    """Generate named B-rep coupons; fit ranges are design labels, not calibration data."""
    from build123d import Align, Box, Cylinder, Pos, Rot
    clearances=[float(x) for x in config.get('clearances_mm',[.15,.20,.25,.30,.35,.40])]
    walls=[float(x) for x in config.get('wall_thicknesses_mm',[.8,1.0,1.2,1.6,2.0])]
    spans=[float(x) for x in config.get('bridge_spans_mm',[5,10,15,20])]
    angles=[float(x) for x in config.get('overhang_angles_deg',[30,45,60,75])]
    if not clearances or min(clearances)<0 or not walls or min(walls)<=0:
        raise ValueError('Listas de folga e espessura precisam conter valores válidos positivos')
    pitch=float(config.get('pitch_mm',9)); pin_d=float(config.get('pin_diameter_mm',4)); pin_h=float(config.get('feature_height_mm',8))
    width=max(10,pitch*(len(clearances)+1)); plate_t=float(config.get('plate_thickness_mm',3))
    pins=Box(width,12,plate_t,align=(Align.CENTER,Align.CENTER,Align.MIN))
    holes=Box(width,12,plate_t,align=(Align.CENTER,Align.CENTER,Align.MIN))
    for i,gap in enumerate(clearances):
        x=(i-(len(clearances)-1)/2)*pitch
        pins += Pos(x,0,plate_t)*Cylinder(pin_d/2,pin_h,align=(Align.CENTER,Align.CENTER,Align.MIN))
        boss=Pos(x,0,plate_t)*Cylinder((pin_d+gap)/2,pin_h,align=(Align.CENTER,Align.CENTER,Align.MIN))
        bore=Pos(x,0,plate_t-1e-5)*Cylinder(pin_d/2,pin_h+2e-5,align=(Align.CENTER,Align.CENTER,Align.MIN))
        holes += boss-bore
    wall_base=Box(max(12,3*len(walls)),12,plate_t,align=(Align.CENTER,Align.CENTER,Align.MIN))
    for i,t in enumerate(walls):
        x=(i-(len(walls)-1)/2)*3
        wall_base += Pos(x,0,plate_t)*Box(t,8,pin_h,align=(Align.CENTER,Align.CENTER,Align.MIN))
    # Supported bar roots at x=0; free spans vary toward +X.
    bridge=Box(8,12,plate_t,align=(Align.CENTER,Align.CENTER,Align.MIN))
    root_x=4
    bridge += Pos(root_x,0,plate_t)*Box(2,12,pin_h,align=(Align.MIN,Align.CENTER,Align.MIN))
    for span in spans:
        bridge += Pos(root_x+2, (span-len(spans)*2)/2,plate_t+pin_h-1)*Box(span,2,1,align=(Align.MIN,Align.MIN,Align.MIN))
    overhang=Box(max(12,4*len(angles)),12,plate_t,align=(Align.CENTER,Align.CENTER,Align.MIN))
    for i,angle in enumerate(angles):
        length=pin_h
        fin=Rot(0,-angle,0)*Box(length,2,1,align=(Align.MIN,Align.CENTER,Align.MIN))
        overhang += Pos((i-(len(angles)-1)/2)*4,0,plate_t)*fin
    shapes={'clearance_pins':pins,'clearance_holes':holes,'wall_steps':wall_base,
            'bridge_spans':bridge,'overhang_steps':overhang}
    if not all(s.is_valid and s.volume>0 for s in shapes.values()):
        raise ValueError('Gerador produziu geometria inválida')
    return shapes,{'clearances_mm':clearances,'wall_thicknesses_mm':walls,'bridge_spans_mm':spans,
                   'overhang_angles_deg':angles,'fit_values_are_uncalibrated_labels':True}
