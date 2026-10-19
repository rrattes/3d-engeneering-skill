"""Geometric face references with trimmed-face anchors and explicit ambiguity."""
import math
from collections import Counter
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.GeomAbs import GeomAbs_Plane,GeomAbs_Cylinder,GeomAbs_Cone,GeomAbs_Sphere
from build123d import Vector,Vertex


def surface(face):
    surf=BRepAdaptor_Surface(face.wrapped,True)
    kind={GeomAbs_Plane:'plane',GeomAbs_Cylinder:'cylinder',GeomAbs_Cone:'cone',GeomAbs_Sphere:'sphere'}.get(surf.GetType(),'other')
    return kind,({'radius_mm':float(surf.Cylinder().Radius())} if kind=='cylinder' else {})


def _number(value,name,minimum=0):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<minimum:raise ValueError('invalid '+name)
    return float(value)


def _vector(value,name):
    if not isinstance(value,(list,tuple)) or len(value)!=3 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in value):raise ValueError('invalid '+name)
    return value


def select_face(shape,selector):
    ref=selector.get('ref') if isinstance(selector,dict) else None
    rejected=Counter();nearest=[];candidates=[]
    base={'ref':ref,'status':'NOT_EVALUATED'}
    try:
        if not isinstance(selector,dict) or shape is None or not shape.is_valid:raise ValueError('invalid selector or BREP')
        if 'center_mm' in selector and 'point_mm' in selector:raise ValueError('use center_mm or point_mm, not both')
        point=_vector(selector['point_mm'],'point_mm') if 'point_mm' in selector else None
        center_target=_vector(selector['center_mm'],'center_mm') if 'center_mm' in selector else None
        normal=_vector(selector['normal'],'normal') if 'normal' in selector else None
        normal_length=math.hypot(*normal) if normal is not None else 1
        if not math.isfinite(normal_length) or normal_length==0:raise ValueError('invalid normal length')
        tol=_number(selector.get('point_tolerance_mm',.25) if point is not None else selector.get('center_tolerance_mm',.25),'position tolerance')
        dot_min=_number(selector.get('normal_dot_min',.95),'normal_dot_min',-1)
        if dot_min>1:raise ValueError('normal_dot_min must be <=1')
        radius=_number(selector['radius_mm'],'radius_mm') if 'radius_mm' in selector else None
        radius_tol=_number(selector.get('radius_tolerance_mm',.05),'radius_tolerance_mm')
        area=_number(selector['area_mm2'],'area_mm2') if 'area_mm2' in selector else None
        area_tol=_number(selector.get('area_tolerance_mm2',.1),'area_tolerance_mm2')
        vertex=Vertex(*point) if point is not None else None
        for face in shape.faces():
            kind,attrs=surface(face);center=face.center();distance=0.;sample=center
            if selector.get('surface') and selector['surface']!=kind:rejected['surface_mismatch']+=1;continue
            if point is not None:
                calc=BRepExtrema_DistShapeShape(face.wrapped,vertex.wrapped);calc.Perform()
                if not calc.IsDone():raise RuntimeError('OCP face-point distance unavailable')
                distance=float(calc.Value());at=calc.PointOnShape1(1);sample=Vector(at.X(),at.Y(),at.Z())
            elif center_target is not None:distance=math.dist(tuple(center),center_target)
            if not math.isfinite(distance):raise ValueError('invalid face distance')
            descriptor={'surface':kind,'center_mm':list(center),**attrs,'anchor_distance_mm':distance,'area_mm2':face.area}
            nearest.append(descriptor)
            if distance>tol:rejected['anchor_outside_tolerance']+=1;continue
            if radius is not None and abs(attrs.get('radius_mm',-1)-radius)>radius_tol:rejected['radius_mismatch']+=1;continue
            if area is not None and abs(face.area-area)>area_tol:rejected['area_mismatch']+=1;continue
            normal_dot=None
            if normal is not None:
                actual=face.normal_at(sample);normal_dot=sum(x*y for x,y in zip(actual,normal))/normal_length
                if normal_dot<dot_min:rejected['normal_mismatch']+=1;continue
            candidates.append((distance,face,{**descriptor,'normal_dot':normal_dot,'selection_basis':'trimmed_face_point' if point is not None else 'face_center' if center_target is not None else 'geometric_constraints'}))
        diagnosis={'rejection_counts':dict(rejected),'nearest_candidates':sorted(nearest,key=lambda x:x['anchor_distance_mm'])[:5],'matches':len(candidates)}
        if not candidates:return None,{**base,'reason':'face_selector_matched_no_face',**diagnosis}
        candidates.sort(key=lambda x:x[0])
        if len(candidates)>1 and abs(candidates[0][0]-candidates[1][0])<1e-5:return None,{**base,'reason':'face_selector_ambiguous',**diagnosis}
        return candidates[0][1],{**base,'status':'PASS',**candidates[0][2],**diagnosis}
    except Exception as exc:return None,{**base,'reason':'face_reference_unavailable','detail':str(exc),'rejection_counts':dict(rejected)}
