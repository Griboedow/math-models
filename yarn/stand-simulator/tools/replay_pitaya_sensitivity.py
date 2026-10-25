"""Replay saved diameter/tension cases on another PITAYA geometry.

The main recheck selects near-contact azimuths adaptively. Symmetric ties can
select a different azimuth after a small CAD edit, so replay the baseline
cases explicitly when comparing two revisions.

Usage: python tools/replay_pitaya_sensitivity.py RESULTS_DIRECTORY BASELINE_CASES_JSON
"""
from pathlib import Path
from dataclasses import replace
import argparse,hashlib,json,os,sys
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO))
from yarnstand import presets
from yarnstand.mesh import MeshScene,taut_path
from yarnstand.cli import save

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('nominal_directory',type=Path);p.add_argument('baseline_cases',type=Path)
a=p.parse_args();out=a.nominal_directory.resolve();source=a.baseline_cases.resolve()
metadata=json.loads((out/'metadata.json').read_text(encoding='utf-8-sig'))
cases=json.loads(source.read_text(encoding='utf-8-sig'))
scene=MeshScene.from_manifest(out/'mesh_scene.json')
stand=type(presets.stand('pitaya_v09'))(**metadata['stand_assumptions'])
rows=[]
keys=['ball','setup','exit_fraction','azimuth_deg','diameter_m','tension_N']
for r in cases:
    b=replace(type(presets.ball(r['ball']))(**metadata['ball_presets'][r['ball']]),exit_height_fraction=r['exit_fraction'])
    setup=replace(type(presets.setup(r['setup']))(**metadata['setup_presets'][r['setup']]),azimuth_deg=r['azimuth_deg'])
    points,status=taut_path(stand,b,setup,r['tension_N'],step_m=.004)
    result=scene.screen(points,r['diameter_m']/2) if points is not None else {'status':status}
    if result['status']=='unresolved_sampling_margin':
        points,_=taut_path(stand,b,setup,r['tension_N'],step_m=.001)
        result=scene.screen(points,r['diameter_m']/2,max_step_m=.00005)
        result['refined_from_unresolved_sampling']=True
    rows.append({k:r[k] for k in keys}|result)
save(out/'mesh_sensitivity.json',rows)
metadata['sensitivity_input_source']={'path':os.path.relpath(source,out).replace('\\','/'),
    'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'cases':len(rows),
    'strategy':'exact replay of saved input combinations, replacing adaptive near-contact selection'}
metadata['sensitivity_replay_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
save(out/'metadata.json',metadata)
print(f'Replayed {len(rows)} saved diameter/tension cases',flush=True)
