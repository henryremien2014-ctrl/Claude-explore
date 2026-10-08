#!/usr/bin/env python3
"""Contact sheet: tile rendered frames with their frame number and shot name.

    sheet.py frames_dir out.png [cols] [thumb_width]
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    tw = int(sys.argv[4]) if len(sys.argv) > 4 else 320
    shots = json.loads((ROOT / "analysis" / "out" / "shots.json").read_text())["shots"]
    name_of = lambda f: next(s["name"] for s in shots if s["f0"] <= f < s["f1"])
    files = sorted(src.glob("f*.png"))
    th = tw * 9 // 16
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 16)), (12, 12, 12))
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 11)
    d = ImageDraw.Draw(sheet)
    for i, p in enumerate(files):
        f = int(p.stem[1:])
        im = Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS)
        x, y = (i % cols) * tw, (i // cols) * (th + 16)
        sheet.paste(im, (x, y + 16))
        d.text((x + 4, y + 2), f"{f:03d} {name_of(f)}", fill=(220, 210, 200), font=font)
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
