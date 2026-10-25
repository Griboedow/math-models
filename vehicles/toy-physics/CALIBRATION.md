# Measurements that improve the model

Record printer, filament batch, layer orientation, layer height, walls, infill,
support cleanup and room conditions with each sample. Keep raw observations
separate from fitted parameters. Use ordinary test weights and instruments;
the contact-event module does not call for anyone to kick or step on the toy.

## Mass and geometry

1. Weigh the assembled vehicle without the key, coupons, brim or support.
2. Measure wheel radius/width, bearing diameter, axle overhang and wheel-center
   positions. Check that wheels touch a flat reference plane.
3. Measure reactions on small scales or by weighing one axle at a time at the
   same support height. Infer horizontal CG from those reactions. A separate
   controlled incline/fixture test can estimate CG height.
4. Set `mass_override_kg` and `cg_override_m` in the input when retaining the
   volume-based mass components. Without components, replace `mass_kg` and `cg_m`.
   The supplied mesh/slicer allocation
   is an estimate; it is not the same as a measured assembled mass distribution.

## Material and axle screening

Start with the actual spool's density and product data, rather than assuming
every PLA or PETG has the reference profile's properties. Record orientation and
print settings. Compare force/deflection and failure observations from controlled
printed coupons or spare axle assemblies against the local beam calculation.
Use fixture loads, not a child, for strength measurements. Fit effective modulus,
strength reduction and the critical section/load path; do not use infill percent
as a direct strength multiplier. Inspect creep under sustained load separately.
The report's default factors are provisional assumptions and cannot calibrate
themselves from the mesh.

## Floors, carpet and rolling

For each actual floor or carpet, record pile type, height, backing, pad, grain
direction, cleanliness and any seams. Test perpendicular directions on carpet.

- Apply several known static loads to a wheel or representative test coupon.
  Measure vertical compression to fit support stiffness, carpet foundation
  coefficient and the backing transition. Fit both loading and unloading if
  hysteresis is of interest.
- Tow the assembled vehicle slowly with a spring scale or force gauge and a
  nearly horizontal, low attachment point. Repeat runs and record starting and
  steady force separately. Fit journal losses using a separate wheel/axle test
  where possible; otherwise acknowledge their correlation with floor losses.
- Use at least two loads and two wheel radii before treating a fitted rolling
  arm as transferable. Check predictions against a withheld condition.
- A footprint/pressure film measurement can replace the assumed tread fraction.
  Inspect the validity warnings when a contact patch or pile indentation is
  large. Do not transfer full-size wheelchair coefficients to tiny printed tires.

The report's half/double parameter sweep demonstrates sensitivity. It is not
measurement uncertainty, a confidence interval or a bound on every possible
carpet.

## Buoyancy and horizon

The box examples are separate from the trike design. For a chosen printed
floating sample, record dry mass, water density/temperature, draft, roll and
pitch. Compare with the geometry-based prediction. Add a known small ballast
offset and check the change in attitude. A small imposed angle can check the
sign and approximate magnitude of the restoring moment.

Weigh the drained sample again after controlled immersion intervals to detect
water ingress. A fitted flooded fraction is a scenario parameter; dry STL
closure is not a leakage test. If water sloshes inside a large cavity, the
current fixed-flooding model is inadequate and needs a free-surface correction.

## Contact and washing comparisons

For contact proxies, measure force and deformation with a fixture and a chosen
compliant pad. Report pad material, geometry and contact area; the result is a
mechanical comparison of configurations, not a prediction of pain in a person.

For washing, use a repeatable benign soil mixture with known starting mass and
particle size. Keep drying interval, water volume, brush size, brush strokes,
orientation and rinse duration constant. Compare assembled and disassembled
states. Record disassembly/reassembly time separately. Measure retained water
after a specified drain time and residual dry soil mass after cleaning.

Replace estimated pocket volumes, drainage fractions and operation counts with
observations. Fit heuristic weights only if they improve prediction on held-out
samples. Keep the raw accessible-area and retained-volume metrics even if the
aggregate index changes. Washing performance does not establish microbiological
cleanliness or toy safety.
