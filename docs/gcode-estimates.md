# Manufacturing inputs from Bambu G-code

`yarnstand.manufacturing.read_gcode` integrates deposited model extrusion about
an explicitly supplied mechanical axis. PEACH v15 uses this reader after all
parts are sliced, and then reconstructs the assembly coordinates in its own CAD
repository. The reader was developed during the neighboring Lemon print audit;
this commit makes the shared calculation available independently of that local
UI work.

```python
from yarnstand.manufacturing import read_gcode

estimate = read_gcode("plate_1.gcode", axis_xy_mm=[128, 128])
print(estimate["model_mass_kg"], estimate["axis_inertia_kg_m2"])
```

The example axis is illustrative. Read the actual project placement; do not
assume the bounding-box centre is the rotation axis. For labeled multi-object
plates, pass `object_ids=["8"]`. Some single-object CLI exports omit object labels:
use an unfiltered read only after verifying that the slice contains one object.

The importer accounts for per-tool material data, relative/absolute coordinates
and extrusion, G92 resets and retraction repayment. It excludes supports, purge,
brim and other non-model features. Deposited material occupies the layer slab
below the nozzle. Unsupported extrusion arcs and non-planar model deposition
fail explicitly; disable arc fitting when preparing input.

These are slicer estimates, not measurements. Nozzle-centre path bounds are not
outside part dimensions. Material density, flow and shrinkage need calibration.
Bead cross-section inertia is neglected. A slice is not proof of FDM strength or
physical bearing preload. Feature names alone do not verify infill density;
Peach checks actual extrusion-width coverage of representative CAD sections.

`calibrate(config, observations)` applies only explicitly measured values with
a stated source. A measured stand mass does not silently scale inertia or
change bearing drag. Uncertainty is recorded but not propagated by this helper.

Run `python -m unittest discover -s tests -p test_gcode_manufacturing.py` for
analytic line-mass, centroid, inertia, object filtering, tool-material,
retraction and measurement-separation checks.
