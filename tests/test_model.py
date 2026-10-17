import copy, math, unittest
from dataclasses import replace
from yarnstand.model import *
from yarnstand import presets


class MechanicsTests(unittest.TestCase):
    def test_pulse_integral_equals_stitch_length(self):
        m=Motion();n=20000
        length=sum(draw_speed((i+.5)*m.cycle_s/n,m)*m.cycle_s/n for i in range(n))
        self.assertAlmostEqual(length,m.draw_m,places=8)

    def test_horizontal_slide_matches_coulomb(self):
        s=Stand();b=Ball(eccentricity_m=0);p=Setup(hand_height_m=s.platform_height_m+b.radius_z_m)
        r=static_limits(s,b,p)
        self.assertAlmostEqual(r['slide_N'],s.foot_friction*(s.mass_kg+b.mass_kg)*G,places=10)

    def test_square_horizontal_tipping_analytic(self):
        s=Stand(support_points_m=[[-.05,-.05],[.05,-.05],[.05,.05],[-.05,.05]])
        b=Ball(eccentricity_m=0);p=Setup(hand_height_m=s.platform_height_m+b.radius_z_m)
        q,h,u,lever,L=geometry(s,b,p)
        expected=(s.mass_kg+b.mass_kg)*G*.05/(q[2]*max(abs(u[0]),abs(u[1])))
        self.assertAlmostEqual(static_limits(s,b,p)['tip_N'],expected,places=9)

    def test_tangent_force_virtual_work_lever(self):
        s,b,p=Stand(),Ball(),Setup();q,h,u,lever,L=geometry(s,b,p)
        r=math.hypot(q[0],q[1]);cos_elevation=math.hypot(u[0],u[1])
        self.assertAlmostEqual(lever,r*cos_elevation,places=10)
        self.assertAlmostEqual(q[0]*(h[0]-q[0])+q[1]*(h[1]-q[1]),0,places=10)

    def test_small_ball_higher_breakaway(self):
        s,p=Stand(),Setup()
        self.assertGreater(static_limits(s,presets.ball('nearly_empty'),p)['start_tension_N'],static_limits(s,presets.ball(),p)['start_tension_N'])

    def test_exit_section_stays_on_ellipsoid(self):
        b=Ball(radius_x_m=.045,radius_y_m=.045,unwind_radius_ratio=1)
        for fraction in [-.9,-.65,0,.65,.9]:
            q,*_=geometry(Stand(),replace(b,exit_height_fraction=fraction),Setup())
            self.assertAlmostEqual((q[0]**2+q[1]**2)/b.radius_x_m**2+fraction**2,1,places=12)

    def test_low_exit_reduces_horizontal_torque_arm(self):
        s=Stand();b=Ball();low=replace(b,exit_height_fraction=-.8)
        middle=static_limits(s,b,Setup(hand_height_m=s.platform_height_m+b.radius_z_m))
        bottom=static_limits(s,low,Setup(hand_height_m=s.platform_height_m+low.radius_z_m*.2))
        self.assertAlmostEqual(bottom['lever_m']/middle['lever_m'],.6,places=12)

    def test_weight_increases_static_reserve(self):
        s,b,p=Stand(),Ball(),Setup()
        self.assertGreater(static_limits(replace(s,mass_kg=.4),b,p)['critical_snag_N'],static_limits(s,b,p)['critical_snag_N'])

    def test_rotating_whole_setup_preserves_results(self):
        s,b,p=Stand(),Ball(),Setup()
        a=static_limits(s,b,p)
        c=static_limits(replace(s,pad_angle_deg=s.pad_angle_deg+17),b,replace(p,azimuth_deg=p.azimuth_deg+17))
        self.assertAlmostEqual(a['tip_N'],c['tip_N'],places=9)

    def test_time_step_convergence(self):
        s=presets.stand();b=presets.ball();p=presets.setup();m=replace(presets.motion('crochet'),duration_s=4.05)
        a=simulate(s,b,m,p,False)['summary'];c=simulate(s,b,replace(m,dt_s=.00025),p,False)['summary']
        self.assertLess(abs(a['peak_tension_N']-c['peak_tension_N'])/c['peak_tension_N'],.025)
        self.assertLess(abs(a['max_slack_m']-c['max_slack_m']),.001)

    def test_invalid_config_and_unknown_fields(self):
        for cfg in [{'ball':{'mass_kg':-1}},{'stand':{'mass':.3}},{'setp':{}},{'setup':{'hand_height_m':float('nan')}}]:
            with self.assertRaises(ValueError): from_config(cfg)

    def test_input_not_mutated(self):
        cfg=presets.config();before=copy.deepcopy(cfg)
        from_config(cfg)
        self.assertEqual(cfg,before)

    def test_partial_final_step_stays_within_requested_duration(self):
        r=simulate(m=replace(Motion(),duration_s=2.0001))
        self.assertLessEqual(r['trace'][-1]['t_s'],2.0001)

    def test_names_must_be_strings_for_the_ui(self):
        for group in ['stand','ball','motion','setup']:
            with self.assertRaises(ValueError):from_config({group:{'name':None}})

    def test_both_fruit_presets_survive_integration(self):
        peach=presets.config('peach_v13');pitaya=presets.config('pitaya_v09')
        from_config(peach);from_config(pitaya)
        self.assertGreater(peach['stand']['platform_height_m'],pitaya['stand']['platform_height_m'])
        self.assertEqual(len(pitaya['stand']['leaves']),6)

    def test_no_compression_or_negative_rotation(self):
        r=simulate(m=replace(Motion(),duration_s=2.0))
        self.assertTrue(all(t['tension_N']>=0 and t['rpm']>=0 for t in r['trace']))

    def test_lost_coupling_is_reported(self):
        r=simulate(s=Stand(start_torque_Nm=.003,running_torque_Nm=.0015),b=presets.ball('nearly_empty'),m=replace(Motion(),duration_s=2.))
        self.assertIn('ball_slipping',r['summary']['first_events_s'])
        self.assertFalse(r['summary']['hypotheses_valid_for_entire_run'])
        s=r['summary']
        self.assertEqual(s['valid_coupled_interval_end_s'],min(s['first_events_s'].values()))
        self.assertLess(s['peak_tension_before_first_event_N'],s['peak_tension_N'])
        self.assertFalse(r['trace'][-1]['coupled_assumptions_valid'])

    def test_low_exit_downward_ray_contacts_rim(self):
        c=path_clearance(presets.stand(),replace(presets.ball('nearly_empty'),exit_height_fraction=-.65),presets.setup('high_table'),.04)
        self.assertEqual(c['status'],'possible_contact')

    def test_zero_tension_path_not_claimed_clear(self):
        self.assertEqual(path_clearance(Stand(),Ball(),Setup(),0)['status'],'slack_or_too_low_tension')


if __name__=='__main__': unittest.main()
