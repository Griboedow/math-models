"""Manufacturing evidence: planned toolpaths are estimates, not measurements.

Dependency-free reader for Bambu-style G-code with feature/layer comments.
It never reads printer credentials, connects to a printer, or changes G-code.
"""
from copy import deepcopy
import hashlib
import math
from pathlib import Path
import re

MODEL_FEATURES = {'Outer wall', 'Inner wall', 'Overhang wall', 'Sparse infill',
                  'Internal solid infill', 'Top surface', 'Bottom surface',
                  'Bridge', 'Internal bridge', 'Gap infill', 'Floating vertical shell'}
WORDS = re.compile(r'([XYZE])([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)')


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be a finite positive number')
    return float(value)


def read_gcode(path, *, axis_xy_mm, object_ids=None):
    """Integrate deposited model lines about an explicit mechanical axis.

    Supports absolute/relative XYZ and E, per-tool density/diameter, G92 and
    retraction repayment. Rejects model extrusion arcs instead of treating
    chords as arcs. Supports, skirts and purge towers are excluded.
    Path bounds refer to nozzle centres, NOT the printed outside dimensions.
    """
    path = Path(path)
    if len(axis_xy_mm) != 2 or not all(math.isfinite(v) for v in axis_xy_mm):
        raise ValueError('A finite two-coordinate mechanical axis is required')
    selected = None if object_ids is None else {str(v) for v in object_ids}
    xyz = [0., 0., 0.]
    epos, debt = {}, {}
    relative_e, relative_xyz = False, False
    tool, obj, feature, layer_top, layer_height = 0, None, '', None, None
    density, diameter = [1.24], [1.75]
    density_explicit = diameter_explicit = False
    mass = mx = my = mz = second = 0.
    bounds = [[math.inf]*3, [-math.inf]*3]
    layers, tools, features, settings = {}, {}, {}, {}
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for raw in stream:
            sha.update(raw)
            line = raw.decode('utf-8', errors='replace').strip()
            match = re.match(r';\s*(filament_density|filament_diameter)\s*[:=]\s*(.+)', line)
            if match:
                values = [_positive(float(v.strip()), match[1]) for v in re.split(r'[;,]', match[2]) if v.strip()]
                if match[1] == 'filament_density': density, density_explicit = values, True
                else: diameter, diameter_explicit = values, True
            for key in ('layer_height', 'initial_layer_print_height', 'wall_loops',
                        'sparse_infill_density', 'xy_contour_compensation', 'xy_hole_compensation',
                        'elefant_foot_compensation', 'print_sequence'):
                if line.startswith('; '+key+' = '): settings[key] = line.split(' = ', 1)[1]
            if line.startswith('; Z_HEIGHT:'): layer_top = float(line.split(':', 1)[1])
            if line.startswith('; LAYER_HEIGHT:'): layer_height = float(line.split(':', 1)[1])
            if line.startswith('; FEATURE:'): feature = line.split(':', 1)[1].strip()
            if line.startswith('; start printing object, unique label id:'): obj = line.rsplit(':', 1)[1].strip()
            if line.startswith('; stop printing object'): obj = None
            code = line.split(';', 1)[0].strip()
            if not code: continue
            command = code.split()[0]
            if re.fullmatch(r'T\d+', command): tool = int(command[1:])
            elif command == 'M83': relative_e = True
            elif command == 'M82': relative_e = False
            elif command == 'G91': relative_xyz = True
            elif command == 'G90': relative_xyz = False
            elif command == 'G92':
                values = {k:float(v) for k,v in WORDS.findall(code)}
                if 'E' in values: epos[tool] = values['E']
                for i,k in enumerate('XYZ'):
                    if k in values: xyz[i] = values[k]
            elif command in ('G0', 'G1', 'G2', 'G3'):
                values = {k:float(v) for k,v in WORDS.findall(code)}
                new = [xyz[i]+values.get(k,0.) if relative_xyz else values.get(k,xyz[i]) for i,k in enumerate('XYZ')]
                delta = values.get('E',0.) if relative_e else values.get('E',epos.get(tool,0.))-epos.get(tool,0.)
                if 'E' in values: epos[tool] = epos.get(tool,0.)+values['E'] if relative_e else values['E']
                if delta < 0: debt[tool] = debt.get(tool,0.)-delta
                repaid = min(max(delta,0.),debt.get(tool,0.)) if delta > 0 else 0.
                if repaid: debt[tool] -= repaid
                deposited = max(0.,delta-repaid)
                model = layer_top is not None and feature in MODEL_FEATURES and (selected is None or obj in selected)
                moved = math.hypot(new[0]-xyz[0],new[1]-xyz[1]) > 1e-9
                if model and deposited > 0 and moved:
                    if command in ('G2', 'G3'): raise ValueError('Model extrusion arcs are unsupported; disable arc fitting')
                    if layer_height is None or layer_height <= 0: raise ValueError('Missing positive layer height')
                    if abs(new[2]-layer_top) > .002 or abs(xyz[2]-layer_top) > .002:
                        raise ValueError('Non-planar model extrusion is unsupported')
                    def material(values):
                        if len(values) == 1: return values[0]
                        if tool >= len(values): raise ValueError('Missing material data for tool')
                        return values[tool]
                    m = deposited*math.pi*(material(diameter)/2)**2*material(density)/1e6
                    # If unretraction shares a move with deposition, only its
                    # remaining portion carries newly extruded material.
                    fraction = repaid/delta if delta > 0 else 0.
                    start = [xyz[i]+fraction*(new[i]-xyz[i]) for i in range(3)]
                    mass += m
                    mx += m*(start[0]+new[0])/2; my += m*(start[1]+new[1])/2
                    # Material occupies the slab below the nozzle, not the layer top.
                    mz += m*(layer_top-layer_height/2)
                    ax,ay = axis_xy_mm
                    x0,x1,y0,y1 = start[0]-ax,new[0]-ax,start[1]-ay,new[1]-ay
                    second += m*(x0*x0+x0*x1+x1*x1+y0*y0+y0*y1+y1*y1)/3*1e-6
                    for i in range(3):
                        bounds[0][i] = min(bounds[0][i],start[i],new[i]); bounds[1][i] = max(bounds[1][i],start[i],new[i])
                    layers[layer_top] = layer_height
                    info = tools.setdefault(str(tool),{'mass_kg':0.,'layers':{}})
                    info['mass_kg'] += m; info['layers'][layer_top] = layer_height
                    features[feature] = features.get(feature,0.)+m
                xyz = new
    if mass <= 0: raise ValueError('No selected model deposition found')
    return {'source_file':path.name,'source_sha256':sha.hexdigest(),'object_ids':sorted(selected) if selected is not None else None,
            'model_mass_kg':mass,'centroid_print_mm':[mx/mass,my/mass,mz/mass],
            'axis_xy_mm':list(axis_xy_mm),'axis_inertia_kg_m2':second,
            'nozzle_path_bounds_mm':bounds,'layer_top_mm':max(layers),
            'tools':{key:{'mass_kg':v['mass_kg'],'layer_tops_mm':sorted(v['layers']),
                          'deposited_layer_thickness_sum_mm':sum(v['layers'].values())} for key,v in tools.items()},
            'feature_mass_kg':features,'settings':settings,
            'material_data_from_gcode':density_explicit and diameter_explicit,
            'support_and_purge_excluded':True,'status':'slicer_estimate',
            'limitations':['Not a measurement of deposited mass or dimensions',
                           'Nozzle-centre bounds exclude bead width and must not be used as outside diameters',
                           'Moments use straight-line beads; bead cross-section contribution is neglected',
                           'Density, flow, cooling shrinkage and layer bonding require physical calibration']}


# Only these observations have a defined mapping into the dynamics model.
MEASUREMENT_TARGETS = {
    'stand_mass_g': ('mass_kg', .001),
    'platform_height_mm': ('platform_height_m', .001),
    'platform_diameter_mm': ('platform_radius_m', .0005),
    'support_radius_mm': ('support_radius_m', .001),
    'rotor_inertia_kg_m2': ('rotor_inertia_kg_m2', 1.),
    'com_height_mm': ('com_height_m', .001),
    'start_torque_mNm': ('start_torque_Nm', .001),
    'running_torque_mNm': ('running_torque_Nm', .001),
}


def calibrate(config, observations):
    """Apply explicit measured observations, preserving all unmeasured inputs.

    A measured total mass does not rescale inertia or bearing friction. Dimension
    deltas do not turn into unmeasured bearing preload or friction coefficients.
    """
    from .model import from_config
    from_config(config)
    result = deepcopy(config)
    if not isinstance(observations,dict) or set(observations)-set(MEASUREMENT_TARGETS):
        raise ValueError('Unknown measurement; use documented observation names')
    applied = {}
    for name,record in observations.items():
        if record is None: continue
        if not isinstance(record,dict) or set(record)-{'value','uncertainty','source'}:
            raise ValueError(f'Invalid observation: {name}')
        value = _positive(record.get('value'),name)
        uncertainty = record.get('uncertainty')
        if uncertainty is not None:
            if isinstance(uncertainty,bool) or not isinstance(uncertainty,(int,float)) or not math.isfinite(uncertainty) or uncertainty < 0 or uncertainty >= value:
                raise ValueError(f'Invalid uncertainty: {name}')
        if not isinstance(record.get('source'),str) or not record['source'].strip():
            raise ValueError(f'Measurement source required: {name}')
        field,scale = MEASUREMENT_TARGETS[name]
        result.setdefault('stand',{})[field] = value*scale
        applied[name] = {**record,'target':'stand.'+field,'status':'measured'}
    if applied:
        result['stand']['name'] = result['stand'].get('name','Stand').split('; measured overrides')[0]+'; measured overrides'
    from_config(result)
    return {'config':result,'measurements':applied,
            'limitations':['Only explicitly measured fields replaced; other values retain their previous evidence status',
                           'Uncertainty is recorded but not propagated into the time-domain simulation',
                           'No strength or bearing-preload claim follows from geometric fit alone']}
