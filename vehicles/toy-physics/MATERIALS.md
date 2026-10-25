# PLA and PETG calculation profiles

**PLA is the default.** These profiles use particular Bambu products as reference
data, not universal values for every PLA or PETG spool. They change the physics
calculations; they do not rewrite the trike's existing PETG/clear-PLA print projects.

| Reference profile | Density, g/cm³ | Young's modulus XY / Z, MPa | Bending modulus XY / Z, MPa | Tensile strength XY / Z, MPa |
|---|---:|---:|---:|---:|
| PLA — Bambu PLA Basic | 1.24 | 2580 / 2060 | 2750 / 2370 | 35 / 31 |
| PETG — Bambu PETG HF | 1.28 | 1810 / 1540 | 2050 / 1810 | 34 / 23 |

Sources: [Bambu PLA Basic TDS V3.0](https://store.bblcdn.com/s7/default/b189de92249a4b9ebed28b8ea1f080f0/Bambu_PLA_Basic_Technical_Data_Sheet.pdf)
and [Bambu PETG HF TDS V1.0](https://store.bblcdn.com/ce12d65176a94f1086e6aefa238e62e2.pdf),
accessed 2026-10-26. Values above are reported central values, not guaranteed
minimum strengths. Manufacturer specimens used 100% infill and conditioning
at 55 °C for 8 h for PLA, 75 °C for 8 h for PETG HF. The manufacturer describes
the data as reference/comparison values; real print performance depends on
geometry and printing conditions. Those conditioning procedures are not a
recommendation to heat this assembled toy.

## Convenient controls

```sh
python run.py                                              # PLA
python run.py --material PETG --output reports/petg
python run.py --material PLA --density-g-cm3 1.25 --output reports/custom
python run.py --material PETG --print-axis Z --safety-factor 3 --output reports/petg-z
```

Use `examples/material.json` to save the defaults for subsequent runs:

```json
{
  "material": "PLA",
  "print_axis": "XY",
  "strength_factor": 0.5,
  "modulus_factor": 0.7,
  "safety_factor": 2.0,
  "stress_concentration_factor": 1.5
}
```

The optional `density_g_cm3` field replaces the density only. Other optional
property overrides are `young_modulus_MPa`, `bending_modulus_MPa`,
`tensile_strength_MPa` and `poisson`. Use supplier data or measurements for the
actual spool. `1 g/cm³ = 1000 kg/m³`; internal calculations use SI throughout.
`--strength-factor`, `--modulus-factor` and `--stress-concentration-factor` also
override the JSON values. The report includes a PLA/PETG reference comparison
using the same factors, without global property overrides; its caption explains
that local explicit overrides and fixed masses still apply.

The HTML and JSON record the selected settings and actual resolved inputs.
Changing output folders preserves earlier reports. `make_examples.py` restores
all bundled examples, including the default material settings.

## Mass and flotation

Vehicle `mass_components` contain **polymer volume**, not external envelope
volume. For each part `mass = polymer_volume × density`; its mass and position
contribute to the combined center of gravity. A fixed ballast can instead use
`fixed_mass_kg`. With one material everywhere, changing density scales mass but
does not move CG. Mixed materials or fixed ballast can move CG.

For the trike, the existing slicer object masses are allocated among parts with
the documented shell-volume proxy, then divided by the **original recorded
slicer density**: 1270 kg/m³ for Generic PETG, 1240 kg/m³ for Generic PLA. These
reference values remain stored per part. The selected new density is applied
to those volumes. The key, supports, brim and fit coupons are excluded.
This remains an estimate of deposited material; it is not a physical weighing.

The buoyancy module computes polymer volume from outer geometry, wall thickness
and infill. Its density follows the selected material unless overridden per
component. Lower density reduces mass and draft; it does not change external
displacement volume. Flooded voids reduce displacement. The output reports
buoyancy reserve, bulk density, roll/pitch and local restoring stability.
Both solid polymers are denser than water; a sufficiently hollow, sealed print
can still float. The floating box examples remain independent of the trike.
Changing buoyancy infill does not silently change the trike's slicer-derived
polymer volumes or its solid axle cross-section.

## Local strength estimate

Density is not strength. Material selection independently changes the elastic
moduli and tensile reference strength. `XY` means the principal stress direction
lies in the layer plane; `Z` means across layers. The trike axles are intended
to print with their long axes in XY. This is a two-direction screening model,
not an anisotropic finite-element material law.

```text
effective bending modulus = reference bending modulus × modulus_factor
screening allowable       = reference tensile strength × strength_factor / safety_factor
nominal bending stress    = 32 × bending moment / (pi × diameter³)
local stress              = nominal bending stress × stress_concentration_factor
utilization               = local stress / screening allowable
reserve factor            = 1 / utilization, when loaded
```

Tensile reference strength is used as an intentionally lower comparison basis
than the manufacturer's flexural strength. This is still not a qualified design
allowable. The default strength reduction 0.5, modulus reduction 0.7, safety
factor 2 and stress concentration 1.5 are **assumptions**, not measured print
properties or values required by a standard. Poisson ratios 0.35 / 0.38 are also
assumed. The modulus factor affects contact elasticity and beam deflection;
it does not automatically change the separately specified support springs.

`utilization <= 1` produces `within_assumed_allowable` for **local static axle
bending only**. A value above 1 produces `exceeds_assumed_allowable`.
`strength_pass_fail` remains null: neither result approves the whole toy.
The beam assumes a solid circular section at the entered diameter and idealized
supports. The default stress concentration is not extracted from the groove
mesh. Inspect the actual critical section and load path before relying on it.
Infill fraction is not a strength multiplier. Chassis walls, fork roots, threads,
retainers, bearing crushing, shear failure, temperature, creep, fatigue and
impact require separate models or tests. A tipping case has no supported axle
result and must not be interpreted as zero utilization.

## Explicit overrides and Python use

Global settings apply first. A vehicle, wheel, axle or mass component may have a
`material_settings` object; a buoyant body or component may do the same. More
local values win. Selecting a different local material clears inherited density,
modulus, strength and Poisson overrides, while retaining the print factors.
For example, a part can keep `{"material_settings": {"material": "PLA"}}`
inside a PETG calculation. To keep physical mass and mechanics consistent,
apply the same local choice to that part's mass component and mechanical entry.

Existing explicit `surface_modulus_Pa`, `poisson`, axle `effective_modulus_Pa`,
`allowable_stress_Pa` and `stress_concentration_factor` remain authoritative.
The resolved profile is retained as reference; the effective numbers are stored
on the resolved wheel/axle. Explicit buoyancy `polymer_density_kg_m3` likewise
overrides the selected profile.

If a vehicle has `mass_components`, they determine mass/CG; use
`mass_override_kg` and `cg_override_m` for actual measurements. Without
`mass_components`, `mass_kg` and `cg_m` remain fixed inputs. The six-wheel demo
therefore stays at 600 g. Buoyancy mass/CG overrides also remain fixed.

```python
from toyphysics.materials import prepare_vehicle
from toyphysics.rolling import solve
from toyphysics.buoyancy import Body

settings = {"material": "PETG", "print_axis": "XY"}
resolved = prepare_vehicle(source_vehicle, settings)
rolling_result = solve(resolved, floor, child_load)
floating_result = Body(floating_spec, material_settings=settings).solve()
```

Resolve from original source inputs each time you change material. The resolved
vehicle contains explicit calculated moduli for the mechanical solver; feeding
it back into `prepare_vehicle` would preserve those explicit values.
