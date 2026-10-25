"""Generate repeatable pre-print risk cases from the saved fruit CAD audits.

python tools/make_snag_cases.py peach_v13
python tools/make_snag_cases.py pitaya_v10
The external CAD meshes are referenced, not changed or copied.
"""
from pathlib import Path
import argparse,json,math,os,sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from yarnstand.cli import save

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('model',choices=['peach_v13','pitaya_v10'])
args=parser.parse_args();old=ROOT/'results'/f'{args.model}_audit_fix';out=ROOT/'results'/f'{args.model}_snags';out.mkdir(parents=True,exist_ok=True)
manifest=json.loads((old/'mesh_scene.json').read_text(encoding='utf-8-sig'))
for item in manifest['parts']:item['path']=os.path.relpath((old/item['path']).resolve(),out).replace('\\','/')
save(out/'scene.json',manifest)
cases=[]
if args.model=='peach_v13':
    for path in sorted(old.glob('sweep_*mm_*.json')):
        data=json.loads(path.read_text(encoding='utf-8-sig'))['inputs']
        cases.append({'id':path.stem,'poses_m':data['poses_m'],'yarn_radius_m':data['yarn_radius_m'],
                      'description':'Replay of saved prescribed leaf route; not spontaneous sliding'})
    rotating=['02_puffy_platter_peach','03_striped_spindle_honey'];top=.0707
else:
    data=json.loads((old/'sweeps.json').read_text(encoding='utf-8-sig'))
    for case in data:
        if not case['kind'].startswith('loop_'):continue
        for leaf in range(6):
            angle=math.radians(leaf*60);c,s=math.cos(angle),math.sin(angle)
            rotation=np.array([[c,-s,0],[s,c,0],[0,0,1]])
            for diameter in [2,4]:
                poses=np.asarray(case['poses_m'])@rotation.T
                poses[:,:,2]+=(diameter-2)*.0005  # keep initial lower cord surface at the same height
                cases.append({'id':f'leaf_{leaf+1}_{case["kind"]}_{diameter}mm','poses_m':poses.tolist(),
                              'yarn_radius_m':diameter*.0005,'description':'Prescribed loose cord under leaf; larger cord starts higher'})
    rotating=['platter','seeds','post'];top=.04511
# A cord segment deliberately placed by the rotating platter edge. Angles are
# unwrapped: 0 -> 360 is a full revolution, not two identical static snapshots.
for diameter in [2,4]:
    for direction in [-1,1]:
        pose=[[.0535,-.012,top-.001],[.0535,.012,top-.001]]
        cases.append({'id':f'platter_edge_{diameter}mm_{direction:+d}_turn','yarn_radius_m':diameter*.0005,
                      'poses_m':[pose,pose],'part_rotation_deg':{n:[0,direction*360] for n in rotating},
                      'description':'Stress case: cord by platter rim while platter and spindle rotate; body and leaves fixed'})
save(out/'cases.json',{'description':'Geometry risk scenarios; allowances are explicit design assumptions, not measurements',
                       'allowances_m':{'print':.0002,'fuzz':.0002,'mesh':.00005,'reserve':.00005},
                       'sampling_step_m':.00025,'motion_step_m':.00025,'cases':cases})
print(out/'cases.json',len(cases),'cases')
