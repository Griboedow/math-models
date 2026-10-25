"""Check saved PITAYA STEP parts against the unchanged v09 mechanism (CadQuery).
Usage: python tools/check_pitaya_cad.py PITAYA_v10 PITAYA_v09 --out report.json
No CAD files are overwritten. This checks fit, not printed material strength.
"""
from pathlib import Path
import argparse,hashlib,json,math,time
import cadquery as cq

p=argparse.ArgumentParser(description=__doc__);p.add_argument('current',type=Path);p.add_argument('previous',type=Path);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();t=time.monotonic()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return cq.importers.importStep(str(path)).val()
def surface_distance(x,y):
    # Compare all boundary shells after checking intersection volumes. The
    # solid-distance shortcut may report a spurious containment at a STEP
    # spline seam (OCCT 7.9); it must not replace the boundary measurement.
    return min(s.distance(t) for s in x.Shells() for t in y.Shells())
body=load(a.current/'cad/body_preview.step');leaf=load(a.current/'cad/leaf_preview.step')
old=load(a.previous/'cad/PITAYA_v09_assembly.step').Solids()
if len(old)!=49: raise ValueError('Unexpected v09 assembly structure; do not guess part indices')
platter,post,collar,spacer,washer,bolt,nut=[old[i] for i in [1,23,30,31,32,41,42]]
assert abs(post.BoundingBox().zlen-139)<.1 and abs(platter.Center().z-39.52)<.1
unchanged={}
for name in ['platter','post','seeds','collar','spacer','washer','bearing_lower','bearing_upper','bolt_M8x45','nut_M8_nyloc','pads']:
    current=a.current/'cad'/f'{name}.stl';previous=a.previous/'cad'/f'{name}.stl'
    unchanged[name]={'unchanged':digest(current)==digest(previous),'sha256':digest(current)}
if not all(x['unchanged'] for x in unchanged.values()):raise ValueError('An assumed unchanged mechanism mesh was modified')
checks={}
for label,x,y in [('body_platter',body,platter),('body_post',body,post),('body_bolt',body,bolt),
                   ('body_collar',body,collar),('body_spacer',body,spacer),('platter_post',platter,post),
                   ('post_bolt',post,bolt),('post_nut',post,nut)]:
    checks[label]=x.intersect(y).Volume()
rotor_envelope=cq.Solid.makeCylinder(52,7.5,cq.Vector(0,0,37))
checks['body_rotor_envelope']=body.intersect(rotor_envelope).Volume()
leaf_seated={}
for angle in [30,90,150,210,270,330]:
    placed=leaf.rotate((0,0,0),(0,0,1),angle)
    leaf_seated[str(angle)]={'body_intersection_mm3':body.intersect(placed).Volume(),
                             'platter_intersection_mm3':platter.intersect(placed).Volume()}
insertion=[]
normal=(math.sin(math.radians(55)),0,math.cos(math.radians(55)))
for offset in [0,.5,1.5,3,6,9]:
    placed=leaf.translate(tuple(offset*v for v in normal)).rotate((0,0,0),(0,0,1),30)
    insertion.append({'offset_mm':offset,'intersection_mm3':body.intersect(placed).Volume()})
report={'scope':'Saved STEP geometry and assembly fit; no FEA or physical print validation',
 'native_source_hashes':{n:digest(a.current/'cad'/n) for n in ['body_preview.step','leaf_preview.step']},
 'body_valid':body.isValid(),'leaf_valid':leaf.isValid(),'body_solids':len(body.Solids()),'leaf_solids':len(leaf.Solids()),
 'unchanged_mechanism_meshes':unchanged,'intersection_volumes_mm3':checks,
 'six_leaf_positions':leaf_seated,'leaf_insertion':insertion,
 'body_to_platter_min_distance_mm':body.distance(platter),
 'leaf_to_body_min_distance_mm':surface_distance(body,leaf.rotate((0,0,0),(0,0,1),30)),
 'leaf_to_body_raw_solid_distance_mm':body.distance(leaf.rotate((0,0,0),(0,0,1),30)),
 'clearance_method':'Minimum distance between all boundary shells; solid non-overlap checked separately by Boolean intersection. Raw solid-distance containment shortcut retained for diagnostics.',
 'leaf_floor_clearance_mm':leaf.BoundingBox().zmin+1,
 'elapsed_s':time.monotonic()-t,'physically_printed':False}
values=list(checks.values())+[x[k] for x in leaf_seated.values() for k in x]+[x['intersection_mm3'] for x in insertion]
report['pass']=all(x<.0001 for x in values) and report['body_valid'] and report['leaf_valid'] and report['leaf_solids']==1 and report['body_solids']==1
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['native_source_hashes','unchanged_mechanism_meshes','six_leaf_positions','leaf_insertion']},indent=2),flush=True)
if not report['pass']:raise SystemExit(1)
