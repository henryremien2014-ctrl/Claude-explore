#!/usr/bin/env python3
"""Which feature costs what: render the same frames with one feature off at a time.

    profile2.py scene.blend out_dir frames width spp
"""
import sys
import time
from pathlib import Path

import bpy


def variants(sc):
    haze = bpy.data.objects["HAZE"]
    yield "baseline", lambda: None, lambda: None
    yield "no_haze", lambda: setattr(haze, "hide_render", True), lambda: setattr(haze, "hide_render", False)
    yield "no_mblur", lambda: setattr(sc.render, "use_motion_blur", False), lambda: setattr(sc.render, "use_motion_blur", True)

    def dof(on):
        for cam in bpy.data.cameras:
            cam.dof.use_dof = on
    yield "no_dof", lambda: dof(False), lambda: dof(True)
    yield "adaptive_0.05", lambda: setattr(sc.cycles, "adaptive_threshold", 0.05), \
        lambda: setattr(sc.cycles, "adaptive_threshold", 0.02)

    def bounces(n):
        sc.cycles.max_bounces, sc.cycles.glossy_bounces = n, min(n, 3)
    yield "bounces_2", lambda: bounces(2), lambda: bounces(4)


def main():
    blend, out, frames, width, spp = sys.argv[1], Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = width, width * 9 // 16
    sc.cycles.samples = spp
    sc.render.use_persistent_data = False
    sc.render.image_settings.file_format = "PNG"
    for f in map(int, frames.split(",")):
        sc.frame_set(f)
        for name, on, off in variants(sc):
            on()
            sc.render.filepath = str(out / f"f{f:04d}_{name}.png")
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            print(f"PROFILE2 frame {f} {name}: {time.time() - t0:.1f} s", flush=True)
            off()


if __name__ == "__main__":
    main()
