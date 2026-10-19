# OrcaSlicer Manufacturing Engine

CAD3D deliberately keeps the build123d/OCP CAD engine separate from the `cad3d-orca:2.4.2` OrcaSlicer manufacturing engine. The latter runs on demand inside a network-disabled Docker container. It does not connect to or send jobs to a printer.

## Enabled preset tuple

- Printer: `elegoo-cc2` → upstream `Elegoo Centauri Carbon 2 0.4 nozzle`.
- Material: `petg` → upstream `Elegoo PETG @ECC2`.
- Process: `standard-0.20` → upstream `0.20mm Standard @Elegoo CC2 0.4 nozzle`.
- Nominal envelope: 256×256×256 mm; CAD3D applies a configurable 5 mm margin per axis by default (251 mm effective axis-aligned envelope).

The image and profiles are both pinned to OrcaSlicer v2.4.2. `cad3d slicer doctor` checks the actual executable version, resolves the `inherits` chain from the image's bundled profile library, verifies profile types, nozzle, envelope, and machine/material/process compatibility, then reports SHA-256 for every parent and selected preset. Only a single-color PETG configuration is enabled. Do not change `--load-*` profiles to Centauri Carbon original profiles, choose another nozzle/material, enable AMS/multicolor, or add custom start/end/toolchange G-code without a reviewed profile update and tests.

## Workflow

```sh
cad3d slicer doctor
cad3d build
cad3d validate
cad3d slice --printer elegoo-cc2 --material petg --model build/outputs/part.stl
cad3d slice-report
```

Use one explicit STL or 3MF. When the default `build/outputs` directory contains multiple models, select one with `--model`. `cad3d slice --compare-orientations` runs actual Orca CLI slicing for six axis-aligned poses and places each result, log, and estimate beside the others. Choose only among successful candidates. The time/material objective is advisory, not a strength or print-success prediction; honor CAD functional layer direction and manual review.

The output directory `build/slicer/` contains an input copy, sliced 3MF candidate(s), per-invocation logs, `slice-report.json`, and a SHA-256 manifest. The bridge checks the process return code, 3MF ZIP CRC, and 3D model entry. It records estimates only when Orca output/3MF metadata provides parseable evidence; a missing metric stays null and must not be guessed. Candidate slicing can be `FAIL` if any requested pose fails. An out-of-envelope model is rejected before invoking the slicer.

State distinctions remain mandatory:

- `CAD Validity`: build123d/OCP geometry checks.
- `Assembly Validity`: CAD3D assembly and interface checks.
- `Manufacturing Assessment`: envelope/orientation heuristics and process settings.
- `Slicing Success`: actual Orca subprocess plus valid sliced 3MF artifact.
- `Printer Compatibility`: only the preset tuple is verified; the slicer profile `host_type` or output format does not prove the printer will load the project.
- `Physical Print Validation`: remains `NOT_EVALUATED` until a controlled print has been produced and inspected.

Orca's CLI emits a transient `plate_1.gcode` as a side effect of `--slice`; the adapter removes it immediately after extracting estimates, and records this action. No standalone G-code is retained or delivered, no file is uploaded, no network is available in the slicer runtime, and no printer protocol is used. The user remains responsible for opening/reviewing the 3MF with the printer vendor's supported workflow.


## Early requested-profile check

Before modeling for a selected FDM setup, run
`cad3d slicer preflight --printer elegoo-cc2 --material <requested> --process standard-0.20`
when these printer/process IDs apply. It needs no STL and writes no slicing report.
Exit 0/PASS covers installed preset inheritance and engine version only; exit 4/
NOT_EVALUATED means unsupported requested selection, and exit 2/FAIL means an
installed chain/engine error. Unsupported PETG-CF remains PETG-CF; do not replace it
with PETG. A CAD material profile is separate from an installed Orca preset. This
command does not slice, validate firmware compatibility or prove a physical print.
