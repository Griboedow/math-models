"""Check taut-yarn paths against a PITAYA v09 CAD package (requires VTK).
Usage: python tools/check_pitaya_mesh_paths.py /path/to/PITAYA_v09
This is specific to the PITAYA assembly coordinates, not an arbitrary mesh.
Only triangle intersections are checked; fuzz and slack loops are not modeled.
"""
from pathlib import Path
import sys,json,math,hashlib,argparse
import vtk
from dataclasses import replace,asdict
REPO=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('cad_package',type=Path)
parser.add_argument('--out',type=Path,default=REPO/'results/pitaya_v09_mesh_paths.json')
args=parser.parse_args()
ROOT=args.cad_package.resolve()
sys.path.insert(0,str(REPO))
from yarnstand import presets
from yarnstand.model import geometry,G
from yarnstand.paths import prescribed_path
trees=[]
mesh_hashes={}
stand=presets.stand('pitaya_v09')
for name in ['body','platter','post']+[f'leaf_{i}' for i in range(1,7)]:
    mesh_hashes[name]=hashlib.sha256((ROOT/'cad'/(name+'.stl')).read_bytes()).hexdigest()
    reader=vtk.vtkSTLReader();reader.SetFileName(str(ROOT/'cad'/(name+'.stl')));reader.Update()
    transform=vtk.vtkTransform();transform.Translate(0,0,1) # feet place body Z0 one mm above table
    f=vtk.vtkTransformPolyDataFilter();f.SetTransform(transform);f.SetInputData(reader.GetOutput());f.Update()
    tree=vtk.vtkOBBTree();tree.SetDataSet(f.GetOutput());tree.BuildLocator();trees.append((name,tree))
rows=[]
for ba in ['full','nearly_empty']:
    for po in ['desk_side','high_table','floor']:
        for fraction in [-.65,0,.65]:
            for azimuth in range(0,360,15):
                b=replace(presets.ball(ba),exit_height_fraction=fraction)
                p=replace(presets.setup(po),azimuth_deg=azimuth)
                q,h,u,_,L=geometry(stand,b,p)
                horizontal=math.hypot(h[0]-q[0],h[1]-q[1]);H=.04*math.hypot(u[0],u[1])
                checked,status,curve=prescribed_path(stand,b,p,.04)
                if checked is None:
                    rows.append({'ball':ba,'setup':po,'exit_fraction':fraction,'azimuth_deg':azimuth,'status':status,'hit_parts':[]})
                    continue
                stop=min(1,.14/horizontal);points=[]
                for j in range(51):
                    t=stop*j/50
                    points.append([v*1000 for v in curve.point(t)])
                hits=set()
                for name,tree in trees:
                    for a,c in zip(points,points[1:]):
                        hitpoints=vtk.vtkPoints();ids=vtk.vtkIdList()
                        if tree.IntersectWithLine(a,c,hitpoints,ids): hits.add(name);break
                rows.append({'ball':ba,'setup':po,'exit_fraction':fraction,'azimuth_deg':azimuth,'status':'contact' if hits else 'clear_zero_radius_ray','hit_parts':sorted(hits)})
out={'geometry_version':ROOT.name,'mesh_sha256':mesh_hashes,
     'winding_radius_model':'tangent to actual ellipsoid horizontal section; spatial paths entering the ball are rejected',
     'stand_assumptions':asdict(stand),
     'ball_presets':{n:asdict(presets.ball(n)) for n in ['full','nearly_empty']},
     'setup_presets':{n:asdict(presets.setup(n)) for n in ['desk_side','high_table','floor']},
     'method':'VTK segment/triangle intersection; 51 points on a catenary within 140 mm horizontal distance from yarn exit; CAD Z shifted +1 mm for feet',
     'cases':len(rows),'ray_tension_N':.04,'line_only_no_yarn_radius':True,'physical_print_tested':False,'cases_with_hits':sum(bool(r['hit_parts']) for r in rows),'results':rows}
args.out.parent.mkdir(parents=True,exist_ok=True)
args.out.write_text(json.dumps(out,indent=2),encoding='utf-8')
print({k:v for k,v in out.items() if k in ['geometry_version','cases','cases_with_hits','ray_tension_N']},flush=True)
print('Contacts:',{(ba,po):sum(bool(r['hit_parts']) for r in rows if r['ball']==ba and r['setup']==po) for ba in ['full','nearly_empty'] for po in ['desk_side','high_table','floor']})
