"""Unilateral N-wheel support, contact pressure and rolling-force estimates."""
import math
import numpy as np
from scipy.optimize import linprog, minimize
from scipy.spatial import ConvexHull

G = 9.80665


def positive(x, name, zero=False):
    x = float(x)
    if not math.isfinite(x) or x < 0 or (not zero and x == 0):
        raise ValueError(f'{name} must be finite and {"nonnegative" if zero else "positive"}')
    return x


def fraction(x, name):
    x = positive(x, name, True)
    if x > 1:
        raise ValueError(f'{name} must be in [0, 1]')
    return x


def compliance(wheel, surface, force):
    """Compression and complementary elastic energy, including pile bottoming.

    A small-indentation Winkler approximation gives N=C*delta**1.5.
    The backing spring takes incremental load after the pile is compressed.
    Structural stiffness is a separate measured/assumed spring, not Hertz E.
    """
    n = positive(force, 'normal force', True)
    k = positive(wheel['vertical_stiffness_N_m'], 'wheel/support stiffness')
    delta, energy = n/k, n*n/(2*k)
    pile = 0.0
    bottomed = False
    if surface['kind'] == 'carpet':
        r = positive(wheel['radius_m'], 'radius')
        width = positive(wheel['width_m'], 'width')
        phi = fraction(wheel.get('tread_contact_fraction', 1), 'tread fraction')
        positive(phi, 'tread fraction')
        h = positive(surface['pile_height_m'], 'pile height')
        c = 2*width*phi*math.sqrt(2*r)*positive(surface['foundation_Pa_m'], 'foundation')
        limit = c*h**1.5
        if n <= limit:
            pile = (n/c)**(2/3)
            energy += 0.6*n*pile
        else:
            kb = positive(surface['backing_stiffness_N_m'], 'backing stiffness')
            pile = h + (n-limit)/kb
            energy += 0.6*limit*h + h*(n-limit) + (n-limit)**2/(2*kb)
            bottomed = True
        delta += pile
    return delta, energy, pile, bottomed


def contact(wheel, surface, force):
    n = positive(force, 'normal force', True)
    r = positive(wheel['radius_m'], 'radius')
    width = positive(wheel['width_m'], 'width')
    phi = fraction(wheel.get('tread_contact_fraction', 1), 'tread fraction')
    length = width*positive(phi, 'tread fraction')
    delta, _, pile, bottomed = compliance(wheel, surface, n)
    warnings = []
    if n == 0:
        return dict(area_m2=0., mean_pressure_Pa=0., peak_pressure_Pa=0.,
                    compression_m=0., pile_compression_m=0., rolling_force_N=0.,
                    journal_force_N=0., warnings=[], pile_bottomed=False)
    if surface['kind'] == 'carpet':
        a = math.sqrt(2*r*pile)
        area = 2*a*length
        mean, peak = n/area, None
        if pile/r > .1:
            warnings.append('Pile indentation exceeds 10% of radius: small-indentation approximation is weak.')
        if bottomed:
            warnings.append('Pile bottomed; incremental backing spring is an approximation.')
        loss = fraction(surface['hysteresis_fraction'], 'hysteresis')*n*pile/(2*a)
    elif surface['kind'] == 'hard':
        ew = positive(wheel['surface_modulus_Pa'], 'wheel surface modulus')
        ef = positive(surface['modulus_Pa'], 'floor modulus')
        vw, vf = float(wheel['poisson']), float(surface['poisson'])
        if not (-1 < vw < .5 and -1 < vf < .5):
            raise ValueError('Poisson ratios must be between -1 and 0.5')
        effective = 1/((1-vw*vw)/ew+(1-vf*vf)/ef)
        a = math.sqrt(4*n*r/(math.pi*length*effective))
        area = 2*a*length
        mean, peak = n/area, 2*n/(math.pi*a*length)
        loss = 0.
        if a/r > .1 or a/length > .1:
            warnings.append('Hertz patch is not small relative to radius/width.')
    else:
        raise ValueError('Surface kind must be hard or carpet')
    journal = positive(wheel.get('journal_friction', 0), 'journal friction', True)*n*positive(wheel.get('journal_radius_m', 0), 'journal radius', True)/r
    rolling = n*positive(surface['rolling_arm_m'], 'rolling arm', True)/r + loss
    return dict(area_m2=area, mean_pressure_Pa=mean, peak_pressure_Pa=peak,
                compression_m=delta, pile_compression_m=pile, pile_bottomed=bottomed,
                rolling_force_N=rolling, journal_force_N=journal, warnings=warnings)


def axle_estimate(wheel, normal_force):
    """Elastic beam demand and optional local, assumption-based stress screen."""
    a = wheel.get('axle')
    if not a:
        return None
    d = positive(a['diameter_m'], 'axle diameter')
    length = positive(a['span_or_overhang_m'], 'axle length')
    e = positive(a['effective_modulus_Pa'], 'axle bending modulus')
    inertia = math.pi*d**4/64
    if a['support'] == 'cantilever':
        moment, deflection = normal_force*length, normal_force*length**3/(3*e*inertia)
    elif a['support'] == 'two_supports_center_load':
        moment, deflection = normal_force*length/4, normal_force*length**3/(48*e*inertia)
    else:
        raise ValueError('Unknown axle support')
    stress = 32*moment/(math.pi*d**3)
    result = dict(bending_stress_Pa=stress, deflection_m=deflection,
                  model=a['support'], strength_pass_fail=None)
    if 'allowable_stress_Pa' in a:
        allowable = positive(a['allowable_stress_Pa'], 'screening allowable')
        kt = positive(a.get('stress_concentration_factor', 1), 'stress concentration')
        if kt < 1:
            raise ValueError('Stress concentration factor must be at least 1')
        utilization = kt*stress/allowable
        result.update(local_stress_Pa=kt*stress, allowable_stress_Pa=allowable,
                      stress_concentration_factor=kt, utilization=utilization,
                      reserve_factor=1/utilization if utilization else None,
                      screen_status='within_assumed_allowable' if utilization <= 1 else 'exceeds_assumed_allowable',
                      scope='Local static axle bending only; no chassis, fastener, bearing, fatigue, creep or impact verification.')
    return result


def step_force(normal_force, radius, height):
    """Horizontal force at axle to start climbing a sharp, rigid step."""
    n = positive(normal_force, 'normal force', True)
    r = positive(radius, 'radius')
    h = positive(height, 'step height', True)
    if h >= r:
        return dict(force_N=None, status='blocked_in_horizontal_axle_force_model')
    return dict(force_N=n*math.sqrt(2*r*h-h*h)/(r-h), status='quasistatic')


def solve(vehicle, surface, load=None):
    """Minimize complementary spring energy subject to force/moment balance.

    This resolves N>3 indeterminacy and lift-off using compliance and wheel gaps.
    It assumes a rigid chassis, small pitch/roll, and vertical point reactions.
    """
    wheels = vehicle['wheels']
    if not wheels:
        raise ValueError('At least one wheel is required')
    xy = np.array([w['position_m'][:2] for w in wheels], dtype=float)
    if not np.isfinite(xy).all():
        raise ValueError('Nonfinite wheel positions')
    weight = positive(vehicle['mass_kg'], 'mass')*G
    cg = np.asarray(vehicle['cg_m'], float)
    if cg.shape != (3,) or not np.isfinite(cg).all():
        raise ValueError('cg_m must contain three finite coordinates')
    force = 0.
    load = load or {}
    if 'force_N' in load and 'child_mass_kg' in load:
        raise ValueError('Use force_N or child_mass_kg, not both')
    if 'child_mass_kg' in load:
        force = positive(load['child_mass_kg'], 'child mass')*G*fraction(load['weight_fraction'], 'weight fraction')
    else:
        force = positive(load.get('force_N', 0), 'applied force', True)
    at = np.asarray(load.get('position_m', cg), float)
    total = weight+force
    moment = weight*cg[:2]+force*at[:2]
    push = np.asarray(load.get('horizontal_force_N', [0, 0]), float)
    height = positive(load.get('horizontal_height_m', 0), 'push height', True)
    if at.shape != (3,) or push.shape != (2,) or not np.isfinite(at).all() or not np.isfinite(push).all():
        raise ValueError('Invalid load position or horizontal force')
    moment += height*push
    cop = moment/total
    scale = max(float(np.max(np.abs(xy))), .01)
    a = np.vstack([np.ones(len(wheels)), xy.T/scale])
    b = np.r_[1., cop/scale]
    # SVD removes redundant constraints for one/two/collinear wheel cases.
    u, singular, _ = np.linalg.svd(a, full_matrices=True)
    rank = int(np.sum(singular > 1e-10))
    ar, br = u[:, :rank].T@a, u[:, :rank].T@b
    base = dict(wheel_count=len(wheels), total_vertical_force_N=total,
                child_force_N=force, required_cop_m=cop.tolist(), surface=surface['name'],
                parameter_status=surface.get('parameter_status', 'user supplied'))
    if 'contact_area_m2' in load:
        base['applied_load_mean_pressure_Pa'] = force/positive(load['contact_area_m2'], 'load contact area')
    if np.linalg.norm(b-u[:, :rank]@br) > 1e-8:
        return dict(base, status='tipping', reason='Required center of pressure lies outside the support subspace')
    feasible = linprog(np.zeros(len(wheels)), A_eq=ar, b_eq=br, bounds=(0, None), method='highs')
    if not feasible.success:
        return dict(base, status='tipping', reason='No nonnegative wheel reactions balance the specified load')
    gaps = np.array([float(w['position_m'][2])-positive(w['radius_m'], 'radius')-float(w.get('ground_height_m', 0)) for w in wheels])
    if not np.isfinite(gaps).all():
        raise ValueError('Nonfinite ground/hub height')
    gaps -= gaps.min()
    def objective(q):
        return sum(compliance(w, surface, total*x)[1] for w, x in zip(wheels, q))/(total*scale)+np.dot(gaps, q)/scale
    def gradient(q):
        return (np.array([compliance(w, surface, total*x)[0] for w, x in zip(wheels, q)])+gaps)/scale
    fit = minimize(objective, feasible.x, jac=gradient, method='SLSQP', bounds=[(0, None)]*len(wheels),
                   constraints={'type':'eq','fun':lambda q:ar@q-br,'jac':lambda q:ar},
                   options={'ftol':1e-12,'maxiter':400})
    if not fit.success or np.max(np.abs(a@fit.x-b)) > 1e-6:
        raise RuntimeError(f'Load distribution did not converge: {fit.message}')
    normal = np.maximum(fit.x, 0)*total
    rows = []
    for w, n in zip(wheels, normal):
        c = contact(w, surface, float(n))
        rows.append(dict(name=w['name'], normal_force_N=float(n), unloaded=bool(n < total*1e-7),
                         **c, axle=axle_estimate(w, n)))
    margin = None
    if rank == 3:
        eq = ConvexHull(xy).equations
        margin = float(np.min(-(eq[:, :2]@cop+eq[:, 2])))
    resistance = sum(r['rolling_force_N']+r['journal_force_N'] for r in rows)
    grip = positive(surface.get('traction_coefficient', 0), 'traction coefficient', True)*total
    return dict(base, status='supported' if rank == 3 and margin > 1e-8 else 'marginal_support',
                support_margin_m=margin, wheels=rows, pull_force_N=resistance,
                traction_bound_N=grip, rolling_without_slip_feasible=resistance <= grip,
                equilibrium_residual_N=float(np.max(np.abs(a@normal-total*b))),
                warnings=['Floor and bearing parameters require calibration.',
                          'Small-angle rigid chassis model; body-ground contact and structural failure are not simulated.'])
