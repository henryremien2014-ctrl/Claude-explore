"""Everything around the hero: the spectrogram canyon, the tape rings, the halo and the
Seed-of-Life mandala, the 16-step light sequencer, phosphene dust, haze and lights."""
import math

import bpy
import numpy as np

from common import (ANALYSIS, CORAL, GOLD, MAGENTA, MAGMA, ORANGE, PALE, VIOLET, WORK, Tree, gn_group, hex_lin,
                    new_material, output, principled, set_visibility)

CANYON_L = 60.0      # metres of canyon = one full loop of spectrogram
STRIP_X0, STRIP_X1 = -30.0, 30.0 + CANYON_L   # static strip; the object slides by -scroll * L
CANYON_W = 14.0      # half width: bass on the centre line, 14 kHz on the rims
RIVER_Z = -0.4


def spectrogram_image(name="spectrogram", blur=None):
    tex = np.load(ANALYSIS / "spectrogram_window.npy")            # (rows=freq, cols=time), 0..1
    if blur:
        from scipy.ndimage import gaussian_filter
        tex = gaussian_filter(tex, blur, mode=("nearest", "wrap"))
    rows, cols = tex.shape
    # G: loudness relative to its own frequency row (median -> 0, 99th percentile -> 1)
    med = np.median(tex, axis=1, keepdims=True)
    hi = np.percentile(tex, 99, axis=1, keepdims=True)
    rel = np.clip((tex - med) / np.maximum(hi - med, 1e-3), 0.0, 1.0)
    path = WORK / f"{name}.exr"
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, width=cols, height=rows, float_buffer=True, alpha=False)
    px = np.ones((rows, cols, 4), np.float32)
    px[..., 0] = tex
    px[..., 1] = rel
    px[..., 2] = tex
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = str(path)
    img.file_format = "OPEN_EXR"
    img.save()
    img.source = "FILE"
    img.colorspace_settings.name = "Non-Color"
    img.reload()
    return img


# ----------------------------------------------------------------------------- canyon

def set_material(t, geo, mat):
    sm = t.node("GeometryNodeSetMaterial")
    t.link(geo, sm.inputs["Geometry"])
    sm.inputs["Material"].default_value = mat
    return sm.outputs[0]


def canyon_nodes(img, img_geo, mat):
    ng, t, gi, go = gn_group("CanyonGN", [("Geometry", "NodeSocketGeometry"), ("Scroll", "NodeSocketFloat", 0.0),
                                          ("Relief", "NodeSocketFloat", 1.0)])
    I = gi.outputs
    grid = t.node("GeometryNodeMeshGrid")
    t.feed(grid, {"Size X": STRIP_X1 - STRIP_X0, "Size Y": 2 * CANYON_W, "Vertices X": 1920, "Vertices Y": 448})
    pos = t.node("GeometryNodeInputPosition").outputs[0]
    x0, y, _ = t.xyz(pos)
    x = t.add(x0, 0.5 * (STRIP_X0 + STRIP_X1))
    ay = t.math("ABSOLUTE", y)
    u = t.math("FRACT", t.add(t.div(x, CANYON_L), I["Scroll"]))
    v = t.clamp01(t.div(ay, CANYON_W))
    def sample(image):
        tx = t.node("GeometryNodeImageTexture", interpolation="Linear", extension="REPEAT")
        tx.inputs["Image"].default_value = image
        t.link(t.vec(u, v, 0.0), tx.inputs["Vector"])
        r, g, _ = t.xyz(tx.outputs["Color"])
        return t.clamp01(r), t.clamp01(g)

    S, rel = sample(img)
    Sg, _ = sample(img_geo)
    wall = t.smoothstep(1.5, 6.5, ay)
    base = t.add(RIVER_Z, t.mul(t.pow(t.smoothstep(1.8, CANYON_W, ay), 1.35), 6.5))
    # break the mirror symmetry a little with slow terrain noise that travels with the tape
    flow_x = t.mul(u, CANYON_L)
    terr = t.noise(t.vec(t.mul(flow_x, 0.08), t.mul(y, 0.12), 0.0), scale=1.0, detail=3.0)
    base = t.add(base, t.mul(t.mul(t.sub(terr, 0.5), 1.4), wall))
    ridge = t.mul(t.pow(Sg, 1.6), t.add(0.12, t.mul(wall, 1.7)))
    z = t.add(base, t.mul(ridge, I["Relief"]))
    sp = t.node("GeometryNodeSetPosition")
    t.link(grid.outputs["Mesh"], sp.inputs["Geometry"])
    t.link(t.vec(x, y, z), sp.inputs["Position"])
    geo = sp.outputs[0]
    for name, val in (("spec", S), ("rel", rel), ("row", v), ("flow_x", flow_x)):
        st = t.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain="POINT")
        t.link(geo, st.inputs["Geometry"])
        st.inputs["Name"].default_value = name
        t.link(val, st.inputs["Value"])
        geo = st.outputs[0]
    sm = t.node("GeometryNodeSetShadeSmooth")
    t.link(geo, sm.inputs["Geometry"])
    t.link(set_material(t, sm.outputs[0], mat), go.inputs[0])
    return ng


def obsidian_material():
    """Obsidian crust. Lava shows in the cracks only where the spectrum is loud; loud harmonics
    tint the ridges violet; the bass river is dark crust split by glowing seams that widen and
    melt open where the bass is loud."""
    m, t = new_material("Canyon")
    S = t.node("ShaderNodeAttribute", attribute_name="spec").outputs["Fac"]
    G = t.node("ShaderNodeAttribute", attribute_name="rel").outputs["Fac"]
    row = t.node("ShaderNodeAttribute", attribute_name="row").outputs["Fac"]
    fx = t.node("ShaderNodeAttribute", attribute_name="flow_x").outputs["Fac"]
    pos = t.node("ShaderNodeNewGeometry").outputs["Position"]
    _, py, pz = t.xyz(pos)
    cc = t.vec(fx, py, t.mul(pz, 0.5))
    nz = t.node("ShaderNodeTexNoise")
    t.feed(nz, {"Vector": cc, "Scale": 0.6, "Detail": 3.0})
    warp = t.vscale(t.vsub(nz.outputs["Color"], (0.5, 0.5, 0.5)), 0.9)
    cw = t.vadd(cc, warp)
    vor = t.node("ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE")
    t.feed(vor, {"Vector": cw, "Scale": 1.7, "Randomness": 1.0})
    crack = t.sub(1.0, t.smoothstep(0.0, 0.028, vor.outputs["Distance"]))
    fine = t.node("ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE")
    t.feed(fine, {"Vector": cw, "Scale": 6.0})
    crack = t.mx(crack, t.mul(t.sub(1.0, t.smoothstep(0.0, 0.03, fine.outputs["Distance"])), 0.35))
    river = t.sub(1.0, t.smoothstep(0.10, 0.19, row))            # the bass rows: |y| < ~2 m
    seam_w = t.add(0.022, t.mul(t.mul(G, G), 0.10))              # loud bass melts the crust: cracks widen
    molten = t.sub(1.0, t.smoothstep(0.0, seam_w, vor.outputs["Distance"]))
    wall = t.smoothstep(0.12, 0.45, row)
    loud = t.smoothstep(0.45, 1.0, G)                        # loud for its own band, not just loud
    lava_col = t.ramp(t.add(0.52, t.mul(G, 0.40)), MAGMA)
    river_col = t.mixc(t.ramp(t.add(0.48, t.mul(G, 0.16)), MAGMA), t.ramp(t.add(0.70, t.mul(G, 0.26)), MAGMA), molten)
    crack_em = t.mul(t.mul(crack, t.mul(loud, loud)), t.mul(t.sub(1.0, river), 1.1))
    river_em = t.mul(river, t.mul(t.add(0.04, t.mul(t.pow(G, 1.6), 1.6)), t.add(0.10, t.mul(molten, 0.90))))
    ridge_em = t.mul(t.mul(t.pow(G, 3.0), wall), 0.10)
    em_col = t.mixc(lava_col, t.ramp(t.add(0.22, t.mul(S, 0.16)), MAGMA), t.div(ridge_em, t.add(t.add(crack_em, ridge_em), 1e-4)))
    em_col = t.mixc(em_col, river_col, river)
    em = t.add(t.add(crack_em, river_em), ridge_em)
    ridge_col = t.mixc((0.008, 0.006, 0.010, 1.0), tuple(c * 0.5 for c in VIOLET[:3]) + (1.0,),
                       t.mul(t.pow(S, 2.2), wall))
    rough = t.add(0.14, t.mul(t.noise(cc, scale=0.7, detail=4.0), 0.3))
    bump = t.node("ShaderNodeBump")
    t.feed(bump, {"Strength": 0.3, "Distance": 0.05, "Height": t.noise(cc, scale=3.0, detail=2.0)})
    bsdf = principled(t, **{"Base Color": ridge_col, "Roughness": rough, "IOR": 1.49,
                            "Emission Color": em_col, "Emission Strength": em, "Normal": bump.outputs[0]})
    output(t, surface=bsdf)
    return m


def build_canyon(coll, img):
    """The canyon is displaced once into a static strip two loops long; scrolling it is a rigid
    slide of the object, so Cycles keeps its BVH (and light tree) across frames."""
    mat = obsidian_material()
    tmp = bpy.data.objects.new("CANYON_GEN", bpy.data.meshes.new("CANYON_GEN"))
    coll.objects.link(tmp)
    mod = tmp.modifiers.new("Canyon", "NODES")
    mod.node_group = canyon_nodes(img, spectrogram_image("spectrogram_geo", blur=(1.6, 5.0)), mat)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    me.name = "CANYON"
    bpy.data.objects.remove(tmp)
    if not me.materials:
        me.materials.append(mat)
    ob = bpy.data.objects.new("CANYON", me)
    coll.objects.link(ob)
    ob.cycles.use_motion_blur = False
    return ob


# ----------------------------------------------------------------------------- tape rings

def tape_material(img):
    m, t = new_material("Tape")
    uv = t.node("ShaderNodeTexCoord").outputs["UV"]
    ux, uy, _ = t.xyz(uv)
    tx = t.node("ShaderNodeTexImage", interpolation="Linear", extension="REPEAT")
    tx.image = img
    t.link(t.vec(ux, t.add(t.mul(uy, 0.9), 0.05), 0.0), tx.inputs["Vector"])
    S = tx.outputs["Color"]
    sv = t.xyz(S)[0]
    col = t.ramp(sv, MAGMA)
    edge = t.mul(t.smoothstep(0.0, 0.06, uy), t.smoothstep(1.0, 0.94, uy))
    bsdf = principled(t, **{"Base Color": (0.012, 0.008, 0.007, 1.0), "Roughness": 0.22, "IOR": 1.5,
                            "Emission Color": col, "Emission Strength": t.mul(t.mul(t.pow(sv, 3.0), edge), 0.9)})
    output(t, surface=bsdf)
    return m


def ring_mesh(name, radius, width, seg=720):
    a = np.linspace(0, 2 * np.pi, seg + 1)[:-1]
    top = np.stack([radius * np.cos(a), radius * np.sin(a), np.full(seg, width / 2)], 1)
    bot = top.copy()
    bot[:, 2] = -width / 2
    verts = np.vstack([bot, top])
    faces = [(i, (i + 1) % seg, seg + (i + 1) % seg, seg + i) for i in range(seg)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts.tolist(), [], faces)
    uvl = me.uv_layers.new()
    uvs = []
    for i in range(seg):
        u0, u1 = i / seg, (i + 1) / seg
        uvs += [(u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)]
    uvl.data.foreach_set("uv", np.array(uvs, np.float32).ravel())
    me.polygons.foreach_set("use_smooth", np.ones(seg, bool))
    return me


def build_rings(coll, parent, img):
    mat = tape_material(img)
    rings = []
    spec = ((2.45, 0.050, (math.radians(72), 0.0, 0.0)),
            (3.05, 0.042, (math.radians(-28), math.radians(58), 0.0)),
            (3.75, 0.036, (math.radians(18), math.radians(-35), math.radians(20))))
    for i, (r, w, rot) in enumerate(spec):
        tilt = bpy.data.objects.new(f"RING_TILT_{i}", None)
        coll.objects.link(tilt)
        tilt.parent = parent
        tilt.rotation_euler = rot
        ob = bpy.data.objects.new(f"RING_{i}", ring_mesh(f"RING_{i}", r, w))
        coll.objects.link(ob)
        ob.parent = tilt
        ob.data.materials.append(mat)
        rings.append(ob)
    return rings


# ----------------------------------------------------------------------------- halo and mandala

def emission_material(name, color, strength, value_name=None):
    m, t = new_material(name)
    e = t.node("ShaderNodeEmission")
    s = strength
    if value_name:
        val = t.node("ShaderNodeValue", name=value_name, label=value_name)
        val.outputs[0].default_value = 1.0
        s = t.mul(val.outputs[0], strength)
    t.feed(e, {"Color": color, "Strength": s})
    output(t, surface=e)
    return m


def build_halo(coll, face):
    """Halo ring and the Seed of Life, behind the hero in the plane facing the camera."""
    holder = bpy.data.objects.new("HALO_PLANE", None)
    coll.objects.link(holder)
    holder.parent = face
    holder.location = (0.0, -1.05, 0.0)
    holder.rotation_euler = (math.pi / 2, 0.0, 0.0)            # local XY plane -> faces +Y
    spinner = bpy.data.objects.new("MANDALA_SPIN", None)
    coll.objects.link(spinner)
    spinner.parent = holder

    bpy.ops.mesh.primitive_torus_add(major_radius=1.62, minor_radius=0.012, major_segments=256, minor_segments=10)
    halo = bpy.context.active_object
    for c in halo.users_collection:
        c.objects.unlink(halo)
    coll.objects.link(halo)
    halo.name = "HALO"
    halo.parent = holder
    halo.data.materials.append(emission_material("Halo", MAGENTA, 18.0, "halo_glow"))

    mat = emission_material("Mandala", GOLD, 14.0, "mandala_glow")
    r = 0.81
    circles = []
    centres = [(0.0, 0.0)] + [(r * math.cos(k * math.pi / 3 + math.pi / 2), r * math.sin(k * math.pi / 3 + math.pi / 2))
                              for k in range(6)]
    for k, (cx, cy) in enumerate(centres):
        cu = bpy.data.curves.new(f"SEED_{k}", "CURVE")
        cu.dimensions = "3D"
        sp = cu.splines.new("POLY")
        n = 256
        start = math.atan2(-cy, -cx) if k else math.pi / 2       # each petal starts drawing at the centre
        sp.points.add(n)
        for i in range(n + 1):
            a = start + 2 * math.pi * i / n
            sp.points[i].co = (cx + r * math.cos(a), cy + r * math.sin(a), 0.0, 1.0)
        cu.bevel_depth = 0.0055
        cu.bevel_resolution = 2
        cu.bevel_factor_mapping_end = "SPLINE"
        cu.bevel_factor_end = 0.0                             # drawn on the drop
        cu.use_fill_caps = True
        ob = bpy.data.objects.new(f"SEED_{k}", cu)
        coll.objects.link(ob)
        ob.parent = spinner
        cu.materials.append(mat)
        circles.append(ob)
    return {"halo": halo, "holder": holder, "spinner": spinner, "seeds": circles}


# ----------------------------------------------------------------------------- sequencer, dust, haze, lights

def build_sequencer(coll, root):
    """16 panels in a ring above the hero, seen only in reflections. Object colour carries each
    step's brightness, so one material serves all 16."""
    m, t = new_material("Sequencer")
    oi = t.node("ShaderNodeObjectInfo")
    e = t.node("ShaderNodeEmission")
    t.feed(e, {"Color": oi.outputs["Color"], "Strength": 22.0})
    output(t, surface=e)
    panels = []
    for k in range(16):
        a = 2 * math.pi * k / 16
        me = bpy.data.meshes.new(f"SEQ_{k}")
        w, h = 0.55, 0.16
        me.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], [], [(0, 1, 2, 3)])
        ob = bpy.data.objects.new(f"SEQ_{k}", me)
        coll.objects.link(ob)
        ob.parent = root
        ob.location = (3.4 * math.cos(a), 3.4 * math.sin(a), 2.4)
        ob.rotation_euler = (math.radians(55), 0.0, a + math.pi / 2)
        me.materials.append(m)
        set_visibility(ob, camera=False, diffuse=False, glossy=True, transmission=False, scatter=False, shadow=False)
        panels.append(ob)
    return panels


def dust_nodes(mat):
    ng, t, gi, go = gn_group("DustGN", [("Geometry", "NodeSocketGeometry"), ("Phase", "NodeSocketFloat", 0.0)])
    I = gi.outputs

    def named(name, kind="FLOAT"):
        a = t.node("GeometryNodeInputNamedAttribute", data_type=kind)
        a.inputs["Name"].default_value = name
        return a.outputs["Attribute"]

    ph = t.mul(I["Phase"], 2 * math.pi)
    k = named("k")
    off = named("off")
    a = t.add(t.mul(ph, k), off)
    orbit = t.vadd(t.vscale(named("ax1", "FLOAT_VECTOR"), t.math("COSINE", a)),
                   t.vscale(named("ax2", "FLOAT_VECTOR"), t.math("SINE", a)))
    p = t.vadd(t.node("GeometryNodeInputPosition").outputs[0], t.vscale(orbit, named("orad")))
    rot = t.node("ShaderNodeVectorRotate", rotation_type="Z_AXIS")
    t.feed(rot, {"Vector": p, "Center": (0, 0, 1.75), "Angle": ph})
    sp = t.node("GeometryNodeSetPosition")
    t.link(I["Geometry"], sp.inputs["Geometry"])
    t.link(rot.outputs[0], sp.inputs["Position"])
    ico = t.node("GeometryNodeMeshIcoSphere")
    t.feed(ico, {"Radius": 1.0, "Subdivisions": 1})
    inst = t.node("GeometryNodeInstanceOnPoints")
    t.link(sp.outputs[0], inst.inputs["Points"])
    t.link(ico.outputs["Mesh"], inst.inputs["Instance"])
    t.link(t.vec(named("size"), named("size"), named("size")), inst.inputs["Scale"])
    t.link(set_material(t, inst.outputs[0], mat), go.inputs[0])
    return ng


def build_dust(coll, n=600, seed=11):
    rng = np.random.default_rng(seed)
    r = 1.7 + 5.5 * rng.random(n) ** 1.8
    th = rng.uniform(0, 2 * np.pi, n)
    z = rng.normal(1.8, 0.9, n)
    pts = np.stack([r * np.cos(th), r * np.sin(th), z], 1)
    me = bpy.data.meshes.new("DUST")
    me.from_pydata(pts.tolist(), [], [])
    ax1 = rng.normal(size=(n, 3))
    ax1 /= np.linalg.norm(ax1, axis=1, keepdims=True)
    ax2 = np.cross(ax1, rng.normal(size=(n, 3)))
    ax2 /= np.linalg.norm(ax2, axis=1, keepdims=True)
    attrs = {"k": rng.integers(1, 4, n).astype(np.float32) * rng.choice([-1, 1], n),
             "off": rng.uniform(0, 2 * np.pi, n), "orad": rng.uniform(0.08, 0.45, n),
             "size": 0.003 + 0.008 * rng.random(n) ** 3, "hue": 0.45 + 0.55 * rng.random(n)}
    for name, vals in attrs.items():
        a = me.attributes.new(name, "FLOAT", "POINT")
        a.data.foreach_set("value", np.asarray(vals, np.float32))
    for name, vals in (("ax1", ax1), ("ax2", ax2)):
        a = me.attributes.new(name, "FLOAT_VECTOR", "POINT")
        a.data.foreach_set("vector", vals.astype(np.float32).ravel())
    ob = bpy.data.objects.new("DUST", me)
    coll.objects.link(ob)
    m, t = new_material("Dust")
    hue = t.node("ShaderNodeAttribute", attribute_name="hue", attribute_type="INSTANCER").outputs["Fac"]
    glow = t.node("ShaderNodeValue", name="dust_glow", label="dust_glow")
    glow.outputs[0].default_value = 1.0
    e = t.node("ShaderNodeEmission")
    t.feed(e, {"Color": t.ramp(hue, MAGMA), "Strength": t.mul(glow.outputs[0], 6.0)})
    output(t, surface=e)
    mod = ob.modifiers.new("Dust", "NODES")
    mod.node_group = dust_nodes(m)
    me.materials.append(m)
    set_visibility(ob, diffuse=False, shadow=False, scatter=False)
    return ob


def build_haze(coll, density=0.022):
    me = bpy.data.meshes.new("HAZE")
    sx, sy, z0, z1 = 36.0, 22.0, -1.0, 13.0
    v = [(x, y, z) for z in (z0, z1) for y in (-sy, sy) for x in (-sx, sx)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me.from_pydata(v, [], f)
    ob = bpy.data.objects.new("HAZE", me)
    coll.objects.link(ob)
    m, t = new_material("Haze")
    val = t.node("ShaderNodeValue", name="haze", label="haze")
    val.outputs[0].default_value = 1.0
    vol = t.node("ShaderNodeVolumePrincipled")
    t.feed(vol, {"Color": (0.95, 0.80, 1.0, 1.0), "Density": t.mul(val.outputs[0], density), "Anisotropy": 0.45})
    output(t, volume=vol)
    me.materials.append(m)
    return ob


def softbox_material(name, color, strength):
    m, t = new_material(name)
    uv = t.node("ShaderNodeTexCoord").outputs["UV"]
    d = t.length(t.vsub(t.vscale(uv, 2.0), (1.0, 1.0, 0.0)))
    fall = t.pow(t.clamp01(t.sub(1.0, d)), 1.6)
    val = t.node("ShaderNodeValue", name="softbox", label="softbox")
    val.outputs[0].default_value = 1.0
    e = t.node("ShaderNodeEmission")
    t.feed(e, {"Color": color, "Strength": t.mul(t.mul(fall, strength), val.outputs[0])})
    output(t, surface=e)
    return m


def build_lights(coll, root):
    from common import look_at_quat
    out = {}
    target = (0.0, 0.0, 1.75)
    for name, col, loc, size, power in (("SB_TOP", GOLD, (0.5, -0.5, 7.5), (9, 9), 34.0),
                                        ("SB_LEFT", VIOLET, (-4.8, 0.8, 2.8), (5, 9), 44.0),
                                        ("SB_RIGHT", MAGENTA, (4.8, -0.6, 2.4), (5, 9), 40.0),
                                        ("SB_BACK", CORAL, (0.0, -5.2, 3.2), (9, 4), 30.0),
                                        ("SB_FRONT", VIOLET, (0.3, 5.5, 3.6), (8, 3), 14.0),
                                        ("SB_STRIP_L", PALE, (-3.2, 2.6, 2.4), (0.5, 6), 90.0),
                                        ("SB_STRIP_R", GOLD, (3.0, 2.9, 1.9), (0.5, 6), 80.0)):
        me = bpy.data.meshes.new(name)
        sx, sy = size
        me.from_pydata([(-sx / 2, -sy / 2, 0), (sx / 2, -sy / 2, 0), (sx / 2, sy / 2, 0), (-sx / 2, sy / 2, 0)], [], [(0, 1, 2, 3)])
        uvl = me.uv_layers.new()
        for i, uv in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
            uvl.data[i].uv = uv
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        ob.location = loc
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = look_at_quat(loc, target, axis="Z")
        me.materials.append(softbox_material(name, col, power))
        set_visibility(ob, camera=False, diffuse=False, shadow=False, scatter=False, transmission=False)
        out[name] = ob
    key = bpy.data.lights.new("KEY", "AREA")
    key.shape, key.size, key.energy, key.color = "DISK", 3.0, 900.0, GOLD[:3]
    kob = bpy.data.objects.new("KEY", key)
    coll.objects.link(kob)
    kob.location = (-2.0, -3.5, 7.0)
    kob.rotation_mode = "QUATERNION"
    kob.rotation_quaternion = look_at_quat(kob.location, target)
    out["KEY"] = kob
    rim = bpy.data.lights.new("RIM", "SPOT")
    rim.energy, rim.color, rim.spot_size, rim.spot_blend = 2500.0, MAGENTA[:3], math.radians(28), 0.6
    rob = bpy.data.objects.new("RIM", rim)
    coll.objects.link(rob)
    rob.location = (1.0, -9.0, 5.5)
    rob.rotation_mode = "QUATERNION"
    rob.rotation_quaternion = look_at_quat(rob.location, target)
    out["RIM"] = rob
    return out


RIVER_XS = (-9.0, 0.0, 9.0)
RIVER_POWER = 9000.0


def build_river_lights(coll):
    """The lava river's light on the canyon walls, the haze and the hero's underside. The canyon's
    own emission is not light-sampled (too costly), so three warm point lights stand in for it just
    above the river; their power follows the bass. Invisible to the camera and to reflections."""
    out = []
    for i, x in enumerate(RIVER_XS):
        lt = bpy.data.lights.new(f"RIVER_{i}", "POINT")
        lt.shadow_soft_size, lt.energy, lt.color = 0.6, RIVER_POWER, (1.0, 0.30, 0.08)
        ob = bpy.data.objects.new(f"RIVER_{i}", lt)
        coll.objects.link(ob)
        ob.location = (x, 0.0, 0.7)
        ob.visible_camera = False
        ob.visible_glossy = False
        out.append(ob)
    return out


def link_lights(lights, receivers, haze=None):
    """Softboxes and the key light sculpt the hero only. Cycles' light linking does not reach
    volumes, so the haze is lit by the unlinked lights: the magenta rim and the river lights."""
    def coll(name, objs):
        c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
        for ob in objs:
            if ob.name not in c.objects:
                c.objects.link(ob)
        return c
    sb = coll("SoftboxLight", receivers)
    key = coll("KeyLight", receivers)
    for name, ob in lights.items():
        if name.startswith("SB_"):
            ob.light_linking.receiver_collection = sb
        elif name == "KEY":
            ob.light_linking.receiver_collection = key
    return sb, key


def world_background(wd, strength=0.06):
    """Deep violet horizon fading to black at the zenith and below: the hero's silhouette and
    spikes always reflect a little form, and wide shots get depth instead of a void."""
    wd.use_nodes = True
    t = Tree(wd.node_tree)
    wd.node_tree.nodes.clear()
    tc = t.node("ShaderNodeTexCoord").outputs["Generated"]
    _, _, z = t.xyz(t.normalize(t.vsub(tc, (0.5, 0.5, 0.5))))
    band = t.math("EXPONENT", t.mul(t.mul(t.sub(z, 0.06), t.sub(z, 0.06)), -18.0))
    col = t.ramp(t.mul(band, 0.42), MAGMA)
    bg = t.node("ShaderNodeBackground")
    t.feed(bg, {"Color": col, "Strength": t.mul(band, strength * 10.0)})
    o = t.node("ShaderNodeOutputWorld")
    t.link(bg.outputs[0], o.inputs["Surface"])
