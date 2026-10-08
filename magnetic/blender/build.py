#!/usr/bin/env python3
"""Build the MAGNETIC scene from scratch and save it.

    build.py [--test out_dir width spp]      build, then render a few context stills
    build.py --save path.blend               build with the choreography baked, save
"""
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hero  # noqa: E402
import world  # noqa: E402
from common import FPS, FRAMES, look_at_quat, socket_id  # noqa: E402


def render_settings(sc, width=1920, spp=64):
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = spp
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 1
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 2
    sc.cycles.volume_bounces = 0
    sc.cycles.transparent_max_bounces = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.sample_clamp_indirect = 8.0
    sc.cycles.volume_step_rate = 4.0
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Punchy"
    sc.render.resolution_x, sc.render.resolution_y = width, width * 9 // 16
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 0, FRAMES - 1
    sc.render.use_persistent_data = True
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.5


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    coll = sc.collection
    w = bpy.data.worlds.new("World")
    world.world_background(w)
    sc.world = w
    H = hero.build_hero(coll)
    img = world.spectrogram_image()
    S = {"hero": H, "img": img}
    S["canyon"] = world.build_canyon(coll, img)
    S["rings"] = world.build_rings(coll, H["root"], img)
    S["halo"] = world.build_halo(coll, H["face"])
    S["seq"] = world.build_sequencer(coll, H["root"])
    S["dust"] = world.build_dust(coll)
    S["haze"] = world.build_haze(coll)
    S["lights"] = world.build_lights(coll, H["root"])
    S["river"] = world.build_river_lights(coll)
    world.link_lights(S["lights"], [H["fluid"], H["eye"]] + S["rings"], haze=S["haze"])
    # Lava, dust, tape print and the reflection-only panels are found by BSDF rays, not light sampling.
    for m in bpy.data.materials:
        if m.name in ("Canyon", "Dust", "Tape", "Sequencer") or m.name.startswith("SB_"):
            m.cycles.emission_sampling = "NONE"
    return sc, S


def test_cameras(sc):
    shots = {
        "wide": ((-11.0, 2.2, 2.4), (0.0, 0.0, 1.6), 24, 9.0),
        "medium": ((1.2, 5.8, 2.3), (0.0, 0.0, 1.7), 40, 5.0),
        "low": ((1.4, 4.2, 0.35), (0.0, 0.0, 2.2), 20, 4.4),
        "eye": ((0.15, 2.8, 1.82), (0.0, 0.9, 1.76), 85, 1.8),
    }
    cams = {}
    for name, (loc, tgt, lens, focus) in shots.items():
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.dof.use_dof = True
        cd.dof.focus_distance = focus
        cd.dof.aperture_fstop = 2.8
        cam = bpy.data.objects.new(name, cd)
        sc.collection.objects.link(cam)
        cam.location = loc
        cam.rotation_mode = "QUATERNION"
        cam.rotation_quaternion = look_at_quat(loc, tgt)
        cams[name] = cam
    return cams


def face_camera(S, cam_loc):
    H = S["hero"]
    root = H["root"].location
    H["face"].rotation_quaternion = look_at_quat(root, cam_loc, axis="Y")
    eye_world = Vector(root) + H["face"].rotation_quaternion @ Vector((0.0, hero.EYE_C, 0.0))
    gaze = look_at_quat(eye_world, cam_loc, axis="Y")
    H["eye"].rotation_quaternion = H["face"].rotation_quaternion.inverted() @ gaze


# ----------------------------------------------------------------------------- baking the choreography

def fcurve(id_, path, index=-1):
    """Create the F-Curve with one ordinary keyframe (so 4.5's layered action, slot and
    channelbag all exist), then hand it back for bulk filling."""
    if index >= 0:
        id_.keyframe_insert(path, index=index, frame=0)
    else:
        id_.keyframe_insert(path, frame=0)
    ad = id_.animation_data
    cb = ad.action.layers[0].strips[0].channelbag(ad.action_slot)
    return cb.fcurves.find(path, index=max(index, 0))


def bake_curve(id_, path, values, index=-1, frames=None):
    values = np.asarray(values, float)
    frames = np.arange(len(values)) if frames is None else np.asarray(frames)
    fc = fcurve(id_, path, index)
    kp = fc.keyframe_points
    kp.clear()
    kp.add(len(values))
    co = np.empty(2 * len(values), np.float32)
    co[0::2], co[1::2] = frames, values
    kp.foreach_set("co", co)
    kp.foreach_set("interpolation", np.ones(len(values), np.int32))
    fc.update()
    return fc


def drive(id_, path, ctrl, prop, index=-1, scale=None):
    fc = id_.driver_add(path, index) if index >= 0 else id_.driver_add(path)
    d = fc.driver
    d.type = "SCRIPTED" if scale is not None else "AVERAGE"
    var = d.variables.new()
    var.name = "v"
    var.type = "SINGLE_PROP"
    var.targets[0].id_type = "OBJECT"
    var.targets[0].id = ctrl
    var.targets[0].data_path = f'["{prop}"]'
    if scale is not None:
        d.expression = f"v*{scale}"
        d.use_self = False
    return fc


def bake(sc, S, C, shots):
    """All channels on one controller object; everything in the scene is driven from it."""
    import hero as hero_mod
    from common import CORAL, GOLD, MAGENTA, socket_id
    F = len(C["phase"])
    ctrl = bpy.data.objects.new("CTRL", None)
    sc.collection.objects.link(ctrl)
    scalars = ["phase", "speed", "spike_h", "punch", "punch_age", "eye_open", "melt", "tremor", "pupil", "iris_glow",
               "spin", "drop_tau", "drop_on", "recall", "halo_glow", "mandala_glow", "dust_glow", "haze", "scroll",
               "river"]
    chans = {k: C[k] for k in scalars}
    for i, ax in enumerate("xyz"):
        chans[f"grav_{ax}"] = C["gravity"][:, i]
    for i, ax in enumerate("wxyz"):
        chans[f"face_q{ax}"] = C["face_q"][:, i]
        chans[f"eye_q{ax}"] = C["eye_q"][:, i]
    for k in range(7):
        chans[f"mandala_{k}"] = C["mandala"][:, k]
    for k in range(16):
        chans[f"seq_{k}"] = C["seq"][:, k]
    for k, turns in enumerate((1, -2, 3)):
        chans[f"ring_{k}"] = 2 * np.pi * turns * C["phase"]
    chans["mandala_spin"] = -2 * np.pi * C["phase"]
    for name, vals in chans.items():
        ctrl[name] = float(vals[0])
        bake_curve(ctrl, f'["{name}"]', vals)

    H = S["hero"]
    fl = H["fluid"]
    ng = fl.modifiers["Fluid"].node_group
    for sock, prop in (("Spike Height", "spike_h"), ("Punch", "punch"), ("Punch Age", "punch_age"), ("Eye Open", "eye_open"),
                       ("Spin", "spin"), ("Phase", "phase"), ("Melt", "melt"), ("Tremor", "tremor")):
        drive(fl, f'modifiers["Fluid"]["{socket_id(ng, sock)}"]', ctrl, prop)
    for i, ax in enumerate("xyz"):
        drive(fl, f'modifiers["Fluid"]["{socket_id(ng, "Gravity")}"]', ctrl, f"grav_{ax}", index=i)
    drive(fl, "rotation_euler", ctrl, "spin", index=1)
    for i, ax in enumerate("wxyz"):
        drive(H["face"], "rotation_quaternion", ctrl, f"face_q{ax}", index=i)
        drive(H["eye"], "rotation_quaternion", ctrl, f"eye_q{ax}", index=i)
    eye_nt = bpy.data.materials["ThirdEye"].node_tree
    drive(eye_nt, 'nodes["pupil"].outputs[0].default_value', ctrl, "pupil")
    drive(eye_nt, 'nodes["iris_glow"].outputs[0].default_value', ctrl, "iris_glow")

    drive(S["canyon"], "location", ctrl, "scroll", index=0, scale=-world.CANYON_L)
    du = S["dust"]
    drive(du, f'modifiers["Dust"]["{socket_id(du.modifiers["Dust"].node_group, "Phase")}"]', ctrl, "phase")
    drive(bpy.data.materials["Dust"].node_tree, 'nodes["dust_glow"].outputs[0].default_value', ctrl, "dust_glow")
    drive(bpy.data.materials["Haze"].node_tree, 'nodes["haze"].outputs[0].default_value', ctrl, "haze")
    for ob in S["river"]:
        drive(ob.data, "energy", ctrl, "river", scale=world.RIVER_POWER)
    drive(bpy.data.materials["Halo"].node_tree, 'nodes["halo_glow"].outputs[0].default_value', ctrl, "halo_glow")
    drive(bpy.data.materials["Mandala"].node_tree, 'nodes["mandala_glow"].outputs[0].default_value', ctrl, "mandala_glow")
    for k, seed in enumerate(S["halo"]["seeds"]):
        drive(seed.data, "bevel_factor_end", ctrl, f"mandala_{k}")
    drive(S["halo"]["spinner"], "rotation_euler", ctrl, "mandala_spin", index=2)
    for k, ring in enumerate(S["rings"]):
        drive(ring, "rotation_euler", ctrl, f"ring_{k}", index=2)
    palette = [GOLD, MAGENTA, CORAL, MAGENTA]
    for k, panel in enumerate(S["seq"]):
        col = palette[k % 4]
        for i in range(3):
            drive(panel, "color", ctrl, f"seq_{k}", index=i, scale=round(col[i], 4))

    dr = hero_mod.build_droplets(sc.collection, H, C["face_q"], C["spin"], shots["stop_frame"])
    dng = dr.modifiers["Droplets"].node_group
    for sock, prop in (("Tau", "drop_tau"), ("Recall", "recall"), ("On", "drop_on")):
        drive(dr, f'modifiers["Droplets"]["{socket_id(dng, sock)}"]', ctrl, prop)
    S["droplets"] = dr
    for cname in ("SoftboxLight", "KeyLight"):
        bpy.data.collections[cname].objects.link(dr)

    # One camera per shot, keyed over its shot (plus a frame either side), switched by markers.
    from choreo import quat_look
    cams = []
    for s in shots["shots"]:
        cd = bpy.data.cameras.new(f"CAM_{s['name']}")
        cd.dof.use_dof = True
        cd.sensor_width = 36.0
        cam = bpy.data.objects.new(f"CAM_{s['name']}", cd)
        sc.collection.objects.link(cam)
        cam.rotation_mode = "QUATERNION"
        cam.cycles.use_motion_blur = False
        fr = np.arange(max(s["f0"] - 1, 0), min(s["f1"] + 1, F))
        loc, tgt = C["cam_loc"][fr], C["cam_tgt"][fr]
        quats = np.array([quat_look(t - l, axis="-Z") for l, t in zip(loc, tgt)])
        for i in range(3):
            bake_curve(cam, "location", loc[:, i], index=i, frames=fr)
        for i in range(4):
            bake_curve(cam, "rotation_quaternion", quats[:, i], index=i, frames=fr)
        bake_curve(cd, "lens", C["lens"][fr], frames=fr)
        bake_curve(cd, "dof.focus_distance", C["focus"][fr], frames=fr)
        bake_curve(cd, "dof.aperture_fstop", C["fstop"][fr], frames=fr)
        m = sc.timeline_markers.new(s["name"], frame=s["f0"])
        m.camera = cam
        cams.append(cam)
    sc.camera = cams[0]
    return ctrl, cams


def check_clearance(S, C, margin=0.3):
    """Ray-cast the static canyon under every camera position on every frame (the canyon slides
    by -scroll * L): no camera may sit inside the terrain."""
    from mathutils.bvhtree import BVHTree
    cy = S["canyon"]
    me = cy.data
    tree = BVHTree.FromPolygons([v.co[:] for v in me.vertices], [p.vertices[:] for p in me.polygons])
    bad = []
    for f, (loc, sc_) in enumerate(zip(C["cam_loc"], C["scroll"])):
        x_local = loc[0] + sc_ * world.CANYON_L
        hit = tree.ray_cast(Vector((x_local, loc[1], 60.0)), Vector((0.0, 0.0, -1.0)))
        if hit[0] is not None and loc[2] < hit[0].z + margin:
            bad.append((f, round(float(loc[2]), 2), round(float(hit[0].z), 2)))
    print(f"camera clearance: {len(bad)} frames too close to the terrain" + (f": {bad[:12]}" if bad else ""))
    return bad


def build_full(width=1920, spp=64):
    import json
    from common import ANALYSIS
    sc, S = build_scene()
    render_settings(sc, width, spp)
    C = dict(np.load(ANALYSIS / "choreo.npz"))
    shots = json.loads((ANALYSIS / "shots.json").read_text())
    ctrl, cams = bake(sc, S, C, shots)
    for ob in bpy.data.objects:                         # motion blur on the hero only
        ob.cycles.use_motion_blur = ob.name in ("FLUID", "EYEBALL", "DROPLETS")
    check_clearance(S, C)
    return sc, S, C, shots


def main():
    args = sys.argv[1:]
    if args and args[0] == "--save":
        t0 = time.time()
        sc, S, C, shots = build_full()
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=args[1], compress=False)
        print(f"saved {args[1]} in {time.time() - t0:.1f} s")
        return
    if args and args[0] == "--test":
        out = Path(args[1])
        out.mkdir(parents=True, exist_ok=True)
        width = int(args[2]) if len(args) > 2 else 640
        spp = int(args[3]) if len(args) > 3 else 32
        only = args[4].split(",") if len(args) > 4 else None
        t0 = time.time()
        sc, S = build_scene()
        render_settings(sc, width, spp)
        mod = S["hero"]["fluid"].modifiers["Fluid"]
        mod[socket_id(mod.node_group, "Spike Height")] = 0.26
        S["canyon"].location.x = -0.23 * world.CANYON_L
        print(f"built in {time.time() - t0:.1f} s")
        for name, cam in test_cameras(sc).items():
            if only and name not in only:
                continue
            sc.camera = cam
            face_camera(S, cam.location)
            sc.render.filepath = str(out / f"{name}.png")
            t1 = time.time()
            bpy.ops.render.render(write_still=True)
            print(f"{name}: {time.time() - t1:.1f} s")


if __name__ == "__main__":
    main()
