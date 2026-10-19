# Passive fluid systems

Model the functional architecture before solids: sources, sinks, chambers, passages, direction, operating modes, seals, overflow and blockage/failure cases. Each declared route maps to actual open geometry with inlet/outlet points, section/clearance and sampling resolution. Run `cad3d architecture validate --geometry` and inspect reported blocked sample and B-rep evidence.

A geometric centerline/open-path check establishes only that sampled points lie in void space. It does not establish watertight sealing, flow rate, pressure loss, priming, air removal, fouling resistance, CFD performance or physical leak safety. Keep those as explicit unevaluated verification items until measured or simulated with a suitable method.
