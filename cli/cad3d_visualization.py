"""Headless, component-aware CAD visualization from build123d B-reps."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pyvista as pv

PALETTE = ["#356F9F", "#D27832", "#4A9171", "#A64F55", "#8065A3", "#9C7A3D",
           "#4E9696", "#A45E8B", "#73854C", "#566B91", "#BD654A", "#5D8DAB"]


def _tessellate(shape, tolerance=0.12, angular_tolerance=0.15):
    vertices, triangles = shape.tessellate(tolerance, angular_tolerance)
    points = np.asarray([[p.X, p.Y, p.Z] for p in vertices], dtype=np.float64)
    faces = np.asarray([[3, *map(int, face)] for face in triangles], dtype=np.int64).reshape(-1)
    mesh = pv.PolyData(points, faces).clean(tolerance=1e-9)
    if mesh.n_cells == 0 or mesh.n_points < 4:
        raise ValueError("B-rep tessellation returned an empty visual mesh")
    return mesh


def _component_shapes(shapes, assembly_config):
    from validation import component_position, transform_shape
    if assembly_config and assembly_config.get("components"):
        result = {}
        for item in assembly_config["components"]:
            part = item["part"]
            if part not in shapes:
                raise ValueError(f"visualization assembly references missing part {part}")
            result[str(item["id"])] = transform_shape(
                shapes[part], component_position(item), item.get("rotation_deg", (0, 0, 0)))
        return result
    return dict(shapes)


def _bounds(meshes):
    arrays = [np.asarray(mesh.bounds).reshape(3, 2) for mesh in meshes]
    lows = np.min(np.stack([a[:, 0] for a in arrays]), axis=0)
    highs = np.max(np.stack([a[:, 1] for a in arrays]), axis=0)
    center = (lows + highs) / 2
    half = max(float(np.max(highs - lows)) * 0.58, 1.0)
    return lows, highs, center, half


def _camera(plotter, view, center, half, section_axis="x"):
    directions = {
        "iso": (np.array([1.55, -1.75, 1.25]), np.array([0.0, 0.0, 1.0])),
        "top": (np.array([0.0, 0.0, 1.0]), np.array([0.0, 1.0, 0.0])),
        "front": (np.array([0.0, -1.0, 0.0]), np.array([0.0, 0.0, 1.0])),
        "side": (np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0])),
        "section": (np.array([1.55, -1.75, 1.25]), np.array([0.0, 0.0, 1.0])),
        "exploded": (np.array([1.55, -1.75, 1.25]), np.array([0.0, 0.0, 1.0])),
        "hidden": (np.array([1.55, -1.75, 1.25]), np.array([0.0, 0.0, 1.0])),
        "interfaces": (np.array([1.55, -1.75, 1.25]), np.array([0.0, 0.0, 1.0])),
    }
    direction, up = directions[view]
    if view == "section":
        direction, up = {
            "x": (np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0])),
            "y": (np.array([0.0, -1.0, 0.0]), np.array([0.0, 0.0, 1.0])),
            "z": (np.array([0.0, 0.0, 1.0]), np.array([0.0, 1.0, 0.0])),
        }[section_axis]
    plotter.camera_position = [center + direction * half * 3.4, center, up]
    plotter.camera.parallel_projection = True
    # Project the enclosing cube into the actual renderer viewport. A fixed
    # scale ignores the narrower model area when a legend occupies the right.
    forward=direction/np.linalg.norm(direction)
    right=np.cross(forward,up);right=right/np.linalg.norm(right)
    camera_up=np.cross(right,forward)
    viewport=plotter.renderer.viewport
    width,height=plotter.window_size
    aspect=(width*(viewport[2]-viewport[0]))/(height*(viewport[3]-viewport[1]))
    horizontal=half*np.sum(np.abs(right))
    vertical=half*np.sum(np.abs(camera_up))
    plotter.camera.parallel_scale=max(vertical,horizontal/aspect)*1.22
    plotter.camera.clipping_range = (max(0.001, half * 0.02), half * 10.0)


def _section_intersection(mesh, axis, coordinate):
    normals = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
    origin = {"x": (coordinate, 0, 0), "y": (0, coordinate, 0),
              "z": (0, 0, coordinate)}[axis]
    # A planar intersection draws actual material boundaries; no generic cap
    # triangulation is allowed to fill a cavity or imply solid material.
    return mesh.slice(normal=normals[axis], origin=origin)


def render_views(project_root, shapes, *, assembly_config=None, contract=None,
                 view="iso", section_axis="x", section_at=None, hide=None,
                 interface_id=None, explode_mm=None, output=None):
    """Render one view or a complete engineering set from live B-rep shapes."""
    root = Path(project_root).resolve()
    out = Path(output).resolve() if output is not None else root / "build/outputs"
    out.mkdir(parents=True, exist_ok=True)
    displayed = _component_shapes(shapes, assembly_config)
    if not displayed:
        raise ValueError("no CAD components to visualize")
    meshes = {name: _tessellate(shape) for name, shape in displayed.items()}
    lows, highs, center, half = _bounds(list(meshes.values()))
    ac = contract or {}
    visual_contract = (ac.get("engineering", {}).get("visualization", {}) if ac else {}) or {}
    hidden_ids = set(hide or visual_contract.get("hidden_components", []))
    interface_spec = next((x for x in ac.get("engineering", {}).get("mechanical_architecture", {}).get("interfaces", [])
                           if x.get("id") == interface_id), None) if interface_id else None
    if view == "interfaces" and interface_spec is None:
        if visual_contract.get("critical_interfaces"):
            interface_id = visual_contract["critical_interfaces"][0]
            interface_spec = next((x for x in ac["engineering"]["mechanical_architecture"].get("interfaces", [])
                                   if x.get("id") == interface_id), None)
        if interface_spec is None:
            raise ValueError("interfaces view requires --interface ID or engineering.visualization.critical_interfaces")
    unknown_hide = sorted(hidden_ids - set(meshes))
    if unknown_hide:
        raise ValueError(f"unknown component IDs requested for hiding: {unknown_hide}")
    if view == "hidden" and not hidden_ids:
        raise ValueError("hidden-components view requires --hide ID[,ID...] or engineering.visualization.hidden_components")
    if view not in ("iso", "top", "front", "side", "section", "exploded", "hidden", "interfaces", "engineering", "presentation"):
        raise ValueError(f"unsupported engineering view: {view}")
    if view in ("section", "engineering") and section_at is None:
        section_at = (lows["xyz".index(section_axis)] + highs["xyz".index(section_axis)]) / 2
    if view == "section":
        if section_axis not in "xyz":
            raise ValueError("section axis must be x, y or z")
        section_at = float(section_at if section_at is not None else (lows["xyz".index(section_axis)] + highs["xyz".index(section_axis)]) / 2)
    if view in ("exploded", "engineering"):
        explode_mm = float(explode_mm if explode_mm is not None else max(highs - lows) * 0.18)
        if explode_mm < 0:
            raise ValueError("explode distance must not be negative")

    pairs = (interface_spec or {}).get("components", [])
    color_map = {name: PALETTE[i % len(PALETTE)] for i, name in enumerate(meshes)}
    from component_catalog import resolve_catalog
    catalog=resolve_catalog(shapes,assembly_config or {})
    for name,instance in catalog['instances'].items():
        spec=catalog['parts'][instance['part']]
        if spec['classification_basis']=='explicit':color_map[name]=spec['color']
    if view == "interfaces" and len(pairs) != 2:
        raise ValueError("critical interface must name exactly two components")
    camera_axis_direction = {"x": 1.55, "y": -1.75, "z": 1.25}.get(section_axis, 1.0)
    section_keep_sign = -1 if camera_axis_direction > 0 else 1
    manifest = {"status": "PASS", "renderer": "PyVista/VTK headless", "geometry_source": "live build123d/OCP B-rep tessellation",
                "view": view, "camera_projection": "parallel projection",
                "section": {"axis": section_axis, "coordinate_mm": section_at,
                            "kept_side_toward_camera": section_keep_sign,
                            "method": "tessellated plane-intersection outlines; no synthetic caps"}
                           if view in ("section", "engineering") else None,
                "explosion_distance_mm": explode_mm if view == "exploded" else None,
                "hidden_components": sorted(hidden_ids), "highlighted_interface": interface_id,
                "components": list(meshes), "component_colors": color_map,
                "coordinate_bounds_mm": {"minimum": lows.tolist(), "maximum": highs.tolist()},
                "annotations": "separate viewport legend; full names also in manifest",
                "annotation_layout":"separate_legend_viewport","smooth_shading":False,
                "model_viewport":[0,0,.72,1],"legend_viewport":[.72,0,1,1]}

    if view=="presentation":manifest.update(model_viewport=[0,0,1,1],legend_viewport=None,annotation_layout="presentation_no_legend")

    def write_one(which, path):
        # Engineering sets select interfaces inside the render loop, after setup.
        # Resolve participants here so each image uses its own current interface.
        pairs = (interface_spec or {}).get("components", [])
        if which == "interfaces" and (len(pairs) != 2 or any(name not in meshes for name in pairs)):
            raise ValueError("critical interface must name exactly two known components")
        presentation=which=='presentation'
        pl = pv.Plotter(off_screen=True, shape=(1,1) if presentation else (1,2), border=False, window_size=(1600,1200))
        if not presentation:
            pl.renderers[0].viewport=(0,0,.72,1)
            pl.renderers[1].viewport=(.72,0,1,1)
            pl.subplot(0,0)
        pl.set_background("#f3f5f7", top="#ffffff")
        pl.enable_anti_aliasing("ssaa")
        labels = []
        active_meshes = []
        for name, mesh in meshes.items():
            if which == "hidden" and name in hidden_ids:
                continue
            shown = mesh
            if which == "section":
                shown = _section_intersection(mesh, section_axis, section_at)
                if shown.n_cells == 0:
                    continue
            if which == "exploded":
                c = displayed[name].center()
                position = np.asarray([c.X, c.Y, c.Z], dtype=float)
                vector = position - center
                norm = np.linalg.norm(vector)
                if norm < 1e-8:
                    vector = np.array([1.0 if len(labels) % 2 == 0 else -1.0, 0, 0])
                    norm = 1.0
                shown = shown.translate(vector / norm * explode_mm, inplace=False)
            color = color_map[name]
            if which == "interfaces":
                if name not in pairs:
                    color = "#c8cdd3"
                else:
                    color = "#d14c38" if name == pairs[0] else "#2464a1"
            pl.add_mesh(shown, color=color, opacity=1.0, smooth_shading=False,
                        ambient=0.22, diffuse=0.74, specular=0.16,
                        specular_power=24, label=name,
                        render_lines_as_tubes=which == "section",
                        line_width=3 if which == "section" else 1)
            labels.append([name, color, "rectangle"])
            active_meshes.append(shown)
        if not active_meshes:
            pl.close(); raise ValueError(f"view {which} contains no visible components")
        if which == "section":
            pl.add_text(f"SECTION {section_axis.upper()} = {section_at:g} mm", position="upper_left", font_size=15, color="#263746")
        if which == "interfaces":
            pl.add_text(f"INTERFACE {interface_id}", position="upper_left", font_size=15, color="#263746")
        if not presentation:
            pl.add_axes(line_width=2,color="#263746")
            pl.show_bounds(bounds=(lows[0],highs[0],lows[1],highs[1],lows[2],highs[2]),xtitle="X (mm)",ytitle="Y (mm)",ztitle="Z (mm)",location="outer",color="#45525d",font_size=10,fmt="%.1f")
            pl.subplot(0,1);pl.set_background("#f3f5f7")
            pl.add_text("COMPONENTS",position=(14,1140),font_size=15,color="#263746")
            font=max(8,min(13,int(1000/max(1,len(labels)))-7));line_height=font+9
            max_rows=int(1070/line_height)
            for index,(name,color,_) in enumerate(labels[:max_rows]):
                label=name if len(name)<=48 else name[:45]+'...'
                pl.add_text(label,position=(14,1100-index*line_height),font_size=font,color=color)
            if len(labels)>max_rows:pl.add_text("Full component index: engineering-views.json",position=(14,25),font_size=9,color="#263746")
            pl.subplot(0,0)
        c_low, c_high, c_center, c_half = _bounds(active_meshes)
        _camera(pl, "iso" if presentation else which, c_center, c_half, section_axis)
        pl.screenshot(str(path), return_img=False)
        pl.close()
        if not path.is_file() or path.stat().st_size < 20_000:
            raise RuntimeError(f"rendered image is empty or unexpectedly small: {path}")
        return path

    view_names = {
        "presentation":"P_presentation.png", "iso": "A_assembly_iso.png", "top": "B_top_orthographic.png",
        "front": "C_front_orthographic.png", "side": "D_side_orthographic.png",
        "section": "E_section.png", "exploded": "F_exploded.png",
        "hidden": "G_hidden_components.png", "interfaces": "H_critical_interface.png",
    }
    if view == "engineering":
        generated = []
        standard_views = ["iso", "top", "front", "side", "section", "exploded"]
        for item in standard_views:
            axis = section_axis
            coordinate = section_at
            if item == "section" and coordinate is None:
                coordinate = (lows["xyz".index(axis)] + highs["xyz".index(axis)]) / 2
            path = out / view_names[item]
            generated.append({"view": item, "path": str(write_one(item, path).relative_to(root)),
                              "component_count": len(meshes)})
        if hidden_ids:
            path = out / view_names["hidden"]
            generated.append({"view": "hidden", "path": str(write_one("hidden", path).relative_to(root)),
                              "hidden_components": sorted(hidden_ids)})
        else:
            generated.append({"view": "hidden", "status": "NOT_EVALUATED",
                              "reason": "declare engineering.visualization.hidden_components or supply --hide"})
        if visual_contract.get("critical_interfaces"):
            for iid in visual_contract["critical_interfaces"]:
                spec = next((x for x in ac["engineering"]["mechanical_architecture"].get("interfaces", []) if x.get("id") == iid), None)
                if not spec:
                    generated.append({"view": "interfaces", "interface": iid, "status": "FAIL", "reason": "unknown_interface"})
                    continue
                interface_id = iid; interface_spec = spec
                path = out / (f"H_interface_{iid}.png")
                generated.append({"view": "interfaces", "interface": iid,
                                  "highlighted_components": list(spec.get("components", [])),
                                  "path": str(write_one("interfaces", path).relative_to(root))})
        else:
            generated.append({"view": "interfaces", "status": "NOT_EVALUATED",
                              "reason": "declare critical_interfaces in contract"})
        manifest["views"] = generated
        manifest["status"] = "PASS" if all(x.get("status", "PASS") == "PASS" for x in generated) else "WARNING"
        import shutil
        shutil.copy2(out / view_names["iso"], out / "preview.png")
        main_path = out / "engineering-views.json"
        manifest["preview"] = "build/outputs/A_assembly_iso.png"
        main_path.write_text(json.dumps(manifest, indent=2) + "\n")
        return manifest, main_path
    path = out / view_names[view]
    write_one(view, path)
    if view == "iso":
        import shutil
        shutil.copy2(path, out / "preview.png")
    manifest["path"] = str(path.relative_to(root))
    main_path = out / f"render-{view}.json"
    main_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest, main_path


def render_parts_catalog(project_root,shapes,catalog,output=None):
    """Manufactured parts only, from live BREP; framing is per part, not common scale."""
    import html
    root=Path(project_root);out=Path(output or root/'build/outputs');directory=out/'parts';directory.mkdir(parents=True,exist_ok=True)
    ids=[];cards=[]
    for name,spec in catalog['parts'].items():
        if spec['kind']!='manufactured':continue
        ids.append(name);shape=shapes[name];mesh=_tessellate(shape)
        pl=pv.Plotter(off_screen=True,window_size=(1200,900));pl.set_background('#edf1f5');pl.enable_anti_aliasing('ssaa')
        pl.add_mesh(mesh,color=spec['color'],smooth_shading=False,ambient=.35)
        _,_,center,half=_bounds([mesh]);_camera(pl,'iso',center,half);pl.add_text(name,position='upper_left',font_size=17,color='#263746')
        path=directory/(name+'.png');pl.screenshot(str(path));pl.close()
        links=[]
        for fmt in spec['export_formats']:
            if (out/(name+'.'+fmt)).is_file():links.append(f'<a href="../{name}.{fmt}">{fmt.upper()}</a>')
        cards.append(f'<section><h2>{html.escape(name)}</h2><a href="{name}.png"><img src="{name}.png" alt="{name}"></a><p>Quantity: {spec["quantity"]} · {html.escape(str(spec["material"]))} · '+ ' / '.join(links)+'</p></section>')
    (directory/'index.html').write_text('<!doctype html><html><meta charset="utf-8"><title>CAD parts</title><style>body{font:16px system-ui;background:#edf1f5;padding:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}img{width:100%}</style><h1>Manufactured parts</h1><p>Live BREP render. Individual framing; images are not to common scale. Not physical validation.</p><div class="grid">'+''.join(cards)+'</div></html>')
    result={'status':'PASS','geometry_source':'live_BREP','part_ids':ids,'scale':'individual_framing','physical_validation':'NOT_EVALUATED'}
    (out/'parts-gallery.json').write_text(json.dumps(result,indent=2)+'\n');return result
