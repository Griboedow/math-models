"""Independent regressions for the October 2026 mechanics audit."""
import math
import unittest
from dataclasses import replace
from yarnstand.model import Ball,Stand,Motion,Setup,G,geometry,simulate,validate,drawn_length,path_clearance
from yarnstand.paths import catenary,ball_path_status
from yarnstand import presets


class AuditRegressions(unittest.TestCase):
    def test_inclined_catenary_uses_mass_per_arc_length(self):
        q,h=(0.,0.,.1),(.35,0.,-.05)
        tension,density=.01,.00025
        curve,status=catenary(q,h,tension,density)
        self.assertEqual(status,'catenary')
        self.assertEqual(curve.point(0),q)
        self.assertEqual(curve.point(1),h)
        # Independent differential equilibrium H*z'' = lambda*g*sqrt(1+z'^2).
        dx=1e-4;f=.4
        lo,mid,hi=(curve.point(f+d/curve.horizontal)[2] for d in (-dx,0,dx))
        slope=(hi-lo)/(2*dx);second=(hi-2*mid+lo)/dx**2
        H=tension*curve.horizontal/curve.span
        self.assertAlmostEqual(H*second/(density*G*math.sqrt(1+slope*slope)),1,places=5)
        old_sag=density*G*curve.horizontal**2/(8*H)
        self.assertGreater(curve.sag_m,old_sag*1.07)

    def test_massless_yarn_has_no_sag(self):
        curve,_=catenary((0,0,.1),(.4,0,.2),.04,0)
        self.assertAlmostEqual(curve.point(.5)[2],.15)
        self.assertEqual(curve.sag_m,0)
        almost,_=catenary((0,0,.1),(.4,0,.2),.04,1e-323)
        self.assertAlmostEqual(almost.point(.5)[2],.15)

    def test_inward_path_is_rejected_even_when_exit_is_on_surface(self):
        s=presets.stand('pitaya_v09');b=replace(Ball(),exit_height_fraction=-.65)
        result=path_clearance(s,b,Setup(),.04)
        self.assertEqual(result['status'],'path_intersects_ball')
        self.assertIsNone(result['min_clearance_m'])

    def test_legacy_inner_winding_ratio_is_preserved_but_not_claimed_valid(self):
        b=replace(Ball(),unwind_radius_ratio=.85)
        r=simulate(b=b,m=replace(Motion(),duration_s=2))
        self.assertEqual(r['inputs']['ball']['unwind_radius_ratio'],.85)
        self.assertEqual(r['summary']['path_screen']['status'],'exit_inside_ball')
        self.assertFalse(r['summary']['hypotheses_valid_for_entire_run'])

    def test_ball_collision_cannot_hide_between_nodes(self):
        s,b=Stand(),Ball();z=s.platform_height_m+b.radius_z_m
        self.assertEqual(ball_path_status(s,b,[(-.1,0,z),(.1,0,z)]),'path_intersects_ball')

    def test_non_round_section_starts_on_actual_ellipsoid(self):
        s=Stand();b=replace(Ball(),radius_x_m=.055,radius_y_m=.03,exit_height_fraction=.3)
        for azimuth in (0,45,90,135):
            q,*_=geometry(s,b,replace(Setup(),azimuth_deg=azimuth))
            self.assertAlmostEqual((q[0]/b.radius_x_m)**2+(q[1]/b.radius_y_m)**2+b.exit_height_fraction**2,1)

    def test_contact_invalidates_overall_result_without_inventing_event_time(self):
        r=simulate(presets.stand('pitaya_v09'),replace(Ball(),exit_height_fraction=-.9),
                   replace(Motion(),duration_s=2),presets.setup('high_table'))
        s=r['summary']
        self.assertEqual(s['path_screen']['status'],'possible_contact')
        self.assertTrue(s['mechanical_hypotheses_valid_for_entire_run'])
        self.assertFalse(s['hypotheses_valid_for_entire_run'])
        self.assertFalse(s['nominal_path_valid'])
        self.assertIsNone(s['peak_tension_with_valid_path_and_coupling_N'])
        self.assertEqual(s['first_events_s'],{})
        self.assertTrue(all(not x['model_assumptions_valid'] for x in r['trace']))

    def test_underresolved_pulses_are_rejected_instead_of_disappearing(self):
        m=replace(Motion(),duty=.0001,duration_s=2,lateral_amplitude_m=0)
        with self.assertRaisesRegex(ValueError,'draw pulse'):simulate(m=m)
        # The integral remains exact even across several narrow pulses.
        self.assertAlmostEqual(drawn_length(2,m)-drawn_length(0,m),.048,places=14)
        self.assertAlmostEqual(drawn_length(1.0001,m)-drawn_length(.9999,m),.024,places=12)
        validate(Stand(),Ball(),replace(m,dt_s=.000005),Setup())

    def test_underresolved_hand_motion_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'hand motion'):
            simulate(m=replace(Motion(),lateral_cycle_s=.001,duration_s=2))

    def test_damping_has_its_own_step_limit(self):
        with self.assertRaisesRegex(ValueError,'damping/inertia'):
            simulate(s=replace(Stand(),viscous_Nm_s=1),m=replace(Motion(),duration_s=2))
        with self.assertRaisesRegex(ValueError,'damping/inertia'):
            simulate(b=replace(Ball(),yarn_damping_Ns_m=100),m=replace(Motion(),duration_s=2))


if __name__=='__main__':unittest.main()
