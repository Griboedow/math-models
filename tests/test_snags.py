import json
from pathlib import Path
import tempfile
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
    from yarnstand.mesh import MeshScene
    from yarnstand.snags import audit,write_report,compare


@unittest.skipUnless(AVAILABLE,'Install the mesh extra')
class SnagTests(unittest.TestCase):
    def spec(self,poses,radius=.001,**kwargs):
        return {'sampling_step_m':.0005,'motion_step_m':.0005,
                'cases':[{'id':'route','poses_m':poses,'yarn_radius_m':radius,**kwargs}]}

    def test_hook_blocks_lift_but_outward_route_and_cad_edit_clear_it(self):
        hook=trimesh.creation.box(extents=[.03,.03,.004]);hook.apply_translation([.015,0,.015])
        scene=MeshScene([('lip',hook)])
        a=[[.02,-.02,0],[.02,.02,0]];b=[[.02,-.02,.03],[.02,.02,.03]]
        blocked=audit(scene,self.spec([a,b]))
        self.assertEqual(blocked['cases'][0]['status'],'nominal_contact')
        self.assertGreater(blocked['cases'][0]['parts'][0]['first_nominal_contact_pose'],0)
        outside=[[.04,-.02,0],[.04,.02,0]];up=[[.04,-.02,.03],[.04,.02,.03]]
        self.assertEqual(audit(scene,self.spec([a,outside,up]))['cases'][0]['status'],'clear_with_allowance')
        shortened=trimesh.creation.box(extents=[.01,.03,.004]);shortened.apply_translation([.005,0,.015])
        self.assertEqual(audit(MeshScene([('lip',shortened)]),self.spec([a,b]))['cases'][0]['status'],'clear_with_allowance')

    def test_manufacturing_allowance_exposes_nominally_clear_gap(self):
        scene=MeshScene([('wall',trimesh.creation.box(extents=[.02,.02,.02]))])
        spec=self.spec([[[-.02,0,.0112],[.02,0,.0112]]])
        spec['sampling_step_m']=.0001
        self.assertEqual(audit(scene,spec)['cases'][0]['status'],'clear_with_allowance')
        spec['allowances_m']={'print':.0003,'fuzz':.0002}
        r=audit(scene,spec)['cases'][0]['parts'][0]
        self.assertEqual(r['status'],'allowance_contact')
        self.assertAlmostEqual(r['minimum_sampled_nominal_clearance_m'],.0002)
        self.assertIsNone(r['first_nominal_contact_pose'])

    def test_full_rotation_cannot_hide_collision_between_identical_end_poses(self):
        rotor=trimesh.creation.box(extents=[.03,.003,.003]);rotor.apply_translation([.02,0,0])
        scene=MeshScene([('rotor',rotor)])
        pose=[[0,.02,-.004],[0,.02,.004]]
        r=audit(scene,self.spec([pose,pose],part_rotation_deg={'rotor':[0,360]}))['cases'][0]['parts'][0]
        self.assertEqual(r['status'],'nominal_contact')
        self.assertGreater(r['first_nominal_contact_pose'],.1)
        self.assertLess(r['first_nominal_contact_pose'],.3)

    def test_coarse_motion_bound_does_not_claim_clear_between_frames(self):
        obstacle=trimesh.creation.box(extents=[.0001,.01,.01]);obstacle.apply_translation([.005,0,0])
        scene=MeshScene([('wall',obstacle)])
        spec=self.spec([[[-.01,-.001,0],[-.01,.001,0]],[[.02,-.001,0],[.02,.001,0]]],radius=.00001)
        spec['motion_step_m']=.1
        self.assertEqual(audit(scene,spec)['cases'][0]['status'],'unresolved_clearance')

    def test_thin_wall_contact_is_localized_on_surface(self):
        scene=MeshScene([('wall',trimesh.creation.box(extents=[.00001,.02,.02]))])
        spec=self.spec([[[-.01,0,0],[.01,0,0]]],radius=.00001);spec['sampling_step_m']=.03
        r=audit(scene,spec)['cases'][0]['parts'][0]
        self.assertEqual(r['status'],'initial_nominal_contact')
        self.assertAlmostEqual(abs(r['site']['surface_reference_assembly_m'][0]),.000005)

    def test_report_converts_to_original_stl_coordinates_and_is_self_contained(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);trimesh.creation.box(extents=[20,20,20]).export(root/'box.stl')
            manifest={'unit':'mm','parts':[{'name':'translated','path':'box.stl','transform':[[1,0,0,50],[0,1,0,0],[0,0,1,30],[0,0,0,1]]}]}
            (root/'scene.json').write_text(json.dumps(manifest))
            scene=MeshScene.from_manifest(root/'scene.json')
            r=audit(scene,self.spec([[[.05,0,.0405],[.051,0,.0405]]]))
            point=r['cases'][0]['parts'][0]['site']['surface_source_coordinates']
            self.assertAlmostEqual(point[2],10,places=5)
            self.assertEqual(r['cases'][0]['parts'][0]['site']['source_unit'],'mm')
            write_report(root/'report',r)
            self.assertIn('translated',(root/'report/report.html').read_text(encoding='utf-8'))
            self.assertEqual(json.loads((root/'report/audit.json').read_text(encoding='utf-8'))['summary']['cases'],1)
            markers=json.loads((root/'report/review_markers.json').read_text(encoding='utf-8'))
            self.assertEqual(markers[0]['part'],'translated')
            self.assertTrue((root/'report'/markers[0]['file']).exists())

    def test_comparison_rejects_changed_paths_or_allowances(self):
        scene=MeshScene([('wall',trimesh.creation.box(extents=[.02,.02,.02]))])
        spec=self.spec([[[.0112,0,0],[.0112,.001,0]]])
        before=audit(scene,spec)
        after=audit(scene,spec|{'allowances_m':{'print':.0003}})
        with self.assertRaisesRegex(ValueError,'exactly the same'):compare(before,after)

    def test_report_preserves_inputs_after_caller_edits_the_next_scenario(self):
        scene=MeshScene([('wall',trimesh.creation.box(extents=[.02,.02,.02]))])
        spec=self.spec([[[.0112,0,0],[.0112,.001,0]]])
        before=audit(scene,spec)
        spec['cases'][0]['poses_m'][0][0][0]=.02
        self.assertAlmostEqual(before['inputs']['cases'][0]['poses_m'][0][0][0],.0112)

    def test_comparison_reports_cad_improvement_with_same_test(self):
        a=trimesh.creation.box(extents=[.02,.02,.02]);b=trimesh.creation.box(extents=[.01,.02,.02])
        spec=self.spec([[[.0105,0,0],[.0105,.001,0]]])
        before=audit(MeshScene([('body',a)]),spec);after=audit(MeshScene([('body',b)]),spec)
        r=compare(before,after)
        self.assertEqual(r['summary'],{'improved':1,'worsened':0,'remaining_flagged':0})

    def test_bad_units_rotations_and_unbounded_work_are_rejected(self):
        scene=MeshScene([('box',trimesh.creation.box(extents=[.02,.02,.02]))])
        spec=self.spec([[[.03,0,0],[.03,.01,0]],[[-.03,0,0],[-.03,.01,0]]])
        for extra in ({'allowances_m':{'print':-.1}},{'motion_step_m':1e-15}):
            with self.assertRaises(ValueError):audit(scene,spec|extra)
        spec['cases'][0]['part_rotation_deg']={'missing':[0,90]}
        with self.assertRaises(ValueError):audit(scene,spec)

    def test_bounding_volume_proof_is_conservative_for_rotation_and_interpolation(self):
        from yarnstand.snags import _sweep_box_lower_bound,_rotate
        obstacle=trimesh.creation.box(extents=[.01,.02,.03]);obstacle.apply_translation([.1,0,0])
        scene=MeshScene([('far_part',obstacle)])
        poses=np.array([[[.01,0,0],[.02,.01,.01]],[[.015,-.005,.002],[.025,.02,.02]]])
        origin=np.array([.005,0,0])
        for angles in (np.array([20.,20.]),np.array([10.,730.])):
            bound=_sweep_box_lower_bound(scene,poses,angles,origin)
            self.assertGreater(bound,0)
            for f in np.linspace(0,1,51):
                a,b=_rotate(poses[0]+f*(poses[1]-poses[0]),-(angles[0]+f*(angles[1]-angles[0])),origin)
                sampled=a+np.linspace(0,1,21)[:,None]*(b-a)
                self.assertGreaterEqual(scene.distance(sampled)[0].min()+1e-12,bound)


if __name__=='__main__':unittest.main()
