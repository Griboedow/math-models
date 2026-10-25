# Checking yarn paths against STL

Install the optional libraries: `python -m pip install ".[mesh]"`.
The core dynamics still run without them.

```sh
python -m yarnstand preset --stand peach_v13 --out examples/peach.json
python -m yarnstand mesh-check scene.json examples/peach.json --tension .04 --out results/mesh.json
python -m yarnstand mesh-sweep scene.json poses.json --out results/sweep.json
python -m yarnstand snag-audit scene.json cases.json --out results/design_review
```

The `scene.json` manifest specifies closed STL meshes and their transforms into
assembly coordinates. Z=0 is the surface under the feet. Paths are relative to
the manifest. Transforms use manifest units; everything is then converted to meters.
The VTK segment-intersection tolerance is explicitly `1e-9` m.
Its default `0.01` would mean one centimeter and missed some intersections
with small curved surfaces. This is a numerical tolerance, not a yarn radius
or manufacturing tolerance.

```json
{"unit":"mm","parts":[{"name":"body","path":"cad/body.stl",
"transform":[[1,0,0,0],[0,1,0,0],[0,0,1,1.7],[0,0,0,1]]}]}
```

`mesh-check` uses a tangent to the elliptical horizontal section and a catenary
with weight per unit length of the yarn itself. This is the same calculation
as the fast screening and interface. Insufficient tension or excessive sag
returns an out-of-scope status. An exit inside the ball or a path entering it
receives `exit_inside_ball` / `path_intersects_ball`; such a path is not checked
as a free segment near the stand. Standard presets use a radius ratio of 1
instead of the previous 0.85. Imported parameters are not changed automatically.

Yarn is checked as a tube of finite radius, not an infinitely thin ray.
VTK computes signed distances to oriented triangles of closed surfaces;
a separate segment-intersection check catches thin walls.
The default maximum step is the smaller of half the yarn radius and 0.5 mm.

`clearance_lower_bound_m` subtracts half the maximum step from the minimum
sampled clearance. This is a conservative bound for the prescribed polyline
and mesh: distance changes no faster than point displacement.
`clear` is returned only for a positive bound. Small positive clearance
with insufficient sampling receives `unresolved_sampling_margin`, not a false
no-contact result. The bound excludes polyline approximation error relative
to the smooth catenary, STL and print errors, and yarn compression.
For marginal clearances, reduce both path-generation and checking steps;
sampling precision alone is insufficient.

A sweep's `poses.json` contains `yarn_radius_m` and `poses_m`: an array of
poses, each with the same number of corresponding `[x,y,z]` points in meters.
Points move linearly between poses. The tool inserts intermediate poses and
also subtracts half the largest point displacement between them.
Thus two clear endpoints cannot hide an obstacle crossing between them.
Initial intersection receives a separate status.

This is a **kinematic check of prescribed motion**, not a prediction of
a loose loop spontaneously slipping off. The yarn does not bend around
obstacles; flexibility, loops, self-contact, friction, fuzz, and FDM burrs are
not modeled. The tool provides neither release forces nor snag probabilities.

For CAD work, use [snag-audit](snags.md): it checks prescribed loop shapes and
part rotation, adds explicit geometric allowances for printing and fuzz, and
reports zone coordinates in the original STL. Loop formation and force-based
interaction with parts are still not predicted.

The report saves input STL hashes and transforms. A positive total volume
cannot hide an inverted individual shell. Treating separate positive shells
as a union of solids also corrects the distance sign near overlapping components.

Meshes must be watertight and consistently oriented, with positive volume
for each connected shell. Multi-shell parts are checked as unions of solids.
Nested negative cavity shells are rejected as unsupported instead of being
automatically reversed and filled. Connected surfaces with holes and through
cavities are supported.
For large scans, use the Python `MeshScene` API and reuse the scene to avoid
rebuilding spatial indexes. Excessively small steps are rejected before
allocation: at most 250,000 points along a path, 100,000 poses, and 2,000,000
nodes across all sweep poses.
