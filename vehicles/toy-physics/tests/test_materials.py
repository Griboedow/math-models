import copy
import json
import unittest
from pathlib import Path

from toyphysics.materials import resolve_material, prepare_vehicle
from toyphysics.rolling import axle_estimate
from toyphysics.buoyancy import Body


def source_vehicle():
    return dict(mass_components=[dict(name='body', polymer_volume_m3=.0001, position_m=[0, 0, 0])],
                wheels=[dict(axle=dict(diameter_m=.008, span_or_overhang_m=.02, support='cantilever'))])


def floating_box():
    return dict(name='material test', water_density_kg_m3=1000.,
                components=[dict(name='box', size_m=[.2, .1, .1], wall_m=.002, infill=.1)])


class Materials(unittest.TestCase):
    def test_default_and_units(self):
        p = resolve_material()
        self.assertEqual(p['material'], 'PLA')
        self.assertEqual(p['density_kg_m3'], 1240.)
        self.assertEqual(resolve_material({'material': 'petg'})['density_kg_m3'], 1280.)
        self.assertEqual(p['reference_tensile_strength_Pa'], 35e6)

    def test_density_is_not_strength(self):
        a = resolve_material()
        b = resolve_material({'density_g_cm3': 1.5})
        self.assertEqual(b['density_kg_m3'], 1500.)
        self.assertEqual(a['screening_allowable_stress_Pa'], b['screening_allowable_stress_Pa'])
        self.assertEqual(a['effective_bending_modulus_Pa'], b['effective_bending_modulus_Pa'])

    def test_orientation_is_not_density(self):
        a = resolve_material({'material': 'PETG'})
        b = resolve_material({'material': 'PETG', 'print_axis': 'Z'})
        self.assertEqual(a['density_kg_m3'], b['density_kg_m3'])
        self.assertLess(b['screening_allowable_stress_Pa'], a['screening_allowable_stress_Pa'])
        self.assertLess(b['effective_bending_modulus_Pa'], a['effective_bending_modulus_Pa'])

    def test_invalid_settings(self):
        for value in [{'material': 'ABS'}, {'density_g_cm3': 0}, {'density_g_cm3': float('nan')},
                      {'print_axis': 'Q'}, {'strength_factor': 1.1}, {'modulus_factor': 0},
                      {'safety_factor': .5}, {'stress_concentration_factor': .9}, {'poisson': .5}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_material(value)

    def test_new_local_material_resets_property_overrides(self):
        p = resolve_material({'material': 'PETG', 'density_g_cm3': 1.6, 'safety_factor': 3}, {'material': 'PLA'})
        self.assertEqual(p['density_g_cm3'], 1.24)
        self.assertEqual(p['safety_factor'], 3)

    def test_volume_mass_ratio_and_no_mutation(self):
        v = source_vehicle(); original = copy.deepcopy(v)
        a = prepare_vehicle(v); b = prepare_vehicle(v, {'material': 'PETG'})
        self.assertAlmostEqual(a['mass_kg'], .124)
        self.assertAlmostEqual(b['mass_kg']/a['mass_kg'], 1280/1240)
        self.assertEqual(a['cg_m'], b['cg_m'])
        self.assertEqual(v, original)

    def test_mixed_parts_and_fixed_ballast_cg(self):
        v = source_vehicle()
        v['mass_components'] += [dict(name='second', polymer_volume_m3=.0001, position_m=[1, 0, 0],
                                     material_settings={'material': 'PETG'}),
                                 dict(name='ballast', fixed_mass_kg=.1, position_m=[2, 0, 0])]
        a = prepare_vehicle(v)
        self.assertAlmostEqual(a['mass_kg'], .352)
        self.assertAlmostEqual(a['cg_m'][0], (.128+.2)/.352)

    def test_fixed_and_measured_mass_precedence(self):
        v = dict(mass_kg=.6, cg_m=[0, 0, .1], wheels=[])
        self.assertEqual(prepare_vehicle(v, {'material': 'PETG'})['mass_kg'], .6)
        v = source_vehicle(); v.update(mass_override_kg=.2, cg_override_m=[.1, 0, 0])
        a = prepare_vehicle(v, {'material': 'PETG'})
        self.assertEqual(a['mass_kg'], .2)
        self.assertEqual(a['cg_m'], [.1, 0, 0])

    def test_explicit_axle_and_contact_properties_preserved(self):
        v = source_vehicle(); w = v['wheels'][0]
        w.update(surface_modulus_Pa=1e9, poisson=.3)
        w['axle'].update(effective_modulus_Pa=1.1e9, allowable_stress_Pa=5e6, stress_concentration_factor=2)
        a = prepare_vehicle(v, {'material': 'PETG'})['wheels'][0]
        self.assertEqual(a['surface_modulus_Pa'], 1e9)
        self.assertEqual(a['axle']['effective_modulus_Pa'], 1.1e9)
        self.assertEqual(a['axle']['allowable_stress_Pa'], 5e6)
        self.assertEqual(a['axle']['stress_concentration_factor'], 2)

    def test_reconstruct_slicer_reference_mass(self):
        v = json.loads((Path(__file__).parents[1]/'examples/vehicle.json').read_text())
        for c in v['mass_components']:
            c['material_settings'] = {'density_g_cm3': c['reference_slicer_density_kg_m3']/1000}
        a = prepare_vehicle(v)
        self.assertAlmostEqual(a['mass_kg'], v['provenance']['reference_assembled_mass_kg'], places=12)
        for actual, expected in zip(a['cg_m'], v['provenance']['reference_cg_m']):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_axle_allowable_utilization_and_factors(self):
        v = source_vehicle()
        a = axle_estimate(prepare_vehicle(v)['wheels'][0], 10)
        self.assertAlmostEqual(a['allowable_stress_Pa'], 35e6*.5/2)
        self.assertAlmostEqual(a['utilization'], 1.5*a['bending_stress_Pa']/a['allowable_stress_Pa'])
        self.assertIsNone(a['strength_pass_fail'])
        b = axle_estimate(prepare_vehicle(v, {'safety_factor': 4})['wheels'][0], 10)
        c = axle_estimate(prepare_vehicle(v, {'stress_concentration_factor': 3})['wheels'][0], 10)
        self.assertAlmostEqual(b['utilization'], 2*a['utilization'])
        self.assertAlmostEqual(c['utilization'], 2*a['utilization'])
        high = axle_estimate(prepare_vehicle(v)['wheels'][0], 1000)
        self.assertEqual(high['screen_status'], 'exceeds_assumed_allowable')
        zero = axle_estimate(prepare_vehicle(v)['wheels'][0], 0)
        self.assertEqual(zero['utilization'], 0)
        self.assertIsNone(zero['reserve_factor'])
        json.dumps(zero, allow_nan=False)

    def test_smaller_axle_increases_stress_and_deflection(self):
        w = prepare_vehicle(source_vehicle())['wheels'][0]
        a = axle_estimate(w, 10)
        w['axle']['diameter_m'] /= 2
        b = axle_estimate(w, 10)
        self.assertAlmostEqual(b['local_stress_Pa']/a['local_stress_Pa'], 8)
        self.assertAlmostEqual(b['deflection_m']/a['deflection_m'], 16)

    def test_hydro_density_changes_mass_and_draft_not_envelope(self):
        a = Body(floating_box()).solve()
        b = Body(floating_box(), material_settings={'material': 'PETG'}).solve()
        self.assertAlmostEqual(b['mass_kg']/a['mass_kg'], 1280/1240)
        self.assertEqual(a['maximum_supported_mass_kg'], b['maximum_supported_mass_kg'])
        self.assertAlmostEqual((.05-b['equilibrium']['heave_m'])/(.05-a['equilibrium']['heave_m']), 1280/1240)
        self.assertLess(b['reserve_buoyancy_kg'], a['reserve_buoyancy_kg'])

    def test_material_can_cross_buoyancy_threshold(self):
        s = dict(name='threshold', water_density_kg_m3=1000., components=[
            dict(name='box', size_m=[.2, .1, .1], infill=0., shell_volume_fraction=.8)])
        self.assertEqual(Body(s).solve()['status'], 'local_equilibrium')
        self.assertEqual(Body(s, material_settings={'material': 'PETG'}).solve()['status'], 'sinks_or_fully_submerged_neutral')

    def test_hydro_explicit_density_and_measured_mass(self):
        s = floating_box(); s['components'][0]['polymer_density_kg_m3'] = 1100.
        a = Body(s); b = Body(s, material_settings={'material': 'PETG'})
        self.assertEqual(a.mass, b.mass)
        self.assertEqual(b.components[0]['polymer_density_kg_m3'], 1100.)
        s['mass_override_kg'] = .5
        self.assertEqual(Body(s, material_settings={'density_g_cm3': 1.8}).mass, .5)


if __name__ == '__main__':
    unittest.main()
