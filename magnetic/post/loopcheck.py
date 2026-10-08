#!/usr/bin/env python3
"""Prove the loop seam: the last-to-first frame difference must be smaller than a normal
frame-to-frame step.

    loopcheck.py frames_dir [report.png]          (frames p0000.png .. p0623.png)

Difference = mean absolute difference of the frames in linear-ish 0..1 RGB, measured on the
picture (the 1-pixel border and the readout corner are included; nothing is masked).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def load(p, scale=0.5):
    im = Image.open(p).convert("RGB")
    if scale != 1.0:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.BILINEAR)
    return np.asarray(im, np.float32) / 255.0


def main():
    d = Path(sys.argv[1])
    files = sorted(d.glob("p*.png"))
    n = len(files)
    prev = load(files[0])
    first = prev
    steps = []
    for p in files[1:]:
        cur = load(p)
        steps.append(float(np.mean(np.abs(cur - prev))))
        prev = cur
    seam = float(np.mean(np.abs(first - prev)))                  # last -> first
    steps = np.array(steps)
    # A "normal" step: continuous motion inside a shot, excluding cuts and black/held frames.
    normal = steps[(steps > 1e-4)]
    res = {"frames": n, "seam_last_to_first": seam, "median_step": float(np.median(normal)),
           "p10_step": float(np.percentile(normal, 10)), "mean_step": float(np.mean(normal)),
           "steps_last_12": [round(x, 5) for x in steps[-12:]], "steps_first_12": [round(x, 5) for x in steps[:12]]}
    res["seam_smaller_than_median_step"] = bool(seam < res["median_step"])
    # the seam must not stand out from the motion on either side of it
    res["step_into_seam"], res["step_out_of_seam"] = float(steps[-1]), float(steps[0])
    res["seam_smaller_than_neighbour_steps"] = bool(seam < min(steps[-1], steps[0]))
    print(json.dumps(res, indent=1))
    (d / "loopcheck.json").write_text(json.dumps(res, indent=1))
    if len(sys.argv) > 2:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(14, 3.6))
        ax.plot(np.arange(1, n), steps, color="#2b2b2b", lw=0.9)
        ax.axhline(res["median_step"], color="#9a9890", lw=0.8, ls="--")
        ax.plot([n], [seam], "o", color="#b5367a", ms=7)
        ax.text(n - 8, seam, f"seam {seam:.4f}", ha="right", va="bottom", color="#b5367a", fontsize=9)
        ax.text(5, res["median_step"], f"median step {res['median_step']:.4f}", va="bottom", color="#52514e", fontsize=9)
        ax.set_xlabel("frame")
        ax.set_ylabel("mean |difference|")
        ax.set_title("Frame-to-frame difference; the dot is the loop seam (frame 623 -> frame 0)", loc="left")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        plt.tight_layout()
        plt.savefig(sys.argv[2], dpi=110)


if __name__ == "__main__":
    main()
