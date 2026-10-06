#!/usr/bin/env python3
"""How big will the text be on a phone? Prints the on-screen size (in points)
of each text size used in the video and saves a phone-width preview to look at.

Examples:
  phone_check.py out/stills/final.png --size label=68 --size title=76 --size footer=52
  phone_check.py still.png --video-width 1080 --video-height 1080 --size caption=64

Sizes are text sizes in px in the full-resolution frame (a CSS font-size is
close enough). Pass text only; line widths and icon sizes aren't judged.
A phone is taken as 390 x 844 pt (a common modern phone):
  upright   - video fitted into 390 x 844 (a 16:9 video plays inline, full width)
  sideways  - video fitted into 844 x 390 (full screen, landscape)
Aim for 12 pt or more upright for anything the viewer must read; under 9 pt is
too small. The preview is the still scaled to 390 px wide, at 1x, so it shows
the worst case (no retina sharpening). Needs Pillow.
"""
import argparse
import os

from PIL import Image

PHONE_W, PHONE_H = 390, 844


def fit(vw, vh, bw, bh):
    return min(bw / vw, bh / vh)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("still", help="a full-resolution frame (PNG)")
    ap.add_argument("--size", action="append", default=[], help="name=px, repeatable")
    ap.add_argument("--video-width", type=int, help="defaults to the still's width")
    ap.add_argument("--video-height", type=int, help="defaults to the still's height")
    ap.add_argument("--out", help="preview path (default: <still>-phone-390px.png)")
    a = ap.parse_args()

    im = Image.open(a.still).convert("RGB")
    vw = a.video_width or im.width
    vh = a.video_height or im.height
    up = fit(vw, vh, PHONE_W, PHONE_H)
    side = fit(vw, vh, PHONE_H, PHONE_W)

    out = a.out or os.path.splitext(a.still)[0] + "-phone-390px.png"
    preview_w = round(vw * up)
    im.resize((preview_w, round(im.height * preview_w / im.width)), Image.LANCZOS).save(out)

    print(f"video {vw}x{vh}: upright scale {up:.3f} (shown {round(vw * up)}x{round(vh * up)} pt), "
          f"sideways scale {side:.3f}")
    worst = None
    for item in a.size:
        name, px = item.split("=")
        px = float(px)
        pt_up, pt_side = px * up, px * side
        verdict = "ok" if pt_up >= 12 else ("small" if pt_up >= 9 else "TOO SMALL")
        worst = pt_up if worst is None else min(worst, pt_up)
        print(f"  {name:12s} {px:5.0f} px -> {pt_up:5.1f} pt upright, {pt_side:5.1f} pt sideways  [{verdict}]")
    print("preview ->", out)
    if worst is not None and worst < 9:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
