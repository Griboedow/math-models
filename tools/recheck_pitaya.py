"""Recheck PITAYA CAD with the current model and finite-radius mesh API.

Usage: python tools/recheck_pitaya.py /path/to/PITAYA_v10 --out results/pitaya_v10_recheck
Requires the optional mesh dependencies. CAD files are supplied separately.
All material coefficients remain explicit assumptions, not measurements.
"""
from pathlib import Path
from dataclasses import replace,asdict
from collections import Counter
import argparse,json,math,os,subprocess,sys,time,hashlib
import numpy as np

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
from yarnstand import presets
from yarnstand.mesh import MeshScene,taut_path
from yarnstand.model import simulate
from yarnstand.cli import save,write_csv,flatten

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('cad_package',type=Path)
parser.add_argument('--out',type=Path,default=REPO/'results/pitaya_v10_recheck')
args=parser.parse_args();cad=args.cad_package.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
started=time.monotonic()
def log(s): print(f'{time.monotonic()-started:.1f}s {s}',flush=True)
stand=replace(presets.stand('pitaya_v09'),name=f'{cad.name} geometry; v09 mechanical assumptions')
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
names=['body','platter','seeds','post']+[f'leaf_{i}' for i in range(1,7)]+['pads']
transform=[[1,0,0,0],[0,1,0,0],[0,0,1,1],[0,0,0,1]]
manifest={'unit':'mm','parts':[{'name':n,'path':os.path.relpath(cad/'cad'/f'{n}.stl',out).replace('\\','/'),'transform':transform} for n in names]}
save(out/'mesh_scene.json',manifest)
scene=MeshScene.from_manifest(out/'mesh_scene.json');log('Mesh scene loaded and closed surfaces checked')
metadata={'simulator_commit':commit,
          'source_version_note':'Commit identifies the checkout base; SHA-256 values identify the exact sources actually executed, including any local patch.',
          'simulator_source_sha256':{n:hashlib.sha256((REPO/'yarnstand'/n).read_bytes()).hexdigest() for n in ['mesh.py','model.py','presets.py']},
          'geometry_version':cad.name,'stand_assumptions':asdict(stand),
          'ball_presets':{n:asdict(presets.ball(n)) for n in ['full','nearly_empty']},
          'setup_presets':{n:asdict(presets.setup(n)) for n in ['desk_side','front','far_side','high_table','floor']},
          'motion_presets':{n:asdict(presets.motion(n)) for n in ['knitting','crochet']},
          'mesh_provenance':scene.provenance,
          'limitations':['prescribed geometry, not free sliding or a snag probability','no fuzz, FDM roughness, or deformation','stand mass and friction are assumptions','no table edge/environment model'],
          'static_path_tension_N':.04,'static_yarn_diameter_m':.002,'polyline_generation_step_m':.004,
          'path_sampling_step_m':.0005,'sweep_motion_step_m':.001}
save(out/'metadata.json',metadata)

rows=[]
for ba in ['full','nearly_empty']:
    for po in ['desk_side','front','far_side','high_table','floor']:
        for fraction in [-.65,0,.65]:
            b=replace(presets.ball(ba),exit_height_fraction=fraction)
            for azimuth in range(0,360,15):
                p=replace(presets.setup(po),azimuth_deg=azimuth)
                points,status=taut_path(stand,b,p,.04,step_m=.004)
                result=scene.screen(points,.001,max_step_m=.0005) if points is not None else {'status':status}
                rows.append({'ball':ba,'setup':po,'exit_fraction':fraction,'azimuth_deg':azimuth,**result})
        log(f'Static paths: {ba} {po}; {len(rows)} total')
        save(out/'static_paths.json',rows)
flat=[{k:r.get(k) for k in ['ball','setup','exit_fraction','azimuth_deg','status','min_sampled_clearance_m','clearance_lower_bound_m','nearest_part']} | {'contact_parts':';'.join(r.get('contact_parts',[]))} for r in rows]
write_csv(out/'static_paths.csv',flat)

# Diameter and tension sensitivity at the boundaries nearest to contact.
ordered=sorted(rows,key=lambda r:abs(r.get('min_sampled_clearance_m',1)))
selected=[];seen=set()
for r in ordered:
    key=(r['ball'],r['setup'],r['exit_fraction'])
    if key not in seen: selected.append(r);seen.add(key)
    if len(selected)==6:break
sensitivity=[]
for r in selected:
    b=replace(presets.ball(r['ball']),exit_height_fraction=r['exit_fraction'])
    p=replace(presets.setup(r['setup']),azimuth_deg=r['azimuth_deg'])
    for diameter in [.001,.002,.004]:
        for tension in [.01,.04,.10]:
            points,status=taut_path(stand,b,p,tension,step_m=.004)
            result=scene.screen(points,diameter/2) if points is not None else {'status':status}
            if result['status']=='unresolved_sampling_margin':
                points,_=taut_path(stand,b,p,tension,step_m=.001)
                result=scene.screen(points,diameter/2,max_step_m=.00005)
                result['refined_from_unresolved_sampling']=True
            sensitivity.append({k:r[k] for k in ['ball','setup','exit_fraction','azimuth_deg']} | {'diameter_m':diameter,'tension_N':tension,**result})
save(out/'mesh_sensitivity.json',sensitivity);log('Diameter/tension sensitivity complete')

dynamics=[]
for ba in ['full','nearly_empty']:
    for mo in ['knitting','crochet']:
        for po in ['desk_side','front','far_side','high_table','floor']:
            for fraction in [-.65,0,.65]:
                result=simulate(stand,replace(presets.ball(ba),exit_height_fraction=fraction),presets.motion(mo),presets.setup(po),keep_trace=False)
                dynamics.append({'case':{'ball':ba,'motion':mo,'setup':po,'exit_fraction':fraction},**result})
save(out/'dynamics.json',dynamics)
write_csv(out/'dynamics.csv',[flatten(r,r['case']) for r in dynamics]);log('60 dynamics cases complete')

def fixed_path(b,p):
    points,status=taut_path(stand,b,p,.04,step_m=.004)
    if points is None:raise ValueError(status)
    grid=np.linspace(0,1,len(points)); t=np.linspace(0,1,65)
    return np.column_stack([np.interp(t,grid,points[:,i]) for i in range(3)])
sweeps=[]
for ba in ['full','nearly_empty']:
    for mo in ['knitting','crochet']:
        for po in ['desk_side','high_table','floor']:
            for fraction in [-.65,0]:
                b=replace(presets.ball(ba),exit_height_fraction=fraction)
                p=presets.setup(po);amp=presets.motion(mo).lateral_amplitude_m
                poses=[]
                for delta in [-amp,0,amp]:
                    q=replace(p,distance_m=math.hypot(p.distance_m,delta),azimuth_deg=p.azimuth_deg+math.degrees(math.atan2(delta,p.distance_m)))
                    poses.append(fixed_path(b,q))
                result=scene.sweep(poses,.001,max_step_m=.0005,motion_step_m=.001)
                sweeps.append({'kind':'prescribed_hand_movement','case':{'ball':ba,'motion':mo,'setup':po,'exit_fraction':fraction},'poses_m':np.asarray(poses).tolist(),'result':result})
        log(f'Hand sweeps: {ba} {mo}')
        save(out/'sweeps.json',sweeps)

# A slack loop below one decorative leaf, represented by a transverse segment.
# These are imposed routes, not a prediction of how a real loose loop moves.
angle=math.radians(30)
rot=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])
def crossbar(radius,z):
    return np.array([[radius,-.022,z],[radius,.022,z]])@rot.T
routes={
 'loop_lift_straight':[(.080,.002),(.080,.050)],
 'loop_lift_diagonal':[(.080,.002),(.095,.050)],
 'loop_outward_then_up':[(.080,.002),(.095,.002),(.095,.050)],
}
for name,locations in routes.items():
    poses=np.asarray([crossbar(r,z) for r,z in locations])
    result=scene.sweep(poses,.001,max_step_m=.0005,motion_step_m=.0005)
    sweeps.append({'kind':name,'case':{'description':'2 mm cord under leaf 1; prescribed movement'},'poses_m':poses.tolist(),'result':result})
    log(name+': '+result['status'])
save(out/'sweeps.json',sweeps)
summary={'static_paths':len(rows),'static_statuses':dict(Counter(r['status'] for r in rows)),
         'static_contact_parts':dict(Counter(p for r in rows for p in r.get('contact_parts',[]))),
         'diameter_tension_cases':len(sensitivity),'dynamics_cases':len(dynamics),
         'dynamics_events':dict(Counter(k for r in dynamics for k in r['summary']['first_events_s'])),
         'sweeps':len(sweeps),'sweep_statuses':dict(Counter(r['result']['status'] for r in sweeps)),
         'elapsed_s':time.monotonic()-started}
save(out/'summary.json',summary);log(json.dumps(summary))
