import json,math,tempfile,unittest
from pathlib import Path
from yarnstand.manufacturing import read_gcode,calibrate
from yarnstand.presets import config

HEADER='; filament_density: 1\n; filament_diameter: 2\nG90\nM83\nG1 X0 Y0 Z0.2\n; Z_HEIGHT: 0.2\n; LAYER_HEIGHT: 0.2\n; FEATURE: Outer wall\n'


class ManufacturingTests(unittest.TestCase):
    def read(self,body,**kw):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'test.gcode';p.write_text(HEADER+body)
            return read_gcode(p,axis_xy_mm=kw.pop('axis_xy_mm',[0,0]),**kw)

    def test_analytic_line_mass_centroid_inertia_and_support_exclusion(self):
        r=self.read('G1 X10 E1\n; FEATURE: Support\nG1 X20 E50\n; FEATURE: Prime tower\nG1 X30 E50\n')
        m=math.pi/1e6
        self.assertAlmostEqual(r['model_mass_kg'],m)
        for actual,expected in zip(r['centroid_print_mm'],[5.,0.,.1]):self.assertAlmostEqual(actual,expected)
        self.assertAlmostEqual(r['axis_inertia_kg_m2'],m*100/3*1e-6,places=16)
        self.assertEqual(r['nozzle_path_bounds_mm'][1],[10.,0.,.2])

    def test_retraction_repayment_is_not_added_mass_and_trims_moving_segment(self):
        r=self.read('G1 E-1\nG1 E0.5\nG1 X10 E1.5\n')
        self.assertAlmostEqual(r['model_mass_kg'],math.pi/1e6)
        self.assertAlmostEqual(r['centroid_print_mm'][0],20/3)

    def test_absolute_extrusion_reset_and_relative_xyz(self):
        r=self.read('M82\nG92 E10\nG1 X10 E11\nG92 E0\nG91\nG1 X10 E1\n')
        self.assertAlmostEqual(r['model_mass_kg'],2*math.pi/1e6)
        self.assertAlmostEqual(r['centroid_print_mm'][0],10)

    def test_filter_objects_and_use_declared_axis(self):
        code='; start printing object, unique label id: 8\nG1 X10 E1\n; stop printing object\n; start printing object, unique label id: 9\nG1 X20 E10\n'
        r=self.read(code,object_ids=['8'],axis_xy_mm=[5,0])
        self.assertAlmostEqual(r['axis_inertia_kg_m2'],math.pi/1e6*100/12*1e-6,places=16)
        self.assertAlmostEqual(r['model_mass_kg'],math.pi/1e6)

    def test_each_tool_uses_its_own_density(self):
        r=self.read('; filament_density: 1,2\n; filament_diameter: 2,2\nG1 X10 E1\nT1\nG1 X20 E1\n')
        self.assertAlmostEqual(r['model_mass_kg'],3*math.pi/1e6)
        self.assertAlmostEqual(r['tools']['1']['mass_kg'],2*r['tools']['0']['mass_kg'])

    def test_arcs_and_nonplanar_extrusion_fail_instead_of_silent_approximation(self):
        for code in ['G2 X10 I5 E1\n','G1 X10 Z0.3 E1\n']:
            with self.assertRaises(ValueError):self.read(code)

    def test_measurements_do_not_invent_inertia_or_friction(self):
        base=config('lemon_v05');old=json.dumps(base)
        r=calibrate(base,{'stand_mass_g':{'value':225,'uncertainty':.5,'source':'Kitchen scale'},'platform_diameter_mm':{'value':95.8,'source':'Calipers'}})
        self.assertEqual(r['config']['stand']['mass_kg'],.225)
        self.assertAlmostEqual(r['config']['stand']['platform_radius_m'],.0479)
        self.assertEqual(r['config']['stand']['rotor_inertia_kg_m2'],base['stand']['rotor_inertia_kg_m2'])
        self.assertEqual(r['config']['stand']['start_torque_Nm'],base['stand']['start_torque_Nm'])
        self.assertEqual(json.dumps(base),old)

    def test_invalid_or_unsourced_measurements_rejected(self):
        for obs in [{'stand_mass_g':{'value':-3,'source':'x'}},{'stand_mass_g':{'value':float('nan'),'source':'x'}},{'stand_mass_g':{'value':3}},{'stand_mass_g':{'value':3,'uncertainty':4,'source':'x'}},{'bearing_preload':{'value':3,'source':'x'}}]:
            with self.assertRaises(ValueError):calibrate(config(),obs)


if __name__=='__main__':unittest.main()
