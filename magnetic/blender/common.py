"""Shared paths, the magma palette and terse node-building helpers for the MAGNETIC scene."""
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]           # magnetic/
ANALYSIS = ROOT / "analysis" / "out"
WORK = Path("/home/user/mag-work")
FPS = 30
FRAMES = 624

# matplotlib's magma, sRGB. The whole film lives on this ramp.
MAGMA_SRGB = [
    (0.00, "000004"), (0.10, "140e36"), (0.20, "3b0f70"), (0.30, "641a80"), (0.40, "8c2981"),
    (0.50, "b73779"), (0.60, "de4968"), (0.70, "f7705c"), (0.80, "fe9f6d"), (0.90, "fecf92"),
    (1.00, "fcfdbf"),
]


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_lin(h, a=1.0):
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)) + (a,)


MAGMA = [(p, hex_lin(h)) for p, h in MAGMA_SRGB]
VIOLET, MAGENTA, CORAL, ORANGE, GOLD, PALE = (hex_lin(h) for h in ("641a80", "b73779", "f7705c", "fe9f6d", "fecf92", "fcfdbf"))


def magma(x):
    """Linear RGB of the magma ramp at x in [0, 1]."""
    x = min(max(x, 0.0), 1.0)
    for (p0, c0), (p1, c1) in zip(MAGMA[:-1], MAGMA[1:]):
        if x <= p1:
            u = (x - p0) / (p1 - p0)
            return tuple(c0[i] + (c1[i] - c0[i]) * u for i in range(3)) + (1.0,)
    return MAGMA[-1][1]


class Tree:
    """Small wrapper to write node graphs as expressions.

    Every helper takes sockets, nodes or plain numbers/tuples and returns an output socket.
    """

    def __init__(self, tree):
        self.tree = tree
        self.nodes = tree.nodes
        self.links = tree.links
        self.x = 0

    def node(self, kind, **props):
        n = self.nodes.new(kind)
        n.location = (self.x, -len(self.nodes) * 12 % 1200)
        self.x += 30
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def _feed(self, sock, value):
        if value is None:
            return
        if isinstance(value, bpy.types.NodeSocket):
            self.links.new(value, sock)
        elif isinstance(value, bpy.types.Node):
            self.links.new(value.outputs[0], sock)
        else:
            sock.default_value = value

    def feed(self, node, inputs):
        """inputs: dict of name-or-index -> value."""
        for k, v in inputs.items():
            sock = node.inputs[k]
            self._feed(sock, v)
        return node

    def link(self, a, b):
        self.links.new(a, b)

    # --- math ------------------------------------------------------------------------------
    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self._feed(n.inputs[0], a)
        if b is not None:
            self._feed(n.inputs[1], b)
        if c is not None:
            self._feed(n.inputs[2], c)
        return n.outputs[0]

    def add(self, a, b): return self.math("ADD", a, b)
    def sub(self, a, b): return self.math("SUBTRACT", a, b)
    def mul(self, a, b): return self.math("MULTIPLY", a, b)
    def div(self, a, b): return self.math("DIVIDE", a, b)
    def pow(self, a, b): return self.math("POWER", a, b)
    def mx(self, a, b): return self.math("MAXIMUM", a, b)
    def mn(self, a, b): return self.math("MINIMUM", a, b)
    def madd(self, a, b, c): return self.math("MULTIPLY_ADD", a, b, c)

    def clamp01(self, a):
        return self.math("ADD", a, 0.0, clamp=True)

    def smoothstep(self, e0, e1, x):
        n = self.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP", clamp=True)
        self.feed(n, {"Value": x, "From Min": e0, "From Max": e1, "To Min": 0.0, "To Max": 1.0})
        return n.outputs["Result"]

    def maprange(self, x, a0, a1, b0, b1, clamp=True):
        n = self.node("ShaderNodeMapRange", interpolation_type="LINEAR", clamp=clamp)
        self.feed(n, {"Value": x, "From Min": a0, "From Max": a1, "To Min": b0, "To Max": b1})
        return n.outputs["Result"]

    def mix(self, a, b, t):
        n = self.node("ShaderNodeMix", data_type="FLOAT")
        self.feed(n, {"Factor": t, "A": a, "B": b})
        return n.outputs["Result"]

    def mixv(self, a, b, t):
        n = self.node("ShaderNodeMix", data_type="VECTOR")
        self.feed(n, {"Factor": t, 4: a, 5: b})
        return n.outputs[1]

    def mixc(self, a, b, t):
        n = self.node("ShaderNodeMix", data_type="RGBA")
        self.feed(n, {"Factor": t, 6: a, 7: b})
        return n.outputs[2]

    # --- vectors ---------------------------------------------------------------------------
    def vmath(self, op, a, b=None, scale=None):
        n = self.node("ShaderNodeVectorMath", operation=op)
        self._feed(n.inputs[0], a)
        if b is not None:
            self._feed(n.inputs[1], b)
        if scale is not None:
            self._feed(n.inputs["Scale"], scale)
        out = "Value" if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else "Vector"
        return n.outputs[out]

    def vadd(self, a, b): return self.vmath("ADD", a, b)
    def vsub(self, a, b): return self.vmath("SUBTRACT", a, b)
    def vmul(self, a, b): return self.vmath("MULTIPLY", a, b)
    def vscale(self, a, s): return self.vmath("SCALE", a, scale=s)
    def dot(self, a, b): return self.vmath("DOT_PRODUCT", a, b)
    def length(self, a): return self.vmath("LENGTH", a)
    def normalize(self, a): return self.vmath("NORMALIZE", a)

    def xyz(self, v):
        n = self.node("ShaderNodeSeparateXYZ")
        self._feed(n.inputs[0], v)
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def vec(self, x, y, z):
        n = self.node("ShaderNodeCombineXYZ")
        self.feed(n, {0: x, 1: y, 2: z})
        return n.outputs[0]

    def noise(self, vector, scale=1.0, detail=2.0, roughness=0.5, dims="3D", w=None, out="Fac"):
        n = self.node("ShaderNodeTexNoise", noise_dimensions=dims)
        self.feed(n, {"Vector": vector, "Scale": scale, "Detail": detail, "Roughness": roughness})
        if w is not None:
            self._feed(n.inputs["W"], w)
        return n.outputs[out]

    def ramp(self, fac, stops):
        n = self.node("ShaderNodeValToRGB")
        cr = n.color_ramp
        cr.interpolation = "LINEAR"
        while len(cr.elements) > len(stops):
            cr.elements.remove(cr.elements[-1])
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for el, (p, col) in zip(cr.elements, stops):
            el.position = p
            el.color = col
        self._feed(n.inputs[0], fac)
        return n.outputs[0]


def new_material(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, Tree(m.node_tree)


def principled(t, **inputs):
    n = t.node("ShaderNodeBsdfPrincipled")
    t.feed(n, inputs)
    return n


def output(t, surface=None, volume=None, displacement=None):
    o = t.node("ShaderNodeOutputMaterial")
    t.feed(o, {k: v for k, v in {"Surface": surface, "Volume": volume, "Displacement": displacement}.items()
               if v is not None})
    return o


def attr(t, name, kind="GEOMETRY"):
    n = t.node("ShaderNodeAttribute", attribute_name=name, attribute_type=kind)
    return n


def gn_group(name, inputs, outputs=(("Geometry", "NodeSocketGeometry"),)):
    """inputs: list of (name, socket_type, default). Returns (group, Tree, input node, output node)."""
    ng = bpy.data.node_groups.get(name)
    if ng:
        bpy.data.node_groups.remove(ng)
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    for nm, st, *rest in inputs:
        s = ng.interface.new_socket(name=nm, in_out="INPUT", socket_type=st)
        if rest and hasattr(s, "default_value"):
            s.default_value = rest[0]
    for nm, st in outputs:
        ng.interface.new_socket(name=nm, in_out="OUTPUT", socket_type=st)
    t = Tree(ng)
    gi = t.node("NodeGroupInput")
    go = t.node("NodeGroupOutput")
    return ng, t, gi, go


def socket_id(group, name):
    for item in group.interface.items_tree:
        if getattr(item, "in_out", None) == "INPUT" and item.name == name:
            return item.identifier
    raise KeyError(name)


def set_visibility(obj, camera=True, diffuse=True, glossy=True, transmission=True, scatter=True, shadow=True):
    obj.visible_camera = camera
    obj.visible_diffuse = diffuse
    obj.visible_glossy = glossy
    obj.visible_transmission = transmission
    obj.visible_volume_scatter = scatter
    obj.visible_shadow = shadow


def link_to_scene(obj, collection=None):
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def look_at_quat(src, dst, up=(0.0, 0.0, 1.0), axis="-Z"):
    """Quaternion that points an object's axis (-Z for cameras, +Y for the eye) at dst."""
    from mathutils import Vector
    d = (Vector(dst) - Vector(src)).normalized()
    return d.to_track_quat(axis, "Y" if axis in ("-Z", "Z") else "Z")


def deg(x):
    return math.radians(x)
