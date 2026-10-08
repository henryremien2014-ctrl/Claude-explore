#!/usr/bin/env python3
"""Look development for the hero in a stand-in environment.

    lookdev.py out_dir [width] [samples] [eye_open] [spike_h]
"""
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORAL, GOLD, MAGENTA, ORANGE, VIOLET, look_at_quat, new_material, output, socket_id, set_visibility  # noqa: E402
import hero  # noqa: E402


def emissive(name, color, strength):
    m, t = new_material(name)
    e = t.node("ShaderNodeEmission")
    t.feed(e, {"Color": color, "Strength": strength})
    output(t, surface=e)
    return m


def softbox_mat(name, color, strength):
    """Emission that falls off from the centre: soft-edged reflections, no hard rectangles."""
    m, t = new_material(name)
    uv = t.node("ShaderNodeTexCoord").outputs["UV"]
    d = t.length(t.vsub(t.vscale(uv, 2.0), (1.0, 1.0, 0.0)))
    fall = t.pow(t.clamp01(t.sub(1.0, d)), 1.6)
    e = t.node("ShaderNodeEmission")
    t.feed(e, {"Color": color, "Strength": t.mul(fall, strength)})
    output(t, surface=e)
    return m


def plane(name, size, loc, rot, mat, coll):
    me = bpy.data.meshes.new(name)
    sx, sy = size
    me.from_pydata([(-sx / 2, -sy / 2, 0), (sx / 2, -sy / 2, 0), (sx / 2, sy / 2, 0), (-sx / 2, sy / 2, 0)], [], [(0, 1, 2, 3)])
    uvl = me.uv_layers.new()
    for i, uv in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uvl.data[i].uv = uv
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.location, ob.rotation_euler = loc, rot
    me.materials.append(mat)
    return ob


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 640
    spp = int(sys.argv[3]) if len(sys.argv) > 3 else 48
    eye_open = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    spike_h = float(sys.argv[5]) if len(sys.argv) > 5 else 0.28

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    coll = sc.collection
    t0 = time.time()
    H = hero.build_hero(coll)
    print(f"hero built in {time.time() - t0:.1f} s, {len(H['sites'])} spike sites, "
          f"{len(H['fluid'].data.vertices)} verts")
    mod = H["fluid"].modifiers["Fluid"]
    ng = mod.node_group
    mod[socket_id(ng, "Spike Height")] = spike_h
    mod[socket_id(ng, "Eye Open")] = eye_open
    mod[socket_id(ng, "Spin")] = 0.3

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    sc.world = world

    plane("RIVER", (9, 3.2), (0, 0, -0.1), (0, 0, 0), emissive("river", ORANGE, 9.0), coll)
    for name, col, loc, size, power in (("SB_TOP", GOLD, (0.5, -1.0, 7.5), (5, 5), 9.0),
                                        ("SB_LEFT", VIOLET, (-5.0, 0.5, 2.6), (3, 6), 10.0),
                                        ("SB_RIGHT", MAGENTA, (5.0, -0.5, 2.2), (3, 6), 10.0),
                                        ("SB_FRONT", CORAL, (0.0, 6.5, 0.6), (6, 1.5), 4.0)):
        card = plane(name, size, loc, (0, 0, 0), softbox_mat(name, col, power), coll)
        card.rotation_euler = look_at_quat(loc, (0, 0, 1.75), axis="Z").to_euler()
        set_visibility(card, camera=False, diffuse=False, shadow=False, scatter=False, transmission=False)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.62, minor_radius=0.014, major_segments=192, minor_segments=12,
                                     location=(0, -0.9, 1.75), rotation=(math.pi / 2, 0, 0))
    halo = bpy.context.active_object
    halo.data.materials.append(emissive("halo", MAGENTA, 25.0))
    key = bpy.data.lights.new("KEY", "AREA")
    key.shape, key.size, key.energy, key.color = "DISK", 3.0, 700.0, GOLD[:3]
    kob = bpy.data.objects.new("KEY", key)
    coll.objects.link(kob)
    kob.location = (-1.5, -3.0, 6.0)
    kob.rotation_mode = "QUATERNION"
    kob.rotation_quaternion = look_at_quat(kob.location, (0, 0, 1.75))

    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = spp
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 6
    sc.cycles.glossy_bounces = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Punchy"
    sc.render.resolution_x, sc.render.resolution_y = width, width * 9 // 16
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"

    shots = {
        "front": ((0.4, 5.6, 2.2), (0, 0, 1.65), 45),
        "eye": ((0.05, 2.25, 1.80), (0, 0.9, 1.76), 85),
        "side": ((4.2, 3.0, 2.9), (0, 0, 1.6), 40),
    }
    for name, (loc, tgt, lens) in shots.items():
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.dof.use_dof = True
        cd.dof.focus_distance = (Vector(loc) - Vector((0, 1.05, 1.75))).length if name == "eye" else \
            (Vector(loc) - Vector((0, 0.9, 1.75))).length
        cd.dof.aperture_fstop = 2.8 if name == "eye" else 4.0
        cam = bpy.data.objects.new(name, cd)
        coll.objects.link(cam)
        cam.location = loc
        cam.rotation_mode = "QUATERNION"
        cam.rotation_quaternion = look_at_quat(loc, tgt)
        sc.camera = cam
        # The eye tracks the camera.
        eye = H["eye"]
        world_eye = Vector((0, hero.EYE_C, 1.75))
        eye.rotation_quaternion = look_at_quat(world_eye, loc, axis="Y")
        sc.render.filepath = str(out / f"{name}.png")
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"{name}: {time.time() - t1:.1f} s")


if __name__ == "__main__":
    main()
