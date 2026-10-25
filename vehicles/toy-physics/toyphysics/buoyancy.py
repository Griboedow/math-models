"""Hydrostatics of closed triangle meshes, infill, flooding and local stability."""
from pathlib import Path
import math
import numpy as np
import trimesh
from scipy.optimize import brentq, least_squares
from .rolling import G, positive, fraction
from .materials import merge_settings, resolve_material


def integrate(triangles):
    """Signed tetrahedron volume and first moment; triangles face outward."""
    t = np.asarray(triangles, float).reshape(-1, 3, 3)
    volumes = np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2]))/6
    v = float(volumes.sum())
    moment = np.sum(volumes[:, None]*t.sum(axis=1)/4, axis=0)
    return v, moment


def submerged(triangles):
    """Clip at world z=0. Waterplane cap contributes zero tetrahedral moments.

    This integrates the actual closed mesh, without taking its convex hull.
    Concave bodies and through-holes are supported if the input is oriented.
    """
    t = np.asarray(triangles, float)
    inside = t[:, :, 2] <= 0
    complete = t[inside.all(axis=1)]
    v, moment = integrate(complete)
    clipped = []
    for tri in t[inside.any(axis=1) & ~inside.all(axis=1)]:
        polygon = []
        for i in range(3):
            a, b = tri[i], tri[(i+1) % 3]
            if a[2] <= 0:
                polygon.append(a)
            if (a[2] <= 0) != (b[2] <= 0):
                polygon.append(a+(b-a)*(-a[2]/(b[2]-a[2])))
        for i in range(1, len(polygon)-1):
            clipped.append([polygon[0], polygon[i], polygon[i+1]])
    if clipped:
        dv, dm = integrate(clipped)
        v += dv
        moment += dm
    if v < -1e-12:
        raise ValueError('Negative submerged volume: check mesh winding')
    return max(v, 0.), moment


def rotation(roll, pitch):
    cr, sr, cp, sp = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch)
    return np.array([[cp, sp*sr, sp*cr], [0, cr, -sr], [-sp, cp*sr, cp*cr]])


def load_mesh(spec, base):
    if 'size_m' in spec:
        dims = np.array([positive(x, 'box dimension') for x in spec['size_m']])
        if dims.shape != (3,):
            raise ValueError('Box requires three dimensions')
        mesh = trimesh.creation.box(extents=dims)
        mesh.apply_translation(spec.get('center_m', [0, 0, 0]))
    else:
        mesh = trimesh.load_mesh(Path(base)/spec['mesh_file'], process=True)
        mesh.apply_scale(positive(spec.get('mesh_unit_m', .001), 'mesh scale'))
        if 'transform' in spec:
            mesh.apply_transform(spec['transform'])
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError('Buoyancy requires an outward-oriented, closed positive-volume mesh')
    return np.asarray(mesh.triangles)


class Body:
    def __init__(self, spec, base=Path('.'), material_settings=None):
        self.spec = spec
        self.rho = positive(spec.get('water_density_kg_m3', 998.2), 'water density')
        self.terms = []
        self.components = []
        mass, mass_moment = 0., np.zeros(3)
        settings = merge_settings(material_settings, spec.get('material_settings'))
        for c in spec['components']:
            outer = load_mesh(c, base)
            v, moment = integrate(outer)
            material = resolve_material(settings, c.get('material_settings'))
            rho = positive(c.get('polymer_density_kg_m3', material['density_kg_m3']), 'polymer density')
            fill = fraction(c['infill'], 'infill')
            flooded = fraction(c.get('flooded_void_fraction', 0), 'flooded void fraction')
            if 'wall_m' in c:
                if 'size_m' not in c:
                    raise ValueError('wall_m requires a box; provide inner_mesh for arbitrary shells')
                wall = positive(c['wall_m'], 'wall')
                inner_dims = np.maximum(np.asarray(c['size_m'])-2*wall, 0)
                inner = load_mesh(dict(size_m=inner_dims, center_m=c.get('center_m', [0, 0, 0])), base) if inner_dims.min() > 0 else np.empty((0, 3, 3))
            elif 'inner_mesh' in c:
                inner = load_mesh(c['inner_mesh'], base)
            else:
                # Homogenized shell fraction, explicit fallback for complex parts.
                shell = fraction(c['shell_volume_fraction'], 'shell volume fraction')
                inner = outer
                fill = 1-(1-shell)*(1-fill)
            vi, mi = integrate(inner)
            if vi > v+1e-12:
                raise ValueError('Inner volume exceeds outer volume')
            solid = v-(1-fill)*vi
            m = rho*solid
            mass += m
            mass_moment += rho*(moment-(1-fill)*mi)
            self.terms.append((outer, 1.))
            if len(inner):
                self.terms.append((inner, -flooded*(1-fill)))
            self.components.append(dict(name=c['name'], envelope_volume_m3=v,
                                        solid_volume_m3=solid, mass_kg=m,
                                        material=material['material'], polymer_density_kg_m3=rho,
                                        density_source='explicit component override' if 'polymer_density_kg_m3' in c else 'selected material',
                                        maximum_displacement_m3=v-flooded*(1-fill)*vi))
        if not self.terms:
            raise ValueError('At least one buoyant component is required')
        for item in spec.get('point_masses', []):
            m = positive(item['mass_kg'], 'point mass', True)
            mass += m
            mass_moment += m*np.asarray(item['position_m'], float)
        self.mass = positive(spec.get('mass_override_kg', mass), 'body mass')
        positive(mass, 'component and ballast mass')
        self.cg = np.asarray(spec.get('cg_override_m', mass_moment/mass), float)
        if self.cg.shape != (3,) or not np.isfinite(self.cg).all():
            raise ValueError('Invalid center of gravity')
        self.max_volume = sum(c['maximum_displacement_m3'] for c in self.components)

    def pose(self, angles):
        r = rotation(*angles)
        transformed = [(t@r.T, coeff) for t, coeff in self.terms if coeff]
        all_z = np.concatenate([t[:, :, 2].ravel() for t, _ in transformed])
        target = self.mass/self.rho
        def calc(h):
            volume, moment = 0., np.zeros(3)
            for t, coefficient in transformed:
                q = t.copy()
                q[:, :, 2] += h
                v, m = submerged(q)
                volume += coefficient*v
                moment += coefficient*m
            return volume, moment
        h = brentq(lambda z:calc(z)[0]-target, -all_z.max()-.01, -all_z.min()+.01, xtol=1e-12)
        v, moment = calc(h)
        cb = moment/v
        cg = r@self.cg+np.array([0, 0, h])
        tau = self.rho*G*v*np.array([cb[1]-cg[1], -(cb[0]-cg[0]), 0.])
        # Generalized torques for R_y(pitch) R_x(roll), needed at finite angles.
        roll_axis = np.array([math.cos(angles[1]), 0, -math.sin(angles[1])])
        generalized = np.array([tau@roll_axis, tau[1]])
        return dict(heave_m=float(h), displaced_volume_m3=float(v), cb_m=cb.tolist(),
                    cg_world_m=cg.tolist(), torque_Nm=generalized.tolist())

    def solve(self):
        common = dict(name=self.spec['name'], mass_kg=self.mass, cg_m=self.cg.tolist(),
                      maximum_supported_mass_kg=self.rho*self.max_volume,
                      mass_override_applied='mass_override_kg' in self.spec,
                      reserve_buoyancy_kg=self.rho*self.max_volume-self.mass,
                      effective_bulk_density_kg_m3=self.mass/sum(c['envelope_volume_m3'] for c in self.components),
                      components=self.components, assumptions=[
                          'Fixed flooded fraction; no leak-rate or air-compression prediction.',
                          'Components must not overlap; inner meshes must lie inside their outer meshes.',
                          'Part-scale infill is homogenized. Printed watertightness must be measured.',
                          'No internal free-surface sloshing, waves, surface tension or dynamic capsizing.'])
        if self.mass >= self.rho*self.max_volume*(1-1e-10):
            return dict(common, status='sinks_or_fully_submerged_neutral', equilibrium=None)
        level = self.pose([0., 0.])
        scale = self.mass*G*max(np.linalg.norm(self.cg), .05)
        fit = least_squares(lambda a:np.array(self.pose(a)['torque_Nm'])/scale,
                            [0., 0.], bounds=(-math.radians(70), math.radians(70)),
                            xtol=1e-11, ftol=1e-11, gtol=1e-11)
        eq = self.pose(fit.x)
        converged = fit.success and np.linalg.norm(eq['torque_Nm']) < scale*1e-6
        eps = 1e-4
        jac = np.column_stack([(np.array(self.pose(fit.x+np.eye(2)[i]*eps)['torque_Nm'])-
                                np.array(self.pose(fit.x-np.eye(2)[i]*eps)['torque_Nm']))/(2*eps) for i in range(2)])
        stiffness = -(jac+jac.T)/2
        eigen = np.linalg.eigvalsh(stiffness)
        angles = np.degrees(fit.x)
        return dict(common, status='local_equilibrium' if converged else 'no_equilibrium_found_within_70_degrees',
                    level_pose=level, equilibrium=dict(eq, roll_deg=float(angles[0]), pitch_deg=float(angles[1])),
                    holds_level=bool(converged and np.max(np.abs(angles)) < self.spec.get('level_tolerance_deg', 1.)),
                    locally_stable=bool(converged and eigen.min() > 1e-8),
                    restoring_stiffness_Nm_rad=stiffness.tolist(),
                    equivalent_GM_eigenvalues_m=(eigen/(self.mass*G)).tolist(),
                    torque_residual_Nm=float(np.linalg.norm(eq['torque_Nm'])),
                    equilibrium_scope='Root nearest the upright starting pose; not a global capsize search.')
