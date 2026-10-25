import copy, unittest
import numpy as np
import trimesh
from toyphysics.rolling import solve, contact, compliance, step_force, G
from toyphysics.buoyancy import Body, submerged, integrate, rotation
from toyphysics.contact_events import event
from toyphysics.cleaning import washability

HARD=dict(name='test',kind='hard',modulus_Pa=1e9,poisson=.3,rolling_arm_m=.0001,traction_coefficient=.3)
CARPET=dict(name='test carpet',kind='carpet',pile_height_m=.003,foundation_Pa_m=1e7,backing_stiffness_N_m=1e5,hysteresis_fraction=.3,rolling_arm_m=.0002)
def wheel(x,y):
    return dict(name=f'{x}:{y}',position_m=[x,y,.025],radius_m=.025,width_m=.02,vertical_stiffness_N_m=20000,
                surface_modulus_Pa=1e9,poisson=.3,tread_contact_fraction=1.)
def vehicle():
    return dict(mass_kg=1.,cg_m=[0,0,.05],wheels=[wheel(x,y) for x in [-.1,.1] for y in [-.1,.1]])
def box():
    return dict(name='analytic box',water_density_kg_m3=1000.,mass_override_kg=.5,cg_override_m=[0,0,0],
                components=[dict(name='box',size_m=[.2,.1,.1],wall_m=.002,infill=.1,polymer_density_kg_m3=1250.)])

class Mechanics(unittest.TestCase):
    def test_four_equal(self):
        r=solve(vehicle(),HARD)
        np.testing.assert_allclose([w['normal_force_N'] for w in r['wheels']],G/4,atol=1e-6)
        self.assertLess(r['equilibrium_residual_N'],1e-7)
    def test_three_wheels(self):
        v=vehicle();v['wheels']=[wheel(-.1,-.1),wheel(-.1,.1),wheel(.1,0)]
        n=[w['normal_force_N'] for w in solve(v,HARD)['wheels']]
        np.testing.assert_allclose(n,[G/4,G/4,G/2],atol=1e-7)
    def test_six_compliant(self):
        v=vehicle();v['wheels']=[wheel(x,y) for x in [-.1,0,.1] for y in [-.1,.1]]
        r=solve(v,HARD)
        np.testing.assert_allclose([w['normal_force_N'] for w in r['wheels']],G/6,atol=1e-4)
        v['wheels'][0]['ground_height_m']=-.01
        r=solve(v,HARD);self.assertTrue(r['wheels'][0]['unloaded'])
        self.assertLess(r['equilibrium_residual_N'],1e-7)
    def test_stiffness_resolves_indeterminacy(self):
        v=vehicle();v['wheels'][0]['vertical_stiffness_N_m']*=10
        r=solve(v,HARD);n=[w['normal_force_N'] for w in r['wheels']]
        self.assertGreater(n[0],n[1]);self.assertAlmostEqual(n[0],n[3],places=5)
    def test_tip_and_rank_deficiency(self):
        v=vehicle();self.assertEqual(solve(v,HARD,dict(force_N=100,position_m=[1,0,.1]))['status'],'tipping')
        v['wheels']=[wheel(0,0)];self.assertEqual(solve(v,HARD)['status'],'marginal_support')
        v['cg_m'][0]=.01;self.assertEqual(solve(v,HARD)['status'],'tipping')
    def test_horizontal_moment(self):
        r=solve(vehicle(),HARD,dict(horizontal_force_N=[5,0],horizontal_height_m=.1))
        self.assertAlmostEqual(r['required_cop_m'][0],.5/G,places=8)
    def test_child_mass_force(self):
        r=solve(vehicle(),HARD,dict(child_mass_kg=10,weight_fraction=.3,contact_area_m2=.001))
        self.assertAlmostEqual(r['total_vertical_force_N'],4*G)
        self.assertAlmostEqual(r['applied_load_mean_pressure_Pa'],3*G/.001)
    def test_hertz_scaling(self):
        w=wheel(0,0);a=contact(w,HARD,1);b=contact(w,HARD,4)
        self.assertAlmostEqual(b['peak_pressure_Pa']/a['peak_pressure_Pa'],2.)
        w['radius_m']*=4;c=contact(w,HARD,1);self.assertAlmostEqual(c['peak_pressure_Pa']/a['peak_pressure_Pa'],.5)
    def test_complementary_energy_derivative(self):
        for floor in [HARD,CARPET]:
            for n in [1.,1000.]:
                eps=1e-3
                deriv=(compliance(wheel(0,0),floor,n+eps)[1]-compliance(wheel(0,0),floor,n-eps)[1])/(2*eps)
                self.assertAlmostEqual(deriv,compliance(wheel(0,0),floor,n)[0],places=7)
    def test_carpet_bottoming(self):
        self.assertTrue(contact(wheel(0,0),CARPET,1000)['pile_bottomed'])
    def test_step(self):
        self.assertEqual(step_force(10,.02,0)['force_N'],0.)
        self.assertAlmostEqual(step_force(10,.02,.01)['force_N'],10*np.sqrt(3))
        self.assertIsNone(step_force(10,.02,.02)['force_N'])
    def test_invalid(self):
        v=vehicle();v['wheels'][0]['radius_m']=-1
        with self.assertRaises(ValueError):solve(v,HARD)
        with self.assertRaises(ValueError):solve(vehicle(),HARD,dict(force_N=1,child_mass_kg=10,weight_fraction=.5))

class Hydrostatics(unittest.TestCase):
    def test_half_box_volume_and_centroid(self):
        t=trimesh.creation.box(extents=[.2,.1,.1]).triangles
        v,m=submerged(t);self.assertAlmostEqual(v,.001,places=12)
        np.testing.assert_allclose(m/v,[0,0,-.025],atol=1e-10)
    def test_rotated_half_body(self):
        t=trimesh.creation.box(extents=[.2,.1,.1]).triangles@rotation(.3,.2).T
        self.assertAlmostEqual(submerged(t)[0],.001,places=12)
    def test_through_hole_is_preserved(self):
        m=trimesh.creation.annulus(r_min=.02,r_max=.05,height=.04,sections=96)
        v,moment=submerged(m.triangles)
        self.assertAlmostEqual(v,m.volume/2,places=12)
        np.testing.assert_allclose(moment/v,[0,0,-.01],atol=1e-10)
    def test_analytic_draft_and_gm(self):
        r=Body(box()).solve();eq=r['equilibrium'];draft=.5/1000/(.2*.1)
        self.assertAlmostEqual(eq['heave_m'],.05-draft,places=9)
        gm_roll=.1**2/(12*draft)+draft/2-.05
        gm_pitch=.2**2/(12*draft)+draft/2-.05
        np.testing.assert_allclose(np.array(r['restoring_stiffness_Nm_rad']).diagonal()/(.5*G),[gm_roll,gm_pitch],rtol=1e-5)
        self.assertFalse(r['locally_stable'])
    def test_level_stable_low_cg(self):
        s=box();s['cg_override_m']=[0,0,-.03]
        r=Body(s).solve();self.assertTrue(r['holds_level']);self.assertTrue(r['locally_stable'])
    def test_shifted_cg_tilts(self):
        s=box();s['cg_override_m']=[.005,.003,-.03]
        r=Body(s).solve();self.assertFalse(r['holds_level']);self.assertTrue(r['locally_stable'])
        self.assertLess(r['torque_residual_Nm'],1e-7)
    def test_flooding_and_infill(self):
        s=box();s.pop('mass_override_kg');s.pop('cg_override_m')
        a=Body(s);s['components'][0]['infill']=.4;b=Body(s)
        self.assertGreater(b.mass,a.mass);self.assertAlmostEqual(b.max_volume,a.max_volume)
        s['components'][0]['flooded_void_fraction']=1
        self.assertEqual(Body(s).solve()['status'],'sinks_or_fully_submerged_neutral')
    def test_shell_mass(self):
        s=box();s.pop('mass_override_kg');c=s['components'][0]
        expected=1250*(.2*.1*.1-(1-.1)*.196*.096*.096)
        self.assertAlmostEqual(Body(s).mass,expected,places=10)

class Proxies(unittest.TestCase):
    def test_free_toy_has_less_contact_energy(self):
        e=dict(name='kick',kind='kick',effective_impact_mass_kg=1.,speed_m_s=2.,stopping_distance_m=.01,contact_area_m2=.001)
        free=event(e,.25);e['toy_trapped']=True;trapped=event(e,.25)
        self.assertLess(free['available_relative_energy_J'],trapped['available_relative_energy_J'])
        self.assertIsNone(free['pain_score'])
    def test_step_area_scaling(self):
        e=dict(name='step',kind='step',adult_mass_kg=70,weight_fraction=1.,effective_impact_mass_kg=5,stopping_distance_m=.01,contact_area_m2=.001)
        a=event(e,.25);e['contact_area_m2']/=2;b=event(e,.25)
        self.assertAlmostEqual(b['mean_contact_pressure_Pa'],2*a['mean_contact_pressure_Pa'])
    def test_cleaning_access_and_drainage(self):
        s=dict(brush_diameter_m=.003,brush_reach_m=.015,dirt_grain_diameter_m=.0005,layer_height_m=.0002,roughness_reference_m=.0004,
               retention_reference_m3=1e-6,operations_reference=12,disassembly_operations=1,
               features=[dict(name='slot',area_m2=.01,opening_m=.0003,depth_m=.01,pocket_volume_m3=1e-6,drainable_fraction=0.,opens_on_disassembly=True)])
        a=washability(s);b=washability(s,True)
        self.assertGreater(b['washability_index_0_100'],a['washability_index_0_100'])
        self.assertLess(b['modeled_retained_liquid_m3'],a['modeled_retained_liquid_m3'])

if __name__=='__main__':unittest.main()
