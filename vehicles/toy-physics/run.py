"""Generate numerical JSON, comparison figures and a standalone HTML report."""
from pathlib import Path
import argparse, copy, html, json, hashlib, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from toyphysics.rolling import solve, step_force
from toyphysics.buoyancy import Body
from toyphysics.contact_events import event
from toyphysics.cleaning import washability
from toyphysics.materials import PROFILES, merge_settings, resolve_material, prepare_vehicle

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,default=Path(__file__).parent/'examples')
    parser.add_argument('--output',type=Path,default=Path(__file__).parent/'reports')
    parser.add_argument('--material',type=str.upper,choices=sorted(PROFILES),help='PLA by default; overrides material.json')
    parser.add_argument('--density-g-cm3',type=float,help='Actual filament density, e.g. 1.24; does not alter strength')
    parser.add_argument('--print-axis',type=str.upper,choices=['XY','Z'],help='Principal beam stress direction relative to printed layers')
    for name in ['safety-factor','strength-factor','modulus-factor','stress-concentration-factor']:
        parser.add_argument('--'+name,type=float)
    args=parser.parse_args();src=args.inputs;out=args.output;out.mkdir(parents=True,exist_ok=True)
    def read(name):return json.loads((src/name).read_text(encoding='utf-8'))
    settings=read('material.json') if (src/'material.json').exists() else {}
    overrides={k:getattr(args,k) for k in ['material','density_g_cm3','print_axis','safety_factor','strength_factor','modulus_factor','stress_concentration_factor'] if getattr(args,k) is not None}
    settings=merge_settings(settings,overrides)
    try:material=resolve_material(settings)
    except ValueError as error:parser.error(str(error))
    source_vehicle=read('vehicle.json');v=prepare_vehicle(source_vehicle,settings)
    floors=read('surfaces.json');loads=read('loads.json');float_specs=read('buoyancy.json')
    rolling=[]
    for load in loads:
        for floor in floors:
            row=solve(v,floor,load);row['load_name']=load['name']
            if 'pull_force_N' in row:
                estimates=[row['pull_force_N']]
                for multiplier in [.5,2.]:
                    f=copy.deepcopy(floor);vv=copy.deepcopy(v)
                    f['rolling_arm_m']*=multiplier
                    for w in vv['wheels']:w['journal_friction']*=multiplier
                    if f['kind']=='carpet':
                        f['foundation_Pa_m']/=multiplier
                        f['hysteresis_fraction']=min(1.,f['hysteresis_fraction']*multiplier)
                    estimates.append(solve(vv,f,load)['pull_force_N'])
                row['illustrative_parameter_sweep_force_N']=[min(estimates),max(estimates)]
                row['sweep_note']='Half/double loss parameters; carpet stiffness varied inversely. Not a statistical confidence interval.'
            rolling.append(row)
    floats=[Body(s,src,settings).solve() for s in float_specs]
    sweep=[]
    for fill in np.linspace(0,1,21):
        s=copy.deepcopy(float_specs[0]);s['components'][0]['infill']=float(fill)
        r=Body(s,src,settings).solve();eq=r.get('equilibrium')
        sweep.append(dict(infill=float(fill),mass_kg=r['mass_kg'],status=r['status'],
                          heave_m=eq['heave_m'] if eq else None,
                          stable=r.get('locally_stable'),minimum_GM_m=min(r['equivalent_GM_eigenvalues_m']) if eq else None))
    events=[event(s,v['mass_kg']) for s in read('events.json')]
    cleaning=[washability(read('cleaning.json'),state) for state in [False,True]]
    six=solve(prepare_vehicle(read('six_wheels.json'),settings),floors[min(2,len(floors)-1)])
    comparison=[]
    for name in PROFILES:
        # Reference comparison uses the same factors, without global property overrides.
        cs={k:settings[k] for k in ['print_axis','safety_factor','strength_factor','modulus_factor','stress_concentration_factor']}
        cs['material']=name;cv=prepare_vehicle(source_vehicle,cs)
        checks=[dict(load_name=load['name'],**solve(cv,floors[0],load)) for load in loads]
        comparison.append(dict(profile=resolve_material(cs),vehicle_mass_kg=cv['mass_kg'],cg_m=cv['cg_m'],
                               axle_checks=checks,buoyancy=[Body(s,src,cs).solve() for s in float_specs]))
    own=solve(v,floors[0]);steps=[]
    for wheel,row in zip(v['wheels'],own.get('wheels',[])):
        steps.append(dict(wheel=wheel['name'],steps=[dict(height_m=h,**step_force(row['normal_force_N'],wheel['radius_m'],h)) for h in [0,.001,.003,.005,.01,.025]]))
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(src.glob('*.json'))}
    data=dict(vehicle=v['name'],mass_kg=v['mass_kg'],cg_m=v['cg_m'],input_sha256=hashes,
              material_settings=settings,selected_material=material,material_resolution=v['material_resolution'],
              material_comparison=comparison,resolved_vehicle=v,
              material_model_sha256=hashlib.sha256((Path(__file__).parent/'toyphysics/materials.py').read_bytes()).hexdigest(),
              rolling=rolling,six_wheel_example=six,rigid_step_examples=steps,
              buoyancy=floats,infill_sweep=sweep,parent_contact=events,cleaning=cleaning,
              evidence_status='Analytical/numerical checks only. Floor, event and cleaning parameters are illustrative; no physical calibration.')
    (out/'results.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','svg.hashsalt':'toy-physics'})
    def save(fig,name):
        fig.savefig(out/f'{name}.png',dpi=160,bbox_inches='tight')
        svg=out/f'{name}.svg'
        fig.savefig(svg,bbox_inches='tight',metadata={'Date':None});plt.close(fig)
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n')
    fig,ax=plt.subplots(figsize=(10,4.6));x=np.arange(len(floors))
    for j,load in enumerate(loads[:2]):
        rows=[r for r in rolling if r['load_name']==load['name']]
        values=np.array([r.get('pull_force_N',np.nan) for r in rows]);bounds=np.array([r.get('illustrative_parameter_sweep_force_N',[np.nan,np.nan]) for r in rows])
        ax.bar(x+(j-.5)*.34,values,.32,label=load['name'],color=['#397b8b','#cb8846'][j])
        ax.errorbar(x+(j-.5)*.34,values,yerr=[values-bounds[:,0],bounds[:,1]-values],fmt='none',color='#333333',capsize=3)
    ax.set_xticks(x,[s['name'].replace('Carpet ','Carpet\n') for s in floors]);ax.set_ylabel('Estimated pull force (N)')
    if any(r.get('pull_force_N',0)>0 for r in rolling):ax.set_yscale('log')
    ax.legend()
    ax.set_title('Illustrative floor comparison — bars are model outputs, whiskers are parameter sweeps')
    save(fig,'rolling')
    fig,axs=plt.subplots(1,2,figsize=(10,4.4))
    axs[0].plot([s['infill']*100 for s in sweep],[s['mass_kg']*1000 for s in sweep],color='#397b8b')
    axs[0].axhline(floats[0]['maximum_supported_mass_kg']*1000,ls='--',color='#b55545',label='Maximum supported mass')
    axs[0].set(xlabel='Infill (%)',ylabel='Mass (g)',title='Sealed example box');axs[0].legend()
    valid=[s for s in sweep if s['minimum_GM_m'] is not None]
    axs[1].plot([s['infill']*100 for s in valid],[s['minimum_GM_m']*1000 for s in valid],marker='o',color='#397b8b')
    axs[1].axhline(0,color='#b55545',ls='--');axs[1].set(xlabel='Infill (%)',ylabel='Minimum equivalent GM (mm)',title='Initial restoring stability near level')
    fig.suptitle('Separate buoyancy example; this is not a flotation claim for the trike');fig.tight_layout();save(fig,'buoyancy')
    fig,ax=plt.subplots(figsize=(9,4.5));names=[r['name'].replace(', ','\n') for r in events]
    ax.bar(names,[r['mean_contact_pressure_Pa']/1e6 for r in events],color=['#397b8b','#5297a8','#b78c57','#cb8846'])
    ax.set(ylabel='Estimated force / assumed contact area (MPa)',title='Parent contact scenarios — mechanical comparison, not a pain scale')
    save(fig,'contact_events')
    def table(head,rows):
        return '<table><thead><tr>'+''.join('<th>'+html.escape(str(c))+'</th>' for c in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(c))+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table>'
    def doc_link(name,label):
        target=Path(__file__).resolve().parent/name
        try:url=Path(os.path.relpath(target,out.resolve())).as_posix()
        except ValueError:url=target.as_uri()
        return '<a href="'+html.escape(url,quote=True)+'">'+html.escape(label)+'</a>'
    sections=[]
    sections.append('<p class="lead">A reusable N-wheel model, with a separate hydrostatics module. Vehicle: '+html.escape(v['name'])+'. Input provenance is recorded in the vehicle JSON.</p>')
    sections.append(f'<div class="note">Estimated assembled mass: {v["mass_kg"]*1000:.1f} g. Approximate CG: {np.round(np.array(v["cg_m"])*1000,2).tolist()} mm (x forward, y right, z up). All floor presets, parent contact inputs and cleaning inventory require calibration. No physical strength or toy-safety approval is implied.</div>')
    sections.append('<h2>Material settings</h2><p>PLA is the default. Change material.json or use <code>python run.py --material PETG --output reports/petg</code>. Use <code>--density-g-cm3 1.25</code> for a measured or manufacturer-specified density. Full inputs and resolved properties are stored in results.json.</p>')
    sections.append(table(['Selected material','Density (g/cm³)','Print axis','Strength factor','Modulus factor','Safety factor','Stress concentration'],[[material['material'],material['density_g_cm3'],material['print_axis'],material['strength_factor'],material['modulus_factor'],material['safety_factor'],material['stress_concentration_factor']]]))
    sections.append('<p>Reference products: Bambu PLA Basic and PETG HF. Coupon data do not establish the strength of this print. The factors above are editable assumptions. See '+doc_link('MATERIALS.md','properties, sources and override rules')+'. Density changes mass and buoyancy; it does not directly determine strength. '+html.escape(v['material_resolution']['mass_basis'])+'.</p>')
    rows=[]
    for c in comparison:
        b=c['buoyancy'][0]
        checks=[a['utilization'] for r in c['axle_checks'] for w in r.get('wheels',[]) if (a:=w.get('axle')) and 'utilization' in a]
        rows.append([c['profile']['material'],c['profile']['density_g_cm3'],f'{c["vehicle_mass_kg"]*1000:.1f}',f'{max(checks):.3f}' if checks else '—',f'{b["mass_kg"]*1000:.1f}',f'{b["reserve_buoyancy_kg"]*1000:.1f}',b['status'],b.get('locally_stable','—')])
    sections.append('<h3>PLA / PETG reference comparison</h3><p>Same geometry and factors; global density/modulus/strength overrides excluded. Explicit per-part properties and fixed masses still apply. Axle utilization covers the supplied loads on '+html.escape(floors[0]['name'])+'; tipping cases have no supported axle result. Buoyancy refers to the separate first floating example.</p>')
    sections.append(table(['Material','Density (g/cm³)','Toy mass (g)','Max axle utilization','Floating example mass (g)','Buoyancy reserve (g)','Float status','Locally stable'],rows))
    sections.append('<h2>Wheel loads, pressure and rolling</h2><img src="rolling.png" alt="Floor resistance comparison">')
    rows=[]
    for r in rolling:
        rows.append([r['load_name'],r['surface'],r['status'],f'{r["pull_force_N"]:.3f}' if 'pull_force_N' in r else '—',
                     ' / '.join(f'{w["normal_force_N"]:.2f}' for w in r.get('wheels',[])) or '—',
                     f'{max(w["mean_pressure_Pa"] for w in r["wheels"])/1e6:.4f}' if 'wheels' in r else '—'])
    sections.append(table(['Load','Floor','Support','Pull (N)','Wheel reactions (N)','Largest mean patch pressure (MPa)'],rows))
    sections.append(table(['Applied load','Downward force (N)','Mean pressure at specified load area (kPa)'],[[r['load_name'],f'{r["child_force_N"]:.2f}',f'{r["applied_load_mean_pressure_Pa"]/1000:.2f}' if 'applied_load_mean_pressure_Pa' in r else 'Area not specified'] for r in rolling[::len(floors)]]))
    sections.append('<p>Off-center load can tip the toy; failed equilibrium is reported instead of negative wheel reactions. The contact area of the applied load is an input, not a calculated hand or shell deformation.</p>')
    rows=[]
    for r in rolling[::len(floors)]:
        for w in r.get('wheels',[]):
            a=w.get('axle')
            if a and 'utilization' in a:
                rows.append([r['load_name'],w['name'],f'{a["local_stress_Pa"]/1e6:.2f}',f'{a["allowable_stress_Pa"]/1e6:.2f}',f'{a["utilization"]:.3f}',f'{a["deflection_m"]*1000:.3f}',a['screen_status']])
    sections.append('<h3>Local axle bending screen</h3><p>For '+html.escape(floors[0]['name'])+'. Utilization ≤ 1 means the calculated local bending stress is within the assumed allowable. Allowable = reference tensile strength × strength factor / safety factor. Local stress = nominal bending stress × stress concentration factor. This checks solid circular beam sections only; it does not verify the chassis, retainers, threads, bearing crushing, creep, fatigue or impacts. Infill percentage is not a strength multiplier.</p>')
    sections.append(table(['Load','Axle','Local stress (MPa)','Assumed allowable (MPa)','Utilization','Deflection (mm)','Screen result'],rows))
    sections.append('<h3>Six wheels on unequal ground</h3>'+table(['Wheel','Normal load (N)','Unloaded'],[[w['name'],f'{w["normal_force_N"]:.3f}',w['unloaded']] for w in six.get('wheels',[])]))
    sections.append('<p>The first wheel is over a 1 mm depression. Compliance resolves the otherwise indeterminate load sharing. Rigid-step force estimates are included in the JSON; carpet pile is not treated as a hard step.</p>')
    sections.append('<h2>Buoyancy, infill and keeping level</h2><img src="buoyancy.png" alt="Infill and initial stability">')
    sections.append(table(['Example','Mass (g)','Status','Roll / pitch (deg)','Level','Locally stable'],[
        [r['name'],f'{r["mass_kg"]*1000:.1f}',r['status'],f'{r["equilibrium"]["roll_deg"]:.2f} / {r["equilibrium"]["pitch_deg"]:.2f}' if r.get('equilibrium') else '—',r.get('holds_level','—'),r.get('locally_stable','—')] for r in floats]))
    sections.append('<p>Being level is different from being stable. A high CG can produce an upright but unstable equilibrium. Sealed air contributes displacement; flooded pores do not. This model finds a local equilibrium near upright, within ±70°. It does not predict leakage, waves or every possible capsized pose.</p>')
    sections.append('<h2>Parent contact scenarios</h2><img src="contact_events.png" alt="Contact pressure proxies">')
    sections.append(table(['Event','Relative energy (J)','Force estimate (N)','Assumed area (mm²)','Force/area (MPa)'],[[r['name'],f'{r["available_relative_energy_J"]:.3f}',f'{r["estimated_peak_force_N"]:.1f}',f'{r["contact_area_m2"]*1e6:.0f}',f'{r["mean_contact_pressure_Pa"]/1e6:.3f}'] for r in events]))
    sections.append('<p>Pain has no computed score here. Stopping distance, contact area, footwear and whether the toy can move change the mechanical result. The model does not calculate tissue injury or toy breakage.</p>')
    sections.append('<h2>Washability</h2>'+table(['State','Heuristic index /100','Brush-accessible area','Modeled retained liquid (mL)','Disassembly operations'],[[r['state'],f'{r["washability_index_0_100"]:.1f}',f'{r["brush_accessible_area_fraction"]*100:.1f}%',f'{r["modeled_retained_liquid_m3"]*1e6:.2f}',r['operations']] for r in cleaning]))
    sections.append('<p>The index combines brush access, estimated drainage, layer-height roughness proxy and disassembly effort. Inputs are a manual feature inventory. Changing weights changes the score; it is not a hygiene rating or predicted washing time.</p>')
    sections.append('<h2>Reproduce and calibrate</h2><p>See '+doc_link('README.md','README')+', '+doc_link('MODEL.md','equations and limitations')+', '+doc_link('CALIBRATION.md','measurement protocol')+', and <a href="results.json">full results with input hashes</a>.</p>')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Toy vehicle physics</title><style>body{max-width:1160px;margin:36px auto;padding:0 24px;background:#f6f4ef;color:#24313b;font:16px/1.55 system-ui}h1{font-size:38px}h2{margin-top:48px}img{display:block;max-width:100%;height:auto;background:white;margin:22px 0}table{border-collapse:collapse;background:white;font-size:14px;width:100%;margin:18px 0}td,th{padding:10px;text-align:left;border-bottom:1px solid #d8dedf}th{background:#e4edef}.note{padding:18px;border-left:4px solid #cb8846;background:#fff9ed}.lead{font-size:19px}a{color:#24667c}@media(max-width:650px){table{display:block;overflow:auto}body{padding:0 12px}}</style><body><h1>Toy vehicle physics</h1>'+''.join(sections)+'</body></html>'
    (out/'report.html').write_text(page,encoding='utf-8',newline='\n')
    print(json.dumps(dict(output=str(out.resolve()),material=material['material'],density_g_cm3=material['density_g_cm3'],rolling_cases=len(rolling),buoyancy_cases=len(floats),six_wheels=six['status'],mass_kg=v['mass_kg']),indent=2))

if __name__=='__main__':main()
