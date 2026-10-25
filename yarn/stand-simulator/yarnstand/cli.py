"""Run with python -m yarnstand (Python 3.10+; no third-party dependencies)."""
import argparse, csv, json, math
from pathlib import Path
from dataclasses import replace
from .model import simulate,from_config,path_clearance
from . import presets


def clean(value):
    if isinstance(value,float) and not math.isfinite(value): return None
    if isinstance(value,dict): return {k:clean(v) for k,v in value.items()}
    if isinstance(value,list): return [clean(v) for v in value]
    return value


def save(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(clean(data),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def flatten(result,extra=None):
    x=result['summary']; i=result['inputs']
    return {**(extra or {}),'stand':i['stand']['name'],'ball':i['ball']['name'],'motion':i['motion']['name'],'setup':i['setup']['name'],
            'peak_N':x['peak_tension_N'],'p95_N':x['p95_tension_N'],'slack_mm':1000*x['max_slack_m'],
            'critical_snag_N':x['static_limits']['critical_snag_N'],'start_N':x['static_limits']['start_tension_N'],
            'slide_util':x['max_slide_utilization'],'tip_util':x['max_tip_utilization'],
            'ball_traction_util':x['max_ball_traction_utilization'],'model_valid':x['hypotheses_valid_for_entire_run'],
            'events':';'.join(x['first_events_s']), 'valid_until_s':x['valid_coupled_interval_end_s'],
            'peak_before_event_N':x['peak_tension_before_first_event_N'], 'path_status':x['path_screen']['status'],
            'path_clearance_mm':1000*x['path_screen']['min_clearance_m'] if x['path_screen']['min_clearance_m'] is not None else None}


def write_csv(path,rows):
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(clean(rows))


def suite(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    results=[]; rows=[]
    for st in ['pitaya_v08','wide_feet','light_small','high_drag']:
        for ba in ['full','nearly_empty']:
            for mo in ['knitting','crochet']:
                for po in ['desk_side','front','far_side','high_table','floor']:
                    result=simulate(presets.stand(st),presets.ball(ba),presets.motion(mo),presets.setup(po),keep_trace=(st=='pitaya_v08' and po=='desk_side'))
                    result['case']={'stand':st,'ball':ba,'motion':mo,'setup':po}
                    rows.append(flatten(result,result['case'] | {'stand_preset':st}));results.append(result)
        print('Completed',st,flush=True)
    save(out/'scenarios.json',results);write_csv(out/'scenarios.csv',rows)
    # Geometry screen includes low/high exits around a full turn, not only centre.
    screens=[]
    for st in ['pitaya_v07','pitaya_v08']:
        for ba in ['full','nearly_empty']:
            for po in ['desk_side','high_table','floor']:
                for fraction in [-.65,0,.65]:
                    for azimuth in range(0,360,15):
                        b=replace(presets.ball(ba),exit_height_fraction=fraction)
                        p=replace(presets.setup(po),azimuth_deg=azimuth)
                        c=path_clearance(presets.stand(st),b,p,.04)
                        screens.append({'stand':st,'ball':ba,'setup':po,'exit_fraction':fraction,'azimuth_deg':azimuth,**c})
    save(out/'path_screens.json',screens)
    return results


def sensitivity(out):
    """Deterministic grid, no probabilistic meaning or measured distributions."""
    rows=[]
    for ba in ['full','nearly_empty']:
        for mo in ['knitting','crochet']:
            for torque in [.0002,.0006,.0015,.003]:
                for foot_mu in [.2,.45,.7]:
                    s=replace(presets.stand(),start_torque_Nm=torque,running_torque_Nm=torque*.5,foot_friction=foot_mu)
                    r=simulate(s,presets.ball(ba),presets.motion(mo),presets.setup(),keep_trace=False)
                    rows.append(flatten(r,{'sweep':'bearing_and_feet','start_torque_mNm':1000*torque,'foot_mu':foot_mu,'peel_force_N':r['inputs']['ball']['peel_force_N'],'axial_rigidity_N':r['inputs']['ball']['yarn_axial_rigidity_N'],'spindle_coupling_Nm':0.,'ball_preset':ba,'motion_preset':mo}))
    for ba in ['full','nearly_empty']:
        for peel in [0.,.015,.05]:
            for rigidity in [.5,4.,12.]:
                b=replace(presets.ball(ba),peel_force_N=peel,yarn_axial_rigidity_N=rigidity)
                r=simulate(presets.stand(),b,presets.motion('crochet'),presets.setup(),keep_trace=False)
                rows.append(flatten(r,{'sweep':'yarn_properties','start_torque_mNm':.6,'foot_mu':.45,'peel_force_N':peel,'axial_rigidity_N':rigidity,'spindle_coupling_Nm':0.,'ball_preset':ba,'motion_preset':'crochet'}))
    for coupling in [.0005,.002,.005]:
        b=replace(presets.ball('nearly_empty'),spindle_coupling_Nm=coupling)
        r=simulate(presets.stand(),b,presets.motion('crochet'),presets.setup(),keep_trace=False)
        rows.append(flatten(r,{'sweep':'spindle_grip','start_torque_mNm':.6,'foot_mu':.45,'peel_force_N':b.peel_force_N,'axial_rigidity_N':b.yarn_axial_rigidity_N,'spindle_coupling_Nm':coupling,'ball_preset':'nearly_empty','motion_preset':'crochet'}))
    Path(out).mkdir(parents=True,exist_ok=True);write_csv(Path(out)/'sensitivity.csv',rows);save(Path(out)/'sensitivity.json',rows)
    print('Sensitivity cases:',len(rows))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    run=sub.add_parser('run');run.add_argument('config');run.add_argument('--out',default='results/custom.json')
    pre=sub.add_parser('preset');pre.add_argument('--stand',default='pitaya_v08');pre.add_argument('--ball',default='full');pre.add_argument('--motion',default='knitting');pre.add_argument('--setup',default='desk_side');pre.add_argument('--out',default='examples/custom.json')
    for name in ['suite','sensitivity']: sub.add_parser(name).add_argument('--out',default='results')
    serve=sub.add_parser('serve');serve.add_argument('--port',type=int,default=8765)
    mesh=sub.add_parser('mesh-check',help='Optional mesh extra: finite-radius yarn versus actual STL')
    mesh.add_argument('manifest');mesh.add_argument('config');mesh.add_argument('--tension',type=float,default=.04);mesh.add_argument('--out',default='results/custom_mesh.json')
    sweep=sub.add_parser('mesh-sweep',help='Optional mesh extra: prescribed cord poses, not friction dynamics')
    sweep.add_argument('manifest');sweep.add_argument('poses');sweep.add_argument('--out',default='results/custom_sweep.json')
    snag=sub.add_parser('snag-audit',help='Optional mesh extra: locate geometric snag risks for CAD review')
    snag.add_argument('manifest');snag.add_argument('cases');snag.add_argument('--out',default='results/custom_snags')
    comparison=sub.add_parser('snag-compare',help='Compare CAD revisions checked with identical snag-audit cases')
    comparison.add_argument('baseline');comparison.add_argument('candidate');comparison.add_argument('--out',default='results/custom_snag_comparison.json')
    args=parser.parse_args()
    if args.action=='preset': save(args.out,presets.config(args.stand,args.ball,args.motion,args.setup)); print(args.out)
    elif args.action=='run':
        cfg=json.loads(Path(args.config).read_text(encoding='utf-8-sig'));r=simulate(*from_config(cfg));save(args.out,r)
        print(json.dumps(clean(r['summary']),ensure_ascii=False,indent=2));print('Saved:',args.out)
    elif args.action=='suite': suite(args.out)
    elif args.action=='sensitivity': sensitivity(args.out)
    elif args.action=='serve':
        from .server import serve
        serve(args.port)
    elif args.action=='mesh-check':
        from .mesh import MeshScene,taut_path
        s,b,m,p=from_config(json.loads(Path(args.config).read_text(encoding='utf-8-sig')))
        scene=MeshScene.from_manifest(args.manifest);points,status=taut_path(s,b,p,args.tension)
        result=scene.screen(points,b.yarn_diameter_m/2) if points is not None else {'status':status}
        save(args.out,{'inputs':{'config':json.loads(Path(args.config).read_text(encoding='utf-8-sig')),'tension_N':args.tension},'provenance':scene.provenance,'result':result,'points_m':points.tolist() if points is not None else None})
        print(json.dumps(clean(result),ensure_ascii=False,indent=2))
    elif args.action=='mesh-sweep':
        from .mesh import MeshScene
        scene=MeshScene.from_manifest(args.manifest);data=json.loads(Path(args.poses).read_text(encoding='utf-8-sig'))
        result=scene.sweep(data['poses_m'],data['yarn_radius_m'])
        save(args.out,{'inputs':data,'provenance':scene.provenance,'result':result})
        print(json.dumps(clean({k:v for k,v in result.items() if k!='screens'}),ensure_ascii=False,indent=2))
    elif args.action=='snag-audit':
        from .mesh import MeshScene
        from .snags import audit,write_report
        scene=MeshScene.from_manifest(args.manifest)
        specification=json.loads(Path(args.cases).read_text(encoding='utf-8-sig'))
        report=audit(scene,specification,on_progress=lambda done,total,name:print(f'{done}/{total}: {name}',flush=True));write_report(args.out,report)
        print(json.dumps(report['summary'],ensure_ascii=False,indent=2));print('Report:',Path(args.out)/'report.html')
    elif args.action=='snag-compare':
        from .snags import compare
        report=compare(json.loads(Path(args.baseline).read_text(encoding='utf-8-sig')),json.loads(Path(args.candidate).read_text(encoding='utf-8-sig')))
        save(args.out,report);print(json.dumps(report['summary'],ensure_ascii=False,indent=2))
