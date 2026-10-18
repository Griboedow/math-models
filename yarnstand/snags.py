"""Conservative CAD review of prescribed cord motion, including rotating parts.

Contact is a geometric snag risk, not proof of frictional locking. The report
locates obstacles in both assembly and original STL coordinates for CAD edits.
"""
from collections import Counter
from pathlib import Path
import hashlib
import html
import json
import math
import platform

import numpy as np
import vtk
import trimesh

from .mesh import MeshScene, MAX_PATH_SAMPLES, MAX_SWEEP_POINTS, _subdivisions

SEVERITY={'clear_with_allowance':0,'unresolved_clearance':1,
          'allowance_contact':2,'nominal_contact':3,'initial_nominal_contact':4}


def _number(value, name, positive=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 or (positive and value==0):
        raise ValueError(f'{name} must be finite and {"positive" if positive else "nonnegative"}')
    return float(value)


def _rotate(points, angle_deg, origin):
    angle=math.radians(angle_deg);c,s=math.cos(angle),math.sin(angle)
    rotation=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
    return (np.asarray(points)-origin)@rotation.T+origin


def _frames(poses, angles, origin, motion_step):
    """Exact relative poses; bounds include travel on the rotation arc.

    World nodes and angle interpolate linearly within each input interval.
    ||dq/df|| <= ||dp/df|| + |dtheta/df| * max(radius), even for a full turn.
    """
    counts=[];bounds=[]
    for a,b,aa,bb in zip(poses,poses[1:],angles,angles[1:]):
        radial=max(np.linalg.norm((a-origin)[:,:2],axis=1).max(),np.linalg.norm((b-origin)[:,:2],axis=1).max())
        travel=float(np.linalg.norm(b-a,axis=1).max()+abs(math.radians(bb-aa))*radial)
        count=_subdivisions(travel,motion_step,MAX_SWEEP_POINTS//poses.shape[1]-sum(counts)-1)
        counts.append(count);bounds.append(travel/count)
    margin=max(bounds,default=0.)/2
    yield _rotate(poses[0],-angles[0],origin),0.,float(angles[0]),margin
    for i,count in enumerate(counts):
        for j in range(1,count+1):
            fraction=j/count;angle=angles[i]+fraction*(angles[i+1]-angles[i])
            points=poses[i]+fraction*(poses[i+1]-poses[i])
            yield _rotate(points,-angle,origin),i+fraction,float(angle),margin


def _site(scene, part, points, screen, angle, origin):
    query=np.asarray(screen['worst_point_m'])
    # Thin walls may be crossed entirely between distance samples. Use an
    # actual hit for localization in that case, never an unrelated endpoint.
    if screen['centerline_crossings'] and screen['min_sampled_clearance_m']>0:
        hit=None
        for _,_,tree,_,_ in part.parts:
            for a,b in zip(points,points[1:]):
                p=[0.,0.,0.]
                if tree.IntersectWithLine(a,b,1e-9,vtk.mutable(0.),p,[0.,0.,0.],vtk.mutable(0)):
                    hit=np.array(p);break
            if hit is not None:break
        if hit is not None:query=hit
    nearest=None
    for name,field,_,_,_ in part.parts:
        surface=[0.,0.,0.];distance=field.EvaluateFunctionAndGetClosestPoint(query,surface)
        if nearest is None or distance<nearest[0]:nearest=(distance,surface,field)
    _,surface,field=nearest
    normal=[0.,0.,0.];field.EvaluateGradient(surface,normal)
    norm=np.linalg.norm(normal)
    if norm:normal=(np.asarray(normal)/norm).tolist()
    result={'surface_reference_assembly_m':list(surface),
            'surface_world_m':_rotate(surface,angle,origin).tolist(),
            'cord_world_m':_rotate(query,angle,origin).tolist(),
            'outward_normal_reference':normal}
    sources=[s for s in scene.provenance.get('sources',[]) if s['name']==name]
    unit=scene.provenance.get('input_unit')
    if len(sources)==1 and unit in ('mm','m'):
        scale=.001 if unit=='mm' else 1.
        source=np.linalg.solve(np.asarray(sources[0]['transform']),np.r_[np.asarray(surface)/scale,1.])
        result.update(source_file=sources[0]['file'],surface_source_coordinates=source[:3].tolist(),source_unit=unit)
    return result


def audit(scene, specification):
    """Evaluate every case/part, retaining the worst site and first contacts.

    Allowances are radial, additive worst-case geometric envelopes, not measured
    probabilities or a model of individual fibres. No unseen path is certified.
    """
    allowed={'cases','allowances_m','sampling_step_m','motion_step_m','description'}
    if set(specification)-allowed:raise ValueError('Unknown audit settings')
    allowances=specification.get('allowances_m',{})
    if set(allowances)-{'print','fuzz','mesh','reserve'}:raise ValueError('Unknown allowance')
    allowances={k:_number(allowances.get(k,0),k) for k in ('print','fuzz','mesh','reserve')}
    allowance=sum(allowances.values())
    step=_number(specification.get('sampling_step_m',.00025),'sampling_step_m',True)
    motion_step=_number(specification.get('motion_step_m',.00025),'motion_step_m',True)
    cases=specification.get('cases')
    if not isinstance(cases,list) or not 1<=len(cases)<=5000:raise ValueError('Provide 1 to 5000 cases')
    names=sorted({p[0] for p in scene.parts});parts={}
    for name in names:
        part=object.__new__(MeshScene);part.parts=[p for p in scene.parts if p[0]==name];part.provenance=scene.provenance
        parts[name]=part
    seen=set();results=[];total_samples=0
    for case in cases:
        if set(case)-{'id','description','yarn_radius_m','poses_m','part_rotation_deg','rotation_origin_m'}:raise ValueError('Unknown case fields')
        case_id=case.get('id')
        if not isinstance(case_id,str) or not case_id or case_id in seen:raise ValueError('Case IDs must be unique nonempty strings')
        seen.add(case_id)
        radius=_number(case.get('yarn_radius_m'),'yarn_radius_m',True)
        poses=np.asarray(case.get('poses_m'),dtype=float)
        if poses.ndim!=3 or poses.shape[2]!=3 or poses.shape[0]<1 or poses.shape[1]<2 or not np.isfinite(poses).all():raise ValueError('Cases need finite poses with corresponding nodes in metres')
        if poses.size//3>MAX_SWEEP_POINTS or poses.shape[1]>MAX_PATH_SAMPLES:raise ValueError('Too many pose nodes')
        rotations=case.get('part_rotation_deg',{})
        if not isinstance(rotations,dict) or set(rotations)-set(names):raise ValueError('Rotation names must match scene parts')
        origin=np.asarray(case.get('rotation_origin_m',[0,0,0]),dtype=float)
        if origin.shape!=(3,) or not np.isfinite(origin).all():raise ValueError('Finite rotation origin required')
        rows=[]
        for name,part in parts.items():
            angles=np.asarray(rotations.get(name,[0.]*len(poses)),dtype=float)
            if angles.shape!=(len(poses),) or not np.isfinite(angles).all():raise ValueError('One finite rotation angle per pose required')
            row={'part':name,'status':'clear_with_allowance','first_nominal_contact_pose':None,
                 'first_allowance_contact_pose':None,'minimum_sampled_nominal_clearance_m':math.inf,
                 'clearance_lower_bound_with_allowance_m':math.inf,'checked_frames':0}
            best=math.inf;site_pose=None
            for points,progress,angle,motion_margin in _frames(poses,angles,origin,motion_step):
                r=part.screen(points,radius+allowance,max_step_m=step)
                row['checked_frames']+=1;total_samples+=r['sample_count']
                nominal=r['min_sampled_clearance_m']+allowance
                nominal_contact=nominal<=0 or bool(r['centerline_crossings'])
                allowance_contact=r['status']=='contact'
                lower=r['clearance_lower_bound_m']-motion_margin
                if r['centerline_crossings']:lower=min(lower,-radius-allowance)
                row['minimum_sampled_nominal_clearance_m']=min(row['minimum_sampled_nominal_clearance_m'],nominal)
                row['clearance_lower_bound_with_allowance_m']=min(row['clearance_lower_bound_with_allowance_m'],lower)
                if nominal_contact and row['first_nominal_contact_pose'] is None:
                    row['first_nominal_contact_pose']=progress
                    row['first_nominal_contact_site']=_site(scene,part,points,r,angle,origin)
                if allowance_contact and row['first_allowance_contact_pose'] is None:row['first_allowance_contact_pose']=progress
                if lower<best:
                    best=lower;row['site']=_site(scene,part,points,r,angle,origin)
                    row['site'].update(pose_coordinate=progress,part_angle_deg=angle)
                    # Matching nodes are preserved for viewing the checked pose.
                    site_pose=_rotate(points,angle,origin).tolist()
            if row['first_nominal_contact_pose'] is not None:
                row['status']='initial_nominal_contact' if row['first_nominal_contact_pose']==0 else 'nominal_contact'
            elif row['first_allowance_contact_pose'] is not None:row['status']='allowance_contact'
            elif row['clearance_lower_bound_with_allowance_m']<=0:row['status']='unresolved_clearance'
            row['clearance_deficit_bound_m']=max(0.,-row['clearance_lower_bound_with_allowance_m'])
            if row['status']!='clear_with_allowance':row['site']['cord_pose_world_m']=site_pose
            rows.append(row)
        results.append({'id':case_id,'yarn_radius_m':radius,'status':max((r['status'] for r in rows),key=SEVERITY.get),'parts':rows})
    source_hashes={n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in ('snags.py','mesh.py')}
    return {'schema_version':1,'scope':'prescribed geometry and conservative clearance envelopes; no frictional locking or release force',
            'allowances_m':allowances,'effective_radial_allowance_m':allowance,
            'sampling_step_m':step,'motion_step_m':motion_step,
            'summary':{'cases':len(results),'case_statuses':dict(Counter(r['status'] for r in results)),
                       'part_statuses':dict(Counter(p['status'] for r in results for p in r['parts'])),'distance_samples':total_samples},
            'provenance':scene.provenance,'source_sha256':source_hashes,
            'runtime':{'python':platform.python_version(),'vtk':vtk.vtkVersion.GetVTKVersion(),'numpy':np.__version__,'trimesh':trimesh.__version__},
            'inputs':specification,'cases':results}


def write_report(path, report):
    """Self-contained HTML plus machine-readable JSON for repeated CAD reviews."""
    path=Path(path);path.mkdir(parents=True,exist_ok=True)
    (path/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    labels={'clear_with_allowance':'Свободно с заданным запасом','unresolved_clearance':'Зазор не разрешён точностью',
            'allowance_contact':'Не хватает запаса','nominal_contact':'Контакт на пути','initial_nominal_contact':'Контакт в начальной позе'}
    rows=[]
    for case in report['cases']:
        for part in sorted(case['parts'],key=lambda p:SEVERITY[p['status']],reverse=True):
            if part['status']=='clear_with_allowance':continue
            site=part['site'];p=site.get('surface_source_coordinates',np.asarray(site['surface_reference_assembly_m'])*1000)
            unit=site.get('source_unit','mm');coords=', '.join(f'{v:.3f}' for v in p)
            rows.append(f'<tr><td>{html.escape(case["id"])}</td><td>{html.escape(part["part"])}</td><td>{labels[part["status"]]}</td>'
                        f'<td>{coords} {unit}</td><td>{1000*part["clearance_lower_bound_with_allowance_m"]:.3f}</td>'
                        f'<td>{1000*part["clearance_deficit_bound_m"]:.3f}</td></tr>')
    body=''.join(rows) or '<tr><td colspan="6">Проверенные пути свободны с заданным запасом.</td></tr>'
    summary=html.escape(json.dumps(report['summary']['case_statuses'],ensure_ascii=False))
    allowance=1000*report['effective_radial_allowance_m']
    document=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Проверка зон зацепа перед печатью</title>
<style>body{{font:16px system-ui;max-width:1400px;margin:40px auto;padding:0 24px;color:#182d30;background:#f5f6f2}}h1{{font-size:30px}}p{{max-width:1000px;line-height:1.55}}table{{border-collapse:collapse;background:white;width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ddd}}th{{background:#dce7e1}}td{{font-size:14px}}code{{overflow-wrap:anywhere}}</style>
<h1>Зоны риска зацепа: проверка CAD</h1><p>Проверено сценариев: {report['summary']['cases']}. Добавочный радиальный запас: {allowance:.3f} мм.
Отрицательная граница зазора требует проверки или изменения геометрии. «Контакт» означает препятствие на заданном пути, а не доказанное удержание нити.</p>
<p>Координаты указаны в системе исходного STL, когда она известна; иначе — в системе сборки, мм. Дефицит — запас зазора для проверенного движения, <b>не глубина срезания материала</b>.
После правки повторите те же сценарии. Результат «свободно» относится только к этим движениям и заданным допускам.</p>
<p>Сводка: <code>{summary}</code>. Полные параметры, координаты, позы и хеши: <a href="audit.json">audit.json</a>.</p>
<table><thead><tr><th>Сценарий</th><th>Деталь</th><th>Результат</th><th>XYZ поверхности STL</th><th>Нижняя граница зазора, мм</th><th>Дефицит, мм</th></tr></thead><tbody>{body}</tbody></table>
<p>Трение, сжатие и изгиб пряжи, самоконтакт, заусенцы и усилие освобождения не рассчитываются. Ворс и печать учтены только заданным геометрическим запасом.
Петли задаются пользователем; самопроизвольное образование и затягивание петель не предсказывается.</p></html>'''
    (path/'report.html').write_text(document,encoding='utf-8')
    # Visual CAD overlays in each original STL's coordinates, always in mm.
    # These spheres locate review zones; they are not replacement print parts.
    markers={}
    for case in report['cases']:
        for part in case['parts']:
            if part['status']=='clear_with_allowance':continue
            site=part.get('first_nominal_contact_site',part['site'])
            if 'surface_source_coordinates' not in site:continue
            p=np.asarray(site['surface_source_coordinates'])*(1000 if site['source_unit']=='m' else 1)
            group=markers.setdefault(part['part'],[])
            if all(np.linalg.norm(p-q)>1. for q in group):group.append(p)
    index=[]
    for i,(name,points) in enumerate(sorted(markers.items())):
        spheres=[]
        for p in points:
            sphere=trimesh.creation.icosphere(subdivisions=1,radius=.8);sphere.apply_translation(p);spheres.append(sphere)
        filename=f'review_markers_part_{i+1}.stl'
        trimesh.util.concatenate(spheres).export(path/filename)
        index.append({'part':name,'file':filename,'unit':'mm','coordinates':'original STL','zone_count':len(points)})
    (path/'review_markers.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')


def compare(baseline,candidate):
    """Only compare geometry revisions against exactly the same test inputs."""
    if baseline.get('schema_version')!=candidate.get('schema_version'):raise ValueError('Report schema versions differ')
    if baseline['inputs']!=candidate['inputs']:raise ValueError('Repeat exactly the same cases, allowances and sampling before comparing CAD')
    rows=[]
    before={r['id']:r for r in baseline['cases']}
    for case in candidate['cases']:
        previous=before[case['id']]
        rows.append({'case':case['id'],'before':previous['status'],'after':case['status'],
                     'risk_rank_change':SEVERITY[case['status']]-SEVERITY[previous['status']]})
    return {'scope':candidate['scope'],'cases':rows,
            'summary':{'improved':sum(r['risk_rank_change']<0 for r in rows),
                       'worsened':sum(r['risk_rank_change']>0 for r in rows),
                       'remaining_flagged':sum(r['after']!='clear_with_allowance' for r in rows)},
            'baseline_provenance':baseline['provenance'],'candidate_provenance':candidate['provenance'],
            'same_runtime':baseline['runtime']==candidate['runtime'],
            'same_audit_code':baseline['source_sha256']==candidate['source_sha256']}
