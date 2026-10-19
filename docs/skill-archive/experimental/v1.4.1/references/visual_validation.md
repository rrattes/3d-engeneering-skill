# Visual validation

Use the CAD engine's PyVista/VTK renderer, which tessellates the live build123d/OCP shapes for images without changing the authoritative B-rep. `cad3d render --view engineering` produces common-coordinate opaque isometric, top/front/side orthographic, 2D tessellated section intersection outlines (without synthetic caps), exploded views and configured hidden-component/critical-interface images. Check `engineering-views.json`; optional views without configured targets are not evaluated.

Use section views to reveal internal geometry instead of indiscriminate transparency. Confirm orientation, component colors, legend, crop and occlusion in the actual PNGs. Exploded offsets explain separation only; they are not assembly trajectories. Image agreement does not establish geometric validity. Camera/view evidence should be tied to the source model/assembly revision.
