"""Transparent, calibratable washability heuristic based on explicit features."""
import math
from .rolling import positive, fraction


def washability(spec, disassembled=False):
    brush = positive(spec['brush_diameter_m'], 'brush diameter')
    reach = positive(spec['brush_reach_m'], 'brush reach')
    grain = positive(spec['dirt_grain_diameter_m'], 'grain diameter')
    rows = []
    total_area = accessible_area = trapped = 0.
    for f in spec['features']:
        area = positive(f['area_m2'], 'feature area')
        exposed = not f.get('hidden_until_disassembly', False) or disassembled
        opening = positive(f['opening_m'], 'opening', True)
        depth = positive(f['depth_m'], 'depth', True)
        access = float(exposed and opening >= brush and depth <= reach)
        drainage = fraction(f['drainable_fraction'], 'drainability') if exposed else 0.
        pocket = positive(f['pocket_volume_m3'], 'pocket volume', True)
        if disassembled and f.get('opens_on_disassembly', False):
            access, drainage = 1., 1.
        # A small entrance can exclude a dry grain but cannot exclude mud/liquid.
        dry_grain_can_enter = opening >= grain
        aspect = depth/max(opening, 1e-9)
        total_area += area
        accessible_area += access*area
        trapped += pocket*(1-drainage)
        rows.append(dict(name=f['name'], brush_accessible=bool(access),
                         depth_to_opening_ratio=aspect, retained_volume_m3=pocket*(1-drainage),
                         dry_grain_can_enter=dry_grain_can_enter,
                         liquid_mud_can_enter=opening > 0))
    if total_area <= 0:
        raise ValueError('At least one cleaning feature is required')
    accessibility = accessible_area/total_area
    retention_scale = positive(spec['retention_reference_m3'], 'retention reference')
    drainage_score = math.exp(-trapped/retention_scale)
    roughness = positive(spec['layer_height_m'], 'layer height', True)/positive(spec['roughness_reference_m'], 'roughness reference')
    surface_score = 1/(1+roughness)
    operations = positive(spec.get('disassembly_operations', 0), 'operations', True) if disassembled else 0
    assembly_score = 1/(1+operations/positive(spec['operations_reference'], 'operation reference'))
    weights = spec.get('weights', dict(access=.45, drainage=.30, surface=.15, effort=.10))
    components = dict(access=accessibility, drainage=drainage_score, surface=surface_score, effort=assembly_score)
    if set(weights) != set(components):
        raise ValueError('Cleaning weights must name access, drainage, surface and effort')
    wsum = sum(positive(w, 'weight', True) for w in weights.values())
    positive(wsum, 'weight sum')
    score = 100*sum(weights[k]*components[k] for k in weights)/wsum
    return dict(state='disassembled' if disassembled else 'assembled',
                washability_index_0_100=score, brush_accessible_area_fraction=accessibility,
                modeled_retained_liquid_m3=trapped, operations=operations,
                components=components, features=rows,
                interpretation='Unvalidated design-comparison heuristic; feature inventory is manual, not automatic mesh analysis. No hygiene guarantee or cleaning-time prediction.')
