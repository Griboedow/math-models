# Snags and CAD revisions before printing

`snag-audit` checks geometric causes of large snags: loops under overhangs,
obstacles during pulling, narrow passages, and contact with rotating parts.
It saves **original STL** surface coordinates, yarn poses, and clearance
allowances so the location can be found in CAD and checked again after revision.

This checks prescribed yarn motions, not spontaneous slipping off.
Contact may lead to sliding, stopping, loop tightening, or yarn deformation;
the model does not distinguish these outcomes.
The core model's `critical_snag_N` describes loss of stand stability under
external force and **is not the release force of snagged yarn**.

## Reproducible review

```sh
python -m pip install ".[mesh]"
python -m yarnstand snag-audit scene.json cases.json --out results/design_a
# After editing the STL, use the same poses, diameters, and allowances:
python -m yarnstand snag-audit revised_scene.json cases.json --out results/design_b
python -m yarnstand snag-compare results/design_a/audit.json results/design_b/audit.json --out results/comparison.json
```

Large sets can be distributed across independent processes:

```sh
python tools/run_snag_audit_parallel.py scene.json cases.json --out results/design_a --workers 3
```

Original case order is preserved. Geometry and code hashes, library versions,
and checking parameters are verified before merging. Each process loads its
own meshes; use the sequential command when memory is limited.

Open `report.html`. The `audit.json` file contains every case and part,
the clearance lower bound, first detected contact, tightest location,
coordinates in the original STL and assembly frames, input poses, file hashes,
and library versions. `review_markers.json` maps parts to
`review_markers_part_*.stl`: small marker spheres in the corresponding original
STL frame, in millimeters. Import them over the part in CAD as reference
geometry; they are not printable parts.

Comparisons reject different cases or allowances, since changing the test
could otherwise create a false improvement. Changes to calculation code or
libraries are reported separately in `same_audit_code` and `same_runtime`.

## Parameters

The STL manifest is the same as for [mesh-check](mesh.md). Its rotations define
the initial assembly. Additional rotation over time is specified below,
about the assembly Z axis relative to `rotation_origin_m`. Part names must match
exactly. Use `cad/` meshes in assembly coordinates. STL files from `print/`,
already oriented for printing, first need inverse transforms into the assembled
position. Update external CAD paths in the manifest after moving the project.

```json
{
  "allowances_m": {"print": 0.0002, "fuzz": 0.0002, "mesh": 0.00005, "reserve": 0.00005},
  "sampling_step_m": 0.00025,
  "motion_step_m": 0.00025,
  "cases": [{
    "id": "cord_by_platter_during_full_turn",
    "yarn_radius_m": 0.002,
    "poses_m": [
      [[0.0535, -0.012, 0.04411], [0.0535, 0.012, 0.04411]],
      [[0.0535, -0.012, 0.04411], [0.0535, 0.012, 0.04411]]
    ],
    "part_rotation_deg": {"platter": [0, 360], "post": [0, 360]},
    "rotation_origin_m": [0, 0, 0]
  }]
}
```

All input dimensions are in meters, except angles in degrees. Every pose has
the same number of corresponding nodes: points on the same prescribed polyline.
World coordinates and angles vary linearly between input poses. `0 → 360`
means a full turn; angles are not reduced to the shortest arc.
Unlisted parts remain stationary. One pose means a static check.

Allowances are summed **radially**, not by diameter. In this example a 2 mm
yarn radius becomes a 2.5 mm checking envelope. The 0.2/0.2/0.05/0.05 mm values
are explicit design assumptions for preliminary review, not measured printer
accuracy or a validated fuzz model. Replace them for different yarn or printing
conditions and rerun the calculation.

## Interpreting results

| Status | Meaning for CAD revision |
|---|---|
| `initial_nominal_contact` | Yarn intersects the part in the initial pose. Check whether the starting position is realistic; this is not a successful release test. |
| `nominal_contact` | The prescribed path hits a surface. Revise the overhang/transition or check a different exit route. |
| `allowance_contact` | Nominal yarn passes, but the specified print and fuzz allowance is insufficient. |
| `unresolved_clearance` | No contact was detected, but checking precision cannot establish a clear passage. Reduce both steps. |
| `clear_with_allowance` | This particular motion is clear at the specified dimensions and allowances. It does not cover every possible loop. |

The clearance deficit is conservative for the checked motion.
It **does not equal the depth to cut from the part**: a surface change may
relocate contact, affect strength, or create a new hook. Review the indicated
zone first, then rerun the entire unchanged case set.

Rounding alone does not prove snag elimination: a rounded overhang can still
block a rising loop. A control test covers three outcomes: lifting under an
overhang is blocked, moving outward succeeds, and shortening the overhang
makes the original lift clear.

## Protection against missed contact

Each part is checked separately, including connected shells. Signed distance
accounts for yarn radius; segment–triangle intersections catch thin walls
even between distance samples. Such contact coordinates come from the actual
intersection, not a distant yarn node.
For a point outside an individual closed shell's bounding box, the distance
sign is forced positive. This geometric consequence removes false deep contacts
caused by unstable normal signs on very thin decorative faces. The issue
was reproduced on PITAYA seeds during rotation.

Parts separated from the entire yarn motion by disjoint bounding volumes
are excluded without detailed sampling. A full cylindrical envelope is used
for rotation, so intermediate angles cannot be missed by this filter.
For these rows, `proof` gives the method, the clearance lower bound is derived
from the envelopes, and `minimum_sampled_nominal_clearance_m=null` because no
distances were sampled. A positive bound already proves geometric clearance.

Half the spatial step and half an upper bound on displacement between checked
poses are subtracted from minimum clearance. For rotation, that bound includes
`max|Δp| + max(rho) * |Δangle|`, with the angle in radians. Thus a full turn
does not disappear from the check when endpoint poses coincide.

## Coverage and limits

PITAYA includes 36 yarn motions under six leaves (three routes, 2/4 mm
diameters) and four scenarios at the rotating platform rim. PEACH includes
eight saved sweeps under both leaves and four rotating-rim scenarios.
These are stress cases with known geometry, not probabilities of loop formation.
Nominal taut-yarn paths are checked separately in model audit reports.

This set does not include a complete model of the ball, table, hand,
yarn self-contact, loop tension, or every way yarn can get under a part.
Include additional stationary obstacles in the STL scene when needed.
Prescribed yarn poses are not checked for compatibility with extension or
force balance. Predicting retention and release force requires yarn contact
mechanics with bending, friction, and experimentally determined material
parameters. For example, [Discrete Elastic Rods](https://www.cs.columbia.edu/cg/rods/index.html)
describes thin elastic rods; that is a separate problem and is not implemented here.

This mode aims to find geometrically problematic zones **before the main print**
and compare revisions using the same motions.

[Peach v13 results and coordinates](peach-snag-review.md).
[PITAYA v10 results and coordinates](pitaya-snag-review.md).
[Revised PITAYA v11 compared on identical cases](pitaya-v11.md).

A complete control example requiring no CAD package:

```sh
python tools/validate_snag_workflow.py
```

It creates STL overhangs before and after shortening and invokes the actual CLI.
One blocked path becomes clear; an already clear path stays clear.
This workflow also runs in CI alongside individual contact and rotation tests.
