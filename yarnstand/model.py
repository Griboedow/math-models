"""One rotational DOF with unilateral compliant yarn and dry bearing friction.

This is a comparative prototype model, not a measurement of hand comfort.
Ball and platter are assumed coupled; an explicit traction check marks when
that assumption fails. No subsequent slipping/tipping trajectory is predicted.
"""
from dataclasses import dataclass, asdict, fields
import math

G = 9.80665


@dataclass
class Stand:
    name: str = 'PITAYA v08 estimate'
    mass_kg: float = .230  # complete stand incl. hardware, excluding yarn
    rotor_inertia_kg_m2: float = .000065  # platform + post, estimate
    com_height_m: float = .031
    platform_height_m: float = .045  # table surface, includes feet
    platform_radius_m: float = .052
    support_radius_m: float = .052  # pad CENTRES, not cosmetic body radius
    pad_radius_m: float = .005
    pad_count: int = 6
    pad_angle_deg: float = 30.
    support_points_m: list | None = None  # optional actual convex footprint
    foot_friction: float = .45
    start_torque_Nm: float = .0006  # TOTAL measured torque of assembled unit
    running_torque_Nm: float = .0003
    viscous_Nm_s: float = .000015
    body_profile_m: list | None = None  # [radius, upper surface z] from rim out
    leaves: list | None = None  # [radius,z,angle_deg,radial_half,tangent_half,z_half]


@dataclass
class Ball:
    name: str = 'Full round ball 100 g'
    mass_kg: float = .100
    radius_x_m: float = .045
    radius_y_m: float = .045
    radius_z_m: float = .044
    unwind_radius_ratio: float = .85
    exit_height_fraction: float = 0.  # -1 bottom, +1 top of ellipsoid
    inertia_factor: float = .2  # I_z = factor*m*(a²+b²), .2 uniform ellipsoid
    eccentricity_m: float = .003
    contact_radius_m: float = .018  # effective friction moment arm
    contact_friction: float = .4
    spindle_coupling_Nm: float = 0. # optional measured torque from grip on spindle
    line_density_kg_m: float = .00025  # 100 g / 400 m; sag estimate only
    yarn_axial_rigidity_N: float = 4.0  # EA surrogate, measure force/strain
    yarn_damping_Ns_m: float = .025
    yarn_diameter_m: float = .002
    peel_force_N: float = .015  # effective resistance of unwinding outer layers


@dataclass
class Motion:
    name: str = 'Knitting illustrative'
    cycle_s: float = 1.
    draw_m: float = .024
    duty: float = .55
    lateral_amplitude_m: float = .008
    lateral_cycle_s: float = 1.3
    duration_s: float = 12.
    dt_s: float = .0005


@dataclass
class Setup:
    name: str = 'Beside on desk'
    distance_m: float = .40  # horizontal distance from axis to working hand
    hand_height_m: float = .20  # relative to supporting surface, CAN be negative
    azimuth_deg: float = 0.  # relative to stand, not anatomical handedness


def _positive(obj, names, zero=False):
    for n in names:
        v=getattr(obj,n)
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or (v<0 if zero else v<=0):
            raise ValueError(f'{type(obj).__name__}.{n} must be finite and {"nonnegative" if zero else "positive"}')


def validate(s,b,m,p):
    _positive(s,['mass_kg','rotor_inertia_kg_m2','platform_height_m','platform_radius_m','support_radius_m'])
    _positive(s,['pad_radius_m','foot_friction','start_torque_Nm','running_torque_Nm','viscous_Nm_s','com_height_m'],True)
    _positive(b,['mass_kg','radius_x_m','radius_y_m','radius_z_m','unwind_radius_ratio','inertia_factor','contact_radius_m','yarn_axial_rigidity_N','yarn_diameter_m'])
    _positive(b,['eccentricity_m','contact_friction','spindle_coupling_Nm','line_density_kg_m','yarn_damping_Ns_m','peel_force_N'],True)
    _positive(m,['cycle_s','draw_m','duty','lateral_cycle_s','duration_s','dt_s'])
    _positive(m,['lateral_amplitude_m'],True)
    _positive(p,['distance_m'])
    for v in [p.hand_height_m,p.azimuth_deg,s.pad_angle_deg,b.exit_height_fraction]:
        if not isinstance(v,(int,float)) or not math.isfinite(v): raise ValueError('Nonfinite geometry')
    if not isinstance(s.pad_count,int) or isinstance(s.pad_count,bool) or s.pad_count<3: raise ValueError('At least three pads required')
    if s.running_torque_Nm>s.start_torque_Nm: raise ValueError('Running torque cannot exceed breakaway torque in this model')
    if not 0<m.duty<=1 or not 0<b.unwind_radius_ratio<=1 or not -1<b.exit_height_fraction<1: raise ValueError('Invalid dimensionless fraction')
    if b.eccentricity_m>=min(b.radius_x_m,b.radius_y_m): raise ValueError('Eccentricity must be smaller than ball radius')
    if p.distance_m-m.lateral_amplitude_m<=max(b.radius_x_m,b.radius_y_m): raise ValueError('Working hand must remain outside ball')
    if m.dt_s>.002 or m.duration_s/m.dt_s>2_000_000: raise ValueError('Use dt <= .002 s and <= 2 million steps')
    if m.duration_s<m.cycle_s*2: raise ValueError('Simulate at least two cycles')
    if s.support_points_m is not None:
        if len(s.support_points_m)<3 or any(len(q)!=2 or any(not math.isfinite(x) for x in q) for q in s.support_points_m): raise ValueError('Invalid support polygon')
    if s.body_profile_m is not None:
        if len(s.body_profile_m)<2 or any(len(q)!=2 or any(not math.isfinite(x) for x in q) for q in s.body_profile_m): raise ValueError('Invalid body profile')
        if any(a[0]>=c[0] for a,c in zip(s.body_profile_m,s.body_profile_m[1:])): raise ValueError('Profile radii must increase')
    for q in s.leaves or []:
        if len(q)!=6 or any(not math.isfinite(x) for x in q) or min(q[3:])<=0: raise ValueError('Invalid leaf ellipsoid')


def convex_hull(points):
    pts=sorted(set(tuple(p) for p in points))
    def cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    low=[]
    for q in pts:
        while len(low)>1 and cross(low[-2],low[-1],q)<=0: low.pop()
        low.append(q)
    high=[]
    for q in reversed(pts):
        while len(high)>1 and cross(high[-2],high[-1],q)<=0: high.pop()
        high.append(q)
    return low[:-1]+high[:-1]


def support_edges(s):
    if s.support_points_m is not None: pts=s.support_points_m
    else:
        pts=[]
        for i in range(s.pad_count):
            a=math.radians(s.pad_angle_deg+360*i/s.pad_count)
            for j in range(24):
                t=2*math.pi*j/24+math.radians(s.pad_angle_deg)
                pts.append((s.support_radius_m*math.cos(a)+s.pad_radius_m*math.cos(t),s.support_radius_m*math.sin(a)+s.pad_radius_m*math.sin(t)))
    hull=convex_hull(pts)
    if len(hull)<3: raise ValueError('Degenerate support polygon')
    edges=[]
    for a,b in zip(hull,hull[1:]+hull[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1]; norm=math.hypot(dx,dy)
        nx,ny=dy/norm,-dx/norm; bound=nx*a[0]+ny*a[1]
        if bound<=0: raise ValueError('Stand axis must be strictly inside support polygon')
        edges.append((nx,ny,bound))
    return edges


def geometry(s,b,p,hand_offset=0.):
    a=math.radians(p.azimuth_deg)
    hx=p.distance_m*math.cos(a)-hand_offset*math.sin(a)
    hy=p.distance_m*math.sin(a)+hand_offset*math.cos(a)
    d=math.hypot(hx,hy); ex,ey=hx/d,hy/d
    # Circular surrogate of the ellipsoid's horizontal section. Near the
    # poles both the winding radius and the available torque arm shrink.
    r=math.sqrt(b.radius_x_m*b.radius_y_m)*b.unwind_radius_ratio*math.sqrt(1-b.exit_height_fraction**2)
    radial=r*r/d; tang=r*math.sqrt(1-(r/d)**2)
    px,py=radial*ex+tang*ey,radial*ey-tang*ex
    pz=s.platform_height_m+b.radius_z_m*(1+b.exit_height_fraction)
    delta=(hx-px,hy-py,p.hand_height_m-pz); length=math.sqrt(sum(x*x for x in delta))
    u=tuple(x/length for x in delta)
    lever=abs(px*u[1]-py*u[0])
    return (px,py,pz),(hx,hy,p.hand_height_m),u,lever,length


def draw_speed(t,m):
    phase=(t % m.cycle_s)/m.cycle_s
    if phase>=m.duty: return 0.
    return 2*m.draw_m/(m.cycle_s*m.duty)*math.sin(math.pi*phase/m.duty)**2


def static_limits(s,b,p,edges=None):
    """Conservative worst eccentric-ball phase, quasi-static snag force."""
    edges=edges or support_edges(s)
    q,_,u,a,length=geometry(s,b,p)
    weight=(s.mass_kg+b.mass_kg)*G
    h=math.hypot(u[0],u[1]); denominator=h+s.foot_friction*u[2]
    slide=s.foot_friction*weight/denominator if denominator>0 else math.inf
    tip=math.inf
    for nx,ny,bound in edges:
        c=q[2]*(nx*u[0]+ny*u[1])+(bound-nx*q[0]-ny*q[1])*u[2]
        reserve=weight*bound-b.mass_kg*G*b.eccentricity_m
        if reserve<=0: tip=0.; break
        if c>0: tip=min(tip,reserve/c)
    lift=weight/u[2] if u[2]>0 else math.inf
    return dict(start_tension_N=s.start_torque_Nm/a+b.peel_force_N,slide_N=slide,tip_N=tip,lift_N=lift,
                critical_snag_N=min(slide,tip,lift),lever_m=a,span_m=length,elevation_deg=math.degrees(math.asin(u[2])))


def path_clearance(s,b,p,tension):
    """Screening: taut tangent ray with small-sag parabola; no snag probability."""
    q,h,u,_,L=geometry(s,b,p)
    horizontal=math.hypot(h[0]-q[0],h[1]-q[1]); H=tension*math.hypot(u[0],u[1])
    if H<.001: return {'status':'slack_or_too_low_tension','min_clearance_m':None}
    sag_coefficient=b.line_density_kg_m*G*horizontal**2/(2*H)
    if sag_coefficient/4>.1*L: return {'status':'large_sag_outside_approximation','min_clearance_m':None}
    profile=s.body_profile_m or [[s.platform_radius_m+.001, s.platform_height_m-.004], [s.platform_radius_m+.020,.016]]
    best=math.inf
    for i in range(241):
        f=i/240
        x=q[0]+(h[0]-q[0])*f; y=q[1]+(h[1]-q[1])*f
        z=q[2]+(h[2]-q[2])*f-sag_coefficient*f*(1-f)
        r=math.hypot(x,y)
        if r<=s.platform_radius_m: best=min(best,z-s.platform_height_m-b.yarn_diameter_m/2)
        elif r<=profile[-1][0]:
            surface=profile[0][1]
            for (r0,z0),(r1,z1) in zip(profile,profile[1:]):
                if r>=r0:
                    f0=min(1,(r-r0)/(r1-r0)); surface=z0+(z1-z0)*f0
            best=min(best,z-surface-b.yarn_diameter_m/2)
        for radius,zc,angle,ar,at,az in s.leaves or []:
            a=math.radians(angle); radial=x*math.cos(a)+y*math.sin(a)-radius
            tangent=-x*math.sin(a)+y*math.cos(a)
            if abs(radial)<ar+b.yarn_diameter_m and abs(tangent)<at+b.yarn_diameter_m:
                rho=(radial/ar)**2+(tangent/at)**2
                if rho<=1:
                    top=zc+az*math.sqrt(1-rho)
                    best=min(best,z-top-b.yarn_diameter_m/2)
    return {'status':'possible_contact' if best<=0 else 'clear_in_sampled_path','min_clearance_m':best,'sag_midspan_m':sag_coefficient/4}


def percentile(values,q):
    data=sorted(values); pos=(len(data)-1)*q; i=int(pos)
    return data[i]+(data[min(i+1,len(data)-1)]-data[i])*(pos-i)


def simulate(s= None,b=None,m=None,p=None,keep_trace=True):
    s=s or Stand(); b=b or Ball(); m=m or Motion(); p=p or Setup()
    validate(s,b,m,p); edges=support_edges(s)
    limits=static_limits(s,b,p,edges)
    inertia=s.rotor_inertia_kg_m2+b.inertia_factor*b.mass_kg*(b.radius_x_m**2+b.radius_y_m**2)+b.mass_kg*b.eccentricity_m**2
    _,_,_,a0,L0=geometry(s,b,p)
    spring=b.yarn_axial_rigidity_N/L0
    if m.dt_s> .08*math.sqrt(inertia/(spring*a0*a0)):
        raise ValueError('Time step too large for stiffness/inertia; reduce dt_s')
    theta=omega=payout=demand=0.
    tensions=[]; slacks=[]; trace=[]; slip_peak=tip_peak=traction_peak=0.
    min_margin=math.inf; rpm_max=0.; earliest={}; total_steps=math.ceil(m.duration_s/m.dt_s)
    period=max(1,round(.01/m.dt_s)); peak_t=0.; valid_peak=None
    for step in range(total_steps):
        dt=min(m.dt_s,m.duration_s-step*m.dt_s); t=(step+.5)*m.dt_s
        freq=2*math.pi/m.lateral_cycle_s
        off=m.lateral_amplitude_m*math.sin(freq*t)
        voff=m.lateral_amplitude_m*freq*math.cos(freq*t)
        pos,hand,u,lever,L=geometry(s,b,p,off)
        az=math.radians(p.azimuth_deg)
        demand_v=draw_speed(t,m)+voff*(-u[0]*math.sin(az)+u[1]*math.cos(az))
        demand+=demand_v*dt
        extension=demand-payout
        tension=max(0.,spring*extension+b.yarn_damping_Ns_m*(demand_v-lever*omega)) if extension>0 else 0.
        drive=tension*lever
        old_omega=omega
        peel=b.peel_force_N*lever
        if omega<=1e-12 and drive<=s.start_torque_Nm+peel: omega=0.; friction=max(0.,drive-peel)
        else:
            friction=s.running_torque_Nm+s.viscous_Nm_s*omega
            omega=max(0.,omega+(drive-friction-peel)*dt/inertia)
        alpha=(omega-old_omega)/dt
        theta+=omega*dt; payout+=lever*omega*dt
        # Force -m*a of the eccentric mass enters the support equilibrium.
        ex=b.eccentricity_m*math.cos(theta); ey=b.eccentricity_m*math.sin(theta)
        dynx=b.mass_kg*(omega**2*ex+alpha*ey)
        dyny=b.mass_kg*(omega**2*ey-alpha*ex)
        fx,fy,fz=(tension*x for x in u)
        weight=(s.mass_kg+b.mass_kg)*G; normal=weight-fz
        zc=s.platform_height_m+b.radius_z_m
        if normal<=0:
            slip_util=tip_util=math.inf; margin=-math.inf
        else:
            xcop=(b.mass_kg*G*ex+pos[2]*fx-pos[0]*fz+zc*dynx)/normal
            ycop=(b.mass_kg*G*ey+pos[2]*fy-pos[1]*fz+zc*dyny)/normal
            horizontal_force=math.hypot(fx+dynx,fy+dyny)
            slip_util=horizontal_force/(s.foot_friction*normal) if s.foot_friction>0 else (math.inf if horizontal_force>1e-12 else 0.)
            tip_util=max((nx*xcop+ny*ycop)/bound for nx,ny,bound in edges)
            margin=min(bound-nx*xcop-ny*ycop for nx,ny,bound in edges)
        normal_ball=max(0,b.mass_kg*G-fz)
        cap=b.contact_friction*normal_ball*b.contact_radius_m+b.spindle_coupling_Nm
        needed=abs(s.rotor_inertia_kg_m2*alpha+friction)
        traction=needed/cap if cap>1e-14 else (math.inf if needed>1e-14 else 0.)
        for name,value in [('stand_sliding',slip_util),('stand_tipping',tip_util),('ball_slipping',traction)]:
            if value>1 and name not in earliest: earliest[name]=round(t,5)
        if normal<=0 and 'stand_lifting' not in earliest: earliest['stand_lifting']=round(t,5)
        if fz>=b.mass_kg*G and 'ball_lifting' not in earliest: earliest['ball_lifting']=round(t,5)
        if not earliest:valid_peak=max(valid_peak or 0.,tension)
        slack=max(0.,payout-demand)
        tensions.append(tension); slacks.append(slack)
        slip_peak=max(slip_peak,slip_util); tip_peak=max(tip_peak,tip_util)
        traction_peak=max(traction_peak,traction); min_margin=min(min_margin,margin)
        rpm_max=max(rpm_max,omega*60/(2*math.pi))
        if tension>peak_t: peak_t=tension
        if keep_trace and step%period==0:
            trace.append({'t_s':round(t,5),'tension_N':tension,'slack_m':slack,'rpm':omega*60/(2*math.pi),'slide_utilization':slip_util,'tip_utilization':tip_util,'ball_traction_utilization':traction,'coupled_assumptions_valid':not bool(earliest)})
    warnings=[]
    if abs(limits['elevation_deg'])>60: warnings.append('Steep yarn angle: actual yarn may peel over the ball; fixed tangent model uncertain.')
    if earliest: warnings.append('Coupled stationary-support model fails at the reported first event. Later values are hypothetical locked-motion estimates.')
    if max(slacks)>.05: warnings.append('Over 50 mm idealized coasting payout: real loose loops can wrap or catch. Slack is an upper-bound proxy, not a validated loop trajectory.')
    if max(b.radius_x_m,b.radius_y_m)+b.eccentricity_m>s.platform_radius_m: warnings.append('Ball overhangs platter; soft-ball support not represented.')
    path=path_clearance(s,b,p,max(limits['start_tension_N'],percentile(tensions,.5),.005))
    summary={'peak_tension_N':peak_t,'p95_tension_N':percentile(tensions,.95),'mean_tension_N':sum(tensions)/len(tensions),
             'max_slack_m':max(slacks),'max_rpm':rpm_max,'max_slide_utilization':slip_peak,'max_tip_utilization':tip_peak,
             'minimum_support_margin_m':min_margin,'max_ball_traction_utilization':traction_peak,'first_events_s':earliest,
             'inertia_kg_m2':inertia,'effective_stiffness_N_m':spring,'static_limits':limits,'path_screen':path,
             'hypotheses_valid_for_entire_run':not bool(earliest),
             'valid_coupled_interval_end_s':min(earliest.values()) if earliest else m.duration_s,
             'peak_tension_before_first_event_N':valid_peak,'warnings':warnings}
    return {'inputs':{'stand':asdict(s),'ball':asdict(b),'motion':asdict(m),'setup':asdict(p)},'summary':summary,'trace':trace}


def from_config(data):
    allowed={'stand':Stand,'ball':Ball,'motion':Motion,'setup':Setup}
    if not isinstance(data,dict) or set(data)-set(allowed): raise ValueError('Unknown top-level configuration field')
    result=[]
    for name,cls in allowed.items():
        values=data.get(name,{})
        if not isinstance(values,dict) or set(values)-{f.name for f in fields(cls)}: raise ValueError(f'Unknown {name} parameter')
        result.append(cls(**values))
    validate(*result)
    return tuple(result)
