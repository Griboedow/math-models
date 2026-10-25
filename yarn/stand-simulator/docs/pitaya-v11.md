# PITAYA v11: CAD fixes and recalculation with 0.3.0

V11 fixes the tight wide-leaf fit and the low tip that blocked Ø4 mm yarn moving
outward. V10 is preserved separately. The upper-joint micro-tab, wide asymmetric
leaves, 21 seeds, and rotating mechanism are retained.
This is an **unprinted prototype** checked in CAD and a slicer:
physically test the leaf fit before printing the large body.

![Identical Ø4 mm yarn pose before and after revision](../results/pitaya_v11_validation/yarn_escape.png)

## Geometry changes

| Parameter | V10 | V11 |
|---|---:|---:|
| Minimum leaf clearance above the table | 3.870 mm | 6.974 mm |
| Minimum leaf–body surface distance | 0.00978 mm | 0.21034 mm |
| Leaf width in its own plane | about 34.3 mm | 34.34 mm |
| Clear original stress cases | 8 of 40 | 14 of 40 |
| Contact during motion | 30 | 24 |
| Contact in the initial pose | 2 | 2 |

The distal leaf section is smoothly shortened in its local plane by up to
3.8 mm, starting after X=18 mm. This raises the bottom by about 3.1 mm without
moving the two pins. Thickness and rounded edges are preserved; roots were not
thinned to obtain clearance.

The body recess uses a 0.40 mm outline offset instead of scaling about its
center. Rear clearance is 0.35 mm; radial pin clearance is 0.25 mm.
The nominal outline offset is not the minimum spatial clearance between rounded
parts: that distance was separately measured as 0.21034 mm.

STEP export exposed an OpenCascade 7.9 issue: surfaces extruded directly from
an offset curve were lost on reimport. In the final source, only the recess
outline is converted to a B-spline with tolerance 0.00001 mm **before** solid
creation. Final STL and STEP files come from this same geometry, after which
calculations and slicing were repeated.

![Shape and upper joint](../results/pitaya_v11_validation/shape_comparison.png)

## Identical cases before and after

Both versions use the same simulator code:
**0.3.0, a698bae1f233cdacc0f07e7d9bcadbe07bd1b44e**.
Executed source and mesh hashes, plus Python/VTK/trimesh versions, are in
the reports. Final `snag-compare` confirms `same_audit_code=true` and
`same_runtime=true`: **6 improvements, 0 regressions**, and 26 remaining flagged cases.

The original [40 cases](../results/pitaya_v11_validation/cases.json) are unchanged.
Spatial and motion steps are both 0.25 mm. Additional **radial** allowance:
0.5 mm, comprising print 0.2, fuzz 0.2, mesh 0.05, reserve 0.05 mm.
These are design assumptions, not measured print accuracy or specific yarn fuzz.
No cases or parts have `unresolved_clearance`; no further step refinement
was needed to resolve uncertainty.

| Motion under each of 6 leaves | V10, Ø2/4 mm | V11, Ø2/4 mm |
|---|---|---|
| Straight lift | contact / contact | contact / contact |
| Diagonally outward and up | contact / contact | contact / contact |
| First outward at low height, then up | clear / contact | clear / clear |

For leaf 1 on the last route, the clearance lower bound after subtracting the
allowance and both step corrections is **3.225 mm for Ø2 mm** and
**1.226 mm for Ø4 mm**. All six leaves were checked separately.
Saved motions are stress cases; their proportions do not represent snag
probabilities during knitting.

Two original Ø4 mm rotating-rim cases intersect the stationary body before
rotation. They remain in the original set with that status; this does not
prove rotational pinching. In a [separate additional set](../results/pitaya_v11_validation/additional_rim_cases.json),
the yarn center is raised from 44.11 to 46.11 mm with identical XY, diameter,
allowance, and full turns in both directions. Both additional cases are clear.
They do not replace the original two failing poses or count among the 6 improvements.

- [Before: full snag-audit](../results/pitaya_v11_validation/before/snags/audit.json).
- [After: full snag-audit](../results/pitaya_v11_validation/after/snags/audit.json) and [HTML](../results/pitaya_v11_validation/after/snags/report.html).
- [Comparison](../results/pitaya_v11_validation/comparison.json).
- [Additional rotating-rim check](../results/pitaya_v11_validation/after/additional_rim/audit.json).

## Nominal paths and mechanics

Both geometries were rechecked after the distance-sign fix in 0.3.0.
Each uses 720 static paths, 54 diameter/tension cases, 60 dynamic scenarios,
and 27 prescribed motions. Full and nearly empty round balls, knitting and
crochet, five stand positions, different exit heights, and azimuths are retained.
Stand mass of 230 g, rotating-assembly inertia of 0.000065 kg·m², friction,
and feed rhythms remain identical scenario estimates. Leaf revision is not
presented as a measured change to these physical parameters.

Adaptive selection of azimuths nearest contact can change after even a small
revision because symmetric directions have almost equal clearances.
Therefore the 54 diameter/tension combinations for v11 were explicitly replayed
from the saved v10 set. Their inputs match; source and source hash are in metadata.

For both versions, of 720 nominal paths, **456 are clear, 24 contact parts,
and 240 enter the ball and are rejected as invalid**. All 24 contacts involve
a nearly empty ball, low exit, and hands below a high stand.
That setup needs a different exit route or stand position; cutting away the
body to accommodate a prescribed path through it is not a valid fix.

Of 24 hand motions, 14 are clear, 2 have initial contact, and 8 are rejected for
entering the ball. The 3 older Ø2 mm loop routes give two contacts and one clear
exit. These checks without the 0.5 mm allowance are kept separate from the
new stress set; their conditions are not mixed.

For a full ball, middle exit, and hands to the side, calculated peaks are
**0.092 N for knitting** and **0.203 N for crochet**. With the assumed parameters,
mechanics and this nominal path pass throughout the simulated interval.
For crochet, the model also flags excess loose feed; this estimates overrun,
not the shape of a free loop.

All 30 nearly empty-ball scenarios lose platform traction.
In the side-position example, this occurs after 0.141 s for knitting and
0.082 s for crochet; coupled-rotation validity ends at the event.
Forces before it are about 0.026 N. Late peaks and 6 subsequent ball-lift flags
are not used as reliable CAD revision requirements. Rotational resistance
and actual ball-to-spindle/platform traction need measurement.
The current calculation assumes no additional spindle coupling.
Overall, 20 of 60 dynamic cases pass both mechanics and nominal-path validity.

[Before summary](../results/pitaya_v11_validation/before/nominal/summary.json),
[after summary](../results/pitaya_v11_validation/after/nominal/summary.json),
[parameters and hashes](../results/pitaya_v11_validation/after/nominal/metadata.json).

## CAD and print-package checks

Reimported body and leaf each contain one valid solid; the full STEP assembly
contains **49 valid solids**. Body volume changes by about 0.0125 mm³ during
the STEP round trip. All six leaf positions, insertion offsets of
0/0.5/1.5/3/6/9 mm, mechanical interfaces, and the rotating platform's full
cylindrical envelope were checked: intersection volumes are zero.
Minimum body–platform clearance is **0.8 mm**.
Unchanged mechanism meshes match v09 by SHA-256.

Fit distance is measured between all boundary shells, with a separate
intersection-volume check. STEP exhibits a reproducible OCCT numerical issue:
a shortcut solid-containment check returns zero near one spline seam even
though boundary surfaces are 0.21034 mm apart; shifting a point by 0.001 mm
changes that response. The raw value is retained in the report, not hidden.
It is not substituted for the surface-distance measurement.

All 15 print STL files are watertight, consistently oriented, and have positive
volume. Both material regions of the multicolor 3MF are also watertight.
New body, six-leaf, and fit-coupon projects were created and sliced in Bambu
Studio for P2S/0.4 mm without warnings.
Estimates: body about 289 minutes / 126.7 g, six leaves 108 minutes / 17.2 g,
fit coupon 48 minutes / 13.8 g; mass includes supports.
Compatible projects for the unchanged platform and mechanism retain their
previous version names. G-code is not included in the delivered package.

[CAD check before](../results/pitaya_v11_validation/before/cad_fit.json),
[after](../results/pitaya_v11_validation/after/cad_fit.json),
[STEP and sources](../results/pitaya_v11_validation/after/geometry_provenance.json).

The separate `PITAYA_v11_model.zip` contains parametric sources, print STL files,
STL files in assembly coordinates, STEP, 3MF projects, a fit coupon, instructions,
and a portable scenario set. V10 is preserved.
Print one leaf and a small fit coupon first.

## Repeating the calculations

Paths in scene.json resolve relative to the manifest. If the CAD package moves,
update only `path`, preserving part names and transforms.

```sh
python tools/recheck_pitaya.py /path/to/PITAYA_v10 --out results/pitaya_v11_validation/before/nominal
python tools/recheck_pitaya.py /path/to/PITAYA_v11 --out results/pitaya_v11_validation/after/nominal
python tools/replay_pitaya_sensitivity.py results/pitaya_v11_validation/after/nominal results/pitaya_v11_validation/before/nominal/mesh_sensitivity.json
python tools/run_snag_audit_parallel.py results/pitaya_v11_validation/before/scene.json results/pitaya_v11_validation/cases.json --out results/pitaya_v11_validation/before/snags --workers 3
python tools/run_snag_audit_parallel.py results/pitaya_v11_validation/after/scene.json results/pitaya_v11_validation/cases.json --out results/pitaya_v11_validation/after/snags --workers 3
python -m yarnstand snag-compare results/pitaya_v11_validation/before/snags/audit.json results/pitaya_v11_validation/after/snags/audit.json --out results/pitaya_v11_validation/comparison.json
```

At the time of this review, **65 Python tests and 10 UI tests** passed locally
on the calculation code. CAD changes were separately checked by the geometry
and slicing procedures above. Yarn contact with a surface does not prove
jamming; friction, bending, crushing, burrs, and spontaneous loop release
are not modeled. Printed material strength and actual fits remain untested.
