"""Optional finite-radius cord screening against actual closed triangle meshes.

Distances are SI metres. Sampling reports a conservative lower bound using the
1-Lipschitz property of distance. This is geometry, not a friction/snaggability
certificate. Optional dependencies are imported only when this module is used.
"""
from pathlib import Path
import hashlib,json,math
import numpy as np
import vtk
import trimesh

MAX_PATH_SAMPLES=250000
MAX_SWEEP_POINTS=2000000


def _subdivisions(length,step,budget):
    ratio=float(length)/step
    if budget<1 or not math.isfinite(ratio) or ratio>budget:
        raise ValueError('Sampling would exceed the work limit; use a larger step or split the job')
    return max(1,math.ceil(ratio))


class MeshScene:
    def __init__(self, parts):
        """parts: [(name, trimesh.Trimesh in metres)]."""
        self.parts=[]
        for name,mesh in parts:
            if not np.isfinite(mesh.vertices).all() or not math.isfinite(mesh.volume) or not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:
                raise ValueError(f'{name}: a closed, consistently outward oriented mesh is required')
            from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
            pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(np.asarray(mesh.vertices),deep=True))
            cells=vtk.vtkCellArray()
            a=np.column_stack((np.full(len(mesh.faces),3),mesh.faces)).astype(np.int64)
            cells.ImportLegacyFormat(numpy_to_vtkIdTypeArray(a.ravel(),deep=True))
            poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetPolys(cells)
            field=vtk.vtkImplicitPolyDataDistance();field.SetInput(poly)
            tree=vtk.vtkOBBTree();tree.SetDataSet(poly)
            # Scene units are metres. VTK's 0.01 default is a centimetre and
            # can miss crossings of small curved surfaces. This epsilon is
            # numerical only; yarn radius and clearance margins are separate.
            tree.SetTolerance(1e-9);tree.BuildLocator()
            self.parts.append((name,field,tree,np.asarray(mesh.bounds),poly))
        if not self.parts:raise ValueError('Scene must contain at least one mesh')
        self.provenance={}

    @classmethod
    def from_manifest(cls,path):
        path=Path(path);data=json.loads(path.read_text(encoding='utf-8-sig'))
        if data.get('unit') not in ('mm','m'):raise ValueError('Manifest unit must be mm or m')
        scale=.001 if data['unit']=='mm' else 1.
        parts=[];sources=[]
        for item in data['parts']:
            p=(path.parent/item['path']).resolve()
            m=trimesh.load_mesh(p,process=True)
            m.update_faces(m.nondegenerate_faces(height=1e-9));m.remove_unreferenced_vertices()
            transform=np.asarray(item.get('transform',np.eye(4)),dtype=float)
            if transform.shape!=(4,4) or not np.isfinite(transform).all() or not np.allclose(transform[3],[0,0,0,1]):raise ValueError('Invalid transform')
            m.apply_transform(transform);m.apply_scale(scale)
            parts.append((item['name'],m))
            sources.append({'name':item['name'],'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'transform':transform.tolist()})
        scene=cls(parts);scene.provenance={'manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sources':sources,'units':'m'}
        return scene

    def distance(self,points,normals=False):
        p=np.asarray(points,dtype=float).reshape(-1,3)
        if not np.isfinite(p).all():raise ValueError('Finite query points required')
        distances=np.full(len(p),np.inf);indices=np.full(len(p),-1,dtype=int)
        gradient=np.zeros_like(p)
        for i,(name,field,tree,bounds,poly) in enumerate(self.parts):
            # AABB distance is a valid pruning bound only for outside points.
            bound=np.linalg.norm(np.maximum(np.maximum(bounds[0]-p,p-bounds[1]),0),axis=1)
            for j in np.flatnonzero((bound<=np.maximum(distances,0)) | (bound==0)):
                d=field.EvaluateFunction(p[j])
                if d<distances[j]:
                    distances[j]=d;indices[j]=i
                    if normals:
                        g=[0.,0.,0.];field.EvaluateGradient(p[j],g)
                        norm=np.linalg.norm(g);gradient[j]=np.asarray(g)/norm if norm>0 else [0,0,1]
        return distances,gradient,indices

    def intersections(self,points):
        found=set()
        for name,field,tree,bounds,poly in self.parts:
            for a,b in zip(points,points[1:]):
                if np.any(np.maximum(a,b)<bounds[0]) or np.any(np.minimum(a,b)>bounds[1]):continue
                hits=vtk.vtkPoints();ids=vtk.vtkIdList()
                if tree.IntersectWithLine(a,b,hits,ids):found.add(name);break
        return sorted(found)

    def screen(self,points,radius_m,max_step_m=None):
        points=np.asarray(points,dtype=float)
        if points.ndim!=2 or points.shape[1]!=3 or len(points)<2 or not np.isfinite(points).all():raise ValueError('Invalid polyline')
        if not math.isfinite(radius_m) or radius_m<=0:raise ValueError('Positive finite yarn radius required')
        step=max_step_m if max_step_m is not None else min(radius_m/2,.0005)
        if not math.isfinite(step) or step<=0:raise ValueError('Positive finite sampling step required')
        if len(points)>MAX_PATH_SAMPLES:raise ValueError('Too many path points; split the job')
        samples=[points[0]];largest=0.
        for a,b in zip(points,points[1:]):
            length=np.linalg.norm(b-a);count=_subdivisions(length,step,MAX_PATH_SAMPLES-len(samples))
            largest=max(largest,length/count)
            samples.extend(a+(b-a)*(j/count) for j in range(1,count+1))
        samples=np.asarray(samples)
        # We need the global minimum and contacts, not all far-field distances.
        # AABB lower bounds let us skip provably irrelevant sample/part pairs.
        best=math.inf;worst=0;nearest=0;contacts=set()
        for part,(name,field,tree,bounds,poly) in enumerate(self.parts):
            bound=np.linalg.norm(np.maximum(np.maximum(bounds[0]-samples,samples-bounds[1]),0),axis=1)
            for j in np.argsort(bound):
                if bound[j]>max(best,radius_m):break
                d=field.EvaluateFunction(samples[j])
                if d<=radius_m:contacts.add(name)
                if d<best:best=d;worst=int(j);nearest=part
        lower=float(best-radius_m-largest/2)
        crossings=self.intersections(points)
        status='contact' if contacts or crossings else ('clear' if lower>0 else 'unresolved_sampling_margin')
        return {'status':status,'min_sampled_clearance_m':float(best-radius_m),'clearance_lower_bound_m':lower,
                'worst_point_m':samples[worst].tolist(),'nearest_part':self.parts[nearest][0],
                'contact_parts':sorted(contacts),'centerline_crossings':crossings,'sample_count':len(samples),'max_sample_spacing_m':largest,
                'yarn_radius_m':radius_m,'scope':'prescribed finite-radius centerline; no contact rerouting or friction'}

    def sweep(self,poses,radius_m,max_step_m=None,motion_step_m=None):
        """Screen a prescribed, linearly interpolated movement of a cord.

        Matching material nodes are required in every pose. The time-direction
        clearance bound uses the maximum node movement; this prevents declaring
        clear two end poses that actually pass through an obstacle between them.
        No force, friction, elasticity or real-world release is inferred.
        """
        poses=np.asarray(poses,dtype=float)
        if poses.ndim!=3 or poses.shape[2]!=3 or min(poses.shape[:2])<2 or not np.isfinite(poses).all():
            raise ValueError('At least two finite poses with matching nodes required')
        if not math.isfinite(radius_m) or radius_m<=0:raise ValueError('Positive finite radius required')
        step=motion_step_m if motion_step_m is not None else min(radius_m/2,.0005)
        if not math.isfinite(step) or step<=0:raise ValueError('Positive finite motion step required')
        frame_limit=min(100000,MAX_SWEEP_POINTS//poses.shape[1])
        if len(poses)>frame_limit:raise ValueError('Sweep requires too many points; split the job')
        frames=[poses[0]];largest=0.
        for a,b in zip(poses,poses[1:]):
            movement=float(np.linalg.norm(b-a,axis=1).max());count=_subdivisions(movement,step,frame_limit-len(frames))
            largest=max(largest,movement/count)
            frames.extend(a+(b-a)*(j/count) for j in range(1,count+1))
        results=[]
        for index,points in enumerate(frames):
            r=self.screen(points,radius_m,max_step_m);results.append(r)
            if r['status']=='contact':
                return {'status':'initial_contact' if index==0 else 'contact_on_prescribed_sweep',
                        'first_contact_frame':index,'frame_count':len(frames),'checked_frames':len(results),'screens':results,
                        'contact_points_m':points.tolist(),
                        'scope':'prescribed linear motion only; no friction or contact rerouting'}
        lower=min(r['clearance_lower_bound_m'] for r in results)-largest/2
        return {'status':'clear_prescribed_sweep' if lower>0 else 'unresolved_sampling_margin',
                'clearance_lower_bound_m':lower,'frame_count':len(frames),'checked_frames':len(results),
                'max_node_motion_m':largest,'screens':results,'scope':'prescribed linear motion only; no friction or contact rerouting'}


def taut_path(stand,ball,setup,tension_N,step_m=.001):
    """Full-span small-sag path; return None rather than extrapolate to slack."""
    from .model import geometry,G
    if not math.isfinite(tension_N) or tension_N<0:raise ValueError('Finite nonnegative tension required')
    if not math.isfinite(step_m) or step_m<=0:raise ValueError('Positive finite path step required')
    q,h,u,_,length=geometry(stand,ball,setup)
    horizontal=math.hypot(h[0]-q[0],h[1]-q[1]);H=tension_N*math.hypot(u[0],u[1])
    if H<.001:return None,'slack_or_too_low_tension'
    coefficient=ball.line_density_kg_m*G*horizontal**2/(2*H)
    if coefficient/4>.1*length:return None,'large_sag_outside_approximation'
    count=_subdivisions(length,step_m,MAX_PATH_SAMPLES-1)
    t=np.linspace(0,1,count+1)
    points=np.asarray(q)+t[:,None]*(np.asarray(h)-q)
    points[:,2]-=coefficient*t*(1-t)
    return points,'small_sag_approximation'
