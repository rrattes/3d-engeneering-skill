# Workflow dependency gates — 1.9.0

## Purpose

Prevent a project phase from advancing on a manually asserted PASS, stale image, absent
requirement, undispositioned warning, or CAD evidence that does not support the claim.
This evaluation records the candidate work and its local promotion as 1.9.0; the 1.8.0
source/runtime remain preserved for rollback.

## Baseline findings

- OceanTech aquarium cover review: the preview was not legible enough for the user to
  understand the lid, support on the aquarium rim, height, and lamp. The lamp was not
  traced to a modeled/verified part, yet a requirement checkbox and zone marker could
  be mistaken for closure. This is a genuine negative baseline: requirement presence,
  model geometry, readable render review, and user acceptance were not linked by a gate.
  Sources: workspace product `Aquario_OceanTech_71L_Tampa_Rev_A/`, especially its
  requirements, engineering contract and generated outputs, plus the user's review
  feedback in this conversation.
- AIO filter positive control: the project retains colored assembly/exploded views and
  male/female interface details, with B-rep clearance reported separately. These views
  make assembly and CAD interface review inspectable. Their own project record keeps
  physical fit pending; image and B-rep evidence do not establish physical fit.
  Inspectable examples: [AIO Rev B assembly](../../../../Filtro_AIO_Reinicio_Rev_B/renders/CONJUNTO_FECHADO.png),
  [exploded view](../../../../Filtro_AIO_Reinicio_Rev_B/renders/EXPLODIDA_REV_B.png),
  and [interface detail](../../../../Filtro_AIO_Reinicio_Rev_B/renders/DETALHES_REV_B.png).
- Three clean-context pressure scenarios run before the skill edit found: (1) a lamp
  marker is not a modeled/verified luminaire; (2) unreadable required views block
  acceptance; (3) a checked plan and user style approval cannot advance a failed gate.
  All preserved the AIO presentation/evidence distinction. These are qualitative
  agent scenarios, not automated coverage; automated gate tests follow separately.

## Gate contract

`requirements -> functional_architecture -> mechanical_architecture -> modeling ->
 system_verification -> visual_review`. Optional product-design depends on visual
review. Manufacturing depends on system and visual review; slicing and physical
validation depend on manufacturing. CAD prototype release depends on modeling, system
verification and visual review, and explicitly does not claim physical validation.

## Verification artifacts

- `source/` and `packaged/`: full prepromotion candidate-image suites.
- `promoted-source/` and `promoted-packaged/`: final stable 1.9.0 suites, PASS 30/30 each, both with `source_frozen: true`.
- Legacy V1.4 acceptance: PASS, 35 checks on both candidate and stable runtime; final evidence in `legacy-v1.4-promoted/`.
- Promoted image: `cad3d-engineering:1.9.0`, ID `sha256:e8e3af356c82877a10317a4e915f543e0fc9b8c970576ba9f1b9624fb98539f2`.
- Prepromotion candidate image: `cad3d-engineering:1.9.0-candidate.1`, ID
  `sha256:7d50fe2ebcf09f94e0152c4226f25a0d3a4f266a658d9a78f16fcd62720f981a`.
- `preliminary/`: retained prior runs; they exposed the critical unresolved-item
  bypass and a source mutation during one packaged run, so they are not the final
  acceptance evidence.
- Physical product validation: not evaluated by platform regression.
- Promotion record and user authorization: `APROVACAO_E_PROMOCAO.md`.

The regression `WF-11` reproduced the old defect first: a dispositioned minor warning
allowed a phase to PASS while critical `REQ-LAMP` was `NOT_EVALUATED`. After the fix,
all unresolved FAIL/NOT_EVALUATED subchecks block the phase. The regression now asserts
that behavior.

## Promotion status

Promoted locally as 1.9.0 on 19/10/2026 after explicit user authorization. The 1.8.0
baseline and the original candidate test logs remain preserved for historical review.
