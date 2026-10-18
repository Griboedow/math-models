"""Shared gravity-loaded yarn path, independent of the optional mesh libraries.

The prescribed endpoints and nominal chord tension define H. Mass is per unit
arc length, so the equilibrium is a catenary even for unequal endpoint heights.
This does not solve peeling, contact rerouting, or the shape of a slack loop.
"""
from dataclasses import dataclass
import math

G = 9.80665


@dataclass
class Catenary:
    start: tuple
    end: tuple
    horizontal: float
    span: float
    scale: float = math.inf
    origin: float = 0.
    sag_m: float = 0.

    def point(self, fraction):
        if fraction == 0: return self.start
        if fraction == 1: return self.end
        x, y = (self.start[i]+fraction*(self.end[i]-self.start[i]) for i in (0, 1))
        if math.isinf(self.scale):
            z = self.start[2]+fraction*(self.end[2]-self.start[2])
        else:
            # cosh(u)-cosh(v) as a product avoids cancellation for small sag.
            dx = fraction*self.horizontal
            z = self.start[2]+2*self.scale*math.sinh(dx/(2*self.scale))*math.sinh((dx/2-self.origin)/self.scale)
        return (x, y, z)


def catenary(start, end, tension_N, density_kg_m):
    if not math.isfinite(tension_N) or tension_N < 0:
        raise ValueError('Finite nonnegative tension required')
    if not math.isfinite(density_kg_m) or density_kg_m < 0:
        raise ValueError('Finite nonnegative line density required')
    delta = tuple(y-x for x,y in zip(start,end))
    horizontal = math.hypot(*delta[:2]); span = math.sqrt(sum(x*x for x in delta))
    if horizontal <= 0 or span <= 0: return None, 'unsupported_vertical_path'
    H = tension_N*horizontal/span
    if H < .001: return None, 'slack_or_too_low_tension'
    curve = Catenary(tuple(start), tuple(end), horizontal, span)
    if density_kg_m == 0: return curve, 'catenary'
    scale = H/(density_kg_m*G)
    if not math.isfinite(scale): return curve, 'catenary'  # numerically weightless limit
    half = horizontal/(2*scale)
    # Large sag is outside the force model and would overflow hyperbolic terms.
    if not math.isfinite(half) or half > 1: return None, 'large_sag_outside_approximation'
    origin = horizontal/2-scale*math.asinh(delta[2]/(2*scale*math.sinh(half)))
    curve.scale, curve.origin = scale, origin
    fraction = (origin+scale*math.asinh(delta[2]/horizontal))/horizontal
    fraction = min(1.,max(0.,fraction))
    curve.sag_m = start[2]+fraction*delta[2]-curve.point(fraction)[2]
    if curve.sag_m > .1*horizontal: return None, 'large_sag_outside_approximation'
    return curve, 'catenary'


def ball_path_status(stand, ball, points):
    """Reject centerlines entering the prescribed ellipsoid (exit contact allowed).

    Minimise the ellipsoid quadratic on every segment, including between nodes.
    Yarn thickness at detachment is not treated as a collision with its own ball.
    """
    axes = (ball.radius_x_m, ball.radius_y_m, ball.radius_z_m)
    center = (0.,0.,stand.platform_height_m+ball.radius_z_m)
    def normalized(p): return tuple((p[i]-center[i])/axes[i] for i in range(3))
    previous = normalized(points[0])
    if sum(x*x for x in previous) < 1-1e-9: return 'exit_inside_ball'
    for point in points[1:]:
        current = normalized(point); delta = tuple(y-x for x,y in zip(previous,current))
        norm2 = sum(x*x for x in delta)
        fraction = min(1.,max(0.,-sum(x*y for x,y in zip(previous,delta))/norm2)) if norm2 else 0.
        if sum((x+fraction*y)**2 for x,y in zip(previous,delta)) < 1-1e-9:
            return 'path_intersects_ball'
        previous = current
    return None


def prescribed_path(stand, ball, setup, tension_N, count=240, hand_offset=0.):
    from .model import geometry
    start,end,*_ = geometry(stand,ball,setup,hand_offset)
    curve,status = catenary(start,end,tension_N,ball.line_density_kg_m)
    if curve is None: return None,status,None
    points = [curve.point(i/count) for i in range(count+1)]
    invalid = ball_path_status(stand,ball,points)
    return (None,invalid,curve) if invalid else (points,status,curve)
