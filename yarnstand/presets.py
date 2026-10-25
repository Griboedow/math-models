"""Editable assumptions, NOT measured knitting/crochet population data."""
from dataclasses import replace
from .model import Stand, Ball, Motion, Setup

PROFILE=[[.0531,.040],[.0548,.0424],[.0564,.0421],[.0588,.0402],
         [.0618,.037],[.0662,.031],[.0695,.024],[.0714,.0165]]


def stand(name='pitaya_v08'):
    leaves=[[.074,.019,30+60*i,.006,.010,.015] for i in range(6)]
    s=Stand(body_profile_m=PROFILE,leaves=leaves)
    if name=='pitaya_v07':
        return replace(s,name='PITAYA v07 estimate',leaves=[[.082,.014,30+60*i,.012,.016,.010] for i in range(6)])
    if name=='pitaya_v08': return s
    if name=='lemon_v05':
        # Same estimates as the final LEMON v05 audit. Friction is unmeasured;
        # the conservative axisymmetric envelope is not the asymmetric STL.
        return replace(s,name='LEMON v05; explicit unmeasured friction assumptions',
                       mass_kg=.2221891594120714,rotor_inertia_kg_m2=3.327726625318396e-05,
                       com_height_m=.03001080219262895,platform_height_m=.045,
                       platform_radius_m=.048,support_radius_m=.044,pad_angle_deg=0,
                       body_profile_m=[[.0491,.0445],[.0505,.0445],[.052,.043],
                                       [.056,.0395],[.061,.034],[.066,.030],[.071,.024]],leaves=[])
    if name=='peach_v13':
        return Stand(name='PEACH v13 CAD + slicer estimate',mass_kg=.3003084,rotor_inertia_kg_m2=.0000545155,
                     com_height_m=.0350184,platform_height_m=.0707,platform_radius_m=.052,
                     support_radius_m=.054,pad_radius_m=.00395,pad_count=6,pad_angle_deg=30,
                     body_profile_m=[[.0531,.0667],[.057,.0664],[.061,.064],[.067,.058],[.072,.051],[.078,.036]],leaves=[])
    if name=='pitaya_v09':
        # Broad calyx leaves: coarse ellipsoids, not exact CAD collision surfaces.
        # Mechanical mass/inertia assumptions are unchanged, not new measurements.
        return replace(s,name='PITAYA v09 estimate',leaves=[[.074,.021,30+60*i,.012,.019,.020] for i in range(6)])
    if name=='wide_feet': return replace(s,name='Comparison: pads at r=62 mm',support_radius_m=.062)
    if name=='light_small': return replace(s,name='Example lightweight small stand',mass_kg=.10,support_radius_m=.032,platform_radius_m=.045,rotor_inertia_kg_m2=.000035,body_profile_m=[[.046,.041],[.050,.025]],leaves=[])
    if name=='high_drag': return replace(s,name='Sensitivity: high bearing drag',start_torque_Nm=.003,running_torque_Nm=.0015)
    raise ValueError('Unknown stand preset')


def ball(name='full'):
    b=Ball()
    if name=='full': return b
    if name=='nearly_empty': return replace(b,name='Nearly empty round ball 10 g',mass_kg=.010,radius_x_m=.021,radius_y_m=.021,radius_z_m=.023,contact_radius_m=.009,eccentricity_m=.003,peel_force_N=.01)
    if name=='large': return replace(b,name='Large round ball 200 g',mass_kg=.200,radius_x_m=.057,radius_y_m=.057,radius_z_m=.055,contact_radius_m=.024)
    raise ValueError('Unknown ball preset')


def motion(name='knitting'):
    m=Motion()
    if name=='knitting': return m
    if name=='crochet': return replace(m,name='Crochet illustrative',cycle_s=1.35,draw_m=.045,duty=.30,lateral_amplitude_m=.014,lateral_cycle_s=1.35)
    if name=='gentle': return replace(m,name='Slow smooth draw',cycle_s=1.8,draw_m=.024,duty=.8,lateral_amplitude_m=.003)
    raise ValueError('Unknown motion preset')


def setup(name='desk_side'):
    options={
        'desk_side':Setup('Desk side: hand 20 cm above base',.40,.20,0),
        'front':Setup('In front: hand 16 cm above base',.35,.16,90),
        'far_side':Setup('Far side: hand 15 cm above base',.70,.15,150),
        'high_table':Setup('High table: hand 5 cm below base',.35,-.05,30),
        'floor':Setup('On floor: hand 65 cm above base',.45,.65,0),
    }
    if name not in options: raise ValueError('Unknown position preset')
    return options[name]


def config(stand_name='pitaya_v08',ball_name='full',motion_name='knitting',setup_name='desk_side'):
    from dataclasses import asdict
    return {k:asdict(v) for k,v in zip(['stand','ball','motion','setup'],[stand(stand_name),ball(ball_name),motion(motion_name),setup(setup_name)])}
