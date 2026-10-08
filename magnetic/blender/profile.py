#!/usr/bin/env python3
"""Profile render cost: per-frame overhead (1 spp) against sampling cost, at final resolution.

    profile.py scene.blend out_dir frames spp_list [width]
"""
import sys
import time
from pathlib import Path

import bpy


def main():
    blend, out, frames, spps = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4]
    width = int(sys.argv[5]) if len(sys.argv) > 5 else 1920
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = width, width * 9 // 16
    sc.render.image_settings.file_format = "PNG"
    sc.render.use_persistent_data = True
    for f in map(int, frames.split(",")):
        for spp in map(int, spps.split(",")):
            sc.cycles.samples = spp
            sc.frame_set(f)
            sc.render.filepath = str(out / f"f{f:04d}_{spp}spp.png")
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            print(f"PROFILE frame {f} {spp} spp {width}px: {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
