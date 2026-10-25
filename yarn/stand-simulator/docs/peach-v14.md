# PEACH v14: validated exit widening and bearing alignment

V13 and v14 were rechecked with model 0.3.0 (`a698bae`), identical scenarios,
libraries, and allowances. Geometry is in the external `PEACH_v14` CAD package;
the simulator does not reconstruct it from a preset.

## CAD changes

- A smooth local body recess after the small leaf, with specified depth up
  to 1.25 mm. Across 899 samples of the exported STL, maximum change is about
  1.231 mm. The depth was chosen by rechecking the entire motion.
- Relief of only the small leaf's reverse side, up to 0.35 mm. The front,
  edges, tips, and asymmetry are preserved. 2,888 front-surface samples differ
  by less than 0.000001 mm; the large leaf's print mesh is byte-identical to v13.
- The lower bearing shoulder moved from Z=20.01 to 19.85 mm. Shoulder spacing
  and spacer height now match at 8.15 mm, removing the previous 0.16 mm mismatch.
  This is nominal CAD alignment, not a measured printed fit.

## Results of identical checks

The main set contains eight saved sweeps and four full-turn scenarios.
The radial allowance is 0.5 mm: print 0.2, fuzz 0.2, mesh 0.05, reserve 0.05 mm.

| Result after refinement | v13 | v14 |
|---|---:|---:|
| Clear with allowance | 7 | 8 |
| Contact on a route toward a root | 4 | 4 |
| Insufficient allowance | 1 | 0 |

For `sweep_second_4mm_tip`, with both steps at 0.025 mm:

| Surface | Nominal clearance v13 → v14, mm | Lower bound with allowance v13 → v14, mm |
|---|---:|---:|
| Body | 0.189 → 0.667 | −0.336 → +0.142 |
| Small leaf | 0.544 → 0.608 | +0.019 → +0.084 |

For the remaining marginal body clearance in `sweep_second_2mm_root`, both
steps were reduced to 0.0125 mm for both versions. Refining the body alone
does not cancel the confirmed leaf contact along the complete route.

Each root/tip pair has identical initial poses. Thus the checked tip route
starts at the same position from which rootward motion encounters an obstacle.
This does not guarantee escape from every loop position.

Four additional routes were checked separately: approach the root through 75%
of the clear segment, reverse, exit toward the tip, and continue 20 mm outward.
All four v14 routes pass with allowance; one v13 route fails. This set is
compared only with itself. Reverse motion is prescribed manually; spontaneous
slipping and friction are not calculated. `snag-compare` finds no regressions.

## Mechanics and export

For each version, 8,640 nominal paths were repeated: 3,704 clear,
664 contacting parts, and 4,272 entering the ball and rejected.
Every scenario classification matches. Also repeated: 45 baseline dynamic
scenarios, 60 sensitivity variants, 15 traction variants, and 3 time-step pairs.
Mass, inertia, friction, and yarn properties retain identical PEACH v13
estimates, so mechanics match; STL geometry is checked separately.
The full ball passes 15 baseline scenarios; the nearly empty ball loses traction
in all 15, with vertical lift-off also flagged in two. Deformation of a large
ball overhanging the platform is not modeled.

14 part and test meshes are valid; 30 assembly-intersection checks passed.
The body and small leaf were sliced in Bambu Studio for P2S 0.4 mm without
warnings. The body creates no new isolated islands on a 0.16 mm layer grid.
The package contains STL, STEP, four geometric 3MF plates, and source files.
Physical printing and yarn snag tests have not yet been performed.

Values, hashes, refinements, and comparisons:
[results/peach_v14_validation](../results/peach_v14_validation).
Raw reports, identical input poses, both geometries, and reproducible code
are supplied separately in `PEACH_v14_SIMULATION.zip`; print files are in
`PEACH_v14_PRINT_FILES.zip`. General commands: [snags.md](snags.md).
