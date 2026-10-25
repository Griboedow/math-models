"""Reference filament profiles and explicit, editable print assumptions.

These are product coupon data, not universal properties or qualified allowables.
See MATERIALS.md for sources, specimen conditions and override precedence.
"""
import copy
import math


PROFILES = {
    'PLA': {
        'reference_product': 'Bambu PLA Basic, TDS V3.0',
        'density_g_cm3': 1.24,
        'young_modulus_MPa': {'XY': 2580., 'Z': 2060.},
        'bending_modulus_MPa': {'XY': 2750., 'Z': 2370.},
        'tensile_strength_MPa': {'XY': 35., 'Z': 31.},
        'poisson': .35,
        'source_url': 'https://store.bblcdn.com/s7/default/b189de92249a4b9ebed28b8ea1f080f0/Bambu_PLA_Basic_Technical_Data_Sheet.pdf',
        'specimen_condition': '100% infill; manufacturer conditioned specimens at 55 C for 8 h.',
    },
    'PETG': {
        'reference_product': 'Bambu PETG HF, TDS V1.0',
        'density_g_cm3': 1.28,
        'young_modulus_MPa': {'XY': 1810., 'Z': 1540.},
        'bending_modulus_MPa': {'XY': 2050., 'Z': 1810.},
        'tensile_strength_MPa': {'XY': 34., 'Z': 23.},
        'poisson': .38,
        'source_url': 'https://store.bblcdn.com/ce12d65176a94f1086e6aefa238e62e2.pdf',
        'specimen_condition': '100% infill; manufacturer conditioned specimens at 75 C for 8 h.',
    },
}

DEFAULT_SETTINGS = dict(material='PLA', print_axis='XY', strength_factor=.5,
                        modulus_factor=.7, safety_factor=2., stress_concentration_factor=1.5)


def _positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be positive and finite')
    return value


def merge_settings(settings=None, overrides=None):
    """A local material choice resets global property overrides, not factors."""
    result = dict(DEFAULT_SETTINGS)
    result.update(settings or {})
    local = overrides or {}
    if 'material' in local and str(local['material']).upper() != str(result['material']).upper():
        for key in ('density_g_cm3', 'young_modulus_MPa', 'bending_modulus_MPa',
                    'tensile_strength_MPa', 'poisson'):
            result.pop(key, None)
    result.update(local)
    return result


def resolve_material(settings=None, overrides=None):
    s = merge_settings(settings, overrides)
    name, axis = str(s['material']).upper(), str(s['print_axis']).upper()
    if name not in PROFILES:
        raise ValueError('Material must be PLA or PETG')
    if axis not in ('XY', 'Z'):
        raise ValueError('print_axis must be XY or Z')
    p = PROFILES[name]
    density = _positive(s.get('density_g_cm3', p['density_g_cm3']), 'density_g_cm3')
    factors = {k: _positive(s[k], k) for k in
               ('strength_factor', 'modulus_factor', 'safety_factor', 'stress_concentration_factor')}
    if factors['strength_factor'] > 1 or factors['modulus_factor'] > 1:
        raise ValueError('Strength and modulus reduction factors must be in (0, 1]')
    if factors['safety_factor'] < 1 or factors['stress_concentration_factor'] < 1:
        raise ValueError('Safety and stress concentration factors must be at least 1')
    props = {k: _positive(s.get(k, p[k][axis]), k) for k in
             ('young_modulus_MPa', 'bending_modulus_MPa', 'tensile_strength_MPa')}
    poisson = float(s.get('poisson', p['poisson']))
    if not math.isfinite(poisson) or not -1 < poisson < .5:
        raise ValueError('Poisson ratio must be between -1 and 0.5')
    return dict(material=name, print_axis=axis, density_g_cm3=density,
                density_kg_m3=density*1000, poisson=poisson, **factors,
                reference_product=p['reference_product'], source_url=p['source_url'],
                specimen_condition=p['specimen_condition'],
                property_overrides={k: s[k] for k in ('density_g_cm3', 'young_modulus_MPa',
                    'bending_modulus_MPa', 'tensile_strength_MPa', 'poisson') if k in s},
                reference_young_modulus_Pa=props['young_modulus_MPa']*1e6,
                reference_bending_modulus_Pa=props['bending_modulus_MPa']*1e6,
                reference_tensile_strength_Pa=props['tensile_strength_MPa']*1e6,
                effective_young_modulus_Pa=props['young_modulus_MPa']*1e6*factors['modulus_factor'],
                effective_bending_modulus_Pa=props['bending_modulus_MPa']*1e6*factors['modulus_factor'],
                screening_allowable_stress_Pa=props['tensile_strength_MPa']*1e6*factors['strength_factor']/factors['safety_factor'],
                evidence='Reference coupon data plus assumed reductions. Poisson ratio and all four factors are uncalibrated assumptions.')


def prepare_vehicle(vehicle, settings=None):
    """Resolve volume-based mass and default mechanics; preserve explicit inputs.

    Always call with source inputs to change material. Resolved output contains
    explicit calculated moduli and is intended for the mechanical solver.
    """
    v = copy.deepcopy(vehicle)
    s = merge_settings(settings, v.get('material_settings'))
    material = resolve_material(s)
    components = []
    if 'mass_components' in v:
        moment, total = [0., 0., 0.], 0.
        for c in v['mass_components']:
            if 'fixed_mass_kg' in c:
                if 'polymer_volume_m3' in c:
                    raise ValueError('Use fixed_mass_kg or polymer_volume_m3, not both')
                mass = _positive(c['fixed_mass_kg'], 'fixed_mass_kg')
                density = None
                label = 'fixed mass'
            else:
                p = resolve_material(s, c.get('material_settings'))
                density = p['density_kg_m3']
                mass = density*_positive(c['polymer_volume_m3'], 'polymer_volume_m3')
                label = p['material']
            position = c['position_m']
            if len(position) != 3 or not all(math.isfinite(float(x)) for x in position):
                raise ValueError('Mass component position must contain three finite coordinates')
            total += mass
            moment = [a+mass*float(x) for a, x in zip(moment, position)]
            components.append(dict(name=c['name'], material=label, density_kg_m3=density, mass_kg=mass))
        _positive(total, 'assembled mass')
        v['mass_kg'] = total
        v['cg_m'] = [x/total for x in moment]
        mass_basis = 'Sum of polymer volume times selected density, plus fixed masses'
    else:
        _positive(v['mass_kg'], 'fixed vehicle mass')
        mass_basis = 'Fixed mass input; density does not rescale a measured/fixed mass'
    if 'mass_override_kg' in v:
        v['mass_kg'] = _positive(v['mass_override_kg'], 'mass override')
        mass_basis = 'Explicit mass_override_kg; calculated component masses retained for comparison'
    if 'cg_override_m' in v:
        v['cg_m'] = list(v['cg_override_m'])
    if len(v['cg_m']) != 3 or not all(math.isfinite(float(x)) for x in v['cg_m']):
        raise ValueError('Vehicle CG must contain three finite coordinates')
    v['material_resolution'] = dict(profile=material, mass_basis=mass_basis, components=components)
    for w in v['wheels']:
        ws = merge_settings(s, w.get('material_settings'))
        p = resolve_material(ws)
        w.setdefault('surface_modulus_Pa', p['effective_young_modulus_Pa'])
        w.setdefault('poisson', p['poisson'])
        if 'axle' in w:
            a = w['axle']
            p = resolve_material(ws, a.get('material_settings'))
            a.setdefault('effective_modulus_Pa', p['effective_bending_modulus_Pa'])
            a.setdefault('allowable_stress_Pa', p['screening_allowable_stress_Pa'])
            a.setdefault('stress_concentration_factor', p['stress_concentration_factor'])
            a['material_resolution'] = p
    return v
