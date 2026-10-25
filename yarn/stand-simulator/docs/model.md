# Model and assumptions

## Units and provenance

Internal units are m, kg, s, N, N·m, and kg·m²; configuration angles are in degrees.
Conversion to grams, millimeters, and mN·m happens only in the interface.
PITAYA geometry comes from the original v07/v08 CAD model. Ball dimensions and
masses, hand rhythms, friction, elasticity, and unwinding resistance are scenario
estimates. Friction is specified for **the complete assembled mechanism**,
not multiplied by the number of bearings.

## Ball and yarn

The ball is an ellipsoid with semi-axes a, b, c. Its axial moment of inertia is:

`I_ball = κ m (a² + b²) + m e²`, with `κ=1/5` by default.

This is the uniform-ellipsoid formula with an eccentricity correction e.
Real balls are not uniform, so κ is editable. Total inertia is
`I = I_rotor + I_ball`.

Exit height: `z = z_platform + c(1 + exit_height_fraction)`.
The horizontal projection uses a tangent to an ellipse with semi-axes
`a*ratio*sqrt(1-f²)` and `b*ratio*sqrt(1-f²)`, where f is the height fraction.
The default `unwind_radius_ratio=1` places the exit on the outer surface.
The legacy value 0.85 is preserved on import, but an exit inside the ball
receives `exit_inside_ball`, and forces are marked as conditional.
Unit yarn direction u and exit point p give the effective lever arm
`A = |(p × u)_z|`; for a circular section this is `r cos(β)`.

This local model assumes a fixed tangential exit and allows inclined yarn:
feed along the yarn is `ds = A dθ`, consistent with torque `T A` in work.
It does not track a specific winding or movement of the exit point over a soft
ball. A spatial line entering the ellipsoid receives `path_intersects_ball`.
Automatic exit relocation and routing around the ball are not solved.
The orientation of a non-axisymmetric ellipsoid stays fixed in this local model;
shape changes and rotation of its principal axes are not calculated.

Prescribed feed is a smooth `sin²` pulse over part of a period. Each pulse
integrates to `draw_m`. Changes in free-span length due to transverse hand motion
are added. Default knitting rhythm: 24 mm per 1 s, active fraction 0.55;
crochet: 45 mm per 1.35 s, active fraction 0.30.
These values are **not an empirical norm**.

Positive extension `x = consumed length − supplied length` produces
tension `T = max(0, k x + c_y x_dot)`; tension is zero for `x<=0`.
`k = EA / L_initial`, where EA is the effective axial stiffness of the yarn
and L_initial is its initial free span. This is a local linear approximation.
Negative x represents an idealized reserve of loose yarn.

Outer-layer peeling resistance is specified by `peel_force_N`. It produces
dissipative torque `F_peel A`, including during assumed unwinding on overrun.
This empirical parameter combines friction between windings; it is not a
separate exact model of the ball structure.

## Rotation and traction

The system remains at rest while `T A <= τ_start + F_peel A`.
During rotation:

`I θ_ddot = T A − (τ_run + b θ_dot) − F_peel A`.

Angular velocity is bounded below by zero: this model has no motor or spring
driving the stand backward. Integration uses semi-implicit Euler, usually
dt=0.0005 s. The time step is automatically checked against the spring–inertia
period and damping time `I/(b+c_y*A_max²)`. At least 20 steps per active pulse
and 40 per hand-motion period are required. Draw length is integrated
analytically, including period boundaries. An excessive step raises an error
instead of losing short pulls. A test compares results at half the time step.
This checks the numerical solution, not physical validity.

Torque the ball must transmit to the rotor:
`τ_required = |I_rotor α + τ_bearing|`.
Available torque:
`τ_capacity = μ_ball max(0, m_ball g − T u_z) r_contact + τ_spindle`.

The default is `τ_spindle=0`: unknown extra spindle grip is not invented.
A tight spindle fit can add substantial grip and should be measured.
The first slip is recorded when `τ_required > τ_capacity`. Integration then
continues for the hypothetical coupled system, not a new physical slip model.
Vertical ball lift-off is flagged separately; vertical spindle retention
is not modeled.

## Sliding and onset of tipping

The support is the convex hull of circular foot contacts (each approximated
by 24 vertices) or user-defined points. Decorative leaves are not feet.

Normal reaction: `N = (m_stand + m_ball)g − F_z`.
Sliding starts when `|F_xy + F_inertia| > μ_foot N`.
Ball eccentricity adds a horizontal reaction `−m a_com`.

The center of pressure on the support plane is:

`x_COP = [W x_COM + z_exit F_x − x_exit F_z + z_ball F_inertia,x] / N`,

with an analogous expression for y. Tipping has not started while the COP
remains inside the convex polygon. The stationary body's center-of-mass height
does not enter this initial lift-off condition on a horizontal table.
It matters after tilting, but subsequent rocking and falling are not calculated.

The snag threshold is computed separately from static equilibrium.
For each edge `n·x <= B`, the maximum force is:

`T_tip = [W B − m_ball g e] / [z_exit(n·u_xy) + (B − n·p_xy)u_z]`

for a positive denominator. Subtracting `m_ball g e` represents the worst
phase of ball displacement. The sliding threshold is:

`T_slide = μ_foot W / (|u_xy| + μ_foot u_z)`.

Lift-off is also checked: `T_lift = W/u_z` for u_z>0. The minimum is the snag
threshold. Table compliance, hand pushes, impact impulses, and rotation of
the entire stand about the vertical axis are excluded.

## Path checks

The path is a catenary: `z(x)=a*cosh((x-x0)/a)+C`, `a=H/(λ*g)`.
Constants are determined by the endpoint heights. Density λ is per meter
of yarn length, including inclination, not per meter of horizontal projection.
`H=T*D/L` is set from nominal tension along the straight endpoint span.
This is exact equilibrium of a heavy yarn for the prescribed endpoints and H,
but does not solve unwinding, contacts, or extension. Dynamics still use
the direction of the straight span. If H < 0.001 N or sag exceeds 10% of the
horizontal span, an out-of-scope status is returned rather than extrapolated forces.
For small sag, the leading correction is proportional to `λ*g*D*L/(8*H)`;
the old `D²` formula underestimated sag at unequal endpoint heights.
241 points are compared with the body's surface of revolution and ellipsoidal
leaf envelopes. This is **geometric screening**, not a snag probability.
FDM steps, the rotating gap, fuzz, and loose loops require physical testing.
The CAD package also includes checks of selected rays against STL files.

`hypotheses_valid_for_entire_run` requires both no mechanical events and
a valid nominal path. With a geometric problem,
`peak_tension_with_valid_path_and_coupling_N` is null and all forces are conditional.
`mechanical_hypotheses_valid_for_entire_run`, `valid_coupled_interval_end_s`,
and `peak_tension_before_first_event_N` refer only to support and traction;
they do not override geometric limitations. Trace fields
`coupled_assumptions_valid` and `model_assumptions_valid` distinguish these.
One nominal path check does not validate every instant of motion or loose loops.
A time of first geometric contact is not invented.

## Basis of the equations

- [OpenStax: conditions for static equilibrium](https://openstax.org/books/university-physics-volume-1/pages/12-1-conditions-for-static-equilibrium).
- [OpenStax: rotational dynamics and moment of inertia](https://openstax.org/books/college-physics/pages/10-3-dynamics-of-rotational-motion-rotational-inertia).
- [SKF: bearing friction components](https://evolution.skf.com/using-a-friction-model-as-an-engineering-tool-3/).

These sources support the basic mechanics and the need to distinguish friction
sources. They **do not validate the chosen values for a particular stand,
yarn, or hand motion**.
