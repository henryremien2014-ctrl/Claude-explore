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
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 4
    sc.cycles.transmission_bounces = 2
    sc.cycles.volume_bounces = 1
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
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
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
    world.link_lights(S["lights"], [H["fluid"], H["eye"], S["haze"]] + S["rings"])
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


def main():
    args = sys.argv[1:]
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
        S["canyon"].modifiers["Canyon"][socket_id(S["canyon"].modifiers["Canyon"].node_group, "Scroll")] = 0.23
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
