import unittest
try:
    import numpy as np
    import trimesh
    import vtk
    import scipy
    AVAILABLE=True
except ImportError:
    AVAILABLE=False
if AVAILABLE:
    # A broken import inside our module must fail tests, not silently skip them.
    from yarnstand.mesh import MeshScene,taut_path


@unittest.skipUnless(AVAILABLE,'Install the mesh extra')
class MeshTests(unittest.TestCase):
    def setUp(self):
        self.scene=MeshScene([('cube',trimesh.creation.box(extents=[.02,.02,.02]))])

    def test_signed_distance_and_outward_normal(self):
        d,n,_=self.scene.distance([[.015,0,0],[0,0,0]],True)
        self.assertAlmostEqual(d[0],.005,places=8)
        self.assertAlmostEqual(d[1],-.01,places=8)
        np.testing.assert_allclose(n[0],[1,0,0],atol=1e-8)

    def test_finite_radius_catches_miss_of_zero_thickness_ray(self):
        points=[[-.02,0,.0105],[.02,0,.0105]]
        self.assertEqual(self.scene.intersections(points),[])
        self.assertEqual(self.scene.screen(points,.001)['status'],'contact')

    def test_thin_wall_crossing_between_samples(self):
        wall=trimesh.creation.box(extents=[.00001,.02,.02])
        scene=MeshScene([('wall',wall)])
        r=scene.screen([[-.01,0,0],[.01,0,0]],.00001,max_step_m=.03)
        self.assertEqual(r['centerline_crossings'],['wall'])
        self.assertEqual(r['status'],'contact')

    def test_curved_surface_crossings_in_metre_units(self):
        sphere=trimesh.creation.icosphere(subdivisions=3,radius=.05)
        scene=MeshScene([('sphere',sphere)])
        x=np.arange(-.06,.061,.004)
        points=np.column_stack((x,np.zeros(len(x)),np.full(len(x),.04)))
        # Both endpoints are outside, while this chord enters the sphere.
        # vtkOBBTree's default 0.01 tolerance incorrectly returned no crossings.
        self.assertEqual(scene.intersections(points),['sphere'])

    def test_clearance_lower_bound_is_conservative(self):
        r=self.scene.screen([[-.02,0,.015],[.02,0,.015]],.001,max_step_m=.0005)
        self.assertEqual(r['status'],'clear')
        self.assertLessEqual(r['clearance_lower_bound_m'],.004)
        self.assertGreater(r['clearance_lower_bound_m'],.0037)

    def test_open_mesh_rejected(self):
        m=trimesh.creation.box();m.update_faces(np.arange(len(m.faces)-1))
        with self.assertRaises(ValueError):MeshScene([('open',m)])

    def test_movement_cannot_tunnel_between_clear_end_poses(self):
        a=[[-.02,-.002,0],[-.02,.002,0]]
        b=[[.02,-.002,0],[.02,.002,0]]
        self.assertEqual(self.scene.screen(a,.001)['status'],'clear')
        self.assertEqual(self.scene.screen(b,.001)['status'],'clear')
        r=self.scene.sweep([a,b],.001)
        self.assertEqual(r['status'],'contact_on_prescribed_sweep')

    def test_sweep_clearance_bound(self):
        a=[[-.02,0,.02],[.02,0,.02]]
        b=[[-.02,.005,.02],[.02,.005,.02]]
        r=self.scene.sweep([a,b],.001)
        self.assertEqual(r['status'],'clear_prescribed_sweep')
        self.assertLessEqual(r['clearance_lower_bound_m'],.009)

    def test_initial_interpenetration_not_a_release_success(self):
        a=[[-.002,0,0],[.002,0,0]]
        b=[[-.002,0,.02],[.002,0,.02]]
        self.assertEqual(self.scene.sweep([a,b],.001)['status'],'initial_contact')

    def test_pruning_agrees_with_full_signed_distance(self):
        points=np.column_stack((np.linspace(-.03,.03,101),np.full(101,.012),np.full(101,.005)))
        r=self.scene.screen(points,.001,max_step_m=.0006)
        exact=self.scene.distance(points)[0].min()-.001
        self.assertAlmostEqual(r['min_sampled_clearance_m'],exact,places=9)

    def test_low_tension_does_not_claim_valid_path(self):
        from yarnstand.model import Stand,Ball,Setup
        points,status=taut_path(Stand(),Ball(),Setup(),0)
        self.assertIsNone(points)
        self.assertEqual(status,'slack_or_too_low_tension')

    def test_nonfinite_geometry_rejected_before_vtk(self):
        m=trimesh.creation.box();m.vertices[0,0]=float('nan')
        with self.assertRaises(ValueError):MeshScene([('corrupt',m)])
        with self.assertRaises(ValueError):self.scene.distance([[float('nan'),0,0]])

    def test_tiny_sampling_step_fails_without_allocating_billions_of_points(self):
        from yarnstand.model import Stand,Ball,Setup
        with self.assertRaises(ValueError):self.scene.screen([[0,0,.02],[.1,0,.02]],.001,max_step_m=1e-15)
        with self.assertRaises(ValueError):taut_path(Stand(),Ball(),Setup(),.04,step_m=1e-15)
        with self.assertRaises(ValueError):self.scene.sweep([[[0,0,.02],[.1,0,.02]],[[0,0,.03],[.1,0,.03]]],.001,motion_step_m=1e-15)

    def test_near_zero_positive_clearance_is_not_reported_as_clear(self):
        r=self.scene.screen([[-.02,0,.01101],[.02,0,.01101]],.001,max_step_m=.002)
        self.assertGreater(r['min_sampled_clearance_m'],0)
        self.assertEqual(r['status'],'unresolved_sampling_margin')

    def test_inverted_disconnected_shell_cannot_hide_in_positive_total_volume(self):
        big=trimesh.creation.box(extents=[.1,.1,.1]);big.apply_translation([.3,0,0])
        small=trimesh.creation.box(extents=[.02,.02,.02]);small.invert()
        mesh=trimesh.util.concatenate([big,small])
        self.assertTrue(mesh.is_watertight)
        self.assertTrue(mesh.is_winding_consistent)
        self.assertGreater(mesh.volume,0)
        with self.assertRaisesRegex(ValueError,'each disconnected shell'):MeshScene([('compound',mesh)])

    def test_disconnected_positive_shells_are_checked_as_union(self):
        a=trimesh.creation.box(extents=[.02,.02,.02])
        b=a.copy();b.apply_translation([.018,0,0])
        scene=MeshScene([('compound',trimesh.util.concatenate([a,b]))])
        # Inside a, but the nearest face in the combined surface belongs to b.
        r=scene.screen([[.007,0,0],[.007,.001,0]],.0001)
        self.assertEqual(r['status'],'contact')

    def test_nested_cavity_shells_fail_explicitly_instead_of_filling_the_hole(self):
        outer=trimesh.creation.box(extents=[.04,.04,.04])
        inner=trimesh.creation.box(extents=[.02,.02,.02]);inner.invert()
        with self.assertRaisesRegex(ValueError,'cavity shells are unsupported'):
            MeshScene([('cavity',trimesh.util.concatenate([outer,inner]))])

    def test_mesh_and_core_share_the_ball_path_rejection(self):
        from dataclasses import replace
        from yarnstand.model import Stand,Ball,Setup,path_clearance
        b=replace(Ball(),exit_height_fraction=-.65)
        points,status=taut_path(Stand(),b,Setup(),.04)
        self.assertIsNone(points)
        self.assertEqual(status,path_clearance(Stand(),b,Setup(),.04)['status'])

    def test_inclined_weight_correction_changes_clear_to_contact(self):
        from yarnstand.paths import catenary
        from yarnstand.model import G
        start,end=(0,0,.1),(.35,0,-.05)
        curve,_=catenary(start,end,.01,.00025)
        radius=.0001
        old_z=(start[2]+end[2])/2-.00025*G*.35**2/(8*(.01*.35/curve.span))
        new_z=curve.point(.5)[2]
        top=(new_z+old_z)/2-radius
        box=trimesh.creation.box(extents=[.0001,.01,.01]);box.apply_translation([.175,0,top-.005])
        scene=MeshScene([('obstacle',box)])
        f=np.linspace(0,1,1001)
        old=np.asarray(start)+f[:,None]*(np.asarray(end)-start)
        old[:,2]-=.00025*G*.35**2/(2*(.01*.35/curve.span))*f*(1-f)
        actual=[curve.point(float(x)) for x in f]
        self.assertEqual(scene.screen(old,radius)['status'],'clear')
        self.assertEqual(scene.screen(actual,radius)['status'],'contact')
