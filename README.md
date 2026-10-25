# Mathematical models

Find and fix as many design mistakes as possible **before they become physical
objects**. This repository brings together the calculations behind the things
we design, print and build.

The ambition is the depth of virtual validation used in automotive engineering:
understand geometry, loads, motion, materials, manufacturing variation and
failure modes before committing to hardware. Ideally, a physical prototype
would reveal small differences from a well-understood design, so we could
calibrate and refine it instead of rebuilding the same toy again and again.
That is the direction of this project. The present calculators cover selected
mechanisms and scenarios; their assumptions and validation limits are explicit.

## Model catalog

| Area | Calculator and its README | Questions it explores |
|---|---|---|
| Yarn | [Rotating yarn stands](yarn/stand-simulator/) | Yarn tension, overrun, traction, sliding, tipping, snag clearance and manufacturing mass/inertia; Lemon, Peach and Pitaya examples |
| Vehicles | [Printed toy vehicles](vehicles/toy-physics/) | N-wheel support, floor resistance, child loads, PLA/PETG axle bending, buoyancy and level attitude, contact and washability comparisons; Trike MINI v06 example |

```text
yarn/
  stand-simulator/    # README, Python model, browser UI, inputs, reports, tests
vehicles/
  toy-physics/       # README, Python model, material profiles, inputs, reports, tests
```

Each calculator has its own installation instructions, equations, input units,
examples, results and tests. New calculators belong in separate folders with
their own README. Shared code should emerge from actual common requirements.

## How calculations should improve a design

1. Define geometry, operating conditions and the mistakes we want to catch.
2. Record where every important input comes from: measurement, supplier data,
   CAD/slicer output or an assumption.
3. Explore load cases, parameter variation and failure boundaries before printing.
4. Check equations against limiting cases and independent reference results.
5. Measure the prototype, explain discrepancies and feed those measurements back
   into the model. Keep the evidence that supports each revision.

A calculation should help choose the next design change or the next useful
experiment. A polished plot is not evidence that all relevant physics has been
modeled. Results must distinguish numerical verification from measurements and
state the behavior they do not yet predict.

## Start a calculator

From the repository root, for yarn stands:

```sh
cd yarn/stand-simulator
python -m yarnstand serve
```

Or, from the repository root, for toy vehicles:

```sh
cd vehicles/toy-physics
python -m pip install -r requirements.txt
python run.py
```

The vehicle calculator defaults to PLA. Each model README explains its controls,
dependencies, test commands and interpretation of results.

CAD, printable kits and assembly instructions live in
[3d-Models](https://github.com/Griboedow/3d-Models). Calculators live here;
the CAD repository can retain model-specific inputs and validation evidence.

## Repository history

This is the former `yarn-stand-simulator` repository, renamed and organized for
multiple mathematical models. Existing yarn history is retained. Toy physics
was migrated from `3d-Models`; see [migration notes](MIGRATION.md) for provenance
and updated paths. The yarn calculator retains its [MIT license](yarn/stand-simulator/LICENSE).
The migration does not assign a new license to imported material.
