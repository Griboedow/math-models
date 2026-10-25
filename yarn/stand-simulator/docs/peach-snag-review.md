# Peach v13: zones to review before printing

Eight saved yarn motions under the leaves and four stress cases at the rotating
platform rim were checked. Yarn diameters: 2 and 4 mm. Additional radial
allowance: 0.5 mm, comprising print 0.2, fuzz 0.2, mesh 0.05, reserve 0.05 mm.
These are design assumptions.

**Result: 7 cases clear with allowance, 4 with nominal contact,
and 1 failing the specified allowance.** All four full-turn platform checks
pass for the saved yarn-segment position at the rim.
This does not establish clearance at other positions.

## Narrow passage after the small leaf

In `sweep_second_4mm_tip`, nominal body clearance drops to about **0.189 mm**.
This is insufficient for the 0.5 mm allowance: the difference is about **0.311 mm**.
Refining both spatial and motion steps to 0.025 mm gives a clearance lower
bound with allowance of **−0.336 mm**. Near the small leaf itself, the refined
bound is positive, about **+0.019 mm**.

The location on `01_body_peach.stl`, in original CAD-STL coordinates, mm:
**X=68.553, Y=24.973, Z=49.451**. Here the yarn approaches the body after moving
past the tip. Meeting the chosen allowance requires a passage change or another
valid route. The deficit is not an instruction to remove that depth of material:
the entire path must be checked after revision.

![Yarn near the body after the small leaf](../results/peach_v13_snags/second_leaf_4mm_gap.png)

The red tube is nominal yarn; the translucent envelope is the checking allowance.
Green highlights the checked part; pale parts provide assembly context.
This is a prescribed checking pose, not a calculated contact deformation.

## Routes toward the leaf roots

All four original rootward routes encounter an obstacle. Coordinates of the
first detected leaf contact are in its original frame, in mm:

| Case | Part | X | Y | Z |
|---|---|---:|---:|---:|
| Large leaf, 2 mm yarn | `04_leaf_green.stl` | 77.767 | −24.698 | 23.149 |
| Large leaf, 4 mm yarn | `04_leaf_green.stl` | 79.647 | −21.934 | 18.849 |
| Small leaf, 2 mm yarn | `08_leaf_second_green.stl` | 75.938 | −0.555 | 49.723 |
| Small leaf, 4 mm yarn | `08_leaf_second_green.stl` | 79.077 | 5.871 | 46.579 |

The initial pose does not intersect the leaf. During the prescribed motion,
the yarn enters its volume. Review the reverse side, transitions, and outward
escape options. Simple rounding may leave an overhang; its effectiveness
must be checked by repeating the saved motion.

![Prescribed path intersects the large leaf](../results/peach_v13_snags/main_leaf_root.png)

Other saved routes near the large leaf's tips are clear with allowance for both
diameters. Near the small leaf, the 2 mm route is clear with allowance.
These paths have their own starting positions; they cannot establish a release
route from every position under a root.

## Files for revision and reproduction

- [Cases](../results/peach_v13_snags/cases.json) and [assembly manifest](../results/peach_v13_snags/scene.json).
- [Full report](../results/peach_v13_snags/report.html), [JSON](../results/peach_v13_snags/audit.json).
- [Narrow-passage refinement](../results/peach_v13_snags/refined_tip/report.html).
- [STL zone markers and part mapping](../results/peach_v13_snags/review_markers.json).

```sh
python -m yarnstand snag-audit results/peach_v13_snags/scene.json results/peach_v13_snags/cases.json --out results/peach_new_revision
python -m yarnstand snag-compare results/peach_v13_snags/audit.json results/peach_new_revision/audit.json --out results/peach_comparison.json
```

The test identifies geometric obstacles and insufficient allowance. It does not
provide retention forces, snag probabilities, or a guarantee against printed
micro-snags. Method, coverage, and limitations: [snags.md](snags.md).
