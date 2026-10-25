# Audit fixes — model 0.2.0

Review of the original `main` at commit `8b09b76` found reproducible errors in
sag calculation, free-path validity, result status, multi-shell STL orientation,
and time resolution. All listed cases now have automated regression coverage.

## What changed

- The shared path calculation in `yarnstand/paths.py` uses a catenary with weight
  per unit length of the yarn itself. It is independently checked through
  differential equilibrium `H*z'' = lambda*g*sqrt(1+z'^2)`. The old formula
  treated density per yarn length as a load on the horizontal projection.
- New presets use `unwind_radius_ratio=1` instead of 0.85. The exit point lies
  on the surface of the ellipsoid's horizontal section; unequal semi-axes now
  use the actual ellipse. Legacy imported parameters are not replaced.
  An exit inside the ball or a spatial path entering it receives a separate
  status instead of a clear result. Automatic exit relocation and surface
  routing around the ball remain outside the model.
- Contact, invalid, or undefined nominal paths cancel the overall passing
  status. The interface marks all forces as conditional. Mechanical events
  and their times remain separate: a single path check cannot establish a
  first-contact time.
- Every connected STL shell is checked for watertightness, orientation, and
  positive volume. Multi-shell parts are checked as unions of solids.
  Nested negative cavity shells are explicitly rejected as unsupported;
  automatically reversing normals could incorrectly fill a cavity.
- Feed-pulse length is integrated analytically. The step must resolve the
  active pulse, hand motion, stiffness, and damping. An unresolved short pull
  now raises an error instead of disappearing from the calculation.
- CI installs mesh dependencies and runs geometry and interface tests.
- The first complete CI run found another incompatibility with VTK 9.7:
  `SetTolerance` no longer affected intersections. Its all-intersections
  search also misses curved surfaces even with an explicit tolerance,
  reproduced locally with VTK 9.7.1. VTK 9.7 and later use a first-intersection
  search with explicit `1e-9 m` tolerance, sufficient to detect contact.
  Earlier versions retain the previous call. A sphere-intersection regression
  checks both versions locally and in CI.
  See the [VTK API](https://vtk.org/doc/nightly/html/classvtkOBBTree.html).

## PITAYA v10 recalculation

> Snapshot calculated with version 0.2.0. The later 0.3.0 review also fixed a
> falsely negative distance outside shell bounds near thin decorative faces.
> The grids below were not recalculated with that safeguard; their contact
> lists should not be treated as final CAD revision instructions.
> New snag checks and the current method: [snags.md](snags.md).

Product geometry was unchanged. Mass, inertia, and friction remain scenario
estimates. Parameters and source/STL hashes are in
[metadata.json](../results/pitaya_v10_audit_fix/metadata.json).

| Check | Result |
|---|---|
| 720 nominal paths, Ø2 mm, 0.04 N | 456 clear, 24 contacting parts, 240 entering the ball |
| Diameter / tension | 54 cases with saved inputs |
| 60 dynamic scenarios | 30 lose traction; 20 have invalid paths through the ball, and another 2 contact the coarse screening geometry |
| Overall dynamics status | 20 scenarios pass the applied checks; this does not validate all moving loops |
| 24 prescribed hand motions | 14 clear, 2 with initial contact, 8 rejected for entering the ball |
| 3 loop routes under a leaf | 2 with contact, 1 geometrically clear |

For a full ball, middle exit, and hand to the side, peaks are now about
**0.092 N** for knitting and **0.203 N** for crochet. Changes from the old
values include moving the exit from a radius ratio of 0.85 to the outer surface.
Old and new values must not be compared as if they used identical assumptions.

The old 696 clear paths cannot serve as confirmation: the check did not exclude
yarn passing through the ball. The archived report and inputs remain for
comparison; the replacement results are in
[pitaya_v10_audit_fix](../results/pitaya_v10_audit_fix).

CAD-fit checks from the previous report are unchanged: the fixes concern
the simulator and interpretation, not attachment geometry.

## Reproduction

At the time of this audit, 53 Python tests (including STL, with no skips)
and 10 Node.js UI tests passed locally. The 0.2.0 wheel was built and tested
outside the working directory. PEACH v13 was also rechecked: 3,704 clear paths,
664 contacts, and 4,272 paths through the ball out of 8,640; four of eight saved
sweeps were clear and four contacted parts. See the [Peach report](peach-v13.md).
Saved full grids used VTK 9.6.2 and the main fix at `8ef06cc`; exact executed
source hashes are recorded in metadata. The subsequent VTK 9.7 adaptation
does not change the VTK 9.6 calculation branch.

```sh
python -m pip install ".[mesh]"
python -m unittest discover -s tests -v
node --test tests/test_ui.js
python -m yarnstand suite
python -m yarnstand sensitivity
python tools/recheck_pitaya.py /path/to/PITAYA_v10 --out results/pitaya_v10_audit_fix
python tools/recheck_peach.py /path/to/PEACH_v13 --out results/peach_v13_audit_fix
```

Reproducing Peach sweeps requires the CAD package's saved
`simulation/sweep_*mm_*.json` files. The script saves supplied poses and their
hashes alongside results. All paths are checked geometrically; this does not
calculate friction, fuzz, or spontaneous sliding of flexible yarn over obstacles.
