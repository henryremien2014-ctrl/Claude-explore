#!/usr/bin/env python3
"""Pull exact frames out of a rendered video as PNGs (to look at them), plus an
optional labelled contact sheet.

Examples:
  extract_stills.py out/video.mp4 --times 0 15 29 --out out/stills
  extract_stills.py out/video.mp4 --frames 80 206 332 458 599 --sheet out/stills/sheet.png
  extract_stills.py out/video.mp4 --times 29.99            # clamps to the last frame
  extract_stills.py out/video.mp4 --times 0 15 29 --clean  # delete older <prefix>-*.png first

Times are converted to frame numbers with the video's frame rate, then frames are
selected by index in one ffmpeg pass, so a still at 15 s is exactly frame 450 at
30 fps. Files are named <prefix>-<time>s-f<frame>.png. Needs ffmpeg/ffprobe;
the contact sheet needs Pillow (pip install pillow).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction


def video_facts(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=avg_frame_rate,r_frame_rate,nb_read_frames,width,height", "-of", "json", path],
        capture_output=True, text=True, check=True,
    )
    s = json.loads(out.stdout)["streams"][0]
    fps = float(Fraction(s.get("avg_frame_rate") or s["r_frame_rate"]))
    return fps, int(s["nb_read_frames"]), s["width"], s["height"]


def contact_sheet(paths, labels, out, cols=3, thumb_w=640):
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert("RGB") for p in paths]
    w0, h0 = ims[0].size
    th = round(h0 * thumb_w / w0)
    rows = (len(ims) + cols - 1) // cols
    pad = 28
    sheet = Image.new("RGB", (cols * thumb_w, rows * (th + pad)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (im, label) in enumerate(zip(ims, labels)):
        x, y = (i % cols) * thumb_w, (i // cols) * (th + pad)
        sheet.paste(im.resize((thumb_w, th)), (x, y + pad))
        draw.text((x + 8, y + 8), label, fill="black")
    sheet.save(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--times", type=float, nargs="+", help="seconds")
    g.add_argument("--frames", type=int, nargs="+", help="0-based frame numbers")
    ap.add_argument("--out", default="out/stills")
    ap.add_argument("--prefix", default="still")
    ap.add_argument("--sheet", help="also write a contact sheet to this path")
    ap.add_argument("--clean", action="store_true",
                    help="first delete earlier <prefix>-*.png stills in --out, so old renders can't mix in")
    a = ap.parse_args()

    fps, total, w, h = video_facts(a.video)
    if a.times is not None:
        wanted = [min(total - 1, max(0, round(t * fps))) for t in a.times]
    else:
        wanted = [min(total - 1, max(0, f)) for f in a.frames]
    unique = sorted(set(wanted))
    os.makedirs(a.out, exist_ok=True)
    if a.clean:
        for old in os.listdir(a.out):
            if old.startswith(a.prefix + "-") and old.endswith(".png"):
                os.remove(os.path.join(a.out, old))

    with tempfile.TemporaryDirectory() as tmp:
        expr = "+".join(f"eq(n\\,{f})" for f in unique)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"select='{expr}'", "-fps_mode", "passthrough",
             os.path.join(tmp, "%04d.png")],
            check=True,
        )
        got = sorted(os.listdir(tmp))
        if len(got) != len(unique):
            sys.exit(f"Expected {len(unique)} frames, ffmpeg wrote {len(got)}.")
        written = {}
        for f, name in zip(unique, got):
            dest = os.path.join(a.out, f"{a.prefix}-{f / fps:.2f}s-f{f}.png")
            shutil.move(os.path.join(tmp, name), dest)
            written[f] = dest

    print(f"{a.video}: {w}x{h}, {fps:g} fps, {total} frames")
    for f in wanted:
        print(f"frame {f:5d}  t={f / fps:7.3f}s  -> {written[f]}")
    if a.sheet:
        try:
            contact_sheet([written[f] for f in unique], [f"frame {f}  ({f / fps:.2f} s)" for f in unique], a.sheet)
            print("contact sheet ->", a.sheet)
        except ImportError:
            print("Pillow not installed; skipped the contact sheet (pip install pillow).")


if __name__ == "__main__":
    main()
