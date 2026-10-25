"""End-to-end synthetic CAD correction: shorten an overhang, rerun identical paths."""
from pathlib import Path
import argparse,json,subprocess,sys
import trimesh

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from yarnstand.cli import save

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',type=Path,default=ROOT/'results/snag_validation')
args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
for revision,length in [('before',30),('after',10)]:
    column=trimesh.creation.box(extents=[6,30,30]);column.apply_translation([0,0,15])
    lip=trimesh.creation.box(extents=[length,30,4]);lip.apply_translation([length/2,0,15])
    trimesh.util.concatenate([column,lip]).export(out/f'{revision}.stl')
    save(out/f'{revision}_scene.json',{'unit':'mm','parts':[{'name':'hook','path':f'{revision}.stl'}]})
a=[[.02,-.02,.004],[.02,.02,.004]];up=[[.02,-.02,.03],[.02,.02,.03]]
outside=[[.04,-.02,.004],[.04,.02,.004]];outside_up=[[.04,-.02,.03],[.04,.02,.03]]
save(out/'cases.json',{'description':'Synthetic overhang validation, not a proposed fruit CAD change',
                     'allowances_m':{'reserve':.0005},'sampling_step_m':.0005,'motion_step_m':.0005,
                     'cases':[{'id':'lift_under_overhang','yarn_radius_m':.001,'poses_m':[a,up]},
                              {'id':'outward_then_up','yarn_radius_m':.001,'poses_m':[a,outside,outside_up]}]})
for revision in ['before','after']:
    subprocess.run([sys.executable,'-m','yarnstand','snag-audit',str(out/f'{revision}_scene.json'),str(out/'cases.json'),'--out',str(out/revision)],cwd=ROOT,check=True)
subprocess.run([sys.executable,'-m','yarnstand','snag-compare',str(out/'before/audit.json'),str(out/'after/audit.json'),'--out',str(out/'comparison.json')],cwd=ROOT,check=True)
comparison=json.loads((out/'comparison.json').read_text(encoding='utf-8'))
assert comparison['summary']=={'improved':1,'worsened':0,'remaining_flagged':0},comparison['summary']
print('CAD correction workflow verified:',out)
