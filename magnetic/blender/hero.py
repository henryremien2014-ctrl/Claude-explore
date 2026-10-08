"""The hero: a ferrofluid sphere with a third eye.

Object tree (HERO_FACE turns the eye toward the active camera):

    HERO_ROOT (location)
      HERO_FACE (rotation: eye axis = local +Y, toward the camera)
        FLUID  (mesh + geometry nodes; spins about +Y: one full field rotation per loop)
        EYE_PIVOT (at the eyeball centre)
          EYEBALL (rotation: gaze at the camera + micro-saccades)
"""
import math

import bmesh
import bpy
import numpy as np
from scipy.spatial import cKDTree

from common import (MAGMA, Tree, gn_group, hex_lin, new_material, output, principled, link_to_scene)

R = 1.0                 # fluid radius
EYE_C = 0.80            # eyeball centre along +Y
EYE_R = 0.30            # eyeball radius
LID_T = 0.016           # lid thickness over the eyeball
CORNEA = 0.024          # corneal dome height over the iris
SITE_SPACING = 0.17     # Poisson-disk spacing of the Rosensweig spikes (chord, m)


# ----------------------------------------------------------------------------- fluid mesh

def fluid_mesh(n_seg=512, n_ring=384, gamma=1.8, seed=7):
    """UV sphere with its pole on +Y (the eye). Rings are packed toward the eye pole
    (theta = pi * u^gamma) so the eyelid margin has resolution where it is needed."""
    u = np.arange(1, n_ring) / n_ring
    theta = np.pi * u ** gamma
    phi = 2 * np.pi * np.arange(n_seg) / n_seg
    st, ct = np.sin(theta)[:, None], np.cos(theta)[:, None]
    verts = np.stack([st * np.cos(phi)[None], np.repeat(ct, n_seg, 1), st * np.sin(phi)[None]], -1).reshape(-1, 3)
    verts = np.vstack([[0.0, 1.0, 0.0], verts, [0.0, -1.0, 0.0]]) * R
    nv = len(verts)
    faces = []
    ring = lambda i: 1 + i * n_seg
    for j in range(n_seg):                                  # eye pole fan
        faces.append((0, ring(0) + (j + 1) % n_seg, ring(0) + j))
    for i in range(n_ring - 2):                             # quads
        a, b = ring(i), ring(i + 1)
        for j in range(n_seg):
            j1 = (j + 1) % n_seg
            faces.append((a + j, a + j1, b + j1, b + j))
    last = ring(n_ring - 2)
    for j in range(n_seg):                                  # back pole fan
        faces.append((nv - 1, last + j, last + (j + 1) % n_seg))

    # Poisson-disk sites, snapped to vertices so every spike tip is a real vertex.
    rng = np.random.default_rng(seed)
    order = rng.permutation(nv)
    unit = verts / np.linalg.norm(verts, axis=1, keepdims=True)
    accepted = []
    tree, batch = None, []
    for i in order:
        p = unit[i]
        if tree is not None and tree.query(p)[0] < SITE_SPACING:
            continue
        if batch and np.min(np.linalg.norm(np.asarray(batch) - p, axis=1)) < SITE_SPACING:
            continue
        accepted.append(i)
        batch.append(p)
        if len(batch) >= 64:
            tree = cKDTree(unit[accepted])
            batch = []
    sites = unit[accepted]
    st = cKDTree(sites)
    nn = st.query(sites, k=2)[0][:, 1]
    site_r = 0.62 * nn                                       # round cone bases that just touch their neighbours
    d, idx = st.query(unit, k=2)
    site_rand = rng.random(len(sites))

    me = bpy.data.meshes.new("FLUID")
    me.from_pydata(verts.tolist(), [], faces)
    me.update()
    attrs = {"spike_q1": d[:, 0] / site_r[idx[:, 0]], "spike_q2": d[:, 1] / site_r[idx[:, 1]],
             "spike_r1": site_rand[idx[:, 0]], "spike_r2": site_rand[idx[:, 1]]}
    for name, vals in attrs.items():
        a = me.attributes.new(name, "FLOAT", "POINT")
        a.data.foreach_set("value", vals.astype(np.float32))
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    return me, sites, accepted


# ----------------------------------------------------------------------------- fluid geometry nodes

def fluid_nodes():
    inputs = [("Geometry", "NodeSocketGeometry"), ("Spike Height", "NodeSocketFloat", 0.25),
              ("Punch", "NodeSocketFloat", 0.0), ("Punch Age", "NodeSocketFloat", 1.0),
              ("Eye Open", "NodeSocketFloat", 1.0), ("Spin", "NodeSocketFloat", 0.0),
              ("Phase", "NodeSocketFloat", 0.0), ("Melt", "NodeSocketFloat", 0.0),
              ("Gravity", "NodeSocketVector", (0.0, 0.0, -1.0)), ("Tremor", "NodeSocketFloat", 0.4)]
    ng, t, gi, go = gn_group("FluidGN", inputs)
    I = gi.outputs
    pos = t.node("GeometryNodeInputPosition").outputs[0]
    n = t.normalize(pos)
    nx, ny, nz = t.xyz(n)
    ang = t.math("ARCCOSINE", t.math("MINIMUM", t.mx(ny, -1.0), 1.0))

    # Eyeball: ray from the centre along n against spheres around (0, EYE_C, 0).
    nc = t.mul(ny, EYE_C)
    nc2 = t.mul(nc, nc)
    disc_lid = t.add(nc2, (EYE_R + CORNEA + LID_T) ** 2 - EYE_C ** 2)
    disc_eb = t.add(nc2, EYE_R ** 2 - EYE_C ** 2)
    t_lid = t.add(nc, t.math("SQRT", t.mx(disc_lid, 0.0)))
    sq_eb = t.math("SQRT", t.mx(disc_eb, 0.0))
    t_hidden = t.sub(t.add(nc, sq_eb), 0.03)                # just under the eyeball surface: a gentle lid roll
    front = t.math("GREATER_THAN", ny, 0.0)                 # the eyeball is in front, never behind
    hit_lid = t.mul(t.math("GREATER_THAN", disc_lid, 0.0), front)
    hit_eb = t.mul(t.math("GREATER_THAN", disc_eb, 0.0005), front)
    lid_r = t.mul(t_lid, hit_lid)
    # Polynomial smooth union of the body sphere and the lid shell (exactly max() when far apart).
    k = 0.07
    hh = t.div(t.mx(t.sub(k, t.math("ABSOLUTE", t.sub(lid_r, R))), 0.0), k)
    r_lidded = t.add(t.mx(lid_r, R), t.mul(t.mul(hh, hh), k * 0.25))

    # Aperture: an almond in the eye's frame (counter-rotated by the fluid's spin).
    spin = I["Spin"]
    cs, sn = t.math("COSINE", spin), t.math("SINE", spin)
    xe = t.add(t.mul(nx, cs), t.mul(nz, sn))
    ze = t.sub(t.mul(nz, cs), t.mul(nx, sn))
    A = 0.255
    uu = t.div(xe, A)
    curve = t.pow(t.mx(t.sub(1.0, t.mul(uu, uu)), 0.0), 0.8)
    opn = I["Eye Open"]
    shut = t.mul(t.sub(1.0, opn), 0.03)                     # fully closed: no slit at all
    top = t.sub(t.mul(t.add(t.mul(curve, 0.112), 0.010), opn), shut)
    bot = t.add(t.mul(t.mul(curve, opn), -0.088), shut)
    sdf = t.mx(t.mx(t.sub(ze, top), t.sub(bot, ze)), t.mul(t.sub(t.math("ABSOLUTE", uu), 1.0), A))
    W = 0.022
    outside = t.smoothstep(-W, W, sdf)
    outside = t.mx(outside, t.sub(1.0, hit_eb))             # no aperture off the eyeball
    r_base = t.mix(t_hidden, r_lidded, outside)

    # Rosensweig spikes on Poisson-disk sites.
    def named(name):
        a = t.node("GeometryNodeInputNamedAttribute", data_type="FLOAT")
        a.inputs["Name"].default_value = name
        return a.outputs["Attribute"]

    def cone(q):                                             # concave flanks, C2-smooth foot
        one_q = t.mx(t.sub(1.0, q), 0.0)
        return t.mul(t.pow(one_q, 1.5), t.smoothstep(0.0, 0.35, one_q))

    p1, p2 = cone(named("spike_q1")), cone(named("spike_q2"))
    prof = t.add(t.mul(p1, t.madd(named("spike_r1"), 0.6, 0.7)), t.mul(p2, t.madd(named("spike_r2"), 0.6, 0.7)))
    tip = t.mx(p1, p2)
    ph = t.mul(I["Phase"], 2 * math.pi)
    orbit = t.vec(t.mul(t.math("COSINE", ph), 0.9), t.mul(t.math("SINE", ph), 0.9), 0.0)
    flow = t.noise(t.vadd(t.vscale(n, 1.6), orbit), scale=1.0, detail=1.0)
    mod = t.madd(flow, 0.9, 0.55)
    front = t.mul(I["Punch Age"], 8.0)
    wv = t.div(t.sub(ang, front), 0.45)
    wave = t.mul(I["Punch"], t.math("EXPONENT", t.mul(t.mul(wv, wv), -1.0)))
    h = t.mul(t.mul(I["Spike Height"], prof), mod)
    h = t.mul(h, t.madd(wave, 1.3, 1.0))
    calm = t.smoothstep(t.mix(-0.12, 0.40, opn), t.mix(0.04, 0.66, opn), ang)
    h = t.mul(t.mul(h, calm), t.mul(outside, t.sub(1.0, I["Melt"])))
    r = t.add(r_base, h)
    p = t.vscale(n, r)

    # Melt: flatten along gravity, spread, and drip from the underside.
    g = I["Gravity"]
    melt = I["Melt"]
    pg = t.dot(p, g)
    p = t.vsub(p, t.vscale(g, t.mul(pg, t.mul(melt, 0.38))))
    perp = t.vsub(p, t.vscale(g, pg))
    p = t.vadd(p, t.vscale(perp, t.mul(melt, 0.14)))
    low = t.mx(t.sub(t.dot(n, g), 0.05), 0.0)
    drip = t.noise(t.vadd(t.vscale(n, 5.0), orbit), scale=1.0, detail=2.0)
    sag = t.add(t.mul(t.pow(low, 1.5), 0.30), t.mul(t.pow(low, 3.0), t.mul(drip, 1.1)))
    p = t.vadd(p, t.vscale(g, t.mul(sag, melt)))

    # Microscopic tremor: a fine noise field drifting on a circle.
    tn = t.sub(t.noise(t.vadd(t.vscale(n, 13.0), t.vscale(orbit, 0.6)), scale=1.0, detail=2.0), 0.5)
    p = t.vadd(p, t.vscale(n, t.mul(tn, t.mul(I["Tremor"], 0.007))))

    sp = t.node("GeometryNodeSetPosition")
    t.link(I["Geometry"], sp.inputs["Geometry"])
    t.link(p, sp.inputs["Position"])
    store = t.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain="POINT")
    t.link(sp.outputs[0], store.inputs["Geometry"])
    store.inputs["Name"].default_value = "tip"
    t.link(tip, store.inputs["Value"])
    t.link(store.outputs[0], go.inputs[0])
    return ng


# ----------------------------------------------------------------------------- materials

def ferrofluid_material():
    """Black colloid: near-zero albedo, a sharp dielectric reflection, and a thin oily film
    whose thickness drifts over the surface and thins at the tips (iridescent sheen)."""
    m, t = new_material("Ferrofluid")
    tc = t.node("ShaderNodeTexCoord").outputs["Object"]
    tip = t.node("ShaderNodeAttribute", attribute_name="tip").outputs["Fac"]
    drift = t.noise(tc, scale=2.2, detail=3.0)
    film = t.add(t.add(t.mul(drift, 75.0), 250.0), t.mul(tip, -25.0))   # 250-325 nm: gold..violet, never teal
    rough = t.add(t.mul(t.noise(tc, scale=7.0, detail=2.0), 0.05), 0.035)
    bump = t.node("ShaderNodeBump", invert=False)
    t.feed(bump, {"Strength": 0.06, "Distance": 0.004, "Height": t.noise(tc, scale=55.0, detail=3.0)})
    bsdf = principled(t, **{"Base Color": (0.0035, 0.0032, 0.0042, 1), "Metallic": 0.0, "Roughness": rough,
                            "IOR": 1.52, "Thin Film Thickness": film, "Thin Film IOR": 1.36,
                            "Normal": bump.outputs[0]})
    output(t, surface=bsdf)
    return m


def eye_material():
    """Liquid-metal sclera, a per-pixel magma iris (stroma fibres, crypts, a collarette, a dark
    limbal ring and a glowing pupillary rim) and a black mirror pupil. 'pupil' and 'iris_glow'
    are value nodes the controller drives."""
    m, t = new_material("ThirdEye")
    tc = t.node("ShaderNodeTexCoord").outputs["Object"]
    n = t.normalize(tc)
    nx, ny, nz = t.xyz(n)
    theta = t.math("ARCCOSINE", t.math("MINIMUM", t.mx(ny, -1.0), 1.0))
    psi = t.math("ARCTAN2", nz, nx)
    rho = t.div(theta, math.radians(26.0))
    pupil_node = t.node("ShaderNodeValue", label="pupil", name="pupil")
    pupil_node.outputs[0].default_value = 0.33
    glow_node = t.node("ShaderNodeValue", label="iris_glow", name="iris_glow")
    glow_node.outputs[0].default_value = 1.0
    rp = pupil_node.outputs[0]
    s = t.div(t.sub(rho, rp), t.sub(1.0, rp))                # 0 at the pupil edge, 1 at the limbus
    cps, sps = t.math("COSINE", psi), t.math("SINE", psi)
    polar = lambda f, k: t.vec(t.mul(cps, f), t.mul(sps, f), t.mul(s, k))
    fibres = t.noise(polar(6.0, 1.1), scale=2.0, detail=6.0, roughness=0.55)
    fine = t.noise(polar(14.0, 0.6), scale=2.5, detail=3.0)
    vor = t.node("ShaderNodeTexVoronoi", feature="F1", distance="EUCLIDEAN")
    t.feed(vor, {"Vector": polar(2.6, 3.0), "Scale": 2.2})
    crypt = t.sub(1.0, t.smoothstep(0.05, 0.32, vor.outputs["Distance"]))
    crypt = t.mul(crypt, t.smoothstep(0.38, 0.5, s))         # crypts live outside the collarette
    sc = t.add(0.30, t.mul(t.sub(t.noise(polar(3.0, 0.0), scale=1.4, detail=2.0), 0.5), 0.12))
    dc = t.div(t.sub(s, sc), 0.035)
    coll = t.math("EXPONENT", t.mul(t.mul(dc, dc), -1.0))
    limbal = t.smoothstep(0.74, 1.0, s)
    rim = t.math("EXPONENT", t.mul(t.mul(t.div(s, 0.05), t.div(s, 0.05)), -1.0))
    v = t.add(t.add(t.mul(fibres, 0.55), t.mul(fine, 0.18)), t.mul(coll, 0.38))
    v = t.sub(t.sub(t.add(v, t.mul(t.sub(1.0, s), 0.18)), t.mul(crypt, 0.32)), t.mul(limbal, 0.62))
    v = t.clamp01(t.add(v, -0.02))
    iris_col = t.ramp(v, MAGMA)
    rim_col = t.ramp(t.add(t.mul(rim, 0.25), 0.72), MAGMA)

    pupil_mask = t.sub(1.0, t.smoothstep(t.sub(rp, 0.025), t.add(rp, 0.004), rho))
    iris_mask = t.sub(1.0, t.smoothstep(0.985, 1.035, rho))
    sclera = (0.98, 0.84, 0.66, 1.0)
    base = t.mixc(sclera, t.mixc(iris_col, (0.0, 0.0, 0.0, 1.0), pupil_mask), iris_mask)
    metal = t.sub(1.0, iris_mask)
    rough = t.mix(0.07, t.mix(0.32, 0.008, pupil_mask), iris_mask)
    mult = t.node("ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    t.feed(mult, {"Factor": 1.0, 6: iris_col, 7: (0.55, 0.55, 0.55, 1.0)})
    em_iris = t.node("ShaderNodeMix", data_type="RGBA", blend_type="ADD")
    t.feed(em_iris, {"Factor": rim, 6: mult.outputs[2], 7: rim_col})
    em_strength = t.mul(t.mul(iris_mask, t.sub(1.0, pupil_mask)), t.mul(glow_node.outputs[0], t.madd(rim, 6.0, 1.2)))
    bsdf = principled(t, **{"Base Color": base, "Metallic": metal, "Roughness": rough,
                            "IOR": t.mix(1.5, 1.85, pupil_mask), "Coat Weight": iris_mask, "Coat Roughness": 0.0,
                            "Coat IOR": 1.38, "Emission Color": em_iris.outputs[2], "Emission Strength": em_strength})
    output(t, surface=bsdf)
    return m


# ----------------------------------------------------------------------------- objects

def eyeball_mesh(seg=160, ring=96):
    from mathutils import Matrix
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=EYE_R)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(-math.pi / 2, 3, "X"))  # pole -> +Y
    for v in bm.verts:                                       # corneal dome over the iris
        d = v.co.normalized()
        th = math.acos(max(-1.0, min(1.0, d.y)))
        if th < math.radians(30):
            v.co = d * (EYE_R + CORNEA * math.cos(th / math.radians(30) * math.pi / 2) ** 2)
    me = bpy.data.meshes.new("EYEBALL")
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    return bpy.data.objects.new("EYEBALL", me)


def build_hero(collection):
    root = bpy.data.objects.new("HERO_ROOT", None)
    face = bpy.data.objects.new("HERO_FACE", None)
    pivot = bpy.data.objects.new("EYE_PIVOT", None)
    for o in (root, face, pivot):
        collection.objects.link(o)
    root.location = (0.0, 0.0, 1.75)
    face.parent = root
    face.rotation_mode = "QUATERNION"
    pivot.parent = face
    pivot.location = (0.0, EYE_C, 0.0)

    me, sites, site_idx = fluid_mesh()
    fluid = bpy.data.objects.new("FLUID", me)
    collection.objects.link(fluid)
    fluid.parent = face
    fluid.rotation_mode = "XYZ"
    mod = fluid.modifiers.new("Fluid", "NODES")
    mod.node_group = fluid_nodes()
    fluid.data.materials.append(ferrofluid_material())

    eye = eyeball_mesh()
    collection.objects.link(eye)
    eye.parent = pivot
    eye.rotation_mode = "QUATERNION"
    eye.data.materials.append(eye_material())
    for o in (fluid, eye):
        o.cycles.use_motion_blur = True
    return {"root": root, "face": face, "fluid": fluid, "pivot": pivot, "eye": eye,
            "sites": sites, "site_idx": site_idx}


# ----------------------------------------------------------------------------- bullet-time droplets

def droplet_nodes(mat):
    from common import gn_group
    ng, t, gi, go = gn_group("DropletsGN", [("Geometry", "NodeSocketGeometry"), ("Tau", "NodeSocketFloat", 0.0),
                                            ("Recall", "NodeSocketFloat", 0.0), ("On", "NodeSocketFloat", 0.0)])
    I = gi.outputs

    def named(name, kind="FLOAT_VECTOR"):
        a = t.node("GeometryNodeInputNamedAttribute", data_type=kind)
        a.inputs["Name"].default_value = name
        return a.outputs["Attribute"]

    p0, v = named("p0"), named("v")
    g = (0.0, 0.0, -9.81 * 0.45)
    tau = I["Tau"]
    flight = t.vadd(t.vadd(p0, t.vscale(v, tau)), t.vscale(g, t.mul(t.mul(tau, tau), 0.5)))
    home = t.vadd((0.0, 0.0, 1.75), t.vscale(t.normalize(t.vsub(flight, (0.0, 0.0, 1.75))), 1.04))
    pos = t.mixv(flight, home, I["Recall"])
    vel = t.vadd(v, t.vscale(g, tau))                                   # physical velocity: the teardrop axis
    sp = t.node("GeometryNodeSetPosition")
    t.link(I["Geometry"], sp.inputs["Geometry"])
    t.link(pos, sp.inputs["Position"])
    ico = t.node("GeometryNodeMeshUVSphere")
    t.feed(ico, {"Segments": 24, "Rings": 12, "Radius": 1.0})
    sm = t.node("GeometryNodeSetShadeSmooth")
    t.link(ico.outputs["Mesh"], sm.inputs["Geometry"])
    align = t.node("FunctionNodeAlignRotationToVector", axis="Z")
    t.link(vel, align.inputs["Vector"])
    inst = t.node("GeometryNodeInstanceOnPoints")
    t.link(sp.outputs[0], inst.inputs["Points"])
    t.link(sm.outputs[0], inst.inputs["Instance"])
    t.link(align.outputs[0], inst.inputs["Rotation"])
    r = t.mul(named("r", "FLOAT"), I["On"])
    stretch = t.add(1.0, t.mul(t.length(vel), t.mul(t.sub(1.0, I["Recall"]), 0.55)))
    t.link(t.vec(r, r, t.mul(r, stretch)), inst.inputs["Scale"])
    smat = t.node("GeometryNodeSetMaterial")
    t.link(inst.outputs[0], smat.inputs["Geometry"])
    smat.inputs["Material"].default_value = mat
    t.link(smat.outputs[0], go.inputs[0])
    return ng


def build_droplets(coll, H, face_q, spin, frame, n=150, seed=5):
    """Droplets thrown from spike tips facing the camera at the explosion frame."""
    from choreo import quat_rot
    rng = np.random.default_rng(seed)
    sites = H["sites"]
    q = face_q[frame]
    a = spin[frame]
    ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    world_dirs = np.array([quat_rot(q, ry @ s) for s in sites])
    view = np.array([quat_rot(q, np.array([0.0, 1.0, 0.0]))])[0]
    score = world_dirs @ view + 0.35 * rng.random(len(sites))
    pick = np.argsort(-score)[:n]
    d = world_dirs[pick]
    p0 = np.array([0.0, 0.0, 1.75]) + d * 1.28
    speed = rng.uniform(1.6, 4.4, n)
    v = d * speed[:, None] + rng.normal(0, 0.35, (n, 3)) + np.array([0, 0, 0.6])
    r = 0.012 + 0.05 * rng.random(n) ** 2.5
    me = bpy.data.meshes.new("DROPLETS")
    me.from_pydata(p0.tolist(), [], [])
    for name, vals in (("p0", p0), ("v", v)):
        at = me.attributes.new(name, "FLOAT_VECTOR", "POINT")
        at.data.foreach_set("vector", vals.astype(np.float32).ravel())
    at = me.attributes.new("r", "FLOAT", "POINT")
    at.data.foreach_set("value", r.astype(np.float32))
    ob = bpy.data.objects.new("DROPLETS", me)
    coll.objects.link(ob)
    mod = ob.modifiers.new("Droplets", "NODES")
    mod.node_group = droplet_nodes(bpy.data.materials["Ferrofluid"])
    ob.cycles.use_motion_blur = True
    return ob
