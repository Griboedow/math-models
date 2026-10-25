# Peach v13 — recalculation after the model audit

The `peach_v13` preset uses a platform 70.7 mm above the support surface,
Ø7.9 mm feet on a 54 mm radius, and estimated mass and inertia of 300 g and
0.0000545 kg·m². Mass, friction, and yarn properties need calibration.
Original STL files are in the separate PEACH_v13 CAD project; this fix did not
change part geometry.

Model 0.2.0 fixes inclined-yarn weight, ball-exit checks, validity statuses,
and multi-shell STL handling. The old claim of 6,912 clear paths with the hand
above the base is replaced by this recalculation: the previous check did not
exclude yarn passing through the ball. New presets move the exit to the outer
surface (`unwind_radius_ratio=1`).

## Dynamics

45 scenarios were repeated: three balls, three rhythms, and five hand positions.
All 15 baseline full-ball scenarios retain support, traction, and a valid checked
nominal path. The nearly empty ball loses traction in all 15 scenarios;
subsequent forces are conditional. The large ball also passes the checks,
but retains the platform-overhang warning: deformation and actual soft contact
are not calculated.

For a full ball with the hand to the side, peaks are about 0.091 N for knitting,
0.191 N for short pulls, and 0.042 N for slow feed.
Hypothetical excess feed is 35, 197, and 0 mm, respectively.
These are scenario calculations, not measurements of a finished product.

## Yarn geometry

The 8,640-path grid was repeated: 100/10/200 g balls, five positions,
four exit heights, 24 directions, three tensions, and 2/4 mm diameters.
Contacts, invalid paths through the ball, and unresolved clearances are counted
separately. Marginal clearances use smaller path-generation and checking steps.
Result: **3,704 clear paths, 664 contacts, and 4,272 paths through the ball**.
No unresolved clearances remained in this grid after refinement.
Totals and hashes are in
[summary.json](../results/peach_v13_audit_fix/summary.json) and
[metadata.json](../results/peach_v13_audit_fix/metadata.json).

Eight saved sweeps under the leaves were rechecked. Four routes toward the tips
are geometrically clear; four toward the roots contact parts.
For 4 mm yarn near the small leaf, the nominal clearance lower bound remains
about 0.126 mm. It excludes printing error and fuzz.
The result directory retains input poses, their hashes, and check responses.
Friction and spontaneous path selection by soft yarn are not modeled.

## What still needs physical checking

The previous CAD concern remains: an 8.15 mm spacer with 7.99 mm between body
shoulders. Check axial freedom of the lower outer bearing ring after printing
and tightening. The simulator fix does not change these dimensions or validate
leaf strength or printed fit.

```sh
python -m pip install ".[mesh]"
python tools/recheck_peach.py /path/to/PEACH_v13 --out results/peach_v13_audit_fix
```

Reproducing sweeps requires the CAD package's `simulation` directory with
saved `sweep_*mm_*.json` files. See the [equations](model.md),
[STL method](mesh.md), and [fix description](audit-fixes.md).
