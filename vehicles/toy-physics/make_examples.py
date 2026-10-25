"""Rebuild the trike scenario from current meshes and slicer object mass."""
from pathlib import Path
import sys, json, copy, hashlib
import numpy as np
import trimesh
from toyphysics.materials import DEFAULT_SETTINGS

HERE=Path(__file__).resolve().parent
R=Path(sys.argv[1]).resolve()
OUT=HERE/'examples'; OUT.mkdir(exist_ok=True)
def write(name, data):
    (OUT/name).write_text(json.dumps(data, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
D=json.loads((R/'manifest.json').read_text())
metrics=json.loads((R/'checks/print_estimates.json').read_text())
grams={m['project']:m['object_g'] for m in metrics['projects']}
groups=json.loads((R/'plates/layout_manifest.json').read_text())
parts={p['name']:p for p in D['parts']}
masses={}; shape={}; polymer_volumes={}; reference_densities={}
for group in groups:
    name=Path(group['file']).stem
    if name=='00_fit_first': continue
    profile_file=R/'checks/slice_profiles'/('filament_pla.json' if name=='04_clear_canopy' else 'filament.json')
    profile=json.loads(profile_file.read_text(encoding='utf-8'))
    reference_density=float(profile['filament_density'][0])*1000
    raw={}
    for item in group['parts']:
        n=item['part']; m=trimesh.load_mesh(R/'stl'/f'{n}.stl')
        full=name in ['03_printed_fasteners','04_clear_canopy']
        # First-order shell-volume proxy, not a slicer or material measurement.
        fraction=1. if full else .2+.8*min(1., m.area*2.1/m.volume)
        raw[n]=m.volume*fraction
        if n in parts:
            m.apply_transform(parts[n]['print_to_model']);m.apply_transform(D['model_to_ground'])
            xyz=m.center_mass*.001;shape[n]=np.array([-xyz[1],xyz[0],xyz[2]])
    for n,v in raw.items():
        masses[n]=grams[name]*.001*v/sum(raw.values())
        polymer_volumes[n]=masses[n]/reference_density
        reference_densities[n]=reference_density
mass=sum(masses[n] for n in parts)
cg=sum(masses[n]*shape[n] for n in parts)/mass
wheelbase=[]
for name,center,r in [('front',[0,-54.63445,21.11655],21.125),('rear_right',[56.875,55.4177,25.64705],22.425),('rear_left',[-56.875,55.4177,25.64705],22.425)]:
    p=np.array(D['model_to_ground'])@np.r_[center,1.]
    wheelbase.append(dict(name=name,position_m=[-p[1]*.001,p[0]*.001,p[2]*.001],radius_m=r*.001,width_m=.02935,
                         vertical_stiffness_N_m=20000.,tread_contact_fraction=.65,
                         journal_radius_m=.005,journal_friction=.08,
                         axle=dict(diameter_m=.008,span_or_overhang_m=.04 if name=='front' else .018,
                                   support='two_supports_center_load' if name=='front' else 'cantilever')))
vehicle=dict(name='Trike MINI v06',wheels=wheelbase,
             mass_components=[dict(name=n,polymer_volume_m3=polymer_volumes[n],position_m=shape[n].tolist(),
                                   reference_slicer_mass_kg=masses[n],reference_slicer_density_kg_m3=reference_densities[n]) for n in parts],
             provenance=dict(manifest_sha256=hashlib.sha256((R/'manifest.json').read_bytes()).hexdigest(),
                             model_revision=D['revision'],coordinates='x forward = -ground Y; y right = ground X; z up',
                             mass='Polymer volumes inferred from slicer object mass and the recorded filament density (PETG 1270, PLA 1240 kg/m3); key excluded. Selected calculation material determines new masses.',
                             center_of_gravity='Per-plate object masses allocated by min(1, area*2.1mm/volume) shell proxy plus 20% infill; solid fasteners and canopy. Approximate, not measured.',
                             measured_inputs=False,assumed_inputs=['contact fraction','surface elastic modulus','vertical stiffness','journal friction','axle beam idealization'],
                             reference_assembled_mass_kg=mass,reference_cg_m=cg.tolist(),key_estimate_kg=masses['90_printed_key']))
write('vehicle.json',vehicle)
write('material.json',DEFAULT_SETTINGS)
six=copy.deepcopy(vehicle);six['name']='Six-wheel compliance demonstrator';six['mass_kg']=.6;six['cg_m']=[0,0,.05];six.pop('provenance')
six.pop('mass_components')
six['wheels']=[]
for x in [-.08,0,.08]:
    for y in [-.05,.05]:
        w=copy.deepcopy(wheelbase[0]);w['name']=f'wheel_{len(six["wheels"])+1}';w['position_m']=[x,y,.025];w['radius_m']=.025;w.pop('axle');six['wheels'].append(w)
six['wheels'][0]['ground_height_m']=-.001
write('six_wheels.json',six)
surfaces=[]
for name,e,nu,arm,mu in [('Linoleum',2e7,.45,.00015,.35),('Parquet',1e9,.30,.00010,.25),('Tile',5e10,.22,.00005,.20)]:
    surfaces.append(dict(name=name,kind='hard',modulus_Pa=e,poisson=nu,rolling_arm_m=arm,traction_coefficient=mu,parameter_status='Illustrative uncalibrated preset; not a measured material property'))
for name,pile,k,loss in [('Carpet short pile',.003,5e7,.20),('Carpet medium pile',.008,1e7,.30),('Carpet long pile',.018,2e6,.40)]:
    surfaces.append(dict(name=name,kind='carpet',pile_height_m=pile,foundation_Pa_m=k,backing_stiffness_N_m=1e5,
                         hysteresis_fraction=loss,rolling_arm_m=.0002,traction_coefficient=.5,parameter_status='Illustrative uncalibrated preset; backing, fiber and direction must be measured'))
write('surfaces.json',surfaces)
write('loads.json',[dict(name='Own weight',force_N=0),dict(name='Child presses near center',child_mass_kg=15,weight_fraction=.25,position_m=[0,0,.06],contact_area_m2=.0006),
                   dict(name='Off-center press',force_N=35,position_m=[.03,.06,.06])])
base=dict(name='Sealed level box',water_density_kg_m3=998.2,components=[dict(name='Printed box',size_m=[.20,.12,.06],center_m=[0,0,0],wall_m=.002,infill=.20,flooded_void_fraction=0.)])
floating=[base]
tilt=copy.deepcopy(base);tilt['name']='Shifted ballast';tilt['point_masses']=[dict(mass_kg=.08,position_m=[.035,.020,-.020])];floating.append(tilt)
unstable=copy.deepcopy(base);unstable['name']='High center of gravity';unstable['cg_override_m']=[0,0,.08];floating.append(unstable)
flood=copy.deepcopy(base);flood['name']='Flooded pores';flood['components'][0]['flooded_void_fraction']=1.;floating.append(flood)
write('buoyancy.json',floating)
write('events.json',[
 dict(name='Kick, free toy',kind='kick',effective_impact_mass_kg=1.,speed_m_s=1.5,stopping_distance_m=.008,contact_area_m2=.0006,peak_to_mean_factor=2,toy_trapped=False,edge_radius_m=.003),
 dict(name='Kick, trapped toy',kind='kick',effective_impact_mass_kg=1.,speed_m_s=1.5,stopping_distance_m=.008,contact_area_m2=.0006,peak_to_mean_factor=2,toy_trapped=True,edge_radius_m=.003),
 dict(name='Slow step, broad contact',kind='step',adult_mass_kg=75.,weight_fraction=.7,effective_impact_mass_kg=10.,speed_m_s=0.,stopping_distance_m=.004,contact_area_m2=.0012,peak_to_mean_factor=2,edge_radius_m=.006),
 dict(name='Step onto small contact',kind='step',adult_mass_kg=75.,weight_fraction=.7,effective_impact_mass_kg=10.,speed_m_s=.25,stopping_distance_m=.004,contact_area_m2=.00015,peak_to_mean_factor=2,edge_radius_m=.001)])
write('cleaning.json',dict(name='Trike feature inventory — illustrative estimates',brush_diameter_m=.003,brush_reach_m=.015,dirt_grain_diameter_m=.0005,
 layer_height_m=.0002,roughness_reference_m=.0004,retention_reference_m3=1e-6,operations_reference=12,disassembly_operations=16,
 provenance='Manual area/pocket estimates for v06; depths and nominal gaps informed by CAD. No cleaning experiment or automatic mesh extraction.',
 features=[
 dict(name='Open body and wheel surfaces',area_m2=.040,opening_m=.04,depth_m=0.,pocket_volume_m3=0.,drainable_fraction=1.),
 dict(name='Shallow armor panels',area_m2=.005,opening_m=.008,depth_m=.0015,pocket_volume_m3=.6e-6,drainable_fraction=.9),
 dict(name='Bolt wells and hex sockets',area_m2=.0018,opening_m=.004,depth_m=.010,pocket_volume_m3=1.5e-6,drainable_fraction=.4,opens_on_disassembly=True),
 dict(name='Body joint and axle bearing gaps',area_m2=.002,opening_m=.0003,depth_m=.010,pocket_volume_m3=.4e-6,drainable_fraction=.15,opens_on_disassembly=True),
 dict(name='Internal surfaces',area_m2=.014,opening_m=.02,depth_m=.012,pocket_volume_m3=2e-6,drainable_fraction=.8,hidden_until_disassembly=True,opens_on_disassembly=True)]))
print(json.dumps(dict(mass_kg=mass,cg_m=cg.tolist(),key_estimate_kg=masses['90_printed_key']),indent=2))
