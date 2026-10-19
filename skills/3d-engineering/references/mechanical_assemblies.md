# Mechanical assemblies

Each component has stable ID, function and positioned geometry. Each movable or removable component needs a relation and retention method, or an explicit reason for intentional freedom. Placement only proves location. Distinguish contact, clearance and positive-volume interference. Declared contact does not authorize volume overlap.

Describe interfaces with mating regions/faces, datums, insertion axis, fit/tolerance profile, and intended service operation. Check collision and clearance, then test sampled linear assembly/removal trajectories where supported. Sampling cannot prove continuous collision-free motion or load capacity. For screws, snaps, captured rails and pressure fits, review actual load path, access, deformation and release strategy. Record assembly steps and evidence; unresolved force, fatigue and print anisotropy remain warnings or not evaluated.

## Installed components and hardware

For each installed item, identify locating surfaces, restrained translations/rotations,
intended freedom, operating/service disturbances and the reaction path through its
retention into the supporting structure. A cavity or commercial envelope does not
establish capture. Show how the restraint is engaged, released and reassembled;
keep strength/force evidence separate from geometric engagement.

Use the selected hardware's drawing or measured dimensions, with provenance or explicit
assumptions. Represent shank, head, washer, nut/insert, seating and thread engagement
region as applicable. Check head clearance and seating geometry separately from hole
clearance. Include nut insertion/capture and access to both sides where required.

Create separate tool keep-outs for drive engagement, approach and required movement;
also assess finger/grip access. Compare actual head/tool B-reps to the obstacles
present at that operation using `pair_check` or explicit project geometry checks.
Intended seating contact does not waive positive-volume interference with an obstacle.
A straight cylindrical driver keep-out represents only its declared straight approach;
it does not prove turning room, torque suitability or human access.

## Tolerance stack

Write a signed functional equation from explicit datums and bound every contributing
dimension using vendor limits or applicable printer/material/orientation calibration.
For clearance C = female − male, evaluate C_min = female_min − male_max and
C_max = female_max − male_min against the required operating range. For example,
10.4 ±0.15 minus 10.0 ±0.10 gives 0.15..0.65 mm; nominal 0.4 mm cannot satisfy
a 0.2 mm minimum. Include location, alignment, coating or thermal terms when relevant.
Do not double-count compensation or assume independent statistical errors without
evidence. Uncalibrated uncertainty remains an assumption; nominal fit-band PASS is
not a tolerance-stack result. Preserve the calculation as requirement evidence.

## Service and independent removal

For each service operation record the item, release fasteners, prerequisite removals,
tool/grip access, cable/hose disconnection and slack, full extraction path, obstacles
remaining installed, and reassembly. Check independent replacement against the actual
requirement: a removable panel may need to clear installed equipment and permanent
anchors, and the equipment may need to clear the installed panel.

Use separate assembly/service configurations after prerequisite removals. The existing
`assembly_path_check` checks a sampled linear trajectory against every other supplied
placed component; it does not plan prerequisite removals or compound motion. CAD3D 1.6.0 adds explicit
[helical paths](helical_motion.md) for coupled rotation/translation; declare them
instead of treating threaded withdrawal as a linear path. Report
direction, travel, samples/spacing, obstacle set and allowed contacts. Evaluate additional
poses/segments when needed and retain the limitation between samples. Exploded offsets
are presentation, not proof of removal. Do not silently omit installed obstructions to
obtain PASS. Keep commercial references, manufactured parts and assembly exports
identifiable and separate.

## Explicit service states (additive assembly contract)

A new `assembly_steps` entry can declare `moving_ids`, `removed_ids` and `prerequisite_step_ids`. IDs refer to placed instances, including hardware; all instances not removed/moving remain obstacles. A group moves together, preserving connector/cooler placement. Declare steps in dependency order: each prerequisite must have passed. Every removed ID must be justified by a successful moving/removal operation among its prerequisite ancestors; an unknown/failed or later prerequisite blocks the dependent step as NOT_EVALUATED. Independent conditional snapshots are not proof of a complete sequence. Never remove all hardware by convenience. Legacy `moving_component` insertion samples remain supported and are not a complete assembly-state description.

`direction_mm` retains the legacy insertion convention: the path samples from negative direction × travel to the seated pose. To sample upward removal, use direction `[0,0,-1]`; the sampled poses are the reverse of that removal. Reversibility of this straight path does not prove access, grip or continuous motion. Report sample spacing and unknown kernel results.

Optional `tools` define `origin_mm`, `direction_mm`, `radius_mm`, `length_mm`, `id` and a `target_id` when a retained fastener is intentionally engaged. Only that target is excluded from the tool-clearance comparison. Add driver and counterhold as separate envelopes; they are cylinders, not accurate hand/jaw geometry. Targeted moving parts must be handled in a separate fastener operation.

Optional top-level `fastener_stacks` declare `length_mm`, `grip_mm`, `required_engagement_mm`, `head_to_seat_gap_mm`, `seat_tolerance_mm` and optionally `blind_depth_mm`/`tip_clearance_mm`. Arithmetic flags short/bottomed/unseated stacks. These declarations are not independently measured thread engagement, torque or retention strength.
