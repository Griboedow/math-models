"""Recheck PEACH v13 with the current mechanics and path model.

python tools/recheck_peach.py /path/to/PEACH_v13 --out results/peach_v13_audit_fix
CAD is external. Existing prescribed sweep files in CAD-package/simulation are
replayed, if present, without modifying the package or deriving new release paths.
"""
from pathlib import Path
from dataclasses import replace,asdict
from collections import Counter
import argparse,hashlib,json,os,subprocess,sys,time
import numpy as np

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
from yarnstand import presets
from yarnstand.model import simulate
from yarnstand.mesh import MeshScene,taut_path
from yarnstand.cli import save,write_csv,flatten

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('cad_package',type=Path)
parser.add_argument('--out',type=Path,default=REPO/'results/peach_v13_audit_fix')
args=parser.parse_args();cad=args.cad_package.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
started=time.monotonic()
def log(message):print(f'{time.monotonic()-started:.1f}s {message}',flush=True)

stand=presets.stand('peach_v13')
names=['01_body_peach','02_puffy_platter_peach','03_striped_spindle_honey','04_leaf_green','08_leaf_second_green']
manifest={'unit':'mm','parts':[{'name':n,'path':os.path.relpath(cad/'cad'/f'{n}.stl',out).replace('\\','/'),
    'transform':[[1,0,0,0],[0,1,0,0],[0,0,1,1.7],[0,0,0,1]]} for n in names]}
save(out/'mesh_scene.json',manifest)
scene=MeshScene.from_manifest(out/'mesh_scene.json');log('Mesh scene loaded')
save(out/'metadata.json',{'simulator_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
    'source_version_note':'Commit identifies the checkout base; hashes identify the exact executed sources, including local changes.',
    'simulator_source_sha256':{n:hashlib.sha256((REPO/'yarnstand'/n).read_bytes()).hexdigest() for n in ['model.py','paths.py','mesh.py','presets.py']},
    'stand_assumptions':asdict(stand),'mesh_provenance':scene.provenance,
    'path_model':'arc-length-weight catenary; surface exit; inward paths rejected',
    'limitations':['not physical print validation','no contact rerouting or friction','fixed ball shape and exit latitude','prescribed sweep poses only']})

rows=[]
for ba in ['full','nearly_empty','large']:
    for mo in ['knitting','crochet','gentle']:
        for po in ['desk_side','front','far_side','high_table','floor']:
            result=simulate(stand,presets.ball(ba),presets.motion(mo),presets.setup(po),keep_trace=False)
            rows.append({'case':{'ball':ba,'motion':mo,'setup':po},**result})
save(out/'dynamics.json',rows);write_csv(out/'dynamics.csv',[flatten(r,r['case']) for r in rows]);log('45 dynamics cases complete')
dynamics=rows;rows=[]
for ba in ['full','nearly_empty','large']:
    for po in ['desk_side','front','far_side','high_table','floor']:
        for fraction in [-.8,-.65,0,.65]:
            b=replace(presets.ball(ba),exit_height_fraction=fraction)
            for azimuth in range(0,360,15):
                p=replace(presets.setup(po),azimuth_deg=azimuth)
                for tension in [.01,.04,.15]:
                    points,status=taut_path(stand,b,p,tension)
                    for diameter in [.002,.004]:
                        result=scene.screen(points,diameter/2,max_step_m=.0005) if points is not None else {'status':status}
                        if result['status']=='unresolved_sampling_margin':
                            refined,status=taut_path(stand,b,p,tension,step_m=.00025)
                            result=scene.screen(refined,diameter/2,max_step_m=.00005) if refined is not None else {'status':status}
                            result['refined_from_unresolved_sampling']=True
                        rows.append({'ball':ba,'setup':po,'exit_fraction':fraction,'azimuth_deg':azimuth,'tension_N':tension,'diameter_m':diameter,**result})
        log(f'Paths {ba} {po}: {len(rows)}');save(out/'static_paths.json',rows)

sweeps=[]
for path in sorted((cad/'simulation').glob('sweep_*mm_*.json')):
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    result=scene.sweep(data['poses_m'],data['yarn_radius_m'],max_step_m=.00005,motion_step_m=.0001)
    # Keep inputs with their results, making this replay independent of later CAD-package edits.
    save(out/path.name,{'inputs':data,'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'result':result})
    sweeps.append({'case':path.stem,**{k:v for k,v in result.items() if k not in ('screens','contact_points_m')}})
    log(path.stem+': '+result['status'])
save(out/'sweeps_summary.json',sweeps)
summary={'dynamics_cases':len(dynamics),'dynamics_events':dict(Counter(k for r in dynamics for k in r['summary']['first_events_s'])),
    'dynamics_valid_in_reported_scope':sum(r['summary']['hypotheses_valid_for_entire_run'] for r in dynamics),
    'static_paths':len(rows),'static_statuses':dict(Counter(r['status'] for r in rows)),
    'sweeps':len(sweeps),'sweep_statuses':dict(Counter(r['status'] for r in sweeps)),'elapsed_s':time.monotonic()-started}
save(out/'summary.json',summary);log(json.dumps(summary))
