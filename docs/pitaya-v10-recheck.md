# PITAYA v10: recheck, October 18, 2026

> Archived calculation from before the model audit. The path and dynamics
> values below are superseded by the [model 0.2.0 recalculation](audit-fixes.md).
> In particular, the 696 clear paths included invalid lines through the ball.
> The CAD-fit section remains a separate check of unchanged geometry.

The review used v10 CAD geometry with wide leaves, the pink micro-tab,
and the shifted first pin. The simulator update was pulled from
`f5322a7932dea19f92ca371f747bcb993a7e9e73`; there were no local changes before
updating. An additional VTK numerical tolerance was fixed during the review.
Hashes of executed sources and STL files, plus coordinate transforms, are in
[metadata.json](../results/pitaya_v10_recheck/metadata.json).

**Conclusion: no intersections were found in the rotating assembly, but v10
cannot yet be considered a validated printed fit.** Minimum leaf-to-body CAD
clearance was only 0.0098 mm. A loose loop under a leaf also cannot follow some
prescribed lifting routes without contact.

| Check | Result |
|---|---|
| Taut Ø2 mm yarn, 0.04 N | 696 clear paths and 24 contacts out of 720 |
| Diameters 1/2/4 mm and tensions 0.01/0.04/0.10 N | 54 additional cases; contact found for thick yarn under low tension |
| Prescribed hand motions | 22 clear sweeps and 2 with initial contact out of 24 |
| Three loop routes under a leaf | Two with contact, one geometrically clear |
| Rotation and support dynamics | 60 scenarios; nearly empty ball loses traction in all 30 of its scenarios |
| CAD fit | No intersections found; minimum leaf clearance is too small to establish printed compatibility |

These are counts of selected cases, **not probabilities** of snagging or success.

## Yarn and leaves

The main grid uses full and nearly empty balls, five stand positions,
three yarn exit heights, and 24 azimuths. Yarn diameter is 2 mm; tension is 0.04 N.
The scene includes the body, platform, seeds, spindle, six leaves, and feet.
Z=0 was moved to the surface under the feet (+1 mm relative to CAD).

All 24 main-grid contacts occur with a nearly empty ball, low yarn exit,
and a high stand: hands 5 cm below the surface under the feet, 35 cm away
horizontally. Yarn meets the body and platform; in six directions, also leaves.
The other 696 paths have positive conservative clearance bounds, with a
minimum of about 1.11 mm.

At lower tension, 0.01 N, a full ball on the same low route already gives body
contact for Ø4 mm yarn. For Ø2 mm, step refinement gives only about 0.046 mm
minimum sampled clearance (lower bound 0.021 mm). This formally clear path is
practically near contact: mesh error, printing error, and fuzz are excluded.

![Prescribed loop sweeps under a leaf](../results/pitaya_v10_recheck/leaf_sweep_comparison.png)

The loose-loop check uses a transverse yarn segment under leaf 1:
center radius 80 mm, height 2 mm above the table, segment length 44 mm.
Straight lifting produces contact at about 5 mm height. The selected diagonal
route, lifting and moving outward together, also contacts the leaf.
Moving first to radius 95 mm, then lifting, is geometrically clear;
the clearance lower bound is about 0.38 mm.

This demonstrates a geometric obstacle under the tip. It **does not prove**
that an actual soft loop will stay trapped or slip off: friction, fuzz,
deformation, spontaneous obstacle routing, and release force are not calculated.
The upper-joint micro-tab does not remove this lower overhang.

## Fit and rotating assembly

The review checked saved v10 body and leaf STEP files, six installed leaves,
six insertion positions, and the unchanged v09 mechanism. Hashes for the
platform, spindle, seeds, bushings, bearings, hardware, and feet match v09.

No intersections were found between the body and platform, spindle, hardware,
or the cylindrical volume swept by the rotating platform.
Minimum body–platform distance is 0.8 mm. The leaf tip sits about 3.87 mm
above the table.

Minimum leaf–body distance is **0.0098 mm**, near the inside of the upper leaf
projection. The equivalent v09 check gives 0.0183 mm, so this problem did not
first appear in v10. Scaling a pocket outline does not produce uniform clearance
around a complex contour. A pocket with controlled clearance and a small fit
coupon are needed before printing. No intersections does not establish
assembly compatibility of real parts with print errors.

## Dynamics

Stand mass of 230 g, rotor inertia of 0.000065 kg·m², and friction coefficients
retain their previous **estimated** values, not new v10 measurements.
Ball masses are 100 and 10 g. Additional spindle coupling is zero.

For the full ball, none of the 30 scenarios show traction loss, sliding,
or onset of tipping. Maximum use of the calculated sliding limit is about 20%,
and tipping limit about 23%. With the stand beside the hand on a desk and
a middle exit, peak tension is about 0.107 N for knitting and 0.231 N for crochet.

For the nearly empty ball, all 30 scenarios violate coupled ball/platform
rotation after 0.08–0.21 s. The subsequent curve is a hypothetical continuation,
not a prediction of actual slip. Seven late lift-off events also occur after
traction loss and are not independently reliable predictions.
The first priority is to measure rotational resistance and ball-to-platform/
spindle traction, rather than reinforcing the base using these conditional peaks.

In the sharp crochet example, a full ball produces up to 211 mm of hypothetical
excess feed during overrun. This indicates sensitivity to rhythm and braking,
not a predicted shape or actual length of a hanging loop.

## Simulator fix and reproduction

The default `vtkOBBTree` tolerance was found to be `0.01`: one centimeter when
working in meters. It hid some intersections between short segments and curved
surfaces. PITAYA signed-distance checks still found the 24 main contacts,
but the separate intersection list was incorrectly empty.
Tolerance is now explicitly `1e-9` m. A sphere-chord regression was added;
rerunning restored intersections. **38 Python tests and 9 JS tests** passed
at the time of this review.

```sh
python -m pip install ".[mesh]"
python tools/recheck_pitaya.py /path/to/PITAYA_v10 --out results/pitaya_v10_recheck
# Separate STEP check; also requires CadQuery:
python tools/check_pitaya_cad.py /path/to/PITAYA_v10 /path/to/PITAYA_v09 --out results/pitaya_v10_recheck/cad_fit.json
# Render saved sweeps; also requires Pillow:
python tools/render_pitaya_sweeps.py /path/to/PITAYA_v10 --results results/pitaya_v10_recheck
```

CAD packages are supplied separately. The [results directory](../results/pitaya_v10_recheck)
contains all configurations, tables, prescribed poses, per-frame results,
geometry hashes, and STEP checks. The latest complete sliced package remains
v09; v10 still has CAD-prototype status.
