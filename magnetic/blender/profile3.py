#!/usr/bin/env python3
"""Shading-cost experiments: what the light tent's light sampling and the fine bumps cost.

    profile3.py scene.blend out_dir frames width spp
"""
import sys
import time
from pathlib import Path

import bpy


def softbox_sampling(mode):
    for m in bpy.data.materials:
        if m.name.startswith("SB_"):
            m.cycles.emission_sampling = mode


def bump(mat, on):
    nt = bpy.data.materials[mat].node_tree
    for n in nt.nodes:
        if n.type == "BUMP":
            n.mute = not on


def main():
    blend, out, frames, width, spp = sys.argv[1], Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = width, width * 9 // 16
    sc.cycles.samples = spp
    sc.render.use_persistent_data = False
    sc.render.image_settings.file_format = "PNG"
    tests = [
        ("baseline", lambda: None, lambda: None),
        ("softbox_nee_off", lambda: softbox_sampling("NONE"), lambda: softbox_sampling("AUTO")),
        ("fluid_bump_off", lambda: bump("Ferrofluid", False), lambda: bump("Ferrofluid", True)),
        ("canyon_bump_off", lambda: bump("Canyon", False), lambda: bump("Canyon", True)),
        ("all_three", lambda: (softbox_sampling("NONE"), bump("Ferrofluid", False), bump("Canyon", False)),
         lambda: (softbox_sampling("AUTO"), bump("Ferrofluid", True), bump("Canyon", True))),
    ]
    for f in map(int, frames.split(",")):
        sc.frame_set(f)
        for name, on, off in tests:
            on()
            sc.render.filepath = str(out / f"f{f:04d}_{name}.png")
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            print(f"PROFILE3 frame {f} {name}: {time.time() - t0:.1f} s", flush=True)
            off()


if __name__ == "__main__":
    main()
