# Visual validation

Use the CAD engine's PyVista/VTK renderer, which tessellates the live build123d/OCP shapes for images without changing the authoritative B-rep. `cad3d render --view engineering` produces common-coordinate opaque isometric, top/front/side orthographic, 2D tessellated section intersection outlines (without synthetic caps), exploded views and configured hidden-component/critical-interface images. Check `engineering-views.json`; optional views without configured targets are not evaluated.

Use section views to reveal internal geometry instead of indiscriminate transparency. Confirm orientation, component colors, legend, crop and occlusion in the actual PNGs. Exploded offsets explain separation only; they are not assembly trajectories. Image agreement does not establish geometric validity. Camera/view evidence should be tied to the source model/assembly revision.

Review form in relation to the brief: proportion, useful volume, handling/grip, contact
edges, coherent seams/fasteners, service cues and cleaning access. Explain choices
through use, mechanism and manufacture, with alternatives when those choices materially
affect the result. A style treatment cannot close a functional or mechanical finding.
Inspect opaque overall views plus sections and targeted interfaces: a generated image
PASS does not establish that a hidden carrier, screw head or release feature is legible.
Record concrete image findings and corrections; physical comfort and user preference
remain subject to their own evaluation.

For multicomponent assemblies, preserve a colored overall assembly and exploded view,
then create close interface views for each critical fit. The AIO filter project is a
positive example: distinct colored parts and a male/female cutaway exposed the mating
features; measured B-rep clearance was reported separately. Do not describe the image
as proving fit: it makes the interface inspectable, while CAD geometry checks and
physical fit tests remain separate evidence. Log the actual reviewer, source manifest
hash, image hashes, inspected flags and resolved findings in
`.cad3d/visual-review.yaml`; `cad3d workflow check --gate visual_review` rejects stale
or missing views and required interface details.
