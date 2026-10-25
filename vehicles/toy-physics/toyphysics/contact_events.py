"""Mechanical comparison proxies, deliberately not a pain or injury score."""
import math
from .rolling import G, positive, fraction


def event(spec, toy_mass_kg):
    area = positive(spec['contact_area_m2'], 'contact area')
    speed = positive(spec.get('speed_m_s', 0), 'speed', True)
    distance = positive(spec['stopping_distance_m'], 'stopping distance')
    factor = positive(spec.get('peak_to_mean_factor', 2), 'peak factor')
    if factor < 1:
        raise ValueError('Peak-to-mean force factor must be at least one')
    static = 0.
    if spec['kind'] == 'step':
        mass = positive(spec['adult_mass_kg'], 'adult mass')
        static = mass*G*fraction(spec['weight_fraction'], 'weight fraction')
        effective = positive(spec['effective_impact_mass_kg'], 'effective impact mass')
    elif spec['kind'] == 'kick':
        mass = positive(spec['effective_impact_mass_kg'], 'effective impact mass')
        toy = positive(toy_mass_kg, 'toy mass')
        effective = mass if spec.get('toy_trapped', False) else mass*toy/(mass+toy)
    else:
        raise ValueError('Event must be kick or step')
    energy = .5*effective*speed*speed
    dynamic = energy/distance
    peak = static+factor*dynamic
    out = dict(name=spec['name'], static_force_N=static, available_relative_energy_J=energy,
               mean_dynamic_force_N=dynamic, estimated_peak_force_N=peak,
               mean_contact_pressure_Pa=peak/area, energy_per_area_J_m2=energy/area,
               contact_area_m2=area, effective_mass_kg=effective,
               pain_score=None, injury_probability=None,
               interpretation='Comparative mechanical stimulus only. Area, stopping distance and impact mass are scenario inputs; breakage and tissue response are not modeled.')
    if 'edge_radius_m' in spec:
        out['edge_radius_m'] = positive(spec['edge_radius_m'], 'edge radius')
    if 'effective_contact_modulus_Pa' in spec:
        # Optional spherical-tip Hertz estimate; external tissue/contact modulus.
        radius = positive(spec['edge_radius_m'], 'edge radius')
        modulus = positive(spec['effective_contact_modulus_Pa'], 'contact modulus')
        a = (3*peak*radius/(4*modulus))**(1/3) if peak else 0.
        out['spherical_tip_Hertz_peak_Pa'] = 3*peak/(2*math.pi*a*a) if a else 0.
        out['small_contact_assumption_valid'] = a/radius < .1
    return out
