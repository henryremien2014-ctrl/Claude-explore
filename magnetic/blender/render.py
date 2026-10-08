#!/usr/bin/env python3
"""Render frames of the saved scene, headless and resumable (existing frames are skipped).

    render.py scene.blend out_dir FRAMES [--width W] [--spp N] [--exr] [--log file]

FRAMES: "0-623", "0,12,24", "@frameplan" (the unique frames the post needs) or
"@shots" (a few frames from every shot, for contact sheets).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]


def parse_frames(spec, n=624):
    if spec == "@frameplan":
        return json.loads((ROOT / "analysis" / "out" / "frameplan.json").read_text())["render"]
    if spec.startswith("@shots"):
        per = int(spec.split(":")[1]) if ":" in spec else 3
        shots = json.loads((ROOT / "analysis" / "out" / "shots.json").read_text())["shots"]
        out = []
        for s in shots:
            span = s["f1"] - s["f0"]
            out += [s["f0"] + int(round((k + 0.5) * span / per)) for k in range(per)]
        return sorted(set(out))
    frames = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            frames += list(range(int(a), int(b) + 1))
        elif part:
            frames.append(int(part))
    return frames


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("frames")
    ap.add_argument("--width", type=int, default=480)
    ap.add_argument("--spp", type=int, default=16)
    ap.add_argument("--exr", action="store_true")
    ap.add_argument("--log")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = a.width, a.width * 9 // 16
    sc.render.resolution_percentage = 100
    sc.cycles.samples = a.spp
    sc.render.use_persistent_data = True
    if a.exr:
        sc.render.image_settings.file_format = "OPEN_EXR"
        sc.render.image_settings.color_depth = "16"
        sc.render.image_settings.exr_codec = "DWAA"
        ext = "exr"
    else:
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_depth = "8"
        ext = "png"
    import numpy as np
    mblur = np.load(ROOT / "analysis" / "out" / "choreo.npz")["mblur"]
    log = open(a.log, "a") if a.log else None
    todo = [f for f in parse_frames(a.frames) if not (out / f"f{f:04d}.{ext}").exists()]
    print(f"{len(todo)} frames to render at {sc.render.resolution_x}x{sc.render.resolution_y}, {a.spp} spp")
    for f in todo:
        t0 = time.time()
        sc.render.use_motion_blur = bool(mblur[f])      # motion blur only where the hero visibly moves
        sc.frame_set(f)
        tmp = out / f".f{f:04d}.{ext}"
        sc.render.filepath = str(tmp)
        bpy.ops.render.render(write_still=True)
        tmp.rename(out / f"f{f:04d}.{ext}")       # a frame exists only once it is complete
        msg = f"frame {f} {time.time() - t0:.1f} s"
        print(msg, flush=True)
        if log:
            log.write(msg + "\n")
            log.flush()


if __name__ == "__main__":
    main()
