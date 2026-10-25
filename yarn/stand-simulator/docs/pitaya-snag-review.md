# PITAYA v10: snag zones before printing

Next version: [PITAYA v11 — revised fits and low tips](pitaya-v11.md).
Both geometries were rechecked with 0.3.0 on the same 40 cases:
6 improvements, 0 regressions; straight and diagonal lifts under leaves still contact.

**40 cases** were checked with an additional radial allowance of 0.5 mm:
36 motions under six leaves (three routes, 2/4 mm diameters) and four
full-turn platform checks with yarn near its rim.

Result: **8 clear with allowance, 30 with contact during motion,
and 2 intersecting the body in the initial pose**. These are deliberately chosen
stress cases, not frequencies or probabilities of snagging during normal knitting.

## What to revise or inspect in CAD

| Motion | 2 mm yarn | 4 mm yarn |
|---|---|---|
| Lift a loop straight up under a leaf | Contact, all 6 leaves | Contact, all 6 leaves |
| Lift diagonally outward | Contact, all 6 leaves | Contact, all 6 leaves |
| First outward at low height, then up | Clear with allowance, all 6 leaves | Contact with low tips, all 6 leaves |
| Yarn at the platform rim, full turn in both directions | Clear with allowance | Initial body contact |

The 4 mm yarn meets an obstacle even on the route that is clear for 2 mm yarn.
For leaf 1, the problematic surface is near
**X=69.170, Y=45.457, Z=2.871 mm** in the original `cad/leaf_1.stl`.
In assembly coordinates above the support surface, Z≈3.871 mm.
The case holds the center of the 4 mm yarn at 3 mm height during outward motion;
its nominal lower surface remains 1 mm above the support. The yarn's upper
surface meets the underside of the tip.

![4 mm yarn meets the low leaf tip](../results/pitaya_v10_snags/leaf_4mm_exit.png)

The red tube is yarn, the translucent envelope is the allowance, and green
is the checked leaf. This prescribed pose shows a geometric obstacle,
not a calculated deformation forcing yarn through the part.

Review the low tip and provide a continuous outward loop exit with sufficient
clearance. Checking one fillet or only thin yarn cannot establish this.
Repeat every saved route and diameter; changing leaf height also requires
fit and strength checks.

The 4 mm yarn at the rotating rim already contacts the body in its initial pose.
This does not prove rotational pinching or a successful release test.
A valid initial yarn route near that rim must be determined separately.

## Files

- [HTML report](../results/pitaya_v10_snags/report.html) and [full JSON results](../results/pitaya_v10_snags/audit.json).
- [40 original cases](../results/pitaya_v10_snags/cases.json) and [assembly](../results/pitaya_v10_snags/scene.json).
- [Zone markers for importing over the corresponding STL](../results/pitaya_v10_snags/review_markers.json).

```sh
python tools/run_snag_audit_parallel.py results/pitaya_v10_snags/scene.json results/pitaya_v10_snags/cases.json --out results/pitaya_new_revision --workers 3
python -m yarnstand snag-compare results/pitaya_v10_snags/audit.json results/pitaya_new_revision/audit.json --out results/pitaya_comparison.json
```

The check does not model automatic routing, yarn compression or friction,
loop formation, or printed micro-snags. It identifies geometric risk zones
and provides reproducible revision comparisons. [Method and parameters](snags.md).
