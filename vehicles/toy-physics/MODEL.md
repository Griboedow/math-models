# Equations, inputs and validity

The implementation is a set of independent calculation modules. All units are
SI. Coordinates are right-handed: x forward, y right, z up. Gravity is
`g = 9.80665 m/s²`. Input values describe a scenario; they are not measurements
unless the provenance explicitly says so.

Material selection defaults to PLA. [MATERIALS.md](MATERIALS.md) defines the
PLA/PETG reference properties, density-to-mass conversion, print orientation,
assumed strength reductions and explicit override precedence. Density affects
weight and flotation independently of the mechanical property inputs.

## 1. N-wheel support and child load

For wheel i, input hub position `(x_i, y_i, z_i)`, radius `R_i`, width `b_i`,
local ground height `h_i`, and combined wheel/axle/chassis vertical stiffness
`k_i`. The initial geometric gap is `g_i = z_i - R_i - h_i`; a common offset
does not affect load sharing. The chassis is rigid except for these independent
support springs. Orientations remain close enough to level for linearized
vertical displacement compatibility.

Let toy weight be `W = m g`. A child contributes either explicit force `P` or
`P = child_mass × g × weight_fraction`, at `(x_P, y_P)`. A horizontal push
`(F_x, F_y)` at height `z_F` shifts the required center of pressure:

```text
sum N_i       = W + P
sum x_i N_i   = W x_G + P x_P + z_F F_x
sum y_i N_i   = W y_G + P y_P + z_F F_y
N_i >= 0
```

With more than three contacts, equilibrium alone is insufficient. The solver
minimizes complementary elastic energy:

```text
minimize sum [ integral(0..N_i) delta_i(n) dn + g_i N_i ]
subject to force and moment balance and N_i >= 0.
```

For a linear support, `delta_i = N_i/k_i` and its energy is `N_i²/(2k_i)`.
Carpet compression is added in series. A linear program first checks whether
nonnegative reactions exist; SLSQP then selects the compatible distribution.
The equality residual is returned. Outside the contact convex hull, the model
reports tipping and does not invent a supported pressure result. The support
margin is the shortest distance from the required center of pressure to the
support-polygon edges. One wheel or collinear wheels have marginal support in
this point-contact model, even though real wide patches may provide some moment.

This is quasi-static. It excludes body-floor contact, high-angle wheel motion,
chassis fracture, inertia, slope-normal reactions and transient load transfer.
The example child load is an assumed 15 kg × 25% = 36.8 N, not a limit for use.
When `contact_area_m2` is supplied for the applied load, mean hand/body contact
pressure `P/A` is also returned; it does not resolve local shell deformation.

## 2. Contact pressure and surfaces

### Hard floors

For an elastic cylinder on a plane, use effective width `L = b × phi`, where
`phi` is an assumed tread contact fraction. With wheel/floor moduli `E_w, E_f`
and Poisson ratios `nu_w, nu_f`:

```text
1/E* = (1 - nu_w²)/E_w + (1 - nu_f²)/E_f
a    = sqrt(4 N R / (pi L E*))
A    = 2 a L
p_mean = N/A
p_peak = 2 N/(pi a L)
```

These are Hertz line-contact relations; the implementation is checked against
their load and radius scaling. [INL BISON contact verification](https://mooseframework.inl.gov/bison/verification/Contact/contact_index.html)
provides the analytical cylinder benchmark. Finite, angular tread lugs, plastic
yielding, layered FDM elasticity, flooring coatings and large contact patches
are outside that idealization. A small-patch warning is emitted when relevant.
The surface modulus represents the contacting polymer walls, not an automatic
infill-to-stiffness conversion. Total support deflection uses `k_i` separately;
the geometric quantity `a²/(2R)` is not treated as total Hertz displacement.

Linoleum, parquet and tile have separate editable presets. Their numerical
moduli, loss arms and traction values are illustrative assumptions, not product
data or measured properties of the user's floor.

### Carpet

The carpet model is a simplified compressible foundation with pile thickness H,
foundation stiffness `k_v` in Pa/m, and an incremental backing spring `k_b`.
For small indentation delta, a cylinder has footprint half-length
`a ≈ sqrt(2 R delta)`. The lumped foundation law is:

```text
C = 2 b phi sqrt(2 R) k_v
N = C delta^(3/2)
delta = (N/C)^(2/3), for N <= C H^(3/2)
delta = H + (N - C H^(3/2))/k_b, after pile bottoming
A = 2 b phi sqrt(2 R delta)
p_mean = N/A
```

This is a model choice with an effective fitted `k_v`, not an exact fiber-level
pressure distribution. No carpet peak pressure is asserted. After bottoming,
the footprint law is only an approximation; both bottoming and indentation
above 10% of wheel radius are flagged. Complementary energy is integrated
analytically, continuously through the bottoming transition.

Pile height does not uniquely determine resistance. Backing, cushioning and
texture also matter, as described by the [US Access Board's floor-surface guide](https://www.access-board.gov/ada/guides/chapter-3-floor-and-ground-surfaces/).
Its accessibility requirements are not used as toy design limits. The three
carpet presets require measured compression and pull-force calibration.

### Rolling, bearings and small rigid steps

```text
F_roll,i = N_i c_i/R_i
F_journal,i = mu_j N_i r_j/R_i
F_carpet,i = eta N_i delta_i/(2 a_i)
F_pull = sum(F_roll,i + F_journal,i + F_carpet,i)
```

Here `c` is the rolling-resistance moment arm in meters, `mu_j` the effective
journal coefficient, and `eta` a fitted carpet loss fraction. `c` should cover
losses not already counted in the explicit carpet term, to avoid double
counting. The result represents steady low-speed towing with a low application
point. Starting friction, hair entanglement and tile-joint vibration are not
resolved. A simple `mu_surface × total_load` bound flags possible sliding; it
is not a driven-wheel traction model.

For a sharp rigid step of height h below wheel radius R:

```text
F_step = N sqrt(2 R h - h²)/(R-h), 0 <= h < R
```

This follows moment balance about the step corner, with horizontal force at the
axle. `h >= R` is blocked within that idealization. It is a separate estimate;
soft pile height is never inserted as a hard step height.

The optional axle calculation uses `I=pi d⁴/64`, bending stress
`sigma=32 M/(pi d³)` and elementary beam deflection. For a cantilever with end
load, `M=N L`, `u=N L³/(3 E I)`; for a centered load on two simple supports,
`M=N L/4`, `u=N L³/(48 E I)`. When material properties are resolved, a configurable
stress concentration factor multiplies nominal stress. The local stress is
compared with `reference tensile strength × strength_factor / safety_factor`.
Reference properties distinguish XY and Z; beam modulus includes a separate
reduction factor. This gives a local stress utilization, not a whole-toy
strength pass/fail. See [the material model](MATERIALS.md#local-strength-estimate)
for assumptions and omitted failure modes. No strength is inferred from density
or modulus alone. Without an allowable stress input, only nominal demand is
returned, preserving the standalone beam calculation.

## 3. Buoyancy, infill and horizon

This module is independent of rolling. A component may be a closed box, or an
outward-oriented closed triangle mesh. STL input uses `mesh_unit_m` (default
0.001 m/mm); optional `transform` is applied after unit conversion and its
translations are therefore meters. An `inner_mesh` uses the same specification.
Components must not overlap and each inner mesh must lie inside its outer mesh.
The importer verifies closure, winding and positive volume; it does not prove
component non-overlap or arbitrary shell containment.

For a box, wall thickness gives an explicit inner box. With outer/inner volumes
`V_o, V_i`, infill fraction f and polymer density rho_p:

```text
V_solid = V_o - (1-f) V_i
m = rho_p V_solid
```

Mass first moments use the corresponding outer-minus-inner integrals. Uniform
infill is homogenized within the interior. For a complex part without an inner
mesh, `shell_volume_fraction` supplies an explicitly approximate homogeneous
solid fraction `s + (1-s)f`. Point masses may add idealized ballast; their own
displacement is omitted. Mass and CG overrides are available for measurements.

If fraction q of the void space is freely flooded, the effective displaced
volume at each pose is:

```text
V_displaced = V_outer_submerged - q (1-f) V_inner_submerged
```

Floodwater is excluded from displacement, rather than also being added as a
second mass contribution. q=0 describes sealed voids; q=1 describes fully
flooded connected pores. Intermediate q is a fixed scenario, not a leakage-time
or air-compression solution. A closed digital mesh does not establish printed
watertightness, and an assembly cavity is not automatically a sealed hull.

For each roll/pitch, heave is solved from `rho_water V_displaced = m`. Mesh
triangles are clipped at water level, and signed tetrahedron volumes and first
moments give the center of buoyancy B. At waterplane z=0, a planar closing cap
has zero contribution to those integrals. No convex hull approximation replaces
the supplied mesh. The buoyant moment about G is:

```text
tau = (B-G) × (0, 0, rho_water g V_displaced)
```

The solver uses `R = R_y(pitch) R_x(roll)` and finds zero generalized roll/pitch
torques near upright, constrained to ±70°. At that pose it differentiates
torque after re-equilibrating heave. Positive eigenvalues of restoring matrix
`K = -d(tau)/d(angle)` indicate local stability. The equivalent eigenvalue
lengths are `K_eigen/(m g)`. For an upright symmetric box these reproduce:

```text
GM_roll  = B²/(12 draft) + draft/2 - KG
GM_pitch = L²/(12 draft) + draft/2 - KG
```

Here KG is measured from the bottom. The standard relationships
`BM=I_waterplane/V` and `GM=KB+BM-KG` are described in the
[US Navy Salvage Manual, Volume 1](https://www.navsea.navy.mil/Portals/103/Documents/SUPSALV/Salvage%20Docs/Salvage%20Manual%20Vol%201%20S0300-A6-MAN-010.pdf).
The code uses numerical geometry and checks against the analytical box result.

`holds_level` means the solved angles are within the selected tolerance
(default 1°). It is separate from `locally_stable`: a tall CG can be exactly
upright yet unstable. This is not a global capsize search. Free-surface sloshing,
waves, dynamic impacts, surface tension and changing flooded fraction are not
modeled. There is no requirement that the trike itself float or remain level.

## 4. Parent-contact metrics

For a kick on a freely moving toy, use reduced mass
`m_eff = m_foot m_toy/(m_foot+m_toy)`. For a trapped toy use the supplied effective
foot mass. Relative energy available to the contact is `E=0.5 m_eff v²`.
This is not necessarily all dissipated in the foot. With assumed stopping
distance d and peak/mean shape factor alpha:

```text
F_dynamic_mean = E/d
F_estimated_peak = F_static + alpha E/d
p_comparison = F_estimated_peak/A_assumed
```

A step adds `F_static = m_adult g weight_fraction`; its dynamic effective mass is
an independent input. The assumed contact area, footwear deformation and stopping
distance dominate these results. `edge_radius_m` records local geometry; an
optional supplied contact modulus enables a spherical-tip Hertz estimate, with
a small-contact validity flag. The default report uses explicit areas rather
than inventing tissue properties. Large toy deformation or breakage invalidates
the assumed stopping distance and rigid geometry.

Force, energy and pressure are mechanical proxies, not a validated pain scale.
[IASP's terminology](https://www.iasp-pain.org/resources/terminology/) distinguishes
the personal experience of pain from the physical stimulus. The outputs therefore
leave pain score and injury probability null; there are no clinical thresholds.

## 5. Washability index

Each manually listed feature has surface area, entrance width, depth, pocket
volume and estimated drainable fraction. Brush access requires an exposed
opening at least the chosen brush diameter and depth within brush reach.
Disassembly can expose hidden features and open pockets. Dry-grain entry is
compared with entrance width, while liquid mud can enter smaller openings.

```text
Access = brush-accessible area / listed area
Retained = sum(pocket_volume × (1 - drainable_fraction))
Drainage = exp(-Retained / reference_volume)
Surface = 1 / (1 + layer_height/reference_roughness)
Effort = 1 / (1 + disassembly_operations/reference_operations)
Index = 100 × weighted_mean(Access, Drainage, Surface, Effort)
```

Default weights are 0.45, 0.30, 0.15 and 0.10. These are openly chosen design
weights. Layer height is only a roughness proxy; orientation, extrusion defects
and coating matter too. The inventory is not an automatic STL measurement.
No bacteria, sterilization effectiveness, cleaning time or safety rating is
predicted. [EHEDG's test-method description](https://www.ehedg.org/certification-testing/useful-information/test-methods)
emphasizes application-specific cleaning regimes; the present heuristic is not
an EHEDG test or certification.
